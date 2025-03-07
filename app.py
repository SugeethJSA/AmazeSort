import sys, os, subprocess
from PySide6.QtCore import Qt, QRect, QCoreApplication
from PySide6.QtWidgets import QSplashScreen, QApplication, QGraphicsDropShadowEffect
from PySide6.QtGui import QPixmap, QPainter, QPainterPath, QGuiApplication, QIcon, QColor, QFont

# Determine the base directory
if getattr(sys, 'frozen', False):  
    base_dir = os.path.dirname(sys.executable)  # Running as an .exe
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))  # Running as a .py script

assets_dir = os.path.join(base_dir, "assets")
setup_path = os.path.join(base_dir, "amazesort_gpu_setup.exe")
APP_DIR = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.getcwd()
SITE_PACKAGES = os.path.join(APP_DIR, "site-packages")
os.makedirs(SITE_PACKAGES, exist_ok=True)  # Ensure directory exists
sys.path.insert(0, SITE_PACKAGES)  # Add site-packages to Python path


try:
    import torchaudio
except ImportError:
    print("🚀 Running GPU setup...")
    subprocess.run([setup_path])  # Run the setup script

for path in sys.path[:]:
    if "torch" in path.lower() and "_internal/" in path:  # Adjust condition if needed
        sys.path.remove(path)

# Base directory (where app.py is located)

def show_splash():
    splash_path = os.path.join(assets_dir, "splash.png")
    if not os.path.exists(splash_path):
        print("ERROR: Splash image missing at", splash_path)
        return None  # No splash screen

    pixmap = QPixmap(splash_path)
    if pixmap.isNull():
        print("ERROR: Invalid splash image. Skipping splash screen.")
        return None

    # Scale splash to 40% of screen size, keeping aspect ratio.
    screen = QApplication.primaryScreen().availableGeometry()
    target_width, target_height = int(screen.width() * 0.4), int(screen.height() * 0.4)
    scaled_pixmap = pixmap.scaled(target_width, target_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    
    # Create splash screen with no window frame.
    splash = QSplashScreen(scaled_pixmap, Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
    
    # Center the splash screen based on the actual pixmap size.
    pixmap_size = scaled_pixmap.size()
    x = (screen.width() - pixmap_size.width()) // 2
    y = (screen.height() - pixmap_size.height()) // 2
    splash.setGeometry(x, y, pixmap_size.width(), pixmap_size.height())
    
    splash.show()
    QApplication.processEvents()
    return splash


def main():
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
    window.showNormal()  # Force normal window state instead of minimized
    window.raise_()      # Bring the window to the front
    window.activateWindow()  # Activate the window to get focus
    splash.finish(window)  # Close the splash screen
    
    # Execute the application
    sys.exit(app.exec())

if __name__ == "__main__":
    main()