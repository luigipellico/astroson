import sys
import traceback
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor, QPalette
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, 
    QLabel, QPushButton, QMessageBox
)

from operator_console import OperatorConsole

class AstroSonificationLauncher(QMainWindow):
    """Launcher Principale: Selezione della Modalità Operativa (Master v2.1)"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sistema Avanzato di Sonificazione Astronomica - Master v2.1")
        self.resize(900, 650)
        
        self.init_stylesheet()
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(40, 40, 40, 40)
        main_layout.setSpacing(25)
        
        title_label = QLabel("SELEZIONE MODALITÀ OPERATIVA")
        title_label.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("color: #FF8F00;")
        main_layout.addWidget(title_label)
        
        subtitle_label = QLabel("Seleziona la modalità d'interazione desiderata per avviare la console di controllo:")
        subtitle_label.setFont(QFont("Arial", 12))
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setStyleSheet("color: #FFFFFF;")
        main_layout.addWidget(subtitle_label)
        
        modes_layout = QVBoxLayout()
        modes_layout.setSpacing(15)
        
        self.btn_mode1 = QPushButton("1. Scansione Automatica da File (Multi-Direzione & Inversioni)")
        self.btn_mode2 = QPushButton("2. Modalità Touchscreen Interattiva (Fullscreen su Secondo Video)")
        self.btn_mode3 = QPushButton("3. Telecamera e Tracciamento Mani su Foto Stampata (Integrazione Herakoi)")
        self.btn_mode4 = QPushButton("4. Telecamera Air-Gestures (Persona Inquadrata & Proiezione Scheletro)")
        
        for btn in [self.btn_mode1, self.btn_mode2, self.btn_mode3, self.btn_mode4]:
            btn.setFont(QFont("Arial", 12, QFont.Weight.Bold))
            btn.setFixedHeight(65)
            modes_layout.addWidget(btn)
            
        main_layout.addLayout(modes_layout)
        
        self.footer_label = QLabel("Pronto per l'avvio. Selezionare una modalità per caricare l'immagine e i parametri.")
        footer_font = QFont("Arial", 10)
        footer_font.setItalic(True)
        self.footer_label.setFont(footer_font)
        self.footer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.footer_label.setStyleSheet("color: #FF8F00;")
        main_layout.addWidget(self.footer_label)
        
        self.btn_mode1.clicked.connect(lambda: self.launch_mode(1, "Scansione Automatica da File"))
        self.btn_mode2.clicked.connect(lambda: self.launch_mode(2, "Touchscreen Interattivo (Fullscreen)"))
        self.btn_mode3.clicked.connect(lambda: self.launch_mode(3, "Telecamera su Foto Stampata (Herakoi)"))
        self.btn_mode4.clicked.connect(lambda: self.launch_mode(4, "Air-Gestures e Proiezione Scheletro"))

    def init_stylesheet(self):
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(0, 0, 0))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.Button, QColor(255, 143, 0))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(0, 0, 0))
        self.setPalette(palette)
        
        qss = """
            QMainWindow { background-color: #000000; }
            QPushButton {
                background-color: #FF8F00;
                color: #000000;
                border-radius: 8px;
                font-family: 'Arial';
                font-weight: bold;
                padding: 10px;
                border: 2px solid #FF8F00;
            }
            QPushButton:hover { background-color: #FFA726; border: 2px solid #FFFFFF; }
            QPushButton:pressed { background-color: #E65100; }
            QLabel { font-family: 'Arial'; }
        """
        self.setStyleSheet(qss)

    def launch_mode(self, mode_id, mode_name):
        try:
            self.footer_label.setText(f"Modalità selezionata: {mode_name}. Apertura console di controllo...")
            self.console_window = OperatorConsole(mode_id=mode_id, mode_name=mode_name)
            self.console_window.back_to_menu_signal.connect(self.show_launcher)
            self.console_window.show()
            self.hide()
        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "Errore di Avvio", f"Impossibile aprire la console:\n{str(e)}")

    def show_launcher(self):
        self.show()

if __name__ == '__main__':
    try:
        app = QApplication(sys.argv)
        app.setStyle("Fusion")
        app.setFont(QFont("Arial", 10))
        
        launcher = AstroSonificationLauncher()
        launcher.show()
        sys.exit(app.exec())
    except Exception as e:
        traceback.print_exc()