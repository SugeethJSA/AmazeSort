import sys, os
from PySide6 import QtCore
from PySide6.QtCore import Qt, QRect, QCoreApplication
from PySide6.QtWidgets import QSplashScreen, QApplication, QGraphicsDropShadowEffect
from PySide6.QtGui import QPixmap, QPainter, QPainterPath, QGuiApplication, QIcon, QColor, QFont
import PySide6.QtWidgets as QtWidgets

# Base directory (where app.py is located)
base_dir = os.path.dirname(os.path.abspath(__file__))
assets_dir = os.path.join(base_dir, "assets")

class CustomSplashScreen(QSplashScreen):
    def __init__(self, pixmap):
        super().__init__(pixmap)
        self.message = ""
        self.message_align = Qt.AlignBottom | Qt.AlignCenter
        self.message_color = QColor("white")
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Apply drop shadow effect.
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setOffset(0, 0)
        shadow.setColor(QColor(0, 0, 0, 160))
        self.setGraphicsEffect(shadow)

    def showMessage(self, message, alignment=Qt.AlignBottom | Qt.AlignCenter, color=QColor("white")):
        self.message = message
        self.message_align = alignment
        self.message_color = color
        self.repaint()  # trigger paintEvent

    def paintEvent(self, event):
        # Clear background with transparency to avoid black box.
        painter = QPainter(self)
        painter.setCompositionMode(QPainter.CompositionMode_Source)
        painter.fillRect(self.rect(), Qt.transparent)
        painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
        # Draw the pixmap and any additional elements.
        super().paintEvent(event)
        if self.message:
            painter.setPen(self.message_color)
            painter.setFont(QFont("Arial", 12))
            rect = self.rect()
            painter.drawText(rect, self.message_align, self.message)
        painter.end()

class SplashScreen(QtWidgets.QSplashScreen):
    def round_pixmap(pixmap, radius=20):
        """Returns a new QPixmap with rounded corners."""
        rounded = QPixmap(pixmap.size())
        rounded.fill(Qt.transparent)
        painter = QPainter(rounded)
        painter.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        rect = pixmap.rect()
        path.addRoundedRect(rect, radius, radius)
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, pixmap)
        painter.end()
        return rounded
    def show_splash_fallback():
        # Create a QPixmap for the splash screen
        pixmap = QPixmap(os.path.join(assets_dir, "Splash.png"))  # Use your PNG file here

        # Use primaryScreen to get screen geometry.
        screen = QApplication.primaryScreen().availableGeometry()
        width = int(screen.width() * 0.4)
        height = int(screen.height() * 0.4)
        pixmap = pixmap.scaled(width, height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        
        # Apply rounded corners to the pixmap.
        pixmap = SplashScreen.round_pixmap(pixmap, radius=20)
        
        splash = QSplashScreen(pixmap, Qt.WindowStaysOnTopHint)
        splash.setAttribute(Qt.WA_TranslucentBackground)  # Set transparent background for the widget only.
        
        # Center the splash screen on the screen.
        splash.setGeometry(QRect((screen.width() - width) // 2, (screen.height() - height) // 2, width, height))
        splash.show()
        
        # Process events to show the splash screen immediately.
        QApplication.processEvents()
        return splash

class ShadowedSplashWidget(QtWidgets.QWidget):
    """Custom widget to display a splash screen with drop shadow without a black box."""
    def __init__(self, pixmap: QPixmap, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.resize(pixmap.size())
        self.label = QtWidgets.QLabel(self)
        self.label.setPixmap(pixmap)
        self.label.resize(pixmap.size())
        # Apply drop shadow effect to the label.
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setOffset(0, 0)
        shadow.setColor(QColor(0, 0, 0, 160))
        self.label.setGraphicsEffect(shadow)
        
    def paintEvent(self, event):
        # ...existing code if needed, otherwise simply call the parent's paintEvent.
        super().paintEvent(event)

def show_splash() -> QtWidgets.QWidget:
    """Create and display the custom shadowed splash screen."""
    pixmap = QPixmap(os.path.join(assets_dir, "splash.png"))
    screen = QApplication.primaryScreen().availableGeometry()
    width = int(screen.width() * 0.4)
    height = int(screen.height() * 0.4)
    pixmap = pixmap.scaled(width, height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    
    # Apply rounded corners.
    pixmap = SplashScreen.round_pixmap(pixmap, radius=20)
    
    # Use the custom CustomSplashScreen.
    splash = CustomSplashScreen(pixmap)
    splash.setGeometry(QRect((screen.width() - width) // 2,
                             (screen.height() - height) // 2,
                             width, height))
    splash.show()
    QApplication.processEvents()
    return splash

def main() -> None:
    """Main function to initialize the application and display the main window."""
    # Enable high DPI pixmap support (do this before creating QApplication)
    # High DPI support is enabled by default, however, the policy below ensures that the application knows that it's enabled.
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    # Create the application
    app = QApplication(sys.argv)
    # Set application icon.
    icon_path = os.path.join(assets_dir, "app_icon.ico")
    app.setWindowIcon(QIcon(icon_path))
    
    style_sheet = """    QProgressBar {
        border: 1px solid #e0e0e0;
        text-align: center;
        background-color: #e0e0e0;
        color: #212121;
        height: 25px;
        border-radius: 4px;
    }
    QProgressBar::chunk {
        background-color: #0a84ff;
        margin: 0.5px;
        border-radius: 4px;
    }
    """
    app.setStyleSheet(style_sheet)
    # Show splash screen
    splash = show_splash()
    
    from config import Config
    from main_ui import MainWindow

    # Load configuration.
    config = Config(os.path.join(base_dir, "sorter_config.json"))
    
    # Build relative paths for associations and guidebook files.
    associations_file = os.path.join(base_dir, config.get("associations_file", "associations.json"))
    guidebook_file = os.path.join(base_dir, config.get("guidebook_file", "syllabus.json"))
    
    dest_heads = config.get("dest_heads", [])
    
    if dest_heads and os.path.exists(guidebook_file):
        if not os.path.exists(associations_file):
            print("Associations file not found. A new associations dictionary will be generated when the UI starts training.")
        else:
            print("Associations file found. Using existing associations.")
    else:
        print("Ensure 'dest_heads' and 'guidebook_file' are properly configured in your config file.")
    
    # Create the main window
    window = MainWindow(config)
    
    # Close the splash screen and show the main window
    splash.finish(window)
    window.showNormal()  # Force normal window state instead of minimized
    window.raise_()      # Bring the window to the front
    window.activateWindow()  # Activate the window to get focus
    
    # Execute the application
    sys.exit(app.exec())

if __name__ == "__main__":
    main()