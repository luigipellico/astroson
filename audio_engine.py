import os
try:
    import fluidsynth
    FLUIDSYNTH_AVAILABLE = True
except ImportError:
    FLUIDSYNTH_AVAILABLE = False

try:
    from sf2utils.sf2file import Sf2File
    SF2UTILS_AVAILABLE = True
except ImportError:
    SF2UTILS_AVAILABLE = False

class AudioEngine:
    """Motore audio professionale a 3 canali basato su FluidSynth e SoundFont (.sf2)"""
    def __init__(self, soundfont_path=None):
        self.available = FLUIDSYNTH_AVAILABLE
        self.synth = None
        self.audio_driver = None
        self.sfid = -1
        self.is_initialized = False
        self.current_sf2_path = None

        if not self.available:
            print("[ERRORE] pyfluidsynth non è installato. Esegui: pip install pyfluidsynth")
            return

        try:
            self.synth = fluidsynth.Synth()
            self.synth.start()
            
            # ATTENZIONE: Avvio del driver audio fisico per inviare il suono alle casse
            try:
                self.audio_driver = fluidsynth.AudioDriver(self.synth)
            except Exception as e:
                print(f"[ATTENZIONE] Impossibile avviare AudioDriver nativo automaticamente: {e}")

            default_sf = soundfont_path if soundfont_path else "soundfonts/FluidR3_GM.sf2"
            paths_to_check = [
                default_sf,
                "soundfonts/FluidR3_GM.sf2",
                "soundfonts/GeneralUser.sf2",
                "/opt/homebrew/share/soundfonts/FluidR3_GM.sf2",
                "/usr/local/share/soundfonts/FluidR3_GM.sf2"
            ]
            
            loaded = False
            for path in paths_to_check:
                if os.path.exists(path):
                    if self.load_soundfont(path):
                        loaded = True
                        break
            
            if not loaded:
                print("[ATTENZIONE] Nessun file SoundFont .sf2 trovato nella cartella soundfonts/!")
        except Exception as e:
            print(f"[ERRORE] Inizializzazione FluidSynth fallita: {e}")

    @staticmethod
    def get_available_soundfonts():
        sf2_dir = "soundfonts"
        soundfonts = []
        if os.path.exists(sf2_dir):
            for f in os.listdir(sf2_dir):
                if f.lower().endswith('.sf2'):
                    soundfonts.append(f)
        return soundfonts

    @staticmethod
    def get_soundfont_presets(sf2_filename):
        if not SF2UTILS_AVAILABLE:
            return [{'name': 'Default Preset', 'bank': 0, 'preset': 0}]
        
        sf2_path = os.path.join("soundfonts", sf2_filename)
        presets = []
        if os.path.exists(sf2_path):
            try:
                with open(sf2_path, 'rb') as sf2_file:
                    sf2 = Sf2File(sf2_file)
                    for p in sf2.presets:
                        if p.name != 'EOP':
                            presets.append({'name': p.name, 'bank': p.bank, 'preset': p.preset})
            except Exception as e:
                print(f"[ERRORE] Lettura preset da {sf2_filename}: {e}")
        
        if not presets:
            presets.append({'name': 'Default (Bank 0, Program 0)', 'bank': 0, 'preset': 0})
        return presets

    def load_soundfont(self, path):
        if self.synth and os.path.exists(path):
            try:
                self.sfid = self.synth.sfload(path)
                self.current_sf2_path = path
                self.synth.program_select(0, self.sfid, 0, 0)   # Canale 0: Lead (Picchi)
                self.synth.program_select(1, self.sfid, 0, 89)  # Canale 1: Pad (Sfondo)
                self.synth.program_select(2, self.sfid, 0, 48)  # Canale 2: Accordi (Colori)
                
                # Inizializzazione volumi MIDI (CC 7) al 100% per tutti e 3 i canali
                for ch in range(3):
                    self.synth.cc(ch, 7, 127)
                    
                self.is_initialized = True
                print(f"[OPERATIONAL] SoundFont caricato: {path}")
                return True
            except Exception as e:
                print(f"[ERRORE] Caricamento SoundFont fallito: {e}")
        return False

    def set_channel_instrument(self, channel, bank, preset_num, sf2_filename=None):
        if self.synth and self.is_initialized:
            try:
                if sf2_filename:
                    sf2_path = os.path.join("soundfonts", sf2_filename)
                    if os.path.exists(sf2_path) and sf2_path != self.current_sf2_path:
                        self.sfid = self.synth.sfload(sf2_path)
                        self.current_sf2_path = sf2_path
                self.synth.program_select(channel, self.sfid, bank, preset_num)
            except Exception as e:
                print(f"[ERRORE] Assegnazione strumento canale {channel}: {e}")

    def set_channel_volume(self, channel, volume_0_100):
        if self.synth and self.is_initialized:
            try:
                midi_vol = int((volume_0_100 / 100.0) * 127)
                self.synth.cc(channel, 7, midi_vol)
            except Exception:
                pass

    def note_on(self, channel, key, velocity):
        if self.synth and self.is_initialized:
            try:
                self.synth.noteon(channel, key, velocity)
            except Exception:
                pass

    def note_off(self, channel, key):
        if self.synth and self.is_initialized:
            try:
                self.synth.noteoff(channel, key)
            except Exception:
                pass

    def close(self):
        if self.audio_driver:
            try:
                del self.audio_driver
            except Exception:
                pass
        if self.synth:
            try:
                self.synth.delete()
            except Exception:
                pass