# Copyright holders : Commissariat à l'Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.
#
# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************
"""A web turn must not take the application off the screen.

The session lives on: the next turn's `show_window` / `focus_window` have
to be able to bring a figure forward, and a sub-window whose top-level
was hidden cannot come back -- Qt reports it `visible: false` whatever
`show()` is asked of it (measured: after one turn the whole session
answered `visible: false` for every figure, and `show_window` /
`focus_window` kept answering `visible: false` to every retry the agent
made). The one-shot agent mode and the REPL/web exit paths hide at
*exit*, when the process is leaving -- the end of a turn of a session
that stays open is not that moment.
"""

from imasviz.VizAgent.llm_client import LLMResponse

from test_119_viz_web_session import (
    CASE_URI, FakeLLMClient, FakeWindow, build, inWorker)


class RecordingWindow(FakeWindow):
    """The `FakeWindow` that records every `hide()` it is given."""

    def __init__(self):
        self.hide_calls = 0

    def hide(self):
        self.hide_calls += 1


def test_a_web_turn_keeps_the_application_on_screen(qapp, tmp_path):
    """After a turn the application is still shown -- the session is
    long-lived, and `show_window` / `focus_window` of the next turn must
    be able to bring a figure forward. A sub-window of a hidden
    top-level cannot be shown again (it reports `visible: false` to
    every `show()`), so a turn that hides the application makes every
    following "show me figure N" answer `visible: false` -- the state
    the agent reported and the user saw. The capture of the turn must
    still be the figure it drew, whatever the screen does after."""
    window = RecordingWindow()
    session, _ = build(qapp, tmp_path)
    # The real web session passes the application it runs under (see
    # `viz_web/run.py`); `build` passes `None`, which is the state the
    # settle skips -- give this session the same shape as the one the
    # server builds.
    session.app = qapp
    session.window = window

    session.agent.llm = FakeLLMClient([
        LLMResponse(tool_calls=[
            {'name': 'plot_one',
             'args': {'uri': CASE_URI, 'path': 'core.ion[0].temp'}}],
            content=''),
        LLMResponse(content='tracé.', finish_reason='stop'),
    ])

    record = inWorker(lambda: session.runTurn('trace une figure'), qapp)

    # The turn kept the application on the screen:
    assert window.hide_calls == 0, \
        'the turn hid the application (%d calls): a sub-window of a ' \
        'hidden top-level can never be brought forward any more, and ' \
        'show_window / focus_window answer visible: false to every ' \
        'later ask' % window.hide_calls
    # and the figure it drew is still the capture of the turn:
    assert record['image_files'] == ['SlicesPlot1.png'], \
        record['image_files']


if __name__ == '__main__':
    import sys
    import pytest
    sys.exit(pytest.main([__file__, '-v']))
