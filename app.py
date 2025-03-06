import sys, os
from PySide6 import QtCore
from PySide6.QtCore import Qt, QRect, QCoreApplication
from PySide6.QtWidgets import QSplashScreen, QApplication
from PySide6.QtGui import QPixmap, QPainter, QPainterPath, QGuiApplication
import PySide6.QtWidgets as QtWidgets

# Base directory (where app.py is located)
base_dir = os.path.dirname(os.path.abspath(__file__))

from PySide6.QtWidgets import QSplashScreen, QGraphicsDropShadowEffect
from PySide6.QtGui import QPainter, QColor, QFont
from PySide6.QtCore import Qt

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
        super().paintEvent(event)  # draw pixmap, etc.
        if self.message:
            painter = QPainter(self)
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
        pixmap = QPixmap(os.path.join(base_dir, "splash.png"))  # Use your PNG file here

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

def show_splash():
    # Load high-resolution splash image.
    pixmap = QPixmap(os.path.join(base_dir, "splash.png"))
    # Get primary screen geometry.
    screen = QApplication.primaryScreen().availableGeometry()
    width = int(screen.width() * 0.4)
    height = int(screen.height() * 0.4)
    # Scale the pixmap to the target size.
    pixmap = pixmap.scaled(width, height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    
    # Apply rounded corners.
    pixmap = SplashScreen.round_pixmap(pixmap, radius=20)
    
    # Create our custom splash screen with shadow and text support.
    splash = CustomSplashScreen(pixmap)
    splash.setAttribute(Qt.WA_TranslucentBackground)
    # Use frameless window flags for layered windows.
    splash.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
    
    # Center the splash screen.
    splash.setGeometry(QRect((screen.width() - width) // 2,
                             (screen.height() - height) // 2,
                             width, height))
    
    # Remove the setMask() call. This avoids mismatches between mask and geometry.
    # splash.setMask(pixmap.mask())
    
    # splash.showMessage("Loading, please wait...", alignment=Qt.AlignBottom | Qt.AlignLeft, color=QColor("white"))
    splash.show()
    QApplication.processEvents()
    
    # Optionally show a message.
    # 
    
    return splash

def main():
    # Enable high DPI pixmap support (do this before creating QApplication)
    # High DPI support is enabled by default, however, the policy below ensures that the application knows that it's enabled.
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    # Create the application
    app = QApplication(sys.argv)
    
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
    window.show()
    
    # Execute the application
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
