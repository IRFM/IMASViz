# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""Run one function on the GUI thread from any worker thread, and wait for it.

The MCP SDK answers tool calls on its own worker threads. Those threads may
compute, log, or post events -- but a thread that does not own a widget must
not touch one: measured on this Qt 6.6.3 stack the failure is not a warning
but a hang, the thread staying inside `QWindow::close()` past a 20 s watchdog
while the GUI thread pumped events (see `tests/` and the QThread notes in
`imasviz/VizGUI/VizPlot/`). So every gesture an agent asks for goes through
here: it is put in a queue the GUI thread drains, and its answer -- value or
exception -- comes back over the same queue.

The waiting side blocks on a `threading.Event`, not on a `QEventLoop`: the
dispatcher is the only object with a thread affinity at all, and the event is
the one piece of state two threads genuinely share.
"""

import threading

from PySide6.QtCore import QObject, Qt, Signal


class GuiDispatcher(QObject):
    """A function queue the GUI thread drains, asked from any other thread.

    Built on the GUI thread -- its signals only make sense there -- and then
    handed to whoever calls :meth:`call`.
    """

    _request = Signal(object)

    def __init__(self, parent=None):
        super(GuiDispatcher, self).__init__(parent)
        self._request.connect(self._run, Qt.QueuedConnection)

    # -- asked from the worker thread -------------------------------------

    def call(self, function, timeout=300.0):
        """Run `function` on the GUI thread; return its value, or raise.

        The function holds no widget of its own: it is the gesture itself
        (an `imasviz` command), and it runs where such a gesture may run.
        When the GUI thread does not answer in time, a `TimeoutError` that
        names the wait is what comes back -- the gesture is still running
        where it was put, and a second copy of it must not be started.
        """
        shared = {'event': threading.Event()}
        self._request.emit((shared, function))
        if not shared['event'].wait(timeout):
            raise TimeoutError(
                'The GUI thread did not answer in %.0f s; the gesture is '
                'still running there and must not be asked again.' % timeout)
        error = shared.get('error')
        if error is not None:
            raise error
        return shared.get('result')

    # -- on the GUI thread --------------------------------------------------

    def _run(self, payload):
        shared, function = payload
        try:
            shared['result'] = function()
        except BaseException as error:
            shared['error'] = error
        finally:
            shared['event'].set()
