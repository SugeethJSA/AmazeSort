import os
import sys
import subprocess
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QProgressBar, QPushButton, QTextEdit, QTextCursor
from PySide6.QtCore import Qt, QThread, Signal

# -------------------------------
# CONFIGURATION
# -------------------------------

APP_DIR = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.getcwd()
SITE_PACKAGES = os.path.join(APP_DIR, "site-packages")
os.makedirs(SITE_PACKAGES, exist_ok=True)  # Ensure directory exists
sys.path.insert(0, SITE_PACKAGES)  # Add site-packages to Python path

# -------------------------------
# INSTALLATION THREAD
# -------------------------------

class GPUInstallerThread(QThread):
    progress = Signal(int)   # Progress bar signal
    log = Signal(str)        # Log update signal
    finished_signal = Signal(bool)  # Finished signal
    stop_flag = False  # Flag to cancel installation

    def install_package(self, package, step, total_steps, index_url=None, force_reinstall=False):
        """Installs a package inside site-packages"""
        if self.stop_flag:
            return
        self.log.emit(f"📦 Installing {package} ({step}/{total_steps})...")
        self.progress.emit(int((step / total_steps) * 100))

        try:
            cmd = [sys.executable, "-m", "pip", "install", package, "--target", SITE_PACKAGES, "--no-cache-dir"]
            if force_reinstall:
                cmd.append("--force-reinstall")
            if index_url:
                cmd.extend(["--index-url", index_url])
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as e:
            self.log.emit(f"❌ Failed to install {package}: {str(e)}")
            return
        
        if self.stop_flag:  # Double check after install attempt
            return

    def run(self):
        """Runs the installation process in a background thread"""
        self.log.emit("🔍 Detecting GPU (this may take a moment)...")
        self.progress.emit(5)  # Indicate progress start

        try:
            import torch
            has_cuda = torch.cuda.is_available()
            has_directml = False  # Default to False; manually check next
            has_rocm = hasattr(torch, "has_rocm") and torch.has_rocm

            # Explicit check for DirectML availability
            try:
                import torch_directml
                has_directml = True
            except ImportError:
                has_directml = False

            cuda_version = torch.version.cuda if has_cuda else "None"

        except Exception as e:
            self.log.emit(f"⚠ Error checking GPU: {e}")
            has_cuda = has_directml = has_rocm = False
            cuda_version = "Unknown"

        if self.stop_flag:
            self.log.emit("❌ Installation Canceled.")
            return

        # Determine installation requirements
        total_steps = 1  # Only 1 step needed for GPU-specific install
        step = 1

        if has_cuda:
            self.log.emit(f"✅ NVIDIA GPU detected! CUDA version: {cuda_version}")
            self.log.emit("📦 Installing CUDA dependencies...")
            self.install_package("torch torchvision torchaudio", step, total_steps, "https://download.pytorch.org/whl/cu121", force_reinstall=True)
        elif has_directml:
            self.log.emit("✅ Intel Arc/AMD GPU detected! Installing DirectML support...")
            self.install_package("torch-directml", step, total_steps, force_reinstall=True)
        elif has_rocm:
            self.log.emit("✅ AMD ROCm GPU detected! Installing ROCm dependencies...")
            self.install_package("torch torchvision torchaudio", step, total_steps, "https://download.pytorch.org/whl/rocm5.4", force_reinstall=True)
        else:
            self.log.emit("⚠ No GPU detected. Running in CPU mode...")
            self.install_package("torch torchvision torchaudio", step, total_steps, force_reinstall=True)

        self.progress.emit(100)  # Set progress to 100% when done
        self.log.emit("\n🎉 GPU dependencies installed successfully!")
        self.finished_signal.emit(True)  # Signal that installation is complete

# -------------------------------
# GUI INSTALLER
# -------------------------------

class GPUInstallerApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AmazeSort GPU Setup")
        self.setGeometry(600, 300, 450, 300)

        layout = QVBoxLayout()

        self.label = QLabel("🔍 Detecting system GPU...")
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)

        self.log_output = QTextEdit(self)
        self.log_output.setReadOnly(True)  # Prevent user edits
        self.log_output.setFixedHeight(100)
        layout.addWidget(self.log_output)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        layout.addWidget(self.progress_bar)

        self.start_button = QPushButton("Start Installation")
        self.start_button.clicked.connect(self.start_installation)
        layout.addWidget(self.start_button)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.cancel_installation)
        self.cancel_button.setEnabled(False)  # Initially disabled
        layout.addWidget(self.cancel_button)

        self.launch_button = QPushButton("Launch AmazeSort")
        self.launch_button.clicked.connect(self.launch_amazesort)
        self.launch_button.setEnabled(False)  # Disabled until installation completes
        layout.addWidget(self.launch_button)

        self.setLayout(layout)

    def start_installation(self):
        """Starts the installation in a separate thread"""
        self.start_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.progress_bar.setValue(5)  # Show some progress at start
        self.log_output.clear()
        self.thread = GPUInstallerThread()
        self.thread.progress.connect(self.progress_bar.setValue)
        self.thread.log.connect(self.update_log)
        self.thread.finished_signal.connect(self.on_installation_complete)
        self.thread.start()

    def cancel_installation(self):
        """Cancels the installation process"""
        self.thread.stop_flag = True
        self.cancel_button.setEnabled(False)
        self.label.setText("❌ Installation Canceled.")
        self.log_output.append("❌ Installation Canceled.")

    def launch_amazesort(self):
        """Launches AmazeSort after installation"""
        exe_path = os.path.join(APP_DIR, "AmazeSort.exe")  # Adjust path if needed
        subprocess.Popen(exe_path, shell=True)
        self.close()

    def update_log(self, message):
        """Updates the log output, sets the label, and auto-scrolls to the latest log"""
        self.log_output.append(message)
        self.log_output.moveCursor(self.log_output.textCursor().End)  # Auto-scroll to bottom
        self.label.setText(message)  # Keep label in sync with latest status

    def on_installation_complete(self, success):
        """Called when installation is done"""
        if success:
            self.label.setText("✅ Installation Complete!")
            self.launch_button.setEnabled(True)  # Enable launch button
        self.cancel_button.setEnabled(False)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GPUInstallerApp()
    window.show()
    sys.exit(app.exec())
