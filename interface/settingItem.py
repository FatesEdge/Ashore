"""Reusable settings item composition."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLayout, QSizePolicy, QVBoxLayout, QWidget


class SettingItem(QWidget):
    """A settings title followed by its control block."""

    def __init__(self, label, field, parent=None):
        super().__init__(parent)
        self.setProperty('settingItem', True)
        self.label = label
        self.label.setProperty('settingsFormLabel', True)
        self.label.setWordWrap(True)
        self.label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(self.label)

        if isinstance(field, QLayout):
            self.fieldHost = QWidget(self)
            self.fieldHost.setProperty('settingFieldHost', True)
            self.fieldHost.setLayout(field)
            self.fieldHost.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            layout.addWidget(self.fieldHost)
            self.field = self.fieldHost
        else:
            self.fieldHost = None
            self.field = field
            if field.sizePolicy().horizontalPolicy() == QSizePolicy.Policy.Expanding:
                layout.addWidget(field)
            else:
                layout.addWidget(
                    field, 0, Qt.AlignmentFlag.AlignLeft)

    def titleText(self):
        return self.label.text()
