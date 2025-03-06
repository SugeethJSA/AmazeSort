from PySide6 import QtWidgets, QtCore

class SettingsDialog(QtWidgets.QDialog):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("Advanced Configuration Settings")
        self.resize(500, 400)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        
        # Score Threshold and Method Strengths
        advanced_group = QtWidgets.QGroupBox("Advanced Settings")
        adv_layout = QtWidgets.QFormLayout(advanced_group)
        
        self.score_threshold_edit = QtWidgets.QLineEdit(str(self.config.get("score_threshold", 40)))
        adv_layout.addRow("Score Threshold:", self.score_threshold_edit)
        
        method_strengths = self.config.get("method_strengths", {"rule_based": 0.3, "hybrid": 0.5, "ai_based": 0.2})
        self.rule_based_edit = QtWidgets.QLineEdit(str(method_strengths.get("rule_based", 0.3)))
        self.hybrid_edit = QtWidgets.QLineEdit(str(method_strengths.get("hybrid", 0.5)))
        self.ai_based_edit = QtWidgets.QLineEdit(str(method_strengths.get("ai_based", 0.2)))
        adv_layout.addRow("Rule-Based Strength:", self.rule_based_edit)
        adv_layout.addRow("Hybrid Strength:", self.hybrid_edit)
        adv_layout.addRow("AI-Based Strength:", self.ai_based_edit)
        
        # Deduplication Options
        dedup_group = QtWidgets.QGroupBox("Duplicate Handling")
        dedup_layout = QtWidgets.QFormLayout(dedup_group)
        dup_handling = self.config.get("duplicate_handling", {"skip_duplicates": True, "rename_duplicates": False})
        self.skip_dup_checkbox = QtWidgets.QCheckBox("Skip duplicates")
        self.skip_dup_checkbox.setChecked(dup_handling.get("skip_duplicates", True))
        self.rename_dup_checkbox = QtWidgets.QCheckBox("Rename duplicates")
        self.rename_dup_checkbox.setChecked(dup_handling.get("rename_duplicates", False))
        dedup_layout.addRow(self.skip_dup_checkbox)
        dedup_layout.addRow(self.rename_dup_checkbox)
        
        # Association update options
        assoc_group = QtWidgets.QGroupBox("Association Update Settings")
        assoc_layout = QtWidgets.QFormLayout(assoc_group)
        self.update_mode_combo = QtWidgets.QComboBox()
        self.update_mode_combo.addItems(["full", "incremental"])
        current_mode = self.config.get("association_update_mode", "full")
        index = self.update_mode_combo.findText(current_mode)
        if index >= 0:
            self.update_mode_combo.setCurrentIndex(index)
        self.retain_old_checkbox = QtWidgets.QCheckBox("Retain old associations")
        self.retain_old_checkbox.setChecked(self.config.get("retain_old_associations", True))
        assoc_layout.addRow("Update Mode:", self.update_mode_combo)
        assoc_layout.addRow("", self.retain_old_checkbox)
        
        layout.addWidget(advanced_group)
        layout.addWidget(dedup_group)
        layout.addWidget(assoc_group)
        
        # Save/Cancel Buttons
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.addStretch()
        save_btn = QtWidgets.QPushButton("Save")
        save_btn.clicked.connect(self.accept)
        cancel_btn = QtWidgets.QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
    
    def accept(self):
        # Update configuration settings.
        try:
            self.config.set("score_threshold", float(self.score_threshold_edit.text()))
        except ValueError:
            pass
        method_strengths = {
            "rule_based": float(self.rule_based_edit.text()),
            "hybrid": float(self.hybrid_edit.text()),
            "ai_based": float(self.ai_based_edit.text())
        }
        self.config.set("method_strengths", method_strengths)
        dup_settings = {
            "skip_duplicates": self.skip_dup_checkbox.isChecked(),
            "rename_duplicates": self.rename_dup_checkbox.isChecked()
        }
        self.config.set("duplicate_handling", dup_settings)
        self.config.set("association_update_mode", self.update_mode_combo.currentText())
        self.config.set("retain_old_associations", self.retain_old_checkbox.isChecked())
        super().accept()
