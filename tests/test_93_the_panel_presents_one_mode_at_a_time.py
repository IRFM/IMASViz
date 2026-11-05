# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The case panel presents one mode at a time, and the free mode hides the controls of the list it is not showing.

Choosing "Saisie libre (URI)" left the controls of the *Cas locaux* list
sitting there doing nothing -- the Affichage box, the Trier par box with its
direction, the Afficher HDF5/MDS+ boxes -- because they act on a list that had
not been shown. What a mode change hides is now answered by the selector itself
(``presentAs``), so the frame only says which mode it is in, and the selector
says what that mode shows and what it takes away. The buttons stay in both:
a free URI can still be opened, copied, or turned in from a folder.

The assertions read ``isHidden()`` and not ``isVisible()``: the tests build
the widgets without showing them, so ``isVisible()`` answers "not on a screen"
for a widget that was never hidden -- the on-screen state is exactly what
``isHidden()`` records.
"""

import pytest
from PySide6.QtWidgets import QWidget

from imasviz.VizGUI.QtVIZ_GUI import GUIFrame
from imasviz.VizGUI.VizWidgets.QVizCaseSelector import QVizCaseSelector


def hidden(*widgets):
    return [w.isHidden() for w in widgets]


def test_the_free_mode_hides_the_list_and_every_control_of_it(qapp):
    """The free line is shown; the list and its whole controls row are not.

    A free URI is subject to none of the shape, the sort or the protocol, so
    none of them is left on the panel to promise something to a list the user
    is not looking at; and the list itself is not left under the free line.
    """
    sel = QVizCaseSelector()
    sel.presentAs('free')
    assert sel.listView.isHidden() is True
    assert sel.freeText.isHidden() is False
    assert hidden(
        sel.viewShapeLabel, sel.viewBox,
        sel.sortKeyLabel, sel.sortKeyBox, sel.sortDirButton,
        sel.filterLabel, sel.filterHDF5, sel.filterMDS) \
        == [True] * 8
    # The buttons act on whichever of the two is visible, and both need them.
    assert hidden(sel.openButton, sel.copyButton, sel.folderButton) \
        == [False] * 3


def test_the_list_mode_shows_the_list_and_its_controls(qapp):
    """Choosing the list again puts the list and its controls back.

    The free mode must not be a one-way door: the controls a user set before
    switching away are theirs still, and the only thing the switch cost is the
    time it took while they were out of sight.
    """
    sel = QVizCaseSelector()
    sel.presentAs('free')
    sel.presentAs('list')
    assert sel.listView.isHidden() is False
    assert sel.freeText.isHidden() is True
    assert hidden(
        sel.viewShapeLabel, sel.viewBox,
        sel.sortKeyLabel, sel.sortKeyBox, sel.sortDirButton,
        sel.filterLabel, sel.filterHDF5, sel.filterMDS) \
        == [False] * 8


def test_a_mode_outside_the_two_is_refused_by_name(qapp):
    """A word the panel does not present is named, not guessed.

    A caller that misspells its mode would otherwise get a panel that shows
    neither presentation -- a half-present UI the user had to notice by its
    absence. Refusing by name is what makes the misspelling show up at the
    wrong caller rather than on the screen.
    """
    sel = QVizCaseSelector()
    with pytest.raises(ValueError, match='magic'):
        sel.presentAs('magic')
    with pytest.raises(ValueError, match='LIST'):
        sel.presentAs('LIST')


class AFrame:
    """The two things `onModeChanged` asks of its owner, and nothing else.

    Building the real `GUIFrame` would build the whole start window -- menus,
    controller, the browser -- to reach one method that sets two visibilities
    and asks the selector to present itself.
    """

    def __init__(self):
        self.uriPanel = QVizCaseSelector()
        self.legacyPanel = QWidget()


def test_the_controls_fit_the_panel_width_without_squeezing(qapp):
    """The panel is the eighth of the window, and its controls must fit it.

    A single row of all the controls does not fit in that width -- the boxes
    are squeezed until they overlap, which is the complaint this was written
    to answer. Laid the way they are, each control holds its own ground at
    the panel width: no two of them occupy the same place. The assertion is
    on the named controls, and not on every child of the selector, because a
    checkbox holds its own label inside it, which is what it is for.
    """
    sel = QVizCaseSelector()
    sel.resize(160, 300)
    sel.show()
    qapp.processEvents()
    try:
        controls = [w for w in sel._listControls if not w.isHidden()]
        rects = []
        for w in controls:
            rect = w.geometry()
            if rect.width() > 0 and rect.height() > 0:
                rects.append((w, rect))
        assert len(rects) >= 2, 'no control to check: nothing laid out'
        for i, (first, a) in enumerate(rects):
            for other, b in rects[i + 1:]:
                overlap = a.intersected(b)
                assert overlap.width() == 0 or overlap.height() == 0, \
                    '%s and %s share %dx%d px' % (
                        type(first).__name__,
                        type(other).__name__,
                        overlap.width(), overlap.height())
    finally:
        sel.close()


def test_the_mode_switch_presents_one_mode_at_a_time(qapp):
    """What the mode switch names is what the panel shows, at that index.

    Free mode: the free line, and the controls gone. List mode: the list and
    its controls back, and the free line gone. Legacy: the legacy panel in
    front, the selector off the screen wholesale. And back again, because the
    switch is walked more than once in a run.
    """
    frame = AFrame()

    GUIFrame.onModeChanged(frame, 1)
    assert frame.uriPanel.isHidden() is False
    assert frame.uriPanel.freeText.isHidden() is False
    assert frame.uriPanel.listView.isHidden() is True
    assert frame.uriPanel.viewBox.isHidden() is True

    GUIFrame.onModeChanged(frame, 0)
    assert frame.uriPanel.listView.isHidden() is False
    assert frame.uriPanel.freeText.isHidden() is True
    assert frame.uriPanel.viewBox.isHidden() is False

    GUIFrame.onModeChanged(frame, 2)
    assert frame.uriPanel.isHidden() is True
    assert frame.legacyPanel.isHidden() is False

    GUIFrame.onModeChanged(frame, 1)
    assert frame.uriPanel.isHidden() is False
    assert frame.uriPanel.freeText.isHidden() is False
    assert frame.uriPanel.viewBox.isHidden() is True
