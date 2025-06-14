from PyQt5.QtCore    import Qt, QPoint
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel, QToolButton, QStyle
from PyQt5.QtGui     import QIcon

class TitleBar(QWidget):
    """A frameless, theme-aware title bar with proper icons."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._parent   = parent
        self._drag_pos = None
        self.setFixedHeight(30)

        # Title text
        self.title_label = QLabel(self._parent.windowTitle(), self)
        self.title_label.setStyleSheet("margin-left:8px;")

        # Buttons
        self.btn_min   = QToolButton(self)
        self.btn_max   = QToolButton(self)
        self.btn_close = QToolButton(self)

        for btn, role in (
            (self.btn_min,   QStyle.SP_TitleBarMinButton),
            (self.btn_max,   QStyle.SP_TitleBarMaxButton),
            (self.btn_close, QStyle.SP_TitleBarCloseButton),
        ):
            icon = self.style().standardIcon(role)
            btn.setIcon(icon)
            btn.setFixedSize(24, 24)

        # Connect
        self.btn_min.clicked.connect(self._parent.showMinimized)
        self.btn_max.clicked.connect(self._onMaxRestore)
        self.btn_close.clicked.connect(self._parent.close)

        # Layout
        lay = QHBoxLayout(self)
        lay.setContentsMargins(4, 0, 4, 0)
        lay.addWidget(self.title_label)
        lay.addStretch()
        lay.addWidget(self.btn_min)
        lay.addWidget(self.btn_max)
        lay.addWidget(self.btn_close)

    def _onMaxRestore(self):
        self._parent.toggleMaxRestore()
        # swap icon
        role = QStyle.SP_TitleBarNormalButton if self._parent.isMaximized() \
               else QStyle.SP_TitleBarMaxButton
        self.btn_max.setIcon(self.style().standardIcon(role))

    def mousePressEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            self._drag_pos = ev.globalPos() - self._parent.frameGeometry().topLeft()

    def mouseMoveEvent(self, ev):
        if self._drag_pos:
            self._parent.move(ev.globalPos() - self._drag_pos)

    def mouseReleaseEvent(self, ev):
        self._drag_pos = None

    def updateStyle(self, dark: bool):
        """No-op: theme switching removed, always use light style."""
        self.setStyleSheet("background:#DDD; color:black;")
        self.title_label.setStyleSheet("margin-left:8px; color:black;")
