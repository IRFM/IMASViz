# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

from PySide6.QtCore import Signal, QObject
import logging

class QVizLogger( logging.Handler ):
    """ Logger for handling passing the information and error messages to logWidget.
    """

    def __init__(self, use_rich_text=True):
        super().__init__()
        formatter = Formatter('%(asctime)s|%(levelname)s|%(message)s|', '%d/%m/%Y %H:%M:%S')
        self.setFormatter(formatter)
        self.use_rich_text = use_rich_text
        self.new_signal_emiter = SignalEmiter()

    def emit(self, record):
        msg = self.format(record)
        if self.use_rich_text:
            # The colour of the level, from the theme the application wears --
            # never a hardcoded one. Two readings used to decide it: whether the
            # formatted line contained the word ERROR or WARNING, and a fixed
            # red or black. The first coloured a line whose *text* happened to
            # quote an error while its level was INFO; the second painted every
            # information line in black, which is invisible the moment the log
            # panel is dressed for the dark theme.
            msg = "<font color='%s'>%s</font>" % (logColour(record.levelno), msg)
        self.new_signal_emiter.send_signal(msg)


def logColour(level):
    """The colour one log level is painted with, asked of the theme.

    Imported where it is asked and not at the top of the module: the palette
    lives in ``VizGUI``, which imports this package, so a module-level import
    would be a cycle.
    """
    from imasviz.VizGUI.VizGuiCustomization.QVizStyle import logColour as asked
    return asked(level)


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
