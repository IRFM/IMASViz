# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The equilibrium flux surfaces and radial profiles, run end to end on the case.

Three layers, each answering the same read (`QVizEquilibriumRead`) and pinning
what the two surfaces of that read give back:

* the **read** — the grid the case holds, the psi of a slice, the eight radial
  profiles and their abscissa, and the nearest-slice rule an asked instant
  answers by;
* the **figure** — the `EquiSurfaces:` window that is the read drawn: N
  flux-surface frames in a row, or one frame with the radial profiles stacked
  under it, held in `figureframes` and dressed like every other figure;
* the **menu** — the `equilibriumsurfaces` plugin, whose two entries run the
  two surfaces and stamp the window so a session puts it back under the same
  key and instant rather than asking the user a second time.

Measured on the reference case (WEST 54924 run 0, data dictionary 3.35.0): the
case holds occurrences **[0, 1, 2, 3]** of `equilibrium` and **49** time slices
(**32.13 s** to **48.55 s**), a **7229** point / **13857** triangle grid, and a
**101** point radial profile. The three instants entry 0 draws are the first,
middle and last slice. These do not depend on the `Ignore_GGD` preference,
which moves the shot view's *walk*, not the `db_entry.get` this read goes
through — it is pinned at 1 regardless, because it decides whether the fixture
finishes inside the cap.
"""

import logging
import pytest

from PySide6.QtWidgets import QMainWindow, QMdiArea

from imasviz.VizDataSource.QVizDataSourceFactory import QVizDataSourceFactory
from imasviz.VizDataAccess.QVizEquilibriumRead import QVizEquilibriumRead, PROFILES
from imasviz.VizAgent.core import McpGuiCore
from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizMainMenuController \
    import QVizMainMenuController
from imasviz.VizGUI.VizGUICommands.VizSession.QVizSaveSession import QVizSaveSession
from imasviz.VizGUI.VizGUICommands.VizSession.QVizRestoreSession import QVizRestoreSession
from imasviz.VizPlugins.QVizPluginCatalog import QVizPluginCatalog
from imasviz.VizPlugins.VizPlugin import QVizPluginAnswers
from imasviz.VizUtils import FigureTypes, QVizPreferences

from conftest import (CASE_DATA_DICTIONARY_VERSION, CASE_URI, case_uri_or_skip)
from support import ownership

IDS_NAME = 'equilibrium'
OTHER_ID_NAME = 'core_profiles'
PLUGIN = 'equilibriumsurfaces'
KIND = FigureTypes.EQUISURFACES
PROFILE_NAMES = [name for name, _factor, _units in PROFILES]

GRID_POINTS = 7229
TRIANGLES = 13857
RADIAL_POINTS = 101
WALL_POINTS = 164
SLICES = 49
FIRST_TIME = 32.1336784362793
MIDDLE_SLICE = 24
MIDDLE_TIME = 40.17202377319336
LAST_TIME = 48.54828643798828

pytestmark = [pytest.mark.case, pytest.mark.dd, pytest.mark.ui]


class BrowserStub:

    def getActiveUsername(self):
        return ''

    def addUserDB(self, username):
        pass


class RootWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setObjectName('IMASViz root window')
        self.MDI = QMdiArea(self)
        self.IMASdbBrowserWidget = BrowserStub()

    def getMDI(self):
        return self.MDI


class Session:
    """One application session: one case, one shot view, the two entries run."""

    def __init__(self, qapp, root):
        self.qapp = qapp
        self.root = root
        self.api = QVizMainMenuController(root).openShotView.api
        self.view = None
        self.catalog = None
        self.core = None
        self.keys = {}

    def openCase(self, uri, ddVersion):
        source = QVizDataSourceFactory().create(uri)
        source.dd_version = ddVersion
        self.view = self.api.CreateDataTree(source).dataTreeView
        self.catalog = self.view.pluginCatalog or QVizPluginCatalog(self.view)
        self.view.pluginCatalog = self.catalog
        self.api.ShowDataTree(self.view)
        self.core = McpGuiCore(api=self.api)
        self.qapp.processEvents()

    def entriesOn(self, idsName):
        return self.catalog.entriesFor(self.view.IDSRoots[idsName])

    def pluginEntry(self, number):
        chosen = [entry for entry in self.entriesOn(IDS_NAME)
                  if entry.pluginName == PLUGIN and entry.number == number]
        assert len(chosen) == 1, \
            [(entry.pluginName, entry.number) for entry in self.entriesOn(IDS_NAME)]
        return chosen[0]

    def run(self, number, answers=None):
        """Run one entry through the catalog, and answer what it registers."""
        before = set(self.api.figureframes)
        entry = self.pluginEntry(number)
        if answers is not None:
            self.catalog.run(entry, answers=answers)
        else:
            self.catalog.run(entry)
        self.qapp.processEvents()
        new = sorted(set(self.api.figureframes) - before)
        assert new, 'the entry registered no window in figureframes'
        key = new[-1]
        self.keys[number] = key
        return self.api.figureframes[key]


@pytest.fixture(scope='module')
def session(qapp):
    """One case, read and run once — shared below, so each test reads what the
    one before it left on the screen.
    """
    if case_uri_or_skip() is None:
        pytest.skip('reference case not reachable: %s' % CASE_URI)
    # Pinned, not inherited: this moves the shot view's walk, not the read this
    # file asks (which goes through `db_entry.get`), but it decides whether the
    # fixture finishes inside the cap.
    QVizPreferences.Ignore_GGD = 1
    root = RootWindow()
    root.show()
    qapp.processEvents()
    made = Session(qapp, root)
    made.openCase(CASE_URI, CASE_DATA_DICTIONARY_VERSION)
    ownership.keep(made)
    yield made


@pytest.fixture
def shot(session):
    """The read of occurrence 0 of `equilibrium`, built off the case's source."""
    return QVizEquilibriumRead(session.view.dataSource, 0)


def nonEmptyGrab(widget):
    """Whether the widget renders to a non-empty pixmap, off-screen."""
    pixmap = widget.grab()
    return not pixmap.isNull() and pixmap.size().width() > 0 \
        and pixmap.size().height() > 0


# --------------------------------------------------------------------------
# What the case answers, and what the read gives back
# --------------------------------------------------------------------------

def test_the_read_answers_the_grid_and_the_case_answers_it(shot):
    R, Z, triangles = shot.grid()
    assert R.shape == Z.shape == (GRID_POINTS,)
    assert triangles.shape == (TRIANGLES, 3)
    assert len(shot.timeValues()) == SLICES


def test_the_read_answers_the_slice_named_by_the_nearest_rule(shot):
    # An instant far outside the case's clock is clamped and the slice that
    # answered is named back, not a surface interpolated between two slices.
    index, sliceTime, clamped = shot.resolve(FIRST_TIME)
    assert index == 0 and clamped is False
    assert sliceTime == pytest.approx(FIRST_TIME)
    index, sliceTime, clamped = shot.resolve(FIRST_TIME - 10.0)
    assert index == 0 and clamped is True
    index, sliceTime, clamped = shot.resolve(MIDDLE_TIME)
    assert index == MIDDLE_SLICE
    assert sliceTime == pytest.approx(MIDDLE_TIME)


def test_the_read_answers_one_surface_per_slice_with_the_marks_the_plugin_drew(shot):
    surface = shot.surfaceAt(MIDDLE_SLICE)
    assert surface['index'] == MIDDLE_SLICE
    assert surface['psi'].shape == (GRID_POINTS,)
    assert surface['R'].shape == (GRID_POINTS,)
    assert len(surface['levels']) >= 2
    # The boundary, the axis and the O-point are named positions, and the field.
    assert surface['boundary'] is not None
    assert surface['axis'] is not None
    assert surface['x_point'] is not None
    assert surface['b0'] == pytest.approx(-3.7634230842275067, rel=1e-3)
    assert surface['r0'] == pytest.approx(2.42, rel=1e-3)


def test_the_read_answers_the_wall_the_case_holds(shot):
    wall = shot.wall()
    assert wall is not None
    r, z = wall
    assert r.shape == z.shape == (WALL_POINTS,)


def test_the_read_answers_the_eight_profiles_on_the_radius_the_case_holds(shot):
    profiles = shot.profilesAt(MIDDLE_SLICE)
    assert [name for name, _values, _units in profiles['profiles']] == PROFILE_NAMES
    assert len(profiles['profiles']) == 8
    assert profiles['x_label'] == 'rho_tor_norm'
    assert profiles['x'].shape == (RADIAL_POINTS,)
    for _name, values, _units in profiles['profiles']:
        assert values.shape == (RADIAL_POINTS,)
    # The radially-named profile is drawn against the normalised radius, not the
    # raw one: the last point is the separator, and the abscissa runs to 1.
    assert float(profiles['x'][-1]) == pytest.approx(1.0)
    # The global quantities of the slice are values, not a drawing.
    assert 'ip' in profiles['global']


def test_a_case_with_no_equilibrium_is_refused_named(session):
    # The case is not open in this session, so the named refusal is the one the
    # addressing answers, before any surface is drawn or any window opened.
    core = McpGuiCore(api=session.api)
    with pytest.raises(ValueError) as raised:
        core.equilibrium_surfaces('imas:hdf5?path=/nowhere', [MIDDLE_TIME])
    assert 'not open in this session' in str(raised.value)


# --------------------------------------------------------------------------
# The figure: N frames, or one frame with the profiles under it
# --------------------------------------------------------------------------

def test_entry_zero_draws_the_three_instants_side_by_side(session):
    frame = session.run(0)
    assert session.keys[0] == KIND + '1'
    assert session.api.GetFiguresKeys(figureType=KIND) == [KIND + '1']
    # One frame per instant, on the common bounds, with a named wall.
    assert frame.surfaceFrames() == 3
    assert frame.profilePanels() == 0
    assert frame.isDrawing()
    assert nonEmptyGrab(frame)
    # Registered under its case, like the chart beside it, so the case gestures reach it.
    assert session.api.casesServedBy(frame) == (CASE_URI,)


def test_entry_one_draws_the_surface_with_the_profiles_under_it(session):
    # From the menu, entry 1 asks its instant through a dialog. A restore answers
    # it in the user's place, so the test does too: `answers` carries the time,
    # and the window comes back drawn without a question.
    frame = session.run(1,
                        answers=QVizPluginAnswers(occurrence=0,
                                                  figureKey=KIND + '2',
                                                  time=MIDDLE_TIME))
    assert session.keys[1] == KIND + '2'
    assert frame.surfaceFrames() == 1
    assert frame.profilePanels() == 8
    # The stack runs the eight profiles on the one abscissa they share.
    stack = frame.profilesStack()
    assert stack.abscissa is not None
    assert nonEmptyGrab(frame)
    assert session.api.casesServedBy(frame) == (CASE_URI,)


def test_the_two_windows_are_listed_as_figures_the_menus_walk(session):
    from imasviz.Viz_API import titleWithCases
    assert KIND in [prefix for _l, _i, prefix in FigureTypes.MENU_ORDER]
    assert sorted(session.api.GetFiguresKeys(figureType=KIND)) == [KIND + '1',
                                                                    KIND + '2']
    # One line per window, in the case's group. The line names the key, the case
    # it serves, and the IDS its entry ran on (read off the plugin stamp); the
    # window's own title bar carries the same line without the IDS.
    labels = {record.figureKey: record.label
              for record in session.api.openWindows()
              if record.figureKey in (KIND + '1', KIND + '2')}
    expected = {key: titleWithCases(key, (CASE_URI,), fromIds='equilibrium')
                for key in (KIND + '1', KIND + '2')}
    assert labels == expected, 'neither EquiSurfaces window is a line of the menu'
    for key in (KIND + '1', KIND + '2'):
        assert session.api.figureframes[key].windowTitle() == \
            titleWithCases(key, (CASE_URI,))


def test_the_entry_is_offered_on_equilibrium_and_no_other(session):
    plugin_entries = [entry for entry in session.entriesOn(IDS_NAME)
                      if entry.pluginName == PLUGIN]
    assert sorted(entry.number for entry in plugin_entries) == [0, 1]
    assert PLUGIN not in [entry.pluginName for entry in session.entriesOn(OTHER_ID_NAME)]


# --------------------------------------------------------------------------
# The session: the same window, under the same key and the same instant
# --------------------------------------------------------------------------

def test_a_session_puts_the_instant_window_back_under_its_key(session, tmp_path):
    from imasviz.VizGUI.VizConfigurations.QVizSessionFile import QVizSessionFile
    path = str(tmp_path / 'equilibrium_session.vsess')
    QVizSaveSession(session.api, path=path).execute()

    file = QVizSessionFile.read(path)
    plugin_windows = [window for case in file.cases for window in case.pluginWindows
                      if window.plugin == PLUGIN]
    keyed = {window.entry: window for window in plugin_windows}
    assert set(keyed) == {0, 1}
    assert keyed[0].time is None
    assert keyed[1].time == pytest.approx(MIDDLE_TIME)
    assert keyed[0].key == KIND + '1'
    assert keyed[1].key == KIND + '2'

    # Take the two windows down and put them back through the file.
    for key in (KIND + '2', KIND + '1'):
        session.api.DeleteFigure(figureKey=key)
    assert session.api.GetFiguresKeys(figureType=KIND) == []

    QVizRestoreSession(session.api, path=path).execute()
    session.qapp.processEvents()
    assert sorted(session.api.GetFiguresKeys(figureType=KIND)) == [KIND + '1',
                                                                    KIND + '2']
    # Entry 1 came back drawn on the instant the file held, not the one it opens on.
    assert nonEmptyGrab(session.api.figureframes[KIND + '2'])
    assert session.api.figureframes[KIND + '2'].profilePanels() == 8
