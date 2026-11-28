# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The window chrome of a window a user can see.

The pure helpers the window machinery spells its titles with, the subwindow
a frame is embedded in, the close rule a top-level window answers, and the
record the *Windows* menu draws a line for. Nothing here imports ``Viz_API``
-- the framework that fills those records imports this module.
"""

import weakref

import shiboken6

from PySide6.QtWidgets import QMdiSubWindow


def getNodePath(node):
    # print("getNodePath=", node.getPath())
    return node.getParametrizedDataPath()


def figureDisplayHeading(heading):
    """The word the title bar paints for a figure key.

    New keys — ``Plot1``, ``Image2`` — read with a space between
    the word and the number: ``Plot 1``, ``Image 2``. Old keys
    from saved sessions — ``SlicesPlot1``, ``SlicesImage1`` — read
    the same, so a session saved before the rename still shows the
    word the user expects. Whatever carries its own name
    (``PlotView:1``, ``TablePlotView:0``, ``EquiPlotView:1``,
    ``Agent:0``) passes through untouched — the digit after the
    prefix is what tells a key from a name.
    """
    if heading.startswith('SlicesPlot'):
        return 'Plot ' + heading[len('SlicesPlot'):]
    if heading.startswith('SlicesImage'):
        return 'Image ' + heading[len('SlicesImage'):]
    if (heading.startswith('Plot') and len(heading) > 4
            and heading[4].isdigit()):
        return 'Plot ' + heading[4:]
    if (heading.startswith('Image') and len(heading) > 5
            and heading[5].isdigit()):
        return 'Image ' + heading[5:]
    return heading


def titleWithCases(title, uris, fromIds=None):
    """The window title of a registered window, with the case or cases it serves.

    `title` — the key today, or the plugin's own heading — is read as
    `figureDisplayHeading` answers it, and one short label follows for every
    case, separated by `; `. A figure
    drawn from two cases carries both; a window no case serves -- a frame
    registered without any node -- carries its heading alone, so the answer
    reads exactly `title` again instead of a trailing `— ` nobody could
    explain. The plugin windows name their one case: the Profiles panel and
    the Equilibrium chart both serve the case of the shot view they were
    opened from, and both name the IDS their entry ran on, through `fromIds`
    -- ``PlotView:1 — west-54924.0 (from interferometer)`` — because a case
    holds several IDS and the key alone says nothing about which of them drew
    the window.

    The short label, not the URI, is what fits the one line the title bar is:
    the whole URI is where the user hovers for it, and it is `caseTooltip`.

    A case a node registered without one -- ``None``, the empty string -- is
    no case at all and drops out before the heading is read, so a list of
    nothing-that-is-named answers ``title`` again instead of raising inside
    the label read.

    :param title:   (str) what the window was registered under
    :param uris    : (iterable of str) the case URIs the window serves --
                     ``casesServedBy`` for a figure, ``[uri]`` for a plugin
                     window of one case
    :param fromIds : (str, optional) the name of the IDS the window's entry
                     ran on, for a plugin window of one case -- the ``ids``
                     of its ``QVizPluginWindow`` stamp
    :returns: (str) the title to paint
    """
    title = figureDisplayHeading(title)
    uris = [uri for uri in (uris or ()) if uri]
    result = title
    if uris:
        # Imported here the way CreateDataTree imports the shot view frame: the
        # module that owns `caseLabel` is the data source, whose import chain
        # this one feeds, and the two must not look at each other at import time.
        from imasviz.VizDataSource.QVizIMASDataSource import caseLabel
        labels = []
        for uri in uris:
            label = caseLabel(uri)
            if label not in labels:
                labels.append(label)
        result = title + ' — ' + '; '.join(labels)
    if fromIds:
        result = result + ' (from %s)' % fromIds
    return result


def caseTooltip(uris):
    """What the hover over a window's title bar says: the whole URI, one per line.

    The title line carries the short labels — they are the ones guaranteed to
    fit — and the tooltip carries what a short label leaves out. A window of
    two cases names both, in the order `casesServedBy` answers them.

    :param uris: (iterable of str)
    :returns: (str) the tooltip text, or None for a window no case serves
    """
    uris = [uri for uri in (uris or ()) if uri]
    return '\n'.join(uris) if uris else None


#: The size the embed hands a figure window that settles below a readable
#: size (`addPlotWidgetToMDI`). A subwindow that settles small is the
#: unreadable screenshot the user reported, and `QWidget.grab()` renders at
#: whatever size the window is -- so this is the size that makes a freshly
#: drawn figure a picture the page can serve and the user can read.
#: Showing a window (`focus_window`) is not a resize: it keeps the size
#: the user gave it, and only named pixels (`width`/`height`) move it.
DEFAULT_FIGURE_SIZE = (1280, 800)

class QVizMdiSubWindow(QMdiSubWindow):
    """The MDI window a frame is embedded in -- a figure or a case view.

    The window is what the user closes when no command is involved, so it is
    what applies the close rule to the frame it holds. PySide6 6.6 does not
    expose ``QMdiSubWindow.aboutToClose``, hence the close event.

    A case view used to be embedded in a bare ``QMdiSubWindow``, which receives
    no close event of its own: the close box hid the window and said nothing to
    anyone. It is embedded here now so that the one rule reaches all three
    families of window -- figures, case views, and the top-level windows a
    plugin draws (:class:`QVizClosableWindow`).
    """

    def __init__(self, imas_viz_api):
        super(QVizMdiSubWindow, self).__init__()
        # Held weakly, because the api reaches the frame this window is the
        # parent of: a strong reference here closes a cycle through a Qt widget,
        # and a widget freed by the cyclic collector is freed while Qt still
        # owes it a paint event. The api lives as long as the session does --
        # the menu controller that opened the case holds it.
        self.imas_viz_api = weakref.ref(imas_viz_api)

    def closeEvent(self, event):
        super(QVizMdiSubWindow, self).closeEvent(event)
        api = self.imas_viz_api()
        if api is None:
            return
        if api.closeFromTitleBar(self.widget()):
            # The frame is out of the bookkeeping: take the window with it, so
            # the MDI area does not keep a hidden window nobody can reach. The
            # hide comes first -- a hide reaches the children recursively, which
            # is how the frames nested in this one leave the paint queue before
            # Qt deletes them.
            self.hide()
            self.deleteLater()


class QVizClosableWindow:
    """The close rule for a window that is its own top level.

    A plugin panel is registered like a figure and closed like a window, but it
    is not inside the MDI area, so no :class:`QVizMdiSubWindow` sees its close
    box. A plugin that draws such a window mixes this in and answers
    ``windowApi()`` with the api it registers its window in.
    """

    def windowApi(self):
        """The api the window is registered in, or None.

        Left to the window: the framework cannot know where a plugin keeps its
        collaborator, and a window that answers nothing is a window the close
        box cannot take out of the bookkeeping.
        """
        return None

    def closeEvent(self, event):
        super().closeEvent(event)
        api = self.windowApi()
        if api is None:
            return
        api.closeFromTitleBar(self)


class QVizWindowRecord:
    """One window the user can see, as the *Windows* menu asks for it.

    The frame and the api are both held weakly. The menu hands a record to a
    QAction, and on a shot view that QAction lives in a menu bar the frame owns:
    a strong reference either way is a cycle through a Qt widget, and that is
    the shape that frees a widget on the cyclic collector while Qt still owes it
    a paint event. A record whose frame is gone answers ``None`` and the line
    does nothing -- the menu is rebuilt on every opening anyway.
    """

    def __init__(self, kindLabel, iconLabel, label, frame, figureKey, api,
                 cases=()):
        """
        Arguments:
            kindLabel (str) : the group the line is drawn in -- a case view, or
                              one of the names in ``FigureTypes.MENU_ORDER``
            iconLabel (str) : the ``GlobalIcons`` name, or None
            label     (str) : what the user reads on the line
            frame     (QWidget) : the window's content
            figureKey (str) : the key the window answers to, or None for a case
                              view -- which is addressed by its frame
            api       (Viz_API) : the bookkeeping the window lives in
            cases     (tuple) : the case URIs the window serves -- its own for
                              a case view, every origin a figure drew a curve
                              from for a figure. A window a plugin drew
                              serves the case of the shot view it was opened
                              from -- what both registered plugins carry, the
                              node of one being ``None`` because neither draws
                              a curve of its own -- and a window no case
                              serves (a frame registered without any node)
                              answers ``()``. What the *Windows* menu groups
                              by and what "isolating a case" and "closing a
                              case" act on.
        """
        self.kindLabel = kindLabel
        self.iconLabel = iconLabel
        self.label = label
        self.figureKey = figureKey
        self.cases = tuple(cases)
        self._frame = weakref.ref(frame)
        self._api = weakref.ref(api)

    def frame(self):
        """The window's content, or None once Qt has taken it away.

        A frame released with ``deleteLater`` keeps its Python wrapper as long as
        anything else holds a reference to it, and asking that wrapper anything
        then answers ``RuntimeError: Internal C++ object ... already deleted``. A
        menu line opened before another gesture closed its window is exactly that
        -- so the record answers nothing and the stale line costs nothing, which
        is what :meth:`Viz_API.DeleteFigure` does for a key nobody holds.
        """
        frame = self._frame()
        if frame is None or not shiboken6.isValid(frame):
            return None
        return frame

    def api(self):
        return self._api()

    def visible(self):
        """Whether this window is on the screen right now.

        The same question ``mdiWindowOf`` answers, because that is what hides
        and shows: a window the user took off the screen with its own close box,
        a window the *Windows* menu hid, and a window nobody embedded are three
        spellings of one state, and the line is unchecked for all three.
        """
        api, frame = self.api(), self.frame()
        if api is None or frame is None:
            return False
        window = api.mdiWindowOf(frame)
        return (window if window is not None else frame).isVisible()
