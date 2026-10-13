import os
import sys
import cv2
import numpy as np
from PyQt6.QtCore import Qt, pyqtSignal, QPointF, QTimer
from PyQt6.QtGui import QFont, QColor, QPalette, QPixmap, QPainter, QPen, QImage
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QComboBox, QSlider, QGroupBox, 
    QFileDialog, QTextEdit, QSizePolicy, QFrame, QApplication, QGridLayout
)
from scan_modes import ScanEngine
from hand_tracking import HandTrackingEngine
from audio_engine import AudioEngine

class ImageViewerWidget(QWidget):
    """Widget per l'anteprima con linea di scansione e cerchietti multipli localizzati sulle stelle"""
    position_clicked = pyqtSignal(int, int)

    def __init__(self, placeholder_text="Anteprima Immagine", interactive=False):
        super().__init__()
        self.placeholder_text = placeholder_text
        self.original_pixmap = QPixmap()
        self.scan_item = None  
        self.star_poses = []   # Lista di coordinate (x, y, intensity) delle stelle sulla linea
        self.scan_mode = "horizontal"
        self.interactive = interactive
        self.current_intensity = 128
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(220, 160)

    def set_image(self, path):
        if path and os.path.exists(path):
            self.original_pixmap = QPixmap(path)
            self.scan_item = None
            self.star_poses = []
            self.update()
            if self.isVisible():
                self.repaint()

    def set_frame(self, cv_frame):
        if cv_frame is not None:
            rgb_image = cv2.cvtColor(cv_frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            qt_image = QImage(rgb_image.data, w, h, ch * w, QImage.Format.Format_RGB888)
            self.original_pixmap = QPixmap.fromImage(qt_image)
            self.scan_item = None
            self.star_poses = []
            self.update()
            if self.isVisible():
                self.repaint()

    def set_scan_state(self, scan_item, star_poses=None, mode="horizontal", intensity=128):
        self.scan_item = scan_item
        self.star_poses = star_poses if star_poses is not None else []
        self.scan_mode = mode
        self.current_intensity = intensity
        self.update()

    def set_scan_position(self, pos, mode="horizontal", intensity=128, note=60):
        """Metodo di compatibilità"""
        if pos is None:
            self.scan_item = None
            self.star_poses = []
        else:
            if "vertical" in mode:
                self.scan_item = ('horizontal_line', pos[1])
            else:
                self.scan_item = ('vertical_line', pos[0])
            self.star_poses = [(pos[0], pos[1], intensity)]
        self.scan_mode = mode
        self.current_intensity = intensity
        self.update()

    def mousePressEvent(self, event):
        if self.interactive and not self.original_pixmap.isNull():
            local_pos = event.position()
            inner_rect = self.rect().adjusted(2, 2, -2, -2)
            pixmap_size = self.original_pixmap.size()
            scaled_pixmap = self.original_pixmap.scaled(
                inner_rect.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            )
            scaled_w, scaled_h = scaled_pixmap.width(), scaled_pixmap.height()
            offset_x = inner_rect.left() + (inner_rect.width() - scaled_w) / 2
            offset_y = inner_rect.top() + (inner_rect.height() - scaled_h) / 2
            
            x_in_scaled = local_pos.x() - offset_x
            y_in_scaled = local_pos.y() - offset_y
            
            if 0 <= x_in_scaled < scaled_w and 0 <= y_in_scaled < scaled_h:
                orig_w, orig_h = pixmap_size.width(), pixmap_size.height()
                img_x = int(x_in_scaled * (orig_w / scaled_w))
                img_y = int(y_in_scaled * (orig_h / scaled_h))
                self.position_clicked.emit(img_x, img_y)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        
        painter.fillRect(self.rect(), QColor(0, 0, 0))
        painter.setPen(QPen(QColor(255, 143, 0), 1))
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))

        if self.original_pixmap.isNull():
            painter.setPen(QColor(255, 255, 255))
            painter.setFont(QFont("Arial", 12))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.placeholder_text)
            painter.end()
            return

        inner_rect = self.rect().adjusted(2, 2, -2, -2)
        if inner_rect.width() <= 0 or inner_rect.height() <= 0:
            painter.end()
            return

        pixmap_size = self.original_pixmap.size()
        scaled_pixmap = self.original_pixmap.scaled(
            inner_rect.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        
        scaled_w = scaled_pixmap.width()
        scaled_h = scaled_pixmap.height()
        offset_x = inner_rect.left() + (inner_rect.width() - scaled_w) / 2
        offset_y = inner_rect.top() + (inner_rect.height() - scaled_h) / 2
        
        painter.drawPixmap(int(offset_x), int(offset_y), scaled_pixmap)

        if self.scan_item is not None:
            orig_w = pixmap_size.width()
            orig_h = pixmap_size.height()
            
            if orig_w > 0 and orig_h > 0:
                x_ratio = scaled_w / orig_w
                y_ratio = scaled_h / orig_h
                
                # 1. Linea di scansione continua (Verticale se orizzontale, Orizzontale se verticale)
                painter.setPen(QPen(QColor(255, 143, 0), 2, Qt.PenStyle.SolidLine))
                item_type, val = self.scan_item
                if item_type == 'vertical_line':
                    curr_x = offset_x + (val * x_ratio)
                    painter.drawLine(QPointF(curr_x, inner_rect.top()), QPointF(curr_x, inner_rect.bottom()))
                elif item_type == 'horizontal_line':
                    curr_y = offset_y + (val * y_ratio)
                    painter.drawLine(QPointF(inner_rect.left(), curr_y), QPointF(inner_rect.right(), curr_y))

                # 2. Cerchietti multipli sulle stelle intercettate dalla linea
                for star_x, star_y, intensity in self.star_poses:
                    if intensity > 40:
                        sx = offset_x + (star_x * x_ratio)
                        sy = offset_y + (star_y * y_ratio)
                        
                        radius = int(6 + (intensity / 255.0) * 12)
                        alpha = int(140 + (intensity / 255.0) * 115)
                        
                        painter.setPen(QPen(QColor(255, 255, 255, alpha), 2))
                        painter.drawEllipse(QPointF(sx, sy), radius + 3, radius + 3)
                        
                        painter.setPen(QPen(QColor(255, 143, 0, alpha), 2))
                        painter.drawEllipse(QPointF(sx, sy), radius, radius)
                        
                        painter.setBrush(QColor(255, 255, 255, alpha))
                        painter.drawEllipse(QPointF(sx, sy), 2, 2)

        painter.end()


class SeparateDisplayWindow(QMainWindow):
    position_clicked = pyqtSignal(int, int)

    def __init__(self, interactive=False):
        super().__init__()
        self.setWindowTitle("AstroSonification - Finestra Proiezione Osservatori (16:9)")
        self.resize(1280, 720)
        self.setStyleSheet("background-color: #000000;")
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        self.viewer = ImageViewerWidget("Schermo Osservatori", interactive=interactive)
        self.viewer.position_clicked.connect(self.position_clicked.emit)
        layout.addWidget(self.viewer)

    def load_image(self, path):
        if path and os.path.exists(path):
            self.viewer.set_image(path)

    def update_frame(self, cv_frame):
        self.viewer.set_frame(cv_frame)

    def update_scan_position(self, pos, mode, intensity=128, note=60):
        self.viewer.set_scan_position(pos, mode, intensity, note)


class OperatorConsole(QMainWindow):
    back_to_menu_signal = pyqtSignal()

    def __init__(self, mode_id=1, mode_name="Scansione Automatica da File"):
        super().__init__()
        self.mode_id = mode_id
        self.setWindowTitle(f"Console Operatore - {mode_name} (Master v2.8)")
        self.resize(1400, 900)
        self.setMinimumSize(1100, 800)
        
        self.image_path = None
        self.image_gray = None
        self.current_cv_image = None
        self.separate_window = None
        
        self.capture = None
        self.is_flipped = False
        self.is_playing = False
        self.prescan_done = False
        
        self.current_note = None
        self.current_bg_note = None
        self.current_chord_note = None
        
        self.hand_tracker = HandTrackingEngine()
        self.audio_engine = AudioEngine()
        
        self.camera_timer = QTimer(self)
        self.camera_timer.setInterval(30)
        self.camera_timer.timeout.connect(self.update_camera_frame)
        
        self.scan_timer = QTimer(self)
        self.scan_timer.timeout.connect(self.step_scan)
        self.scan_coordinates = []
        self.scan_index = 0
        self.scan_mode_current = "horizontal"
        
        self.init_stylesheet()
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)
        
        bottom_section_layout = QHBoxLayout()
        bottom_section_layout.setSpacing(15)
        
        self.group_log = QGroupBox("Console di Log & Debug in Tempo Reale")
        group_log_layout = QVBoxLayout()
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setStyleSheet("background-color: #050505; color: #FFFFFF; font-family: 'Courier New', monospace; font-size: 11px; border: 1px solid #FF8F00;")
        group_log_layout.addWidget(self.log_view)
        self.group_log.setLayout(group_log_layout)
        
        self.log_message(f"Console avviata in modalità [{mode_name}] (ID: {mode_id}).", "INFO")
        if self.audio_engine.is_initialized:
            self.log_message("Motore Audio FluidSynth avviato con successo.", "OPERATIONAL")

        top_section_layout = QHBoxLayout()
        top_section_layout.setSpacing(15)
        
        col1_layout = QVBoxLayout()
        col1_layout.setSpacing(10)
        
        self.btn_menu = QPushButton("Menù principale")
        self.btn_menu.setFixedHeight(45)
        self.btn_menu.clicked.connect(self.return_to_main_menu)
        col1_layout.addWidget(self.btn_menu)
        
        col1_layout.addSpacing(15)
        
        self.btn_load = QPushButton("Carica immagine")
        self.btn_load.setFixedHeight(50)
        self.btn_load.clicked.connect(self.load_image_file)
        col1_layout.addWidget(self.btn_load)
        
        self.group_transform = QGroupBox("Allineamento Immagine")
        transform_layout = QGridLayout()
        self.btn_rot = QPushButton("Ruota 90° ↻")
        self.btn_rot.clicked.connect(self.rotate_image_90)
        transform_layout.addWidget(self.btn_rot, 0, 0)
        self.btn_fliph = QPushButton("Ribalta H ⇄")
        self.btn_fliph.clicked.connect(self.flip_horizontal)
        transform_layout.addWidget(self.btn_fliph, 1, 0)
        self.btn_flipv = QPushButton("Ribalta V ⇅")
        self.btn_flipv.clicked.connect(self.flip_vertical)
        transform_layout.addWidget(self.btn_flipv, 1, 1)
        self.group_transform.setLayout(transform_layout)
        self.group_transform.setEnabled(False)
        col1_layout.addWidget(self.group_transform)
        
        col1_layout.addStretch()
        top_section_layout.addLayout(col1_layout, stretch=2)
        
        col2_layout = QVBoxLayout()
        col2_layout.setSpacing(5)
        lbl_preview_title = QLabel("Anteprima immagine")
        lbl_preview_title.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        col2_layout.addWidget(lbl_preview_title)
        
        is_interactive_mode = (self.mode_id == 2)
        self.operator_viewer = ImageViewerWidget("Anteprima Immagine", interactive=is_interactive_mode)
        self.operator_viewer.position_clicked.connect(self.on_viewer_clicked)
        col2_layout.addWidget(self.operator_viewer)
        top_section_layout.addLayout(col2_layout, stretch=5)
        
        if self.mode_id in [3, 4]:
            col3_layout = QVBoxLayout()
            col3_layout.setSpacing(5)
            lbl_cam_title = QLabel("Camera select")
            lbl_cam_title.setFont(QFont("Arial", 11, QFont.Weight.Bold))
            col3_layout.addWidget(lbl_cam_title)
            
            self.combo_camera = QComboBox()
            self.combo_camera.addItem("Nessuna Camera / Disattiva", -1)
            col3_layout.addWidget(self.combo_camera)
            
            self.btn_flip = QPushButton("Ribalta Orizzontalmente (Specchio: OFF)")
            self.btn_flip.setCheckable(True)
            self.btn_flip.setFixedHeight(35)
            self.btn_flip.clicked.connect(self.toggle_flip)
            col3_layout.addWidget(self.btn_flip)
            
            lbl_cam_ctrl = QLabel("Camera control")
            lbl_cam_ctrl.setFont(QFont("Arial", 11, QFont.Weight.Bold))
            col3_layout.addWidget(lbl_cam_ctrl)
            
            self.cam_viewer = ImageViewerWidget("Camera control")
            col3_layout.addWidget(self.cam_viewer)
            top_section_layout.addLayout(col3_layout, stretch=4)
            self.populate_camera_devices()
            self.combo_camera.currentIndexChanged.connect(self.on_camera_selection_changed)
        
        main_layout.addLayout(top_section_layout, stretch=4)
        
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background-color: #FF8F00; max-height: 2px; min-height: 2px;")
        main_layout.addWidget(separator)
        
        title_console = QLabel("Console Operatore")
        title_console.setFont(QFont("Arial", 13, QFont.Weight.Bold))
        title_console.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_console)
        
        bottom_sections_layout = QHBoxLayout()
        bottom_sections_layout.setSpacing(15)
        
        # --- GRUPPO SETUP ---
        self.group_setup = QGroupBox("Configurazione Oggetto & Pre-scan")
        group_setup_layout = QVBoxLayout()
        group_setup_layout.setSpacing(6)
        
        group_setup_layout.addWidget(QLabel("Preset oggetto celeste"))
        self.combo_preset = QComboBox()
        self.combo_preset.addItems([
            "Galassia a Spirale (es. M31 / M51)",
            "Galassia Ellittica / Lenticolare",
            "Nebulosa ad Emissione (es. Orione / Laguna)",
            "Nebulosa Planetaria / Resto di Supernova (es. M1)",
            "Ammasso Globulare & Aperto (es. M13 / Pleiadi)",
            "Via Lattea & Banda Galattica",
            "Sole (Macchie solari & Brillamenti)",
            "Luna (Crateri & Mari)",
            "Pianeta: Giove & Saturno (Bande & Anelli)",
            "Pianeta: Marte & Venere (Rocciosi)",
            "Campo Largo & Costellazioni"
        ])
        group_setup_layout.addWidget(self.combo_preset)
        
        group_setup_layout.addWidget(QLabel("Tavolozza Filtri (Palette Remapping)"))
        self.combo_filter = QComboBox()
        self.combo_filter.addItems(["Standard RGB", "Tavolozza Hubble SHO", "Tavolozza Bicolore HOO", "Infrarossa JWST"])
        group_setup_layout.addWidget(self.combo_filter)
        
        if self.mode_id == 1:
            group_setup_layout.addWidget(QLabel("Direzione / Modalità di Scansione"))
            self.combo_scan_mode = QComboBox()
            self.combo_scan_mode.addItems([
                "Orizzontale (Sinistra -> Destra)",
                "Orizzontale Inversa (Destra -> Sinistra)",
                "Verticale (Alto -> Basso)",
                "Verticale Inversa (Basso -> Alto)",
                "Concentrica / Radiale (Centro -> Bordi)",
                "Concentrica Inversa (Bordi -> Centro)",
                "Orologio / Angolare (Rotazione Oraria)",
                "Orologio Inverso (Rotazione Antioraria)"
            ])
            group_setup_layout.addWidget(self.combo_scan_mode)

        group_setup_layout.addWidget(QLabel("Strumento Principale (Canale 0 - Lead / Picchi)"))
        self.combo_instrument = QComboBox()
        self.combo_instrument.addItems(["Pianoforte a Coda", "Arpa Classica", "Violoncello", "Synth Pad", "Organo", "Flauto"])
        self.combo_instrument.currentIndexChanged.connect(self.on_instrument_changed)
        group_setup_layout.addWidget(self.combo_instrument)

        if self.mode_id == 1:
            self.lbl_duration_title = QLabel("Durata Scansione Completa (s): 30")
            group_setup_layout.addWidget(self.lbl_duration_title)
            self.slider_duration = QSlider(Qt.Orientation.Horizontal)
            self.slider_duration.setRange(5, 60)
            self.slider_duration.setValue(30)
            self.slider_duration.valueChanged.connect(self.update_scan_duration)
            group_setup_layout.addWidget(self.slider_duration)

        group_setup_layout.addSpacing(5)
        self.btn_prescan = QPushButton("Pre-scan immagine (Analisi & Tappeto)")
        self.btn_prescan.setFixedHeight(40)
        self.btn_prescan.clicked.connect(self.run_prescan)
        group_setup_layout.addWidget(self.btn_prescan)
        
        self.group_setup.setLayout(group_setup_layout)
        self.group_setup.setEnabled(False) 
        bottom_sections_layout.addWidget(self.group_setup, stretch=1)
        
        # --- GRUPPO CONTROLLI AUDIO & PLAY ---
        self.group_controls = QGroupBox("Controlli Audio & Play")
        group_controls_layout = QVBoxLayout()
        group_controls_layout.setSpacing(8)
        
        group_controls_layout.addWidget(QLabel("Volume Canale 1 (Picchi / Lead):"))
        self.slider_ch1 = self.create_custom_slider()
        self.slider_ch1.valueChanged.connect(lambda v: self.audio_engine.set_channel_volume(0, v))
        group_controls_layout.addWidget(self.slider_ch1)
        
        group_controls_layout.addWidget(QLabel("Volume Canale 2 (Sfondo / Pad):"))
        self.slider_ch2 = self.create_custom_slider()
        self.slider_ch2.valueChanged.connect(lambda v: self.audio_engine.set_channel_volume(1, v))
        group_controls_layout.addWidget(self.slider_ch2)

        group_controls_layout.addWidget(QLabel("Volume Canale 3 (Colori / Accordi):"))
        self.slider_ch3 = self.create_custom_slider()
        self.slider_ch3.valueChanged.connect(lambda v: self.audio_engine.set_channel_volume(2, v))
        group_controls_layout.addWidget(self.slider_ch3)

        group_controls_layout.addWidget(QLabel("Densità Note / Soglia Picchi (Voice Density):"))
        self.slider_density = self.create_custom_slider()
        self.slider_density.setValue(50)  # Valore predefinito bilanciato
        group_controls_layout.addWidget(self.slider_density)
        
        group_controls_layout.addStretch()

        play_labels = {
            1: "AVVIA SCANSIONE (PLAY)",
            2: "ATTIVA TOUCHSCREEN (PLAY)",
            3: "ATTIVA INTERAZIONE MANI SU FOTO (PLAY)",
            4: "ATTIVA AIR-GESTURE (PLAY)"
        }
        self.btn_play = QPushButton(play_labels.get(self.mode_id, "AVVIA (PLAY)"))
        self.btn_play.setFixedHeight(45)
        self.btn_play.clicked.connect(self.toggle_sonification)
        group_controls_layout.addWidget(self.btn_play)
        
        self.group_controls.setLayout(group_controls_layout)
        self.group_controls.setEnabled(False) 
        bottom_sections_layout.addWidget(self.group_controls, stretch=1)

        bottom_sections_layout.addWidget(self.group_log, stretch=1)
        main_layout.addLayout(bottom_sections_layout, stretch=4)

        # Connessioni per invalidare il pre-scan alla modifica dei parametri
        self.combo_preset.currentIndexChanged.connect(self.invalidate_prescan)
        self.combo_filter.currentIndexChanged.connect(self.invalidate_prescan)
        self.combo_instrument.currentIndexChanged.connect(self.invalidate_prescan)
        if hasattr(self, 'combo_scan_mode'):
            self.combo_scan_mode.currentIndexChanged.connect(self.invalidate_prescan)
        if hasattr(self, 'slider_duration'):
            self.slider_duration.valueChanged.connect(self.invalidate_prescan)

    def invalidate_prescan(self):
        if self.prescan_done and not self.is_playing:
            self.prescan_done = False
            self.group_controls.setEnabled(False)
            self.log_message("Parametri modificati: rieseguire il Pre-scan prima di riattivare il Play.", "ERROR")

    def log_message(self, text, level="INFO"):
        if not hasattr(self, 'log_view') or self.log_view is None:
            return
        color_map = {"INFO": "#FFFFFF", "OPERATIONAL": "#FF8F00", "DEBUG": "#00FF66", "ERROR": "#FF4444"}
        color = color_map.get(level, "#FFFFFF")
        self.log_view.append(f'<span style="color: {color};">[{level}] {text}</span>')
        self.log_view.verticalScrollBar().setValue(self.log_view.verticalScrollBar().maximum())

    def init_stylesheet(self):
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(0, 0, 0))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.Button, QColor(255, 143, 0))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(255, 255, 255))
        self.setPalette(palette)
        
        qss = """
            QMainWindow { background-color: #000000; }
            QPushButton {
                background-color: #FF8F00; color: #000000; border-radius: 6px; font-family: 'Arial'; font-weight: bold; padding: 6px; border: 2px solid #FF8F00;
            }
            QPushButton:hover { background-color: #FFA726; border: 2px solid #FFFFFF; color: #000000; }
            QPushButton:checked { background-color: #E65100; border: 2px solid #FFFFFF; color: #FFFFFF; }
            QPushButton:disabled { background-color: #1a1a1a; color: #777777; border: 2px solid #333333; }
            QLabel, QGroupBox { font-family: 'Arial'; color: #FFFFFF; }
            QGroupBox { border: 2px solid #FF8F00; border-radius: 6px; margin-top: 5px; padding: 8px; }
            QComboBox { background-color: #2E0000; color: #FFFFFF; border: 1px solid #FF8F00; padding: 6px 10px; border-radius: 4px; min-height: 25px; }
            QComboBox QAbstractItemView { background-color: #2E0000; color: #FFFFFF; selection-background-color: #FF8F00; selection-color: #000000; }
            QSlider::groove:horizontal { height: 6px; background: #FFFFFF; border-radius: 3px; }
            QSlider::handle:horizontal { background: #FF8F00; border: 2px solid #FFFFFF; width: 16px; height: 16px; margin: -5px 0; border-radius: 8px; }
        """
        self.setStyleSheet(qss)

    def create_custom_slider(self):
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(0, 100)
        slider.setValue(80)
        return slider

    def update_scan_duration(self, seconds):
        self.lbl_duration_title.setText(f"Durata Scansione Completa (s): {seconds}")
        if hasattr(self, 'scan_coordinates') and len(self.scan_coordinates) > 0:
            total_steps = len(self.scan_coordinates)
            interval_ms = max(10, int((seconds * 1000) / total_steps))
            self.scan_timer.setInterval(interval_ms)

    def on_instrument_changed(self, index):
        presets = [0, 42, 42, 89, 19, 73]
        prog = presets[index] if index < len(presets) else 0
        self.audio_engine.set_channel_instrument(0, 0, prog)
        self.log_message(f"Strumento principale aggiornato (Programma MIDI #{prog})", "OPERATIONAL")

    def toggle_flip(self, checked):
        self.is_flipped = checked
        self.btn_flip.setText(f"Ribalta Orizzontalmente (Specchio: {'ON' if checked else 'OFF'})")

    def populate_camera_devices(self):
        backend = cv2.CAP_AVFOUNDATION if sys.platform == 'darwin' else cv2.CAP_ANY
        for index in range(3):
            cap = cv2.VideoCapture(index, backend)
            if cap.isOpened():
                ret, _ = cap.read()
                if ret:
                    self.combo_camera.addItem(f"Webcam / Device HD #{index}", index)
                cap.release()

    def on_camera_selection_changed(self, index):
        if self.mode_id not in [3, 4]:
            return
        cam_data = self.combo_camera.currentData()
        if self.camera_timer.isActive():
            self.camera_timer.stop()
        if self.capture is not None:
            self.capture.release()
            self.capture = None
            
        if cam_data is not None and cam_data != -1:
            backend = cv2.CAP_AVFOUNDATION if sys.platform == 'darwin' else cv2.CAP_ANY
            self.capture = cv2.VideoCapture(cam_data, backend)
            if self.capture.isOpened():
                self.camera_timer.start()
                self.log_message(f"Flusso camera avviato per Modalità {self.mode_id}", "OPERATIONAL")

    def update_camera_frame(self):
        if self.capture and self.capture.isOpened():
            ret, frame = self.capture.read()
            if ret:
                if self.is_flipped:
                    frame = cv2.flip(frame, 1)
                hand_pos = None
                if self.mode_id in [3, 4]:
                    frame, hand_pos = self.hand_tracker.process_frame(frame)
                
                if self.mode_id in [3, 4]:
                    if hasattr(self, 'cam_viewer'):
                        self.cam_viewer.set_frame(frame)
                    
                    if hand_pos is not None and self.current_cv_image is not None:
                        h_img, w_img, _ = self.current_cv_image.shape
                        img_x = int(hand_pos[0] * w_img)
                        img_y = int(hand_pos[1] * h_img)
                        gray = cv2.cvtColor(self.current_cv_image, cv2.COLOR_BGR2GRAY)
                        intensity = int(gray[img_y, img_x]) if 0 <= img_y < h_img and 0 <= img_x < w_img else 128
                        
                        self.operator_viewer.set_scan_position((img_x, img_y), mode="hand", intensity=intensity, note=60)
                        if self.separate_window:
                            self.separate_window.update_scan_position((img_x, img_y), mode="hand", intensity=intensity, note=60)
                        if self.is_playing:
                            self.play_pixel_sound_from_frame(self.current_cv_image, img_x, img_y, 1.0)

    def check_photo_match(self, current_frame):
        if self.image_gray is None or current_frame is None:
            return False
        try:
            orb = cv2.ORB_create(nfeatures=500)
            gray_cam = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)
            kp1, des1 = orb.detectAndCompute(self.image_gray, None)
            kp2, des2 = orb.detectAndCompute(gray_cam, None)
            if des1 is None or des2 is None or len(kp1) < 10 or len(kp2) < 10:
                return False
            bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
            matches = bf.match(des1, des2)
            good_matches = [m for m in matches if m.distance < 50]
            return len(good_matches) >= 15
        except Exception as e:
            self.log_message(f"Errore matching foto: {e}", "ERROR")
            return False

    def load_image_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Carica Immagine Astronomica", "", "Immagini (*.jpg *.jpeg *.png)")
        if file_name:
            self.image_path = file_name
            self.current_cv_image = cv2.imread(file_name)
            self.update_image_display_and_gray()
            
              
            self.group_setup.setEnabled(True)
            self.group_transform.setEnabled(True)
            self.prescan_done = False
            
            self.log_message(f"Immagine caricata: {os.path.basename(file_name)}", "OPERATIONAL")

    def update_image_display_and_gray(self):
        if self.current_cv_image is not None:
            self.image_gray = cv2.cvtColor(self.current_cv_image, cv2.COLOR_BGR2GRAY)
            temp_path = "temp_preview_transformed.png"
            cv2.imwrite(temp_path, self.current_cv_image)
            self.operator_viewer.set_image(temp_path)
            if self.separate_window and self.mode_id not in [3, 4]:
                self.separate_window.load_image(temp_path)

    def rotate_image_90(self):
        if self.current_cv_image is not None:
            self.current_cv_image = cv2.rotate(self.current_cv_image, cv2.ROTATE_90_CLOCKWISE)
            self.update_image_display_and_gray()
            self.log_message("Immagine ruotata di 90°.", "OPERATIONAL")

    def flip_horizontal(self):
        if self.current_cv_image is not None:
            self.current_cv_image = cv2.flip(self.current_cv_image, 1)
            self.update_image_display_and_gray()
            self.log_message("Immagine ribaltata orizzontalmente.", "OPERATIONAL")

    def flip_vertical(self):
        if self.current_cv_image is not None:
            self.current_cv_image = cv2.flip(self.current_cv_image, 0)
            self.update_image_display_and_gray()
            self.log_message("Immagine ribaltata verticalmente.", "OPERATIONAL")

    def run_prescan(self):
        """Pre-scansione avanzata: mappa gli eventi, calcola la spaziatura e pianifica le durate minime delle note"""
        if not self.image_path:
            self.log_message("Pre-scan fallito: caricare prima l'immagine.", "ERROR")
            return
        
        preset = self.combo_preset.currentText().lower()
        palette = self.combo_filter.currentText()
        
        gray = self.image_gray
        h, w = gray.shape
        
        self.precalculated_events = []
        mean_b = np.mean(gray)
        std_b = np.std(gray)
        
        # Soglia di pre-scansione adattiva: più sensibile e profonda per la Via Lattea (bulge centrale)
        if "via lattea" in preset:
            star_threshold = int(mean_b + 0.7 * std_b)
            star_threshold = max(30, min(star_threshold, 160))
            step_grid = 4  # Griglia più fitta per catturare la densità galattica
        else:
            star_threshold = int(mean_b + (1.5 * std_b))
            star_threshold = max(50, min(star_threshold, 220))
            step_grid = 6
        
        for y in range(0, h, step_grid):
            for x in range(0, w, step_grid):
                val = int(gray[y, x])
                if val >= star_threshold:
                    self.precalculated_events.append((x, y, val))
        
        self.precalculated_events.sort(key=lambda e: e[2], reverse=True)
        
        total_sources = len(self.precalculated_events)
        self.planned_note_duration = max(4, int(10 - (total_sources / 700.0))) 
        self.planned_note_duration = min(self.planned_note_duration, 18)
        
        self.log_message(f"Pre-scan [{preset}] completato. Sorgenti mappate: {total_sources}. Sustain pianificato: {self.planned_note_duration} step.", "OPERATIONAL")

        self.prescan_done = True
        self.group_controls.setEnabled(True)
        
        if not self.separate_window:
            self.separate_window = SeparateDisplayWindow(interactive=(self.mode_id == 2))
            self.separate_window.position_clicked.connect(self.on_viewer_clicked)
        
        self.separate_window.show()
        self.separate_window.raise_()
        self.separate_window.load_image(self.image_path)
        QApplication.processEvents()
        self.log_message("Sistema pronto. Scansione fluida e densità armonica pronte per l'avvio.", "OPERATIONAL")

    def toggle_sonification(self):
        if not self.is_playing:
            self.start_sonification()
        else:
            self.stop_sonification()

    def start_sonification(self):
        if not self.image_path:
            self.log_message("Impossibile avviare: caricare prima l'immagine.", "ERROR")
            return

        if not self.prescan_done:
            self.log_message("Avvio rifiutato: eseguire prima il Pre-scan.", "ERROR")
            return

        if self.separate_window is None or not self.separate_window.isVisible():
            self.separate_window = SeparateDisplayWindow(interactive=(self.mode_id == 2))
            self.separate_window.position_clicked.connect(self.on_viewer_clicked)
            self.separate_window.load_image(self.image_path)
            self.separate_window.show()
            self.separate_window.raise_()
            QApplication.processEvents()
        
        if self.mode_id == 1:
            pixmap = self.operator_viewer.original_pixmap
            w, h = pixmap.width(), pixmap.height()
            mode_text = self.combo_scan_mode.currentText()
            
            mode = "horizontal"
            inverted = "Inversa" in mode_text
            if "Verticale" in mode_text: mode = "vertical"
            elif "Concentrica" in mode_text: mode = "concentric"
            elif "Orologio" in mode_text: mode = "clock"

            self.scan_mode_current = mode
            full_coords = ScanEngine.get_scan_coordinates(w, h, mode=mode, inverted=inverted)
            
            step = 2 if mode in ["horizontal", "vertical"] else 1
            self.scan_coordinates = full_coords[::step]
            
            self.scan_index = 0
            self.note_sustain_counter = 0
            self.update_scan_duration(self.slider_duration.value())
            self.scan_timer.start()
        
        self.is_playing = True
        stop_labels = {1: "FERMA LA SCANSIONE (STOP)", 2: "DISATTIVA TOUCHSCREEN (STOP)", 3: "DISATTIVA INTERAZIONE MANI (STOP)", 4: "DISATTIVA AIR-GESTURE (STOP)"}
        self.btn_play.setText(stop_labels.get(self.mode_id, "DISATTIVA (STOP)"))
        self.btn_play.setStyleSheet("background-color: #D32F2F; color: #FFFFFF; border: 2px solid #FFFFFF; font-weight: bold; border-radius: 6px;")
        
        self.set_controls_locked(True)
        self.log_message("Sonificazione avviata con protezione anti-accavallamento e sustain armonico.", "OPERATIONAL")

    def play_pixel_sound_from_frame(self, frame, x, y, volume_scale=1.0):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape
        if 0 <= y < h and 0 <= x < w:
            brightness = int(gray[y, x])
            b_val, g_val, r_val = frame[y, x]
            color_avg = int((int(r_val) + int(g_val) + int(b_val)) / 3)
            
            pentatonic_scale = [48, 50, 52, 55, 57, 60, 62, 64, 67, 69, 72, 74, 76, 79, 81, 84]
            scale_idx = int((brightness / 255.0) * (len(pentatonic_scale) - 1))
            note = pentatonic_scale[scale_idx]
            
            # Lettura dei volumi dai cursori dedicati (Canali 0, 1, 2)
            vol_ch0 = self.slider_ch1.value()
            vol_ch1 = self.slider_ch2.value()
            vol_ch2 = self.slider_ch3.value()
            
            # Canale 0: Lead (Picchi / Stelle)
            vel_ch0 = int((vol_ch0 / 100.0) * 127 * volume_scale)
            if vel_ch0 > 15:
                if self.current_note != note:
                    if self.current_note is not None:
                        self.audio_engine.note_off(0, self.current_note)
                    self.audio_engine.note_on(0, note, vel_ch0)
                    self.current_note = note
            else:
                if self.current_note is not None:
                    self.audio_engine.note_off(0, self.current_note)
                    self.current_note = None
            
            # Canale 1: Sfondo (Pad / Drone)
            bg_note = 36 + (color_avg % 24)
            vel_ch1 = int((vol_ch1 / 100.0) * 127 * volume_scale)
            if vel_ch1 > 15:
                if self.current_bg_note != bg_note:
                    if self.current_bg_note is not None:
                        self.audio_engine.note_off(1, self.current_bg_note)
                    self.audio_engine.note_on(1, bg_note, vel_ch1)
                    self.current_bg_note = bg_note
            else:
                if self.current_bg_note is not None:
                    self.audio_engine.note_off(1, self.current_bg_note)
                    self.current_bg_note = None

            # Canale 2: Accordi / Colori
            chord_note = 60 + (int(r_val) % 12)
            vel_ch2 = int((vol_ch2 / 100.0) * 127 * volume_scale)
            if vel_ch2 > 15:
                if self.current_chord_note != chord_note:
                    if self.current_chord_note is not None:
                        self.audio_engine.note_off(2, self.current_chord_note)
                    self.audio_engine.note_on(2, chord_note, vel_ch2)
                    self.current_chord_note = chord_note
            else:
                if self.current_chord_note is not None:
                    self.audio_engine.note_off(2, self.current_chord_note)
                    self.current_chord_note = None

            # Aggiornamento della posizione e dei parametri audio per l'onda dinamica visiva
            self.operator_viewer.set_scan_position((x, y), mode=self.scan_mode_current, intensity=brightness, note=note)
            if self.separate_window:
                self.separate_window.update_scan_position((x, y), mode=self.scan_mode_current, intensity=brightness, note=note)

    def on_viewer_clicked(self, x, y):
        if self.is_playing and self.mode_id == 2:
            gray = cv2.cvtColor(self.current_cv_image, cv2.COLOR_BGR2GRAY)
            intensity = int(gray[y, x])
            self.operator_viewer.set_scan_position((x, y), mode="hand", intensity=intensity, note=60)
            if self.separate_window:
                self.separate_window.update_scan_position((x, y), mode="hand", intensity=intensity, note=60)
            self.play_pixel_sound_from_frame(self.current_cv_image, x, y, 1.0)

    def stop_sonification(self):
        if self.mode_id == 1:
            self.scan_timer.stop()
        self.is_playing = False
        
        for ch, n in [(0, self.current_note), (1, self.current_bg_note), (2, self.current_chord_note)]:
            if n is not None:
                self.audio_engine.note_off(ch, n)
        self.current_note = self.current_bg_note = self.current_chord_note = None
            
        self.operator_viewer.set_scan_position(None)
        if self.separate_window:
            self.separate_window.update_scan_position(None, "horizontal")
        
        play_labels = {1: "AVVIA SCANSIONE (PLAY)", 2: "ATTIVA TOUCHSCREEN (PLAY)", 3: "ATTIVA INTERAZIONE MANI SU FOTO (PLAY)", 4: "ATTIVA AIR-GESTURE (PLAY)"}
        self.btn_play.setText(play_labels.get(self.mode_id, "AVVIA (PLAY)"))
        self.btn_play.setStyleSheet("")
        
        self.set_controls_locked(False)
        self.log_message("Riproduzione interrotta.", "OPERATIONAL")

    def set_controls_locked(self, locked):
        self.btn_load.setEnabled(not locked)
        self.group_setup.setEnabled(not locked)
        self.btn_menu.setEnabled(not locked)
        self.group_transform.setEnabled(not locked)
        if hasattr(self, 'combo_camera'):
            self.combo_camera.setEnabled(not locked)
        if hasattr(self, 'btn_flip'):
            self.btn_flip.setEnabled(not locked)
            
        # I volumi restano SEMPRE modificabili
        self.slider_ch1.setEnabled(True)
        self.slider_ch2.setEnabled(True)
        self.slider_ch3.setEnabled(True)
        self.slider_density.setEnabled(True)

    def step_scan(self):
        if self.scan_coordinates and self.scan_index < len(self.scan_coordinates):
            scan_item = self.scan_coordinates[self.scan_index]
            item_type, val = scan_item
            
            gray = self.image_gray
            h, w = gray.shape
            
            # Analisi della linea corrente
            line_intensities = []
            if item_type == 'vertical_line':
                x = val
                col = gray[:, x]
                line_intensities = [int(v) for v in col]
            elif item_type == 'horizontal_line':
                y = val
                row = gray[y, :]
                line_intensities = [int(v) for v in row]
            
            avg_line_intensity = np.mean(line_intensities) if line_intensities else 0
            max_line_intensity = np.max(line_intensities) if line_intensities else 0

            # Filtriamo dal catalogo pre-scansionato le stelle intercettate dalla linea corrente in questo step
            density_val = self.slider_density.value()
            preset_text = self.combo_preset.currentText().lower()

            if "via lattea" in preset_text:
                peak_threshold = int(25 + (density_val / 100.0) * 60)  # Soglia più aperta per il nucleo galattico
                max_stars = 6  # Fino a 6 note simultanee nella Via Lattea per una densità ricca
                tolerance = 5
            else:
                peak_threshold = int(60 + (density_val / 100.0) * 120)
                max_stars = 3
                tolerance = 3
            
            line_stars = []
            tolerance = 3  # Tolleranza in pixel per intercettare la linea
            for sx, sy, inten in getattr(self, 'precalculated_events', []):
                if inten >= peak_threshold:
                    if item_type == 'vertical_line' and abs(sx - val) <= tolerance:
                        line_stars.append((sx, sy, inten))
                    elif item_type == 'horizontal_line' and abs(sy - val) <= tolerance:
                        line_stars.append((sx, sy, inten))
            
            line_stars.sort(key=lambda s: s[2], reverse=True)
            active_stars = line_stars[:max_stars]
            
            # Inviluppo dinamico (Fade-in e Fade-out del 10%)
            total_steps = len(self.scan_coordinates)
            progress = self.scan_index / total_steps
            volume_scale = 1.0
            if progress < 0.10: volume_scale = progress / 0.10
            elif progress > 0.90: volume_scale = (1.0 - progress) / 0.10
            
            star_poses_for_view = [(sx, sy, inten) for sx, sy, inten in active_stars]
            
            # Aggiornamento grafico della linea e dei cerchietti
            self.operator_viewer.set_scan_state(scan_item, star_poses=star_poses_for_view, mode=self.scan_mode_current, intensity=int(max_line_intensity))
            if self.separate_window:
                self.separate_window.viewer.set_scan_state(scan_item, star_poses=star_poses_for_view, mode=self.scan_mode_current, intensity=int(max_line_intensity))
            
            # Esecuzione sonora con regole di sustain e intensità derivate dal pre-scan
            self.play_sustained_prescan_sound(self.current_cv_image, avg_line_intensity, max_line_intensity, active_stars, volume_scale)
            
            self.scan_index += 1
        else:
            self.stop_sonification()
            self.log_message("Scansione completata.", "OPERATIONAL")

    def play_sustained_prescan_sound(self, frame, avg_intensity, max_intensity, active_stars, volume_scale):
        preset_text = self.combo_preset.currentText().lower()
        scale = [48, 50, 52, 55, 57, 60, 62, 64, 67, 69, 72, 74, 76, 79, 81, 84]
        
        # Estrazione colori medi del frame corrente per le variazioni cromatiche
        b_val, g_val, r_val = 128, 128, 128
        if frame is not None and len(frame.shape) == 3:
            # Prende un campione centrale o medio della linea
            b_val, g_val, r_val = np.mean(frame, axis=(0, 1)) if len(frame.shape) > 2 else (128, 128, 128)

        # 1. NOTA DI FONDO (Pad / Drone - Canale 1): Lavora sempre in base alla luminosità media
        bg_note = 36 + (int(avg_intensity) % 12)
        vol_ch1 = self.slider_ch2.value()
        bg_boost = 0.5 + (avg_intensity / 255.0) * 0.5
        vel_ch1 = int((vol_ch1 / 100.0) * 127 * volume_scale * bg_boost)
        vel_ch1 = min(127, max(15, vel_ch1))
        
        if vol_ch1 > 0:
            if self.current_bg_note != bg_note:
                if self.current_bg_note is not None:
                    self.audio_engine.note_off(1, self.current_bg_note)
                self.audio_engine.note_on(1, bg_note, vel_ch1)
                self.current_bg_note = bg_note
        else:
            if self.current_bg_note is not None:
                self.audio_engine.note_off(1, self.current_bg_note)
                self.current_bg_note = None

        # 2. MELODIA / COLORI (Canale 2): Personalizzata in base all'oggetto
        vol_ch2 = self.slider_ch3.value()
        chord_note = scale[0]
        
        if "nebulosa" in preset_text or "sole" in preset_text or "pianeta" in preset_text:
            # Per Nebulose, Sole e Pianeti: la melodia è guidata dalle variazioni cromatiche (RGB)
            color_index = int((r_val + g_val + b_val) / 3) % len(scale)
            chord_note = scale[color_index]
            color_boost = 0.7 + (max_intensity / 255.0) * 0.3
            vel_ch2 = int((vol_ch2 / 100.0) * 127 * volume_scale * color_boost)
        else:
            # Per Galassie, Ammassi e Luna: accordi basati sull'intensità media della zona
            chord_index = (int(avg_intensity) // 16) % len(scale)
            chord_note = scale[chord_index]
            vel_ch2 = int((vol_ch2 / 100.0) * 127 * volume_scale * (avg_intensity / 255.0))

        vel_ch2 = min(127, max(15, vel_ch2))
        if vol_ch2 > 0:
            if self.current_chord_note != chord_note:
                if self.current_chord_note is not None:
                    self.audio_engine.note_off(2, self.current_chord_note)
                self.audio_engine.note_on(2, chord_note, vel_ch2)
                self.current_chord_note = chord_note
        else:
            if self.current_chord_note is not None:
                self.audio_engine.note_off(2, self.current_chord_note)
                self.current_chord_note = None

        # 3. MELODIA PRINCIPALE / LEAD (Canale 0): Gestione specifica per Stelle, Crateri e Ammassi
        vol_ch0 = self.slider_ch1.value()
        
        if "luna" in preset_text:
            # Per la Luna: rileva transizioni nette (crateri/bordi) basate sui picchi locali
            crater_trigger = max_intensity > (avg_intensity + 40)
            if crater_trigger and vol_ch0 > 0:
                crater_note = scale[int(max_intensity / 20) % len(scale)]
                vel_ch0 = int((vol_ch0 / 100.0) * 127 * volume_scale)
                if self.current_note != crater_note:
                    if self.current_note is not None:
                        self.audio_engine.note_off(0, self.current_note)
                    self.audio_engine.note_on(0, crater_note, vel_ch0)
                    self.current_note = crater_note
                    self.note_sustain_counter = 8
            elif self.note_sustain_counter > 0:
                self.note_sustain_counter -= 1
            else:
                if self.current_note is not None:
                    self.audio_engine.note_off(0, self.current_note)
                    self.current_note = None
        else:
            # Per Ammassi, Galassie, Costellazioni e Via Lattea: gestione avanzata stelle brillanti e sustain
            if active_stars:
                primary_star = active_stars[0]
                brightness = primary_star[2]
                scale_idx = int((brightness / 255.0) * (len(scale) - 1))
                lead_note = scale[scale_idx]
                
                star_boost = 0.6 + (brightness / 255.0) * 1.2
                vel_ch0 = int((vol_ch0 / 100.0) * 127 * volume_scale * star_boost)
                vel_ch0 = min(127, max(0, vel_ch0))
                
                if vel_ch0 > 15:
                    if self.current_note is None:
                        self.audio_engine.note_on(0, lead_note, vel_ch0)
                        self.current_note = lead_note
                        # Allunga la durata della nota per le stelle più luminose
                        self.note_sustain_counter = getattr(self, 'planned_note_duration', 12) + int(brightness / 30)
                    elif self.current_note != lead_note and self.note_sustain_counter <= 0:
                        self.audio_engine.note_off(0, self.current_note)
                        self.audio_engine.note_on(0, lead_note, vel_ch0)
                        self.current_note = lead_note
                        self.note_sustain_counter = getattr(self, 'planned_note_duration', 12)
            
            if getattr(self, 'note_sustain_counter', 0) > 0:
                self.note_sustain_counter -= 1
            else:
                if self.current_note is not None and not active_stars:
                    self.audio_engine.note_off(0, self.current_note)
                    self.current_note = None

    def play_continuous_and_peak_sound(self, frame, avg_intensity, max_intensity, active_stars, volume_scale):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        scale = [48, 50, 52, 55, 57, 60, 62, 64, 67, 69, 72, 74, 76, 79, 81, 84]
        
        # 1. Nota di fondo (Pad / Drone - Canale 1): Varia in tempo reale con l'intensità media della linea
        bg_note = 36 + (int(avg_intensity) % 12)
        vol_ch1 = self.slider_ch2.value()
        bg_boost = 0.2 + (avg_intensity / 255.0) * 0.8  # Cresce e diminuisce con la luce dell'immagine
        vel_ch1 = int((vol_ch1 / 100.0) * 127 * volume_scale * bg_boost)
        vel_ch1 = min(127, max(0, vel_ch1))
        
        if vel_ch1 > 10:
            if self.current_bg_note != bg_note:
                if self.current_bg_note is not None:
                    self.audio_engine.note_off(1, self.current_bg_note)
                self.audio_engine.note_on(1, bg_note, vel_ch1)
                self.current_bg_note = bg_note
        else:
            if self.current_bg_note is not None:
                self.audio_engine.note_off(1, self.current_bg_note)
                self.current_bg_note = None

        # 2. Melodia principale / Lead (Canale 0): Reagisce ai picchi se trovati, altrimenti segue l'andamento armonico generale
        if active_stars:
            primary_star = active_stars[0]
            brightness = primary_star[2]
            scale_idx = int((brightness / 255.0) * (len(scale) - 1))
            lead_note = scale[scale_idx]
            
            vol_ch0 = self.slider_ch1.value()
            brightness_boost = 0.4 + (brightness / 255.0) * 0.8
            vel_ch0 = int((vol_ch0 / 100.0) * 127 * volume_scale * brightness_boost)
            vel_ch0 = min(127, max(0, vel_ch0))
            
            if vel_ch0 > 15:
                if self.current_note != lead_note:
                    if self.current_note is not None:
                        self.audio_engine.note_off(0, self.current_note)
                    self.audio_engine.note_on(0, lead_note, vel_ch0)
                    self.current_note = lead_note
            else:
                if self.current_note is not None:
                    self.audio_engine.note_off(0, self.current_note)
                    self.current_note = None
        else:
            # Melodia continua basata sull'intensità media della zona
            scale_idx = int((avg_intensity / 255.0) * (len(scale) - 1))
            lead_note = scale[scale_idx]
            vol_ch0 = self.slider_ch1.value()
            vel_ch0 = int((vol_ch0 / 100.0) * 65 * volume_scale * (avg_intensity / 255.0))
            
            if vel_ch0 > 15:
                if self.current_note != lead_note:
                    if self.current_note is not None:
                        self.audio_engine.note_off(0, self.current_note)
                    self.audio_engine.note_on(0, lead_note, vel_ch0)
                    self.current_note = lead_note
            else:
                if self.current_note is not None:
                    self.audio_engine.note_off(0, self.current_note)
                    self.current_note = None

        # 3. Canale 2: Accordi armonici basati su picchi secondari (se presenti)
        if len(active_stars) > 1:
            secondary_star = active_stars[1]
            sec_brightness = secondary_star[2]
            sec_scale_idx = (int((sec_brightness / 255.0) * len(scale)) + 2) % len(scale)
            chord_note = scale[sec_scale_idx]
            
            vol_ch2 = self.slider_ch3.value()
            vel_ch2 = int((vol_ch2 / 100.0) * 127 * volume_scale * (sec_brightness / 255.0))
            vel_ch2 = min(127, max(0, vel_ch2))
            
            if vel_ch2 > 15:
                if self.current_chord_note != chord_note:
                    if self.current_chord_note is not None:
                        self.audio_engine.note_off(2, self.current_chord_note)
                    self.audio_engine.note_on(2, chord_note, vel_ch2)
                    self.current_chord_note = chord_note
            else:
                if self.current_chord_note is not None:
                    self.audio_engine.note_off(2, self.current_chord_note)
                    self.current_chord_note = None
        else:
            if self.current_chord_note is not None:
                self.audio_engine.note_off(2, self.current_chord_note)
                self.current_chord_note = None

    def return_to_main_menu(self):
        if self.camera_timer.isActive(): 
            self.camera_timer.stop()
        if self.capture is not None: 
            self.capture.release()
        self.audio_engine.close()
        if self.mode_id == 1: 
            self.scan_timer.stop()
        if self.separate_window: 
            self.separate_window.close()
        self.back_to_menu_signal.emit()
        self.close() 