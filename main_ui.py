import sys, os, json
from PySide6 import QtWidgets, QtCore, QtGui
from PySide6.QtWidgets import QVBoxLayout, QGroupBox, QPushButton, QLabel, QProgressBar, QToolBar, QWidget, QHBoxLayout, QListWidget, QWidgetAction
from PySide6.QtGui import QAction
from config import Config
from file_sorter import FileSorter
from ai_model import TransformerAIModel
from associations import generate_associations
from associations import scan_directory_structure  # For completeness; used by worker threads
import utils, traceback
from PySide6.QtCore import Qt
import logging

Assets_Dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
Icons_Dir = os.path.join(Assets_Dir, "icons")

class EmittingStream(QtCore.QObject):
    textWritten = QtCore.Signal(str)
    
    def write(self, text):
        # Emit the text; you can filter out extra newlines if needed.
        self.textWritten.emit(str(text))
    
    def flush(self):
        pass

# Add new LogStream class to redirect output.
class LogStream:
    def __init__(self, callback, log_filename="debug_log.txt"):
        self.callback = callback
        self.log_filename = log_filename
        # Clear previous log file.
        with open(self.log_filename, "w", encoding="utf8") as f:
            f.write("")
    def write(self, text):
        if text.strip():
            self.callback(text)
            with open(self.log_filename, "a", encoding="utf8") as f:
                f.write(text)
    def flush(self):
        pass

class AssociationsWorker(QtCore.QThread):
    progress = QtCore.Signal(int)
    log_signal = QtCore.Signal(str)
    finished = QtCore.Signal(dict)  # Return associations dictionary

    def __init__(self, dest_dir, guidebook_file, output_file, update_mode, retain_old, parent=None):
        super().__init__(parent)
        self.dest_dir = dest_dir
        self.guidebook_file = guidebook_file
        self.output_file = output_file
        self.update_mode = update_mode
        self.retain_old = retain_old
        self._is_running = True

    def run(self):
        try:
            from associations import generate_associations

            # We assume that associations generation takes some time.
            self.log_signal.emit("Starting associations generation...")

            # Generate associations with progress callback.
            associations = generate_associations(self.dest_dir, self.guidebook_file, output_file=self.output_file,
                                                 update_mode=self.update_mode, retain_old=self.retain_old,
                                                 progress_callback=self.progress_callback)

            self.log_signal.emit("Associations generation completed.")
            self.finished.emit(associations)
        except Exception as e:
            self.log_signal.emit(f"Error in associations generation: {e}")
            self.finished.emit({})

    def progress_callback(self, progress):
        if self.isInterruptionRequested():
            raise Exception("Associations generation cancelled by user.")
        self.progress.emit(progress)
        self.log_signal.emit(f"Progress: {progress}%")

    def stop(self):
        self._is_running = False


# Updated Worker Threads (dummy implementations for illustration)
class TrainWorker(QtCore.QThread):
    progress = QtCore.Signal(int)
    log_signal = QtCore.Signal(str)
    finished = QtCore.Signal()

    def __init__(self, guidebook, dest_dir, dictionary=None, parent=None):
        """
        guidebook: A dictionary loaded from your guidebook file (e.g., syllabus.json)
        dest_dir: The root destination directory to scan recursively.
        dictionary: (Optional) A dictionary from extra training examples (e.g., dictionary.json)
        """
        super().__init__(parent)
        self._is_running = True
        self.guidebook = guidebook or {}
        self.dest_dir = dest_dir
        self.dictionary = dictionary or {}
        self.transformer_ai = TransformerAIModel()

    def build_training_dataset(self):
        """
        Build training texts and labels by combining:
         1. Examples generated from the guidebook.
         2. Examples derived from recursively scanning the destination directory.
         3. (Optionally) Extra examples from the provided dictionary.
        Returns two lists: texts and labels.
        """
        texts = []
        labels = []

        # --- Part 1: Build from guidebook ---
        for subject, content in self.guidebook.items():
            if isinstance(content, dict):
                for unit, chapters in content.items():
                    if isinstance(chapters, dict):
                        for chapter, keywords in chapters.items():
                            if not isinstance(keywords, list):
                                continue
                            text = f"{subject} {chapter} {' '.join(keywords)}"
                            texts.append(text)
                            labels.append(f"{subject}/{chapter}")
                    elif isinstance(chapters, list):
                        text = f"{subject} {' '.join(chapters)}"
                        texts.append(text)
                        labels.append(f"{subject}/General")
            elif isinstance(content, list):
                text = f"{subject} {' '.join(content)}"
                texts.append(text)
                labels.append(f"{subject}/General")

        # --- Part 2: Build from directory structure ---
        self.log_signal.emit("Scanning destination directory recursively for training examples...")
        structure = scan_directory_structure(self.dest_dir)
        def traverse_structure(struct, parent_label=""):
            for folder_name, folder_info in struct.items():
                # Use folder name plus any associations if available
                associations = folder_info.get("associations", [])
                if associations:
                    text = f"{folder_name} {' '.join(associations)}"
                else:
                    text = folder_name
                if parent_label:
                    label = f"{parent_label}/{folder_name}"
                else:
                    label = folder_name
                texts.append(text)
                labels.append(label)
                # Recurse into children if present
                if "children" in folder_info and isinstance(folder_info["children"], dict):
                    traverse_structure(folder_info["children"], label)
        traverse_structure(structure)

        # --- Part 3: (Optional) Extra examples from dictionary ---
        extra_examples = self.dictionary.get("examples", [])
        for entry in extra_examples:
            if "text" in entry and "label" in entry:
                texts.append(entry["text"])
                labels.append(entry["label"])

        return texts, labels

    def run(self):
        try:
            self.log_signal.emit("Building training dataset (recursively)...")
            texts, labels = self.build_training_dataset()
            num_examples = len(texts)
            self.log_signal.emit(f"Training dataset built with {num_examples} examples.")
            if num_examples == 0:
                self.log_signal.emit("No training examples available. Aborting training.")
                self.finished.emit()
                return

            def progress_callback(val):
                if self._is_running:
                    # Adjust this mapping if the jump is too abrupt.
                    mapped_val = int(val)
                    self.progress.emit(mapped_val)
                    self.log_signal.emit(f"Training progress: {val}%")
            self.log_signal.emit("Starting transformer model training...")
            # Increase epochs and adjust parameters as needed.
            self.transformer_ai.train(texts, labels, output_dir="transformer_model", epochs=5, progress_callback=progress_callback)
            self.log_signal.emit("Transformer model training completed.")
        except Exception as e:
            err = traceback.format_exc()
            self.log_signal.emit(f"Training error: {e}\n{err}")
        self.finished.emit()

    def stop(self):
        self._is_running = False

class SortWorker(QtCore.QThread):
    progress = QtCore.Signal(int)
    log_signal = QtCore.Signal(str)
    finished = QtCore.Signal(dict)  # Return the log dictionary once sorting is complete

    def __init__(self, sorter, parent=None):
        super().__init__(parent)
        self.sorter = sorter

    def run(self):
        try:
            log = self.sorter.sort_files(progress_callback=self.progress.emit)
            self.log_signal.emit("Sorting completed successfully.")
            self.finished.emit(log)
        except Exception as e:
            self.log_signal.emit(f"Sorting error: {e}")
            self.finished.emit({})

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.sorter = FileSorter(self.config)
        self.setWindowTitle("AmazeSort : Python-based file sorter.")
        # Increase the default width to ensure the ribbon is fully visible.
        width = self.config.get("ui", {}).get("window_width", 1200)
        # Set a minimum width to prevent the ribbon from being hidden.
        self.setMinimumWidth(width)
        self.resize(width, self.sizeHint().height())
        
        icon_path = os.path.join(Assets_Dir, "app_icon.ico")
        self.setWindowIcon(QtGui.QIcon(icon_path))
        
        self.setup_ribbon()
        self.setup_central_area()
        self.adjustSize()  # Shrink window to its sizeHint based on content
        
        # Optionally, set a minimum height based on the computed sizeHint so the content is always visible.
        self.setMinimumHeight(self.sizeHint().height())

        # Redirect stdout and stderr to the log box and debug log file.
        log_stream = LogStream(self.append_log)
        sys.stdout = log_stream
        sys.stderr = log_stream

        # Configure logging to use the custom log stream.
        logging.basicConfig(level=logging.DEBUG, stream=log_stream)

        self.update_ui_from_config()

    def create_group_widget(self, title, actions):
        """Creates a widget with a header above a row of tool buttons for the given actions."""
        container = QtWidgets.QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        
        header = QLabel(title)
        header.setStyleSheet("font-weight: bold; padding: 2px;")
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)
        
        btn_container = QtWidgets.QWidget()
        h_layout = QHBoxLayout(btn_container)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(1)
        
        for act in actions:
            btn = QtWidgets.QToolButton()
            btn.setDefaultAction(act)
            btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            btn.setIconSize(QtCore.QSize(30, 30))
            btn.setStyleSheet("""
                QToolButton {
                    background-color: #f3f3f3;
                    color: black;
                    border: none;
                    padding: 4px 3px;
                    border-radius: 4px;
                }
                QToolButton:hover {
                    background-color: #a5d3ff;
                }
                QToolButton:pressed {
                    background-color: #43a3ff;
                }
            """)
            h_layout.addWidget(btn)
        layout.addWidget(btn_container)
        return container

    def setup_ribbon(self):
        ribbon = QToolBar("Ribbon")
        # Set a larger icon size for consistency.
        ribbon.setIconSize(QtCore.QSize(40, 40))
        # Set a style for basic buttons; they will inherit our larger icon sizes.
        ribbon.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        ribbon.setStyleSheet("QToolButton { margin: 4px; padding: 2px; }")
        self.addToolBar(Qt.TopToolBarArea, ribbon)
        
        # Create basic actions (unchanged).
        train_icon = QtGui.QIcon(os.path.join(Icons_Dir, "train.png"))
        sort_icon = QtGui.QIcon(os.path.join(Icons_Dir, "sort.png"))
        save_icon = QtGui.QIcon(os.path.join(Icons_Dir, "save.png"))
        cancel_icon = QtGui.QIcon(os.path.join(Icons_Dir, "cancel.png"))
        add_icon = QtGui.QIcon(os.path.join(Icons_Dir, "add.png"))
        remove_icon = QtGui.QIcon(os.path.join(Icons_Dir, "remove.png"))
        log_icon = QtGui.QIcon(os.path.join(Icons_Dir, "log.png"))
        settings_icon = QtGui.QIcon(os.path.join(Icons_Dir, "settings.png"))


        self.train_action = QAction(train_icon, "Train AI", self)
        self.train_action.triggered.connect(self.start_training)
        self.sort_action = QAction(sort_icon, "Sort Files", self)
        self.sort_action.triggered.connect(self.start_sorting)
        self.save_config_action = QAction(save_icon, "Save Config", self)
        self.save_config_action.triggered.connect(self.save_config)
        self.cancel_action_ = QAction(cancel_icon, "Cancel", self)
        self.cancel_action_.triggered.connect(self.cancel_action)
        
        basic_actions = [self.train_action, self.sort_action, self.save_config_action, self.cancel_action_]
        basic_group = self.create_group_widget("Basic Actions", basic_actions)
        ribbon.addWidget(basic_group)
        
        ribbon.addSeparator()
        
        # Group: Sources.
        add_icon = QtGui.QIcon(os.path.join(Icons_Dir, "add.png"))
        remove_icon = QtGui.QIcon(os.path.join(Icons_Dir, "remove.png"))
        source_actions = []
        self.add_source_action = QAction(add_icon, "Add", self)
        self.add_source_action.triggered.connect(self.add_source)
        self.remove_source_action = QAction(remove_icon, "Remove", self)
        self.remove_source_action.triggered.connect(self.remove_source)
        source_actions.extend([self.add_source_action, self.remove_source_action])
        source_group = self.create_group_widget("Sources", source_actions)
        ribbon.addWidget(source_group)
        
        ribbon.addSeparator()
        
        # Group: Destinations.
        dest_actions = []
        self.add_dest_action = QAction(add_icon, "Add", self)
        self.add_dest_action.triggered.connect(self.add_dest)
        self.remove_dest_action = QAction(remove_icon, "Remove", self)
        self.remove_dest_action.triggered.connect(self.remove_dest)
        dest_actions.extend([self.add_dest_action, self.remove_dest_action])
        dest_group = self.create_group_widget("Destinations", dest_actions)
        ribbon.addWidget(dest_group)
        
        ribbon.addSeparator()
        
        # Group: Advanced.
        log_icon = QtGui.QIcon(os.path.join(Icons_Dir, "log.png"))
        settings_icon = QtGui.QIcon(os.path.join(Icons_Dir, "settings.png"))
        advanced_actions = []
        self.toggle_log_action = QAction(log_icon, "Toggle Log", self)
        self.toggle_log_action.triggered.connect(self.toggle_log_area_action)
        self.settings_action = QAction(settings_icon, "Settings", self)
        self.settings_action.triggered.connect(self.open_settings_dialog)
        advanced_actions.extend([self.toggle_log_action, self.settings_action])
        advanced_group = self.create_group_widget("Advanced", advanced_actions)
        ribbon.addWidget(advanced_group)

    def setup_central_area(self):
        central = QWidget()
        main_layout = QVBoxLayout(central)
        
        # Create a fixed-size container for the status widgets.
        status_container = QWidget()
        status_container.setFixedHeight(60)  # Adjust the fixed height as needed.
        status_layout = QVBoxLayout(status_container)
        # Optionally remove margins. status_layout.setContentsMargins(0, 0, 0, 0) 
        status_layout.setSpacing(2) # Optionally add spacing.    
             
        self.current_stage_label = QLabel("Current Stage: Idle")
        status_layout.addWidget(self.current_stage_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimumWidth(200)
        status_layout.addWidget(self.progress_bar)
        
        # Add the fixed status container to the main layout.
        main_layout.addWidget(status_container)
        
        # Directories Config Panel using QSplitter for dynamic resizing.
        splitter = QtWidgets.QSplitter(Qt.Horizontal)
        
        # Source Directories Group.
        source_group = QGroupBox("Source Directories")
        src_layout = QVBoxLayout(source_group)
        self.source_list = QListWidget()
        self.source_list.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        for s in self.config.get("source_dirs", []):
            self.source_list.addItem(s)
        src_layout.addWidget(self.source_list)
        splitter.addWidget(source_group)
        
        # Destination Directories Group.
        dest_group = QGroupBox("Destination Directories")
        dest_layout = QVBoxLayout(dest_group)
        self.dest_list = QListWidget()
        self.dest_list.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        for d in self.config.get("dest_heads", []):
            self.dest_list.addItem(d)
        dest_layout.addWidget(self.dest_list)
        splitter.addWidget(dest_group)
        
        main_layout.addWidget(splitter)
        
        # Log Area (minimized by default)
        self.log_text = QtWidgets.QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setVisible(False)
        main_layout.addWidget(self.log_text)
        
        self.setCentralWidget(central)

    def add_source(self):
        directory = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Source Directory")
        if (directory):
            self.source_list.addItem(directory)

    def remove_source(self):
        for item in self.source_list.selectedItems():
            self.source_list.takeItem(self.source_list.row(item))

    def add_dest(self):
        directory = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Destination Directory")
        if (directory):
            self.dest_list.addItem(directory)

    def remove_dest(self):
        for item in self.dest_list.selectedItems():
            self.dest_list.takeItem(self.dest_list.row(item))

    def save_directories(self):
        # Update config with updated directories.
        src_dirs = [self.source_list.item(i).text() for i in range(self.source_list.count())]
        dest_dirs = [self.dest_list.item(i).text() for i in range(self.dest_list.count())]
        self.config.set("source_dirs", src_dirs)
        self.config.set("dest_heads", dest_dirs)
        self.config.save()
        self.append_log("Directory configuration saved.")

    def toggle_log_area(self):
        if self.log_toggle_btn.isChecked():
            self.log_text.setVisible(True)
            self.log_toggle_btn.setText("Less Details")
        else:
            self.log_text.setVisible(False)
            self.log_toggle_btn.setText("> More Details")

    def toggle_log_area_action(self):
        if self.log_text.isVisible():
            self.log_text.setVisible(False)
        else:
            self.log_text.setVisible(True)

    def open_settings_dialog(self):
        from settings_dialog import SettingsDialog
        dialog = SettingsDialog(self.config, self)
        if dialog.exec() == QtWidgets.QDialog.Accepted:
            self.append_log("Settings updated.")
            self.update_ui_from_config()  # Assuming this method refreshes the UI

    def add_source(self):
        directory = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Source Directory")
        if directory:
            self.source_list.addItem(directory)

    def remove_source(self):
        for item in self.source_list.selectedItems():
            self.source_list.takeItem(self.source_list.row(item))

    def add_dest(self):
        directory = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Destination Directory")
        if directory:
            self.dest_list.addItem(directory)

    def remove_dest(self):
        for item in self.dest_list.selectedItems():
            self.dest_list.takeItem(self.dest_list.row(item))
    
    def update_status(self, message):
        self.status_label.setText(f"Status: {message}")

    def log_file_operation(self, operation, filepath):
        self.undo_stack.append((operation, filepath))
        self.redo_stack.clear()  # Clear redo stack on new operation

    def undo_last_operation(self):
        if self.undo_stack:
            operation, filepath = self.undo_stack.pop()
            # Implement logic to reverse the operation
            self.redo_stack.append((operation, filepath))  # Add to redo stack

    def redo_last_operation(self):
        if self.redo_stack:
            operation, filepath = self.redo_stack.pop()
            # Implement logic to reapply the operation
            self.undo_stack.append((operation, filepath))  # Add back to undo stack

    def save_config(self):
        try:
            source_dirs = [self.source_list.item(i).text() for i in range(self.source_list.count())]
            dest_dirs = [self.dest_list.item(i).text() for i in range(self.dest_list.count())]
            self.config.set("source_dirs", source_dirs)
            self.config.set("dest_heads", dest_dirs)
            # Only update config from UI if related widgets exist.
            if hasattr(self, "score_threshold_edit"):
                self.config.set("score_threshold", float(self.score_threshold_edit.text()))
            if hasattr(self, "rule_strength_edit"):
                strengths = self.config.get("method_strengths", {})
                strengths["rule_based"] = float(self.rule_strength_edit.text())
                strengths["hybrid"] = float(self.hybrid_strength_edit.text())
                strengths["ai_based"] = float(self.ai_strength_edit.text())
                self.config.set("method_strengths", strengths)
            if hasattr(self, "update_mode_combo"):
                self.config.set("association_update_mode", self.update_mode_combo.currentText())
            if hasattr(self, "retain_old_checkbox"):
                self.config.set("retain_old_associations", self.retain_old_checkbox.isChecked())
            self.config.save()
            self.append_log("Configuration saved.")
            self.append_log("Current configuration updated.")
            self.update_ui_from_config()
        except Exception as e:
            self.append_log(f"Error saving configuration: {e}")

    def update_ui_from_config(self):
        # Refresh UI elements based on configuration.
        # This is a placeholder to update UI components if needed.
        pass

    def start_training(self):
        self.current_stage_label.setText("Current Stage: Generating Associations...")
        utils.prevent_sleep
        # Prevent system sleep (call your prevent_sleep() here if desired)
        # Load guidebook and set in sorter.
        guidebook_file = self.config.get("guidebook_file", "")
        if (guidebook_file and os.path.exists(guidebook_file)):
            try:
                with open(guidebook_file, "r", encoding="utf-8") as f:
                    guidebook = json.load(f)
                self.sorter.set_syllabus(guidebook)
                self.log_text.append("Guidebook loaded and set in sorter.")
            except Exception as e:
                self.log_text.append(f"Error loading guidebook: {e}")
                self.sorter.set_syllabus({})
        else:
            self.log_text.append("No guidebook file provided. Using empty associations.")
            self.sorter.set_syllabus({})
        # Get association update settings.
        associations_file = self.config.get("associations_file", "associations.json")
        update_mode = self.config.get("association_update_mode", "full")
        retain_old = self.config.get("retain_old_associations", True)
        dest_dir = self.sorter.dest_heads[0] if self.sorter.dest_heads else os.getcwd()
        # Start AssociationsWorker first.
        self.assoc_worker = AssociationsWorker(dest_dir, guidebook_file, associations_file, update_mode, retain_old)
        self.assoc_worker.progress.connect(lambda p: self.progress_bar.setValue(p))
        self.assoc_worker.log_signal.connect(lambda msg: self.append_log(msg))
        self.assoc_worker.finished.connect(self.after_associations_generated)
        self.assoc_worker.start()
        self.cancel_btn.setEnabled(True)
        utils.allow_sleep()

    def after_associations_generated(self, associations):
        self.current_stage_label.setText("Current Stage: Training AI Model...")
        utils.prevent_sleep()
        self.log_text.append("Associations generation completed. Starting AI model training...")
        dest_dir = self.sorter.dest_heads[0] if self.sorter.dest_heads else os.getcwd()
        self.train_worker = TrainWorker(self.sorter.syllabus, dest_dir)
        self.train_worker.progress.connect(lambda p: self.progress_bar.setValue(int(p)))
        self.train_worker.log_signal.connect(lambda msg: self.append_log(msg))
        self.train_worker.finished.connect(lambda: self.append_log("Training Completed!"))
        self.train_worker.start()
        utils.allow_sleep()

    def start_sorting(self):
        self.current_stage_label.setText("Current Stage: Sorting Files...")
        utils.prevent_sleep()  # Prevent system sleep during sorting
        self.sorter.source_dirs = [self.source_list.item(i).text() for i in range(self.source_list.count())]
        self.sorter.dest_heads = [self.dest_list.item(i).text() for i in range(self.dest_list.count())]
        associations_file = self.config.get("associations_file", "associations.json")
        self.sorter.load_associations(associations_file)
        # Create and start new SortWorker with the FileSorter connection.
        self.sort_worker = SortWorker(self.sorter)
        self.sort_worker.progress.connect(self.progress_bar.setValue)
        self.sort_worker.log_signal.connect(lambda msg: self.append_log(msg))
        self.sort_worker.finished.connect(lambda log: self.append_log("Sorting Completed!") or self.append_log(json.dumps(log, indent=4)))
        self.sort_worker.start()
        self.sort_action.setEnabled(False)
        self.cancel_action_.setEnabled(True)
        utils.allow_sleep()  # Allow system sleep again

    def cancel_action(self):
        # Cancel associations worker if running.
        if hasattr(self, "assoc_worker") and self.assoc_worker and self.assoc_worker.isRunning():
            self.assoc_worker.requestInterruption()
            self.assoc_worker.wait()
            self.append_log("Associations generation cancelled!")
        # Cancel training worker: call its stop() to set transformer_ai.cancelled flag.
        if hasattr(self, "train_worker") and self.train_worker and self.train_worker.isRunning():
            self.train_worker.stop()      # Sets transformer_ai.cancelled to True.
            self.train_worker.requestInterruption()
            self.train_worker.wait()
            self.append_log("Training cancelled!")
        # Cancel sorting worker if running.
        if hasattr(self, "sort_worker") and self.sort_worker and self.sort_worker.isRunning():
            self.sort_worker.requestInterruption()
            self.sort_worker.wait()
            self.append_log("Sorting cancelled!")
        self.sort_action.setEnabled(True)       # Changed from self.sort_btn
        self.cancel_action_.setEnabled(False)     # Changed from self.cancel_btn
        utils.allow_sleep()

    def append_log(self, text):
        # Clean the text to avoid empty lines
        cleaned = text.strip()
        if cleaned:
            self.log_text.append(cleaned)

    def open_wiki(self):
        import webbrowser
        webbrowser.open("https://your-wiki-url.com")  # Replace with actual wiki URL

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    style_sheet = """
    QWidget {
        font-family: 'Segoe UI';
        font-size: 12pt;
        background-color: #fafafa;
        color: #212121;
    }
    QGroupBox {
        font-weight: bold;
        border: 1px solid #e0e0e0;
        margin-top: 10px;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 5px;
    }
    QPushButton {
        background-color: #0a84ff;
        color: white;
        border: none;
        padding: 8px 12px;
        border-radius: 4px;
    }
    QPushButton:hover {
        background-color: #0066cc;
    }
    QPushButton:pressed {
        background-color: #004c99;
    }
    QProgressBar {
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
    QListWQProgressBar {
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
    get,QListWQProgressBar {
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
    get QLineEdit {
        border: 1px solid #e0e0e0;
        padding: 5px;
        background-color: white;
    }
    """
    app.setStyleSheet(style_sheet)
    config = Config()
    window = MainWindow(config)
    window.show()
    sys.exit(app.exec())
