# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The bookkeeping of the windows of a run.

The *Windows* menu draws its lines from :meth:`openWindows` and its
*Delete* sub-menu from the same records; the group gestures, the close box
and the layout of the MDI area act on them. State lives on the api:
``figureframes``, ``DTVframeList``/``DTVlist``, ``_layoutApplied``.
"""

import logging

import shiboken6

from PySide6.QtWidgets import QMdiSubWindow

from imasviz.VizUtils import QVizPreferences, FigureTypes
from imasviz.Viz_API_chrome import QVizWindowRecord, titleWithCases


class QVizWindowBookkeepingMixin:
    SHOTVIEW_KIND = ('Shot view', 'Figure')

    def ShowHideFigure(self, figureKey):
        """Shows/Hides a figure.

        The spelling the scripting API and the session commands use; the
        *Windows* menu asks :meth:`showHideWindow` of the frame it drew a line
        for. One verb between the two, because a figure, a case view and a
        window a plugin drew differ in where they live, not in what hiding one
        costs.

        :param figureKey: (str) A figure key (e.g. 'Plot1')
        """
        return self.showHideWindow(self.figureframes[figureKey])

    def showHideWindow(self, frame):
        """Take one window off the screen, or put it back.

        Whether the frame sits in a subwindow or stands alone is asked, never
        assumed -- the same question :meth:`mdiWindowOf` answers, for the same
        reason: hiding the window hides everything in it, so showing a frame
        whose window is hidden changes nothing on screen.

        :param frame: the window's content
        :returns: (bool) whether the window is on the screen afterwards
        """
        window = self.mdiWindowOf(frame)
        target = window if window is not None else frame
        if target.isVisible():
            target.hide()
        else:
            target.show()
            if window is not None:
                frame.show()
        return target.isVisible()

    def openWindows(self):
        """Every window the user can see, in the order the menus draw them.

        The one answer to "what is open". The two menu builders this replaces
        each walked half of the bookkeeping and neither could name the other's
        windows: a case view is in ``DTVframeList``, a figure is in
        ``figureframes`` under one of the prefixes of ``FigureTypes.MENU_ORDER``.
        A kind holding nothing is left out -- a group nobody can click is a group
        that should not be drawn -- and a window no key holds is not on the
        list, which is exactly what the close box used to leave behind.

        Dead registrations leave first: a record whose frame is gone is a line
        the menu would draw for ever and no gesture could act on, so asking
        "what is open" releases them and says where they went -- :meth:`
        releaseLeftBehind` -- and then lists the windows with something behind
        them. Whatever reads the windows of a run -- the menu, a gesture, the
        session save -- therefore goes through this one answer.

        :returns: (list) :class:`QVizWindowRecord` for each window, case views
                          first, then the figures in ``MENU_ORDER`` order
        """
        self.releaseLeftBehind()
        windows = []
        kindLabel, iconLabel = self.SHOTVIEW_KIND
        for frame in list(self.DTVframeList):
            label = frame.dataTreeView.dataSource.getLongLabel()
            uri = getattr(frame.dataTreeView.dataSource, 'uri', None)
            windows.append(QVizWindowRecord(kindLabel, iconLabel, label,
                                            frame, None, self,
                                            cases=(uri,) if uri else ()))
        for kindLabel, iconLabel, figureType in FigureTypes.MENU_ORDER:
            for figureKey in self.GetFiguresKeys(figureType):
                frame = self.figureframes[figureKey]
                cases = self.casesServedBy(frame)
                # A plugin window carries the name of the IDS its entry ran on
                # in its `QVizPluginWindow` stamp, and nothing else does: the
                # line says `(from <ids>)` there, and nowhere the case alone
                # does not already say whose window it is.
                stamp = getattr(frame, 'pluginWindow', None)
                windows.append(QVizWindowRecord(kindLabel, iconLabel,
                                                # The same line the title bar
                                                # paints (`_renameFigure`): the
                                                # key the window is addressed
                                                # by, plus the cases it serves,
                                                # so a line outlives its window
                                                # and still says whose it was.
                                                titleWithCases(figureKey,
                                                               cases,
                                                               fromIds=(stamp.ids
                                                                         if stamp
                                                                         is not None
                                                                         else None)),
                                                frame,
                                                figureKey, self,
                                                cases=cases))
        return windows

    def casesServedBy(self, frame):
        """The case URIs a figure serves, read off `figToNodes`.

        A figure drawn from one case serves that one; a comparison figure serves
        every case that put a curve in it -- so "isolating" or "closing" one
        case shows the comparison while the other case it serves is still
        open. The windows a plugin drew serve the case of the shot view their
        entry ran on -- the Profiles panel and the Equilibrium chart both
        register it here, with a ``None`` node, because neither draws a curve
        of its own, and the *Windows* menu and the case gestures read this
        instead of a second record. A frame registered without any node serves
        none.
        """
        figureKey = self.GetFigureKeyOf(frame)
        if figureKey is None:
            return ()
        uris = []
        for uri, _node in self.figToNodes.get(figureKey, {}).values():
            if uri and uri not in uris:
                uris.append(uri)
        return tuple(uris)

    def setWindowVisible(self, frame, visible):
        """Put a window on or off the screen, whichever state it is in now.

        :meth:`showHideWindow` bounces, which is the answer to "toggle this
        one"; a group gesture needs a state, "these all hidden, these all
        shown", and the two share the one hiding rule: the window is what
        hides and shows (hiding it hides the frame inside), and showing a
        hidden frame whose window is left hidden changes nothing on screen.

        The show path must re-show the *frame* as well as the shell: the shell
        is the window the user sees, but the frame is its content, and a shell
        left up over a frame that is still hidden is a title bar over a blank
        body -- a window the user counts as still on screen, and one the two
        group gestures that go through here (*isolate* and *hide others*) used
        to strand across a whole run. :meth:`showHideWindow` already does this;
        here it is done whatever the shell is already doing, because the frame
        and the shell can disagree.
        """
        window = self.mdiWindowOf(frame)
        if visible:
            if window is not None:
                window.show()
                frame.show()
            else:
                frame.show()
        elif window is not None:
            window.hide()
        else:
            frame.hide()
        return (window if window is not None else frame).isVisible()

    def releaseLeftBehind(self):
        """Release the registrations whose window Qt has already taken away.

        A window killed under a live registration -- a close interrupted
        between its windows, a frame released anywhere while ``figureframes``
        or ``DTVframeList`` kept its entry -- would otherwise be a line the
        *Windows* menu draws for ever, that no gesture can act on: every one
        asks :meth:`QVizWindowRecord.frame`, which answers ``None`` for an
        object that is gone, and the number of the next window of the kind
        skips the dead key for the whole session. This is the single place
        the release happens, so the menu, the gestures and the session save
        all read the same truth: the dead entry is out of the bookkeeping,
        and the line that goes with it names the window, its key and its case.

        :returns: (int) how many registrations were released
        """
        released = 0
        for frame in list(self.DTVframeList):
            if not shiboken6.isValid(frame):
                label = frame.dataTreeView.dataSource.getLongLabel()
                uri = getattr(frame.dataTreeView.dataSource, 'uri', None)
                try:
                    self.DTVframeList.remove(frame)
                except ValueError:
                    pass
                for view in list(self.DTVlist):
                    if view is frame.dataTreeView:
                        self.DTVlist.remove(view)
                        break
                logging.getLogger('logPanel').warning(
                    'The shot view "%s" (case "%s") is no longer on the Qt '
                    'side: its entry is released from the bookkeeping.'
                    % (label, uri))
                released += 1
        for figureKey in list(self.figureframes.keys()):
            if not shiboken6.isValid(self.figureframes[figureKey]):
                cases = self.casesServedBy(self.figureframes[figureKey])
                self.ForgetFigure(figureKey)
                where = ' of case "%s"' % cases[0] if cases else ''
                logging.getLogger('logPanel').warning(
                    'The window "%s"%s is no longer on the Qt side: its '
                    'entry is released from the bookkeeping -- the line of the '
                    '*Windows* menu that held it is gone, and the number of '
                    'the next window of its kind is back.'
                    % (figureKey, where))
                released += 1
        return released

    def windowsFor(self):
        """Every window with its live frame, the records the gestures act on.

        The dead registrations are released before the list is built, because
        a gesture that skips a dead record silently would leave it on the
        screen's bookkeeping for ever -- the stuck entry of the *Windows*
        menu -- while the one that acts on it dies in the middle of its own
        list. :meth:`releaseLeftBehind` is that release and the named line.
        """
        self.releaseLeftBehind()
        for record in self.openWindows():
            frame = record.frame()
            if frame is not None:
                yield record, frame

    def isolateCase(self, uri):
        """Show one case's windows and hide the rest, shared ones shown.

        A case's window set is its own case view, every figure
        :meth:`casesServedBy` answers its URI, and the windows a plugin drew
        on it -- the Profiles panel, the Equilibrium chart -- which serve that
        one case and no other. A figure that serves this case *and* another
        is shown, not hidden: isolating a case is about getting the other
        cases off the screen, not about the figures this case still reads. A
        window that serves no case at all is left exactly where it is, since
        "this case" has nothing to say about it.
        """
        windows = list(self.windowsFor())
        for record, frame in windows:
            if not record.cases:
                continue
            action = 'shown' if uri in record.cases else 'hidden'
            try:
                self.setWindowVisible(frame, uri in record.cases)
            except Exception as error:
                self._gestureFailed(record, action, str(error))

    def hideOthers(self, exceptFrame):
        """Every window off the screen except the one named.

        The gesture for finding one figure in a tiled or cascaded pile: leave
        the one the menu line was drawn for, take the rest off the screen. A
        window already off the screen is left off it.
        """
        for record, frame in list(self.windowsFor()):
            if frame is exceptFrame:
                continue
            try:
                self.setWindowVisible(frame, False)
            except Exception as error:
                self._gestureFailed(record, 'hidden', str(error))

    def closeOthers(self, exceptFrame):
        """Every window closed for good except the one named.

        The same question as :meth:`hideOthers`, and the answer :meth:`closeWindow`
        gives instead of showing nothing: out of the bookkeeping, out of the
        session, out of the *Windows* menu. Kept to a different verb because
        what a close costs -- a figure it was redrawing is read a second time
        to come back -- is not what a hide costs.
        """
        for record, frame in list(self.windowsFor()):
            if frame is exceptFrame:
                continue
            try:
                self.closeWindow(frame)
            except Exception as error:
                self._gestureFailed(record, 'closed', str(error))

    def closeCase(self, uri):
        """Close the windows of one case for good; shared ones hidden, not closed.

        A case view and a figure that serves this case alone leave the book-
        keeping. A figure that serves this case *and* another is hidden, not
        closed: its other case still reads a live curve out of it, and closing
        it would take that curve out of a window somebody is still looking at.
        Hiding keeps the key, so the other case's *Windows* line still reaches it.
        One window that refuses in the middle of the list is named and left
        for the next pass, and the rest of the case's windows are still taken
        care of -- a gesture that raised here used to abandon the rest of the
        list with the failure, which is how the same entry kept meeting the
        same dead state on every repeated *Close this case*.
        """
        windows = list(self.windowsFor())
        for record, frame in windows:
            cases = record.cases
            if not cases or uri not in cases:
                continue
            if set(cases) == {uri}:
                try:
                    self.closeWindow(frame)
                except Exception as error:
                    self._gestureFailed(record, 'closed', str(error))
                    continue
            try:
                self.setWindowVisible(frame, False)
            except Exception as error:
                self._gestureFailed(record, 'hidden', str(error))

    def _gestureFailed(self, record, action, reason):
        """One window of a group gesture refused: name it, and go on.

        The *Windows* lines the gestures answer go over every window of the
        run, so one refusal must not cost the rest of the list -- the report
        behind :meth:`releaseLeftBehind` is a gesture dying on window two and
        leaving the windows three and on unprocessed, the same entry meeting
        the same dead state on every repeated click. The line says which
        window of which case it was, and what it refused.
        """
        where = ' of case "%s"' % record.cases[0] if record.cases else ''
        logging.getLogger('logPanel').warning(
            'The window "%s"%s could not be %s: %s. The other windows of '
            'the gesture were still taken care of.'
            % (record.label, where, action, reason))

    def mdiLayout(self, mode):
        """Lay the MDI area's windows out in `mode` and remember the choice.

        One of `QVizPreferences.LAYOUT_MODES`. *tabbed* puts every window in a
        single strip -- the big declutter when several cases are open -- and
        *tiled* / *cascaded* are the classic tidy-ups; *windowed* is the
        default pile the first case is opened into. The choice is written to
        the preference so the next start-up lays the area the way the user last
        left it.
        """
        from PySide6.QtWidgets import QMdiArea

        mdi = self.getMDI()
        if mdi is None:
            raise ValueError('No MDI area to lay out: no window is open.')
        if mode not in QVizPreferences.LAYOUT_MODES:
            raise ValueError('%r is not a view the MDI area wears: write %s'
                             % (mode, ' or '.join(
                                 repr(one) for one in
                                 QVizPreferences.LAYOUT_MODES)))
        if mode == 'tabbed':
            mdi.setViewMode(QMdiArea.TabbedView)
        else:
            mdi.setViewMode(QMdiArea.SubWindowView)
            if mode == 'tiled':
                mdi.tileSubWindows()
            elif mode == 'cascaded':
                mdi.cascadeSubWindows()
        QVizPreferences.Mdi_view_mode = mode
        return mode

    def _maybeApplyPreferredLayout(self):
        """Lay the area the way the preference says, once a window is in it.

        The area opens in windowed mode and the preference may not. This is
        called from both embed points, after a sub-window is added: the one-shot
        flag means the apply happens only when the area goes from empty to not,
        and a refusal (no MDI to lay out) resets the flag so a later embed --
        the one that actually has a window to lay out -- can still answer it.
        Windowed is the mode the area already answers, so it costs nothing.
        """
        if self._layoutApplied:
            return
        self._layoutApplied = True
        if QVizPreferences.Mdi_view_mode == 'windowed':
            return
        mdi = self.getMDI()
        if mdi is None:
            self._layoutApplied = False
            return
        try:
            self.mdiLayout(QVizPreferences.Mdi_view_mode)
        except ValueError:
            self._layoutApplied = False

    def forgetWindow(self, frame):
        """Take a frame out of the bookkeeping: its key, or its case.

        :param frame: the window's content
        :returns: (bool) whether the frame was in the bookkeeping at all
        """
        figureKey = self.GetFigureKeyOf(frame)
        if figureKey is not None:
            self.ForgetFigure(figureKey)
            return True
        if frame in self.DTVframeList:
            # The frame was the last one showing this case: the IDSs loaded for
            # it go with it, which is what makes closing a case view cost more
            # than hiding one -- and what the manual says out loud.
            self.RemoveDTVFrame(frame)
            return True
        return False

    def closeFromTitleBar(self, frame):
        """What the close box of a window costs the frame it was clicked on.

        With ``Close_button_deletes`` off -- the default -- nothing: the window
        is taken off the screen and stays where it is, so the *Windows* menu
        keeps naming it (unchecked) and clicking the line puts it back, and a
        saved session writes it hidden. Measured before the rule existed, a
        curve figure closed with its own box left ``figureframes`` empty, its
        window hidden inside the MDI area, its frame alive with no key reaching
        it, and the next curve figure of that kind took ``Plot1`` again:
        two windows under one name, one of them unreachable by any gesture.

        With it on, the frame leaves the bookkeeping and the caller releases the
        window it owns -- :class:`QVizMdiSubWindow` does, hiding it first, so
        the nested frames leave the paint queue before Qt deletes them.

        :returns: (bool) whether the window is to be released
        """
        if not QVizPreferences.Close_button_deletes:
            return False
        return self.forgetWindow(frame)

    def closeWindow(self, frame):
        """Take one window off the screen and out of the bookkeeping for good.

        The *Delete* entry of the *Windows* menu. It is the same shape as what
        the close box does when the preference says to close, so the two cannot
        disagree about what a closed window leaves behind.
        """
        window = self.mdiWindowOf(frame)
        if window is not None:
            window.hide()
            window.deleteLater()
        else:
            frame.hide()
            frame.deleteLater()
        return self.forgetWindow(frame)

    def closeAll(self):
        """Take every window of the run off the screen and out of the bookkeeping.

        What a *New session* costs the run: the case views and every figure,
        whatever window held them. The case views go first on purpose: a plugin
        window parented on a view dies with the view, and
        :meth:`RemoveDTVFrame` forgets its key at the same time, so the second
        pass leaves it to Qt rather than closing it twice -- its key is already
        out of ``figureframes`` when the loop gets to it.

        One case that refuses in the middle of the close is named and left for
        the next pass, and the rest of the run is still taken care of -- the
        same shape :meth:`closeOthers` and :meth:`closeCase` already wear.
        `closeAll` is the one that did not: the body of *New session* is the
        gesture the user asked for, and a refusal of the case the close had just
        reached used to be the one the screen was left with -- the window no one
        asked to close, open, the way the field reported it.

        :returns: (list) the frames it took away, the case views first
        """
        closed = []
        for frame in list(self.DTVframeList):
            if self._closeOneWindow(frame, self._caseNameof(frame)):
                closed.append(frame)
        for figureKey, frame in list(self.figureframes.items()):
            if self._closeOneWindow(frame, figureKey):
                closed.append(frame)
        return closed

    def _closeOneWindow(self, frame, name):
        """Close one window of the group gesture; say what it refused and go on.

        :meth:`closeWindow` is the one place the refusal is answered, and
        :meth:`closeAll` is the one place a refusal must cost itself and
        nothing else. The name is the one the log panel reads: a case view is
        the URI behind it, a figure is the key it is registered under.
        """
        try:
            return self.closeWindow(frame)
        except Exception as error:
            logging.getLogger('logPanel').warning(
                'The window "%s" could not be closed: %s. The other '
                'windows of the clean slate were still taken care of.'
                % (name, error))
            return False

    def _caseNameof(self, frame):
        """The name the log panel reads for this case view: the URI it serves.

        Asked off the view rather than the frame, because the frame is the
        bookkeeping's name for the case, and the URI is the user's. A frame
        whose view is already gone still answers something, so a half-closed
        case is still nameable rather than an `AttributeError`.
        """
        try:
            uri = getattr(frame.dataTreeView.dataSource, 'uri', None)
        except Exception:
            uri = None
        return 'case "%s"' % uri if uri else 'the case view'

    def mdiWindowOf(self, frame):
        """The MDI window a frame is embedded in, or None if it stands alone.

        A frame lives either inside a :class:`QMdiSubWindow` handed out by
        `addPlotWidgetToMDI`, or on its own. The *Windows* menu and its
        which, and the old test was the *name* of the top-level window
        ("IMASViz root window"), which only holds while the frame sits under the
        application's main window. Measured on a plain MDI area, that test fails
        and both entries then act on the frame instead of the window: a line
        hides the frame and leaves an empty window on screen, and Delete closes
        the frame and leaves the window visible. Asking what the parent *is*
        says the same thing about the application's windows and the right thing
        about every other one.
        """
        parent = frame.parent()
        return parent if isinstance(parent, QMdiSubWindow) else None

    def getMDI(self):
        if self.parent is not None:
            return self.parent
        return None

    def ForgetFigureOf(self, plotWidget):
        """Take a frame out of the bookkeeping under whichever key holds it.

        Kept for the scripts that close a window without going through a
        command. The close box does not call this: it calls
        :meth:`closeFromTitleBar`, which is the one that decides whether the
        window is only taken off the screen or really gone -- and a frame that
        is only hidden keeps its key, so it stays in the *Windows* menu and in
        the session, under the same name.
        """
        return self.forgetWindow(plotWidget)

