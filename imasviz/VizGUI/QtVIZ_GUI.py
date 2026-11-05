# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

import os
import sys, getopt
import logging
from functools import partial
from PySide6.QtWidgets import (QTabWidget, QWidget, QFormLayout, QApplication,
                             QMenu, QMainWindow, QDockWidget,
                             QLineEdit, QPushButton, QVBoxLayout, QComboBox,
                             QPlainTextEdit, QGridLayout, QMdiArea, QTableView,
                             QLabel, QHBoxLayout)
from PySide6.QtCore import Qt
from pathlib import Path


# Append imasviz source path
sys.path.append((os.environ['VIZ_HOME']))

from imasviz.VizGUI.VizGuiCustomization import QVizDefault, QVizStyle
from imasviz.VizGUI.VizGUICommands import (QVizMainMenuController, QVizFileMenu,
                                           QVizWindowMenu)
from imasviz.VizGUI.VizGUICommands.VizSession.QVizSaveSession import QVizSaveSession
from imasviz.VizGUI.VizGUICommands.VizSession.QVizRestoreSession import QVizRestoreSession
from imasviz.VizGUI.VizConfigurations.QVizSessionFile import QVizSessionFile
from imasviz.VizUtils import QVizGlobalValues, QVizPreferences,QVizGlobalOperations, QVizLogger, UserInputs
from imasviz.VizGUI.VizWidgets.QVizIMASdbBrowserWidget import QVizIMASdbBrowserWidget
from imasviz.VizGUI.VizWidgets.QVizCaseSelector import QVizCaseSelector
from imasviz.VizDataSource.QVizIMASDataSource import QVizIMASDataSource
from imasviz.VizPlugins.QVizPluginWatcher import QVizPluginWatcher


def autoSavesSession():
    """Whether IMASViz keeps the session of a run on its own, without being asked.

    One preference, `Auto_save_session`, decides both ends of it: the session
    written when the window closes, and the offer to put it back at the next
    start. Off (the default), a run leaves nothing on the disk and the next run
    asks nothing.

    A function of the module and not a method of the window: the close event and
    the start-up offer are driven on stand-ins that answer the few calls those two
    paths make, and a method the window would have to own could not be asked of
    them.
    """
    return QVizPreferences.Auto_save_session == 1


class GUIFrame(QTabWidget):
    def __init__(self, parent):
        super(GUIFrame, self).__init__(parent)

        # Every widget the frame's methods and the command line drive is
        # built here, as an attribute, before any of them runs; they are then
        # laid out under one "Cas" tab behind a mode switch. The three
        # presentations are the local case list (URI-first), the free URI line,
        # and the legacy five-field form the -u -d -s -r -b command line fills.
        # The start window used to be two tabs -- the five fields, and a bare
        # URI line -- where the selection a user made was the five parameters
        # behind a URI nobody saw; now the URI is the thing the selection is,
        # and the parameters are one switch removed, in the mode that names them.
        self.mainMenuController = QVizMainMenuController(self)

        self.uriPanel = QVizCaseSelector(self)
        self.uriPanel.uriOpened.connect(self.openUri)
        # The frame's own URI line and the selector's free line are the same
        # widget, so a gesture that reads frame.URI sees what the URI panel
        # types, and the reverse.
        self.URI = self.uriPanel.freeText

        default_user_name, default_machine, default_run = \
            QVizDefault().getGUIEntries()
        self.userName = QLineEdit(default_user_name)
        self.userName.setStatusTip("Name of the user under which the case is stored.")
        self.userName.setToolTip("Name of the user under which the case is stored.")
        self.userName.editingFinished.connect(self.onUserNameEditFinished)
        self.imasDbName = QLineEdit(default_machine)
        self.imasDbName.setStatusTip("Database label under which the case is stored.")
        self.imasDbName.setToolTip("Database label under which the case is stored.")
        self.shotNumber = QLineEdit()
        self.shotNumber.setStatusTip("Shot case identifier.")
        self.shotNumber.setToolTip("Shot case identifier.")
        self.runNumber = QLineEdit(default_run)
        self.runNumber.setStatusTip("Run case identifier.")
        self.runNumber.setToolTip("Run case identifier.")
        self.backend = 13
        self.backendCombo = QComboBox()
        self.backendCombo.addItems(['HDF5', 'MDS+'])
        self.backendCombo.activated.connect(self.onActivated)
        self.IMASdbBrowserWidget = QVizIMASdbBrowserWidget(parent=self)
        self.IMASdbBrowserWidget.onItemDoubleClick.connect(self.updateIDSparam)

        self.legacyPanel = self._buildLegacyPanel()
        self.casePanel = self._buildCasePanel()
        self.addTab(self.casePanel, "Cas")
        self.uriPanel.refresh(self.userName.text())

        title = "IMAS_VIZ (version " + str(QVizGlobalValues.IMAS_VIZ_VERSION) + ")"
        self.setWindowTitle(title)

        if UserInputs.inputs is not None and len(UserInputs.inputs) == 9:
            UserInputs.enable = True
            self.OpenDataSourceFromTab1(None)

        self.contextMenu = None

    def _buildCasePanel(self):
        """The one "Cas" tab: the mode switch, then the two presentations.

        One tab, not two: the selection is one thing to make in every mode, and
        the mode switch is the only thing that changes what the user chooses
        with. The panels are children of this tab, so exactly one is in front
        at a time and the tab never shows an empty half of itself.
        """
        panel = QWidget(self)
        layout = QVBoxLayout(panel)

        header = QHBoxLayout()
        header.addWidget(QLabel('Mode de sélection'))
        self.modeCombo = QComboBox()
        self.modeCombo.addItems(['Cas locaux (liste)', 'Saisie libre (URI)',
                                 'Legacy (5 champs)'])
        self.modeCombo.currentIndexChanged.connect(self.onModeChanged)
        header.addWidget(self.modeCombo)
        header.addStretch(1)
        layout.addLayout(header)

        layout.addWidget(self.uriPanel)
        layout.addWidget(self.legacyPanel)

        self.onModeChanged(self.modeCombo.currentIndex())
        return panel

    def _buildLegacyPanel(self):
        """The legacy five-field form, behind its mode.

        The widgets themselves were built on the frame in __init__ (they are
        what the command line and `updateIDSparam` drive); this only lays them
        out. The form is one presentation and no more, and its *Ouvrir* keeps
        the parameter-to-URI build it has always used.
        """
        panel = QWidget(self)
        layout = QVBoxLayout(panel)

        form = QFormLayout()
        form.addRow('User name', self.userName)
        form.addRow('Database', self.imasDbName)
        form.addRow('Shot number', self.shotNumber)
        form.addRow('Run number', self.runNumber)
        form.addRow('Backend', self.backendCombo)
        layout.addLayout(form)
        layout.addWidget(self.IMASdbBrowserWidget)

        buttonRow = QHBoxLayout()
        self.openButton = QPushButton('Ouvrir', self)
        self.openButton.setStatusTip("Open the case for the given parameters.")
        self.openButton.setToolTip("Open the case for the given parameters.")
        self.openButton.clicked.connect(self.OpenDataSourceFromTab1)
        buttonRow.addWidget(self.openButton)
        buttonRow.addStretch(1)
        layout.addLayout(buttonRow)
        return panel

    def onModeChanged(self, index):
        """Show the presentation the mode switch names, and hide the other two.

        The list, the free URI line, and the legacy form are three ways of
        making the same selection, and exactly one is in front at a time: the
        list and the free line both live in the selector (which the legacy mode
        hides), and the legacy form is the only one it shows. The selector is
        asked through `presentAs` rather than toggled by hand from here, so
        what the free line hides -- its list, its controls row -- and what the
        list mode puts back are answered by one owner at a time.
        """
        if index == 2:
            self.legacyPanel.setVisible(True)
            self.uriPanel.setVisible(False)
            return
        self.legacyPanel.setVisible(False)
        self.uriPanel.setVisible(True)
        self.uriPanel.presentAs('list' if index == 0 else 'free')

    def openUri(self, uri):
        """The URI the selector handed over: refused if empty, else opened.

        The one Open every URI-first gesture lands on -- a double click, the
        free line and *Ouvrir* all reach here -- so a selection made against an
        empty choice is refused in the log of the session, not spent on a case
        that was never named.
        """
        if uri is None or not str(uri).strip():
            logging.getLogger('logPanel').error(
                "No URI to open: choose a case, or type its URI.")
            return
        self.mainMenuController.openShotView.Open(None, uri)

    # def logPanel(self):
    #     #LOG WIDGET
    #     self.logWidget = QPlainTextEdit(parent=self)
    #     #self.logWidget.resize(QSize(500, 300))
    #     self.logWidget.setReadOnly(True)
    #     logging.getLogger('logPanel').setLevel(logging.INFO)
    #     handler = QVizLogger()
    #     logging.getLogger('logPanel').addHandler(handler)
    #     handler.new_signal_emiter.new_signal.connect(self.logWidget.appendHtml)
    #     layout = QVBoxLayout()
    #     layout.addWidget(self.logWidget)
    #     return layout

    def onActivated(self, index):
        if index == 0:
            self.backend = 13
        elif index == 1:
            self.backend = 12

    def OpenDataSourceFromTab1(self, evt):
        try:
            if UserInputs.enable:
                try:
                    opts, args = getopt.getopt(UserInputs.inputs[1:], 'u:d:s:r:b:')
                    for opt, arg in opts:
                        if opt == '-u':
                            self.userName.setText(arg)
                        elif opt in ("-d"):
                            self.imasDbName.setText(arg)
                        elif opt in ("-s"):
                            self.shotNumber.setText(arg)
                        elif opt in ("-r"):
                            self.runNumber.setText(arg)
                        elif opt in ("-b"):
                            self.backend = int(arg)
                            if self.backend == 13:
                                self.backendCombo.setCurrentIndex(0)
                            elif self.backend == 12:
                                self.backendCombo.setCurrentIndex(1)
                            else:
                                raise ValueError("Backend id should be 12 or 13")
                except getopt.GetoptError:
                    logging.getLogger('logPanel').error('Bad user input.')
                    sys.exit(-1)
                    pass

                UserInputs.enable = False

            self.CheckInputsFromTab1()
            tokens = self.shotNumber.text().split()
            try:
                for shotNumber in tokens:

                    """Check if data source is available"""
                    QVizGlobalOperations.check(QVizGlobalValues.IMAS_NATIVE)

                    uri = QVizIMASDataSource.build_uri(
                        backend_id=self.backend,
                        shot=int(shotNumber),
                        run=int(self.runNumber.text()),
                        user_name=self.userName.text(),
                        db_name=self.imasDbName.text(),
                        data_version='3',
                        options='')
                    self.mainMenuController.openShotView.Open(evt, uri)

            except Exception as e:
                raise ValueError(str(e))

        except ValueError as e:
            logging.getLogger('logPanel').error(str(e))

    def CheckInputsFromTab1(self):
        """Display warning message if the required parameter was not specified"""
        if self.userName.text() == '':
            raise ValueError("'User name' field is empty.")

        if self.imasDbName.text() == '':
            raise ValueError("'Database' field is empty.")

        if self.shotNumber.text() == '' or self.runNumber.text() == '':
            raise ValueError("'Shot number' or 'run number' field is empty.")

    def updateIDSparam(self):
        """Fill the IDS parameters from what the database browser just selected.

        The five values are read and checked before any field is written. They
        used to be written as they were read, so a click that did not spell a
        case put None in the four text fields -- PySide6 6.6.3 takes None for a
        string and writes an empty line, so what the user had typed disappeared
        -- and then died on the fifth, outside the gesture, on an AttributeError
        nobody was told about.
        """
        try:
            username = self.IMASdbBrowserWidget.getActiveUsername()
            database = self.IMASdbBrowserWidget.getActiveDatabase()
            shot = self.IMASdbBrowserWidget.getActiveShot()
            run = self.IMASdbBrowserWidget.getActiveRun()
            backend = self.IMASdbBrowserWidget.getActiveBackend()
            for label, value in (('user name', username),
                                 ('database', database),
                                 ('shot number', shot),
                                 ('run number', run),
                                 ('backend', backend)):
                if value is None:
                    raise ValueError(
                        "The database browser did not select a %s: the IDS "
                        "parameters are left as they are." % label)
        except ValueError as e:
            logging.getLogger('logPanel').error(str(e))
            return

        self.userName.setText(username)
        self.imasDbName.setText(database)
        self.shotNumber.setText(shot)
        self.runNumber.setText(run)
        self.backend = backend
        # The combo holds ['HDF5', 'MDS+'], the same two BACKENDS spells.
        self.backendCombo.setCurrentIndex(0 if backend == 13 else 1)

    def onUserNameEditFinished(self):
        self.IMASdbBrowserWidget.setActiveUsername(self.userName.text())

    def OpenDataSourceFromTab2(self, evt):
        import imas
        try:
            try:
                self.CheckInputsFromTab2()
                self.mainMenuController.openShotView.Open(evt, self.URI.text())

            except Exception as e:
                raise ValueError(str(e))

        except ValueError as e:
            logging.getLogger('logPanel').error('Unable to open URI ' + self.URI.text() + ': ' + str(e))

    def CheckInputsFromTab2(self):

        if self.URI.text() == '':
            raise ValueError("'URI' field is empty.")


    def contextMenuEvent(self, event):

        # Get position
        self.pos = event.pos()
        self.showPopUpMenu()

    def showPopUpMenu(self):
        """Display the popup menu .
        """
        self.contextMenu = QMenu()
        # Set new popup menu
        self.mainMenuController.updateMenu(self.contextMenu, self)

        # Map the menu (in order to show it)
        self.contextMenu.exec(self.mapToGlobal(self.pos))
        return 1

    def getMDI(self):
        """ Get MDI area through the root IMASViz main window.
        """
        if self.window().objectName() == "IMASViz root window":
            return self.window().getMDI()
        return None

    # def keyPressEvent(self, event):
    #     # Note Qt.Key_Enter is Enter key on numpad
    #     if event.key() == Qt.Key_Return:
    #         self.OpenDataSourceFromTab1(event)
    #     event.accept()


class QVizStartWindow(QMainWindow):
    def __init__(self, parent):
        super(QVizStartWindow, self).__init__(parent)
        ex = GUIFrame(parent)
        self.setCentralWidget(ex)
        # self.setWidget(ex)
        self.logPanel()

    def logPanel(self):
        # #LOG WIDGET
        self.logWidget = QPlainTextEdit(parent=self)
        self.logWidget.setStatusTip("Log panel.")
        self.logWidget.setReadOnly(True)
        self.dockWidget_log = QDockWidget("Log", self)
        self.dockWidget_log.setFeatures(QDockWidget.DockWidgetFloatable)
        self.dockWidget_log.setObjectName("DockWidget_LOG")
        self.dockWidgetContents_log = QWidget()
        self.dockWidgetContents_log.setObjectName("DockWidgetContents_LOG")
        self.gridLayout_log = QGridLayout(self.dockWidgetContents_log)
        # Set dockwidget size
        self.gridLayout_log.setObjectName("GridLayout_LOG")
        self.gridLayout_log.addWidget(self.logWidget, 0, 0, 1, 1)
        self.dockWidget_log.setWidget(self.dockWidgetContents_log)

        self.addDockWidget(Qt.DockWidgetArea(8), self.dockWidget_log)
        logging.getLogger('logPanel').setLevel(logging.INFO)
        handler = QVizLogger()
        logging.getLogger('logPanel').addHandler(handler)
        handler.new_signal_emiter.new_signal.connect(self.logWidget.appendHtml)
        

    def closeEvent(self, event):
        """Modify close event to request confirmation trough dialog. If
        confirmed, close the application.
        """
        # Get Yes/No answer (returns True/False)
        answer = \
            QVizGlobalOperations.YesNo(question='Exit IMAS_VIZ?',
                                       caption='Please confirm')
        if answer == True:
            event.accept()
        else:
            event.ignore()


class QVizMDI(QMdiArea):
    """Class for Multiple Document Interface (MDI) area.
    """

    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("MDI")
        self.setObjectName("MDI")


class QVizMainWindow(QMainWindow):
    """ Class for IMASViz main window, which contains MDI and all
    sub-main windows, widgets etc.
    """
    def __init__(self):
        super(QVizMainWindow, self).__init__()

        # Set title
        title = "IMASVIZ (version " + str(QVizGlobalValues.IMAS_VIZ_VERSION) + ")"
        self.setWindowTitle(title)
        # Set name of this main window as the root
        self.setObjectName("IMASViz root window")
        # set status bar
        self.setStatusBar()

        # Set MDI (Multiple Document Interface)
        self.MDI = QVizMDI(self)
        # Set central widget
        centralWidget = QWidget(self)
        # Set start window
        self.startWindow = QVizStartWindow(self)

        # Set layout and add start window and MDI to it
        layout = QGridLayout(centralWidget)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 7)

        layout.addWidget(self.startWindow, 0, 0, 1, 1)
        layout.addWidget(self.MDI, 0, 1, 1, 1)
        # Set central widget of the main window
        self.setCentralWidget(centralWidget)
        # The File menu, once the start window exists: its session entries are
        # asked of the menu controller that window was built with.
        self.addFileMenu()
        # ... and the Windows menu next to it, for the same reason: a window is
        # the content of this screen, so the gesture that finds one belongs on a
        # bar that is on screen whatever the user is looking at -- including
        # when the window they are after is the case view whose menu bar they
        # just hid.
        self.addWindowMenu()
        # One watcher for the folder of the user's own plugins, for the whole
        # run: what they save answers the next right click, without a restart.
        # It sits here and not on a shot view because it watches a folder, not a
        # case -- and a session outlives the views that come and go through it.
        # The watcher takes the folder under watch in its own constructor, and
        # asks again after every reload, so a folder that appears later is not
        # missed: nothing here has to call `watch`.
        self.pluginWatcher = QVizPluginWatcher(self.sessionApi, parent=self)
        # Resize to full screen
        self.showMaximized()

    def addFileMenu(self):
        """Hang the *File* menu on this window: the session, and the way out."""
        self.fileMenu = QVizFileMenu(self.menuBar().addMenu(QVizFileMenu.TITLE),
                                     self,
                                     sessionMenu=self.sessionMenuEntries()).show()

    def addWindowMenu(self):
        """Hang the *Windows* menu on this window: every window of the run.

        The api is the session's own -- the one the *Open* gesture drives, the
        same one *Save session* writes -- because a second bookkeeping would
        list windows that are not on the screen. The menu is kept on the window:
        its ``aboutToShow`` slot lives on it, and a menu filler nobody holds
        dies before it can fill anything.
        """
        self.windowMenu = QVizWindowMenu(
            self.menuBar().addMenu(QVizWindowMenu.TITLE),
            self.sessionApi(), applicationBar=True).show()

    def sessionMenuEntries(self):
        """The controller's session entries, or None while it holds none.

        The controller is the start window's own -- the one the *Open* gesture
        drives -- because that is where the api of the session lives. Building a
        second one would give this menu a second bookkeeping holding none of the
        windows on screen (`Viz_API` is not a singleton).
        """
        controller = self.startMenuController()
        return getattr(controller, 'menuSession', None)

    def startMenuController(self):
        """The menu controller the start window was built with, or None.

        Reached with ``getattr`` where the frame may not be there yet: half a
        start window is a normal state during the start-up sequence, and a menu
        bar is not where an ``AttributeError`` should land.
        """
        frame = self.startWindow.centralWidget()
        return getattr(frame, 'mainMenuController', None)

    def closeEvent(self, event):
        """Modify close event to request confirmation trough dialog. If
        confirmed, close the application.
        """
        # Get Yes/No answer (returns True/False)
        answer = \
            QVizGlobalOperations.YesNo(question='Exit IMAS_VIZ?',
                                       caption='Please confirm')
        if answer==True:
            # Written here, before any window is taken away, and not from a
            # `destroyed` handler: by the time Qt starts destroying widgets the
            # session has already lost the windows it is supposed to describe.
            # And only on the user's say-so: `Auto_save_session` is off by
            # default, so a run that ends leaves nothing behind on the disk.
            if autoSavesSession():
                self.saveLastSession()
            event.accept()
        else:
            event.ignore()

    def sessionApi(self):
        """The api this session's menus drive -- its shot views and its figures.

        One api serves the whole session, and it lives where the *Open* gesture
        was built: the start window, its central frame, that frame's menu
        controller. It is reached and not moved: the menus already hold it, and a
        second copy would be a second bookkeeping of the same windows.
        """
        controller = self.startMenuController()
        openShotView = getattr(controller, 'openShotView', None)
        return getattr(openShotView, 'api', None)

    def saveLastSession(self):
        """Write the session that is on screen, under a name nobody chose.

        Refused rather than silent when it cannot be written -- the user is
        leaving, and the one thing they should hear is that the next start will
        not look like this one.
        """
        api = self.sessionApi()
        if api is None:
            return
        try:
            QVizSaveSession(api, path=QVizSessionFile.lastSession()).execute()
        except ValueError as e:
            logging.getLogger('logPanel').error(
                'The session was not kept for the next start: %s' % e)

    def restoreLastSession(self):
        """Put back the session the previous run left behind.

        Only ever called on an answer, so the question stays where the user
        answers it and this stays a call a script can make.
        """
        api = self.sessionApi()
        if api is None:
            return
        try:
            QVizRestoreSession(api,
                               path=QVizSessionFile.lastSession()).execute()
        except ValueError as e:
            logging.getLogger('logPanel').error(
                'The last session was not restored: %s' % e)

    def askForLastSession(self):
        """Offer the session of the previous run, and put it back if it is taken.

        Asked only when the user asked for this: `Auto_save_session` is off by
        default, and a start that offers to put back a session the user never
        agreed to keep is half the behaviour they turned off. Asked only when the
        file is there, too: on a first run -- and on every run that follows one
        closed with nothing open -- the question is one the user answers for
        nothing. The answer belongs here, at the top level of the application, and
        not inside the command that does the work.
        """
        if not autoSavesSession():
            return False
        if not QVizSessionFile.hasLastSession():
            return False
        if not QVizGlobalOperations.YesNo(
                question='Restore the session IMASViz was closed with?',
                caption='Please confirm'):
            logging.getLogger('logPanel').info(
                'The last session was left closed: open it from the File menu if '
                'it is the one you want.')
            return False
        self.restoreLastSession()
        return True

    def getMDI(self):
        if self.MDI != None:
            return self.MDI
        return None

    def getStartWindow(self):
        return self.startWindow

    def setStatusBar(self):
        self.statusBar().show()

def help():
    try:
        if len(sys.argv[1:]) != 1:
            return
        opts, args = getopt.getopt(sys.argv[1:], 'h', ['help'])
        for opt, arg in opts:
            if opt in ('-h', '--help'):
                print("-------------------------------------------------------------------------------")
                print("")
                print("Help:")
                print("")
                print("1. Options for specifying user, database, shot, run numbers and backend at startup time:")
                print("viz -u <user> -d <database> -s <shot> -r <run> -b <backend>")
                print("")
                print("2. User guide for IMASViz:")
                print ("viz_doc")
                print("-------------------------------------------------------------------------------")
                print("")
                sys.exit(0)
    except getopt.GetoptError:
        print("usage: viz -u <user> -d <database> -s <shot> -r <run> -b <backend>")
        print ("or: viz --help")
        sys.exit(-1)

def main():
    help()
    UserInputs().setUserInputs(sys.argv)
    app = QApplication(sys.argv)
    QVizGlobalOperations.checkEnvSettings()
    QVizPreferences().build()
    # After the preferences, because which of the two themes is worn is one of
    # them; before the window, because a window built under the desktop's own
    # palette paints its first frame in colours the user did not ask for.
    QVizStyle.applyToApplication(app)
    window = QVizMainWindow()
    logging.getLogger('logPanel').info("Welcome to Viz!")
    logging.getLogger('logPanel').info("Please report any issue to ITER JIRA: https://jira.iter.org/")

    window.show()
    # Asked once the windows are on screen, so what the restore embeds lands in an
    # MDI area the user can see -- and only when the previous run left a session.
    window.askForLastSession()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
