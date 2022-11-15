from PyQt5.QtCore import pyqtSignal, QObject
import logging


class QVizLogger(QObject, logging.Handler):
    """ Logger for handling passing the information and error messages to logWidget.
    """
    new_record = pyqtSignal(object)
    handler = None

    def __init__(self, use_rich_text=True):
        super().__init__()
        super(logging.Handler).__init__()
        formatter = Formatter('%(asctime)s|%(levelname)s|%(message)s|', '%d/%m/%Y %H:%M:%S')
        self.setFormatter(formatter)
        self.use_rich_text = use_rich_text

    def emit(self, record):
        msg = self.format(record)
        if self.use_rich_text:
            if 'ERROR' in msg or 'WARNING' in msg:
                msg = "<font color='red'>" + msg + "</font>"
            elif 'INFO' in msg:
                msg = "<font color='black'>" + msg + "</font>"
        self.new_record.emit(msg)

    @staticmethod
    def getHandler(use_rich_text=True):
        if QVizLogger.handler is None:
            QVizLogger.handler = QVizLogger(use_rich_text)
            logging.getLogger().addHandler(QVizLogger.handler)
        return QVizLogger.handler


class Formatter(logging.Formatter):

    def formatException(self, ei):
        result = super(Formatter, self).formatException(ei)
        return result

    def format(self, record):
        s = super(Formatter, self).format(record)
        if record.exc_text:
            s = s.replace('\n', '')
        return s
