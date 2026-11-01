# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""Putting a saved plugin back into the session that is already running.

A plugin the user edits has to answer the next right click, not the next launch.
Two things stand between that and a saved file: the catalog each shot view builds
once for itself, and Python's own module cache. `QVizPluginCatalog.reload` answers
the first and `QVizPluginSource.forgetUserModules` the second; this module is who
asks them, and when.

Three things decide the shape:

* **The source is parsed before anything is replaced.** A half-typed file saved
  by habit must not take down the entry that works today. So every changed file
  goes through `compileCheck` first: what parses replaces what was running, what
  does not is named in the log with the line that stopped it and the module it
  belongs to *stays* -- the menu keeps answering with the code from before the
  save, and says so rather than leaving the user to guess why nothing changed.
* **One save is often several signals.** Measured on this Qt: writing a file in
  place emits one `fileChanged`; a save the way vim and emacs do it -- a temporary
  file and a rename over the watched one -- emits **two**, a directory change and
  a file change. Without a debounce that is two reloads of every view's catalog
  for one press of the save key, so the signals collect and one timer decides.
* **A watched file can stop being watched, and a save by rename does exactly
  that.** Same measurement: the signal that arrives names the *old* path -- so the
  change is not missed -- and leaves the watch list without the file that is now
  there. Without a second `watch` after every flush, the first save from such an
  editor is the last one anyone sees. The same call is what picks up a plugin
  folder that appeared from outside the application (a copy, an ``scp``, a
  script): a new file under a watched folder announces itself only as a directory
  change, never as a file change, because it was never watched to begin with.

Everything here runs on the GUI thread: `QFileSystemWatcher` and `QTimer` answer
on the thread that made them, and that is what keeps this out of the one thing a
worker may not do -- a worker computes and logs, it does not touch a window.
"""

import logging
import os

from PySide6.QtCore import QFileSystemWatcher, QTimer

from imasviz.VizPlugins.QVizPluginCatalog import reloadEverywhere
from imasviz.VizPlugins.QVizPluginSource import (compileCheck,
                                                 userPluginsFolder,
                                                 userSources)

# How long a burst of signals has to settle before the folder is read again. Long
# enough that one save is one reload, short enough that it is not worth calling it
# a delay: the user has already moved to the tree by then.
DEBOUNCE = 300


class QVizPluginWatcher:
    """The user's plugin folder, kept in step with the running session."""

    def __init__(self, apiOf, parent=None):
        """
        Arguments:
            apiOf (callable) : answers the api of the session -- the one that
                holds `DTVlist`, the shot views whose catalogs have to be put
                back. Asked at each reload and never kept, because the api belongs
                to the start window's menu controller and this object must not
                hold a second bookkeeping of the same windows alive.

            parent (QObject) : the window that owns this watcher, so the timer and
                the file watcher die with it.
        """
        self._apiOf = apiOf
        self.changed = []
        self.refusals = []
        self.views = 0
        self._pending = set()
        self._watcher = QFileSystemWatcher(parent)
        self._watcher.fileChanged.connect(self._fileChanged)
        self._watcher.directoryChanged.connect(self._directoryChanged)
        self._timer = QTimer(parent)
        self._timer.setSingleShot(True)
        self._timer.setInterval(DEBOUNCE)
        self._timer.timeout.connect(self.flush)
        self.watch()

    def watch(self):
        """Take the folder and the plugins it holds under watch again.

        Idempotent -- `addPath` on a path already watched simply answers False --
        and called after every flush, because a save by rename leaves the old path
        unwatched behind, and because a plugin folder that appeared from outside
        the application has nothing else to announce it.
        """
        folder = userPluginsFolder()
        if not os.path.isdir(folder):
            # No folder yet is the normal state of a first run. It is not watched
            # (there is nothing there to change) and the creator will make it.
            return []
        added = []
        if folder not in self._watcher.directories():
            self._watcher.addPath(folder)
            added.append(folder)
        for source in userSources(folder):
            if source.fileName and source.fileName not in self._watcher.files():
                self._watcher.addPath(source.fileName)
                added.append(source.fileName)
        return added

    def watched(self):
        """What is being listened to, folders and files together.

        Answered because "why did my save change nothing?" is a question with an
        answer here: a plugin that stopped being watched stopped being reloaded,
        and a save by rename is exactly how a file leaves the list -- see the
        module.
        """
        return sorted(set(list(self._watcher.directories())
                          + list(self._watcher.files())))

    def _fileChanged(self, path):
        self._pending.add(path)
        self._timer.start()

    def _directoryChanged(self, path):
        # A folder changes when a plugin was added or removed under it, and no
        # file signal comes with that. The reload is the same one; what is added
        # here is a look at the folder again, which is what `watch` does.
        self.watch()
        self._pending.add(path)
        self._timer.start()

    def flush(self):
        """Read what changed, refuse what does not parse, put the rest in place.

        Public so the *Reload* entry of the plugin manager and a test can ask it
        without waiting for a timer.
        """
        paths, self._pending = self._pending, set()
        if not paths:
            return 0
        self.changed = []
        self.refusals = []
        for path in sorted(paths):
            if not path.endswith('.py'):
                continue
            try:
                with open(path, encoding='utf-8') as handle:
                    text = handle.read()
            except OSError as error:
                # The file is gone -- it was deleted. There is nothing to parse,
                # and the plugin comes off the menu by itself, since the folder is
                # what is looked at.
                self._info('Plugin file %s is gone (%s): it is no longer offered.'
                           % (path, type(error).__name__))
                continue
            try:
                compileCheck(text, path)
            except ValueError as refusal:
                self.refusals.append((path, str(refusal)))
                continue
            self.changed.append(path)

        if self.refusals:
            for path, refusal in self.refusals:
                self._error('%s was not put back: %s -- the Plugins menu still '
                            'runs the code that file had before this save.'
                            % (path, refusal))
        if self.changed or not self.refusals:
            self.views = self._reload()
            self._info('%s reloaded for %d shot view(s).'
                       % (', '.join(os.path.basename(path)
                                    for path in self.changed) or 'Plugins',
                          self.views))
        self.watch()
        return len(self.changed)

    def reload(self):
        """Ask for a reload now, whatever the timer is doing -- *Reload* does."""
        self.watch()
        return self._reload()

    def _reload(self):
        api = self._apiOf() if callable(self._apiOf) else self._apiOf
        if api is None:
            return 0
        return reloadEverywhere(api)

    def _views(self):
        api = self._apiOf() if callable(self._apiOf) else self._apiOf
        return list(getattr(api, 'DTVlist', None) or []) if api else []

    def _info(self, message):
        self._say(logging.INFO, message)

    def _error(self, message):
        self._say(logging.ERROR, message)

    def _say(self, level, message):
        """Say it in the log panel of every open case.

        Asked per view, under the URI of that case: a shot view wires its own
        panel to the logger named after its URI, so a plain `logging.info` would
        go where no one in the GUI is reading. A session with no view open has no
        panel to say it in, and that is the one case where this says nothing.
        """
        for view in self._views():
            logging.getLogger(view.uri).log(level, message)
