# An example running the UI plugin in standalone way.

from PyQt5.QtWidgets import QApplication
from PyQt5 import uic
import sys

app = QApplication(sys.argv)
ui_obj = uic.loadUi("SOLPSplugin.ui")
ui_obj.show()

sys.exit(app.exec_())