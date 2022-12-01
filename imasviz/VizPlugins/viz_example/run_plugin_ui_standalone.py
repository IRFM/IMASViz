# An example running the UI plugin in standalone way.

from PySide2.QtWidgets import QApplication
from PySide2 import uic
import sys

app = QApplication(sys.argv)
ui_obj = uic.loadUi("examplePlugin.ui")
ui_obj.show()

sys.exit(app.exec_())
