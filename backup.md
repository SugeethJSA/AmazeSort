
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
        print("DEBUG: entering show_splash_fallback")  # Debug print
        # Create a QPixmap for the splash screen
        pixmap = QPixmap(os.path.join(assets_dir, "splash.png"))  # Use your PNG file here

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
        print("DEBUG: fallback splash displayed")  # Debug print
        
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

def show_splash():
    splash_path = os.path.join(assets_dir, "splash.png")
    print("DEBUG: loading splash image from", splash_path)  # Debug info
    if not os.path.exists(splash_path):
        print("ERROR: splash image does not exist at", splash_path)
        return SplashScreen.show_splash_fallback()
    pixmap = QPixmap(splash_path)
    if pixmap.isNull():
        print("ERROR: splash image not found or invalid. Falling back to default splash screen.")
        return SplashScreen.show_splash_fallback()
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
