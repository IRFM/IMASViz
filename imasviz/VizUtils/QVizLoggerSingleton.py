from PySide2.QtCore import Signal, QObject
import logging

class QVizLoggerSingleton( logging.Handler ):
    """ Logger for handling passing the information and error messages to logWidget.
    """

    def __new__(cls):
      if not hasattr(cls, 'instance'):
        cls.instance = super(QVizLoggerSingleton, cls).__new__(cls)
      return cls.instance	    

    def __init__(self, use_rich_text=True):
        super().__init__()
        formatter = Formatter('%(asctime)s|%(levelname)s|%(message)s|', '%d/%m/%Y %H:%M:%S')
        self.setFormatter(formatter)
        self.use_rich_text = use_rich_text
        self.new_signal_emiter = SignalEmiter()

    def emit(self, record):
        msg = self.format(record)
        if self.use_rich_text:
            if 'ERROR' in msg or 'WARNING' in msg:
                msg = "<font color='red'>" + msg + "</font>"
            elif 'INFO' in msg:
                msg = "<font color='black'>" + msg + "</font>"
        self.new_signal_emiter.send_signal(msg)


class SignalEmiter( QObject ):

  new_signal = Signal(object)

  def __init__(self):
    super(SignalEmiter, self).__init__()

  def send_signal(self, msg):
    self.new_signal.emit(msg)


class Formatter(logging.Formatter):

    def formatException(self, ei):
        result = super(Formatter, self).formatException(ei)
        return result

    def format(self, record):
        s = super(Formatter, self).format(record)
        if record.exc_text:
            s = s.replace('\n', '')
        return s
