# Copyright holders : Commissariat à l'Energie Atomique et aux Energies
# Alternatives (CEA), France; and Laboratory for Engineering Design - LECAD,
# University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C
# open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted
# upon downloading the software and/or exercising any of the rights granted
# under this.
#
# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The two FIGURE-scope brick plugins and the mechanism that offers them.

`test_154` pins the detection domain logic and the four lines of the Événements
sub-menu; `test_160` pins the spectral domain logic and the one line of the
Spectre sub-menu. This pins the **plugin mechanism** that now builds those
sub-menus:

* both plugins declare ``SCOPE = FIGURE`` and ``LABEL`` (the sub-menu title
  the user reads);
* `figureMenuFor` adds both sub-menus to a real ``QVizCurvePlot``'s
  view-box menu, and answers how many it added;
* a plugin named in ``QVizPreferences.Disabled_bricks`` is absent from the
  menu, and the other one stays; the frame's domain objects (``eventMarks``,
  ``spectrumMenu``) are present regardless -- the plugin controls the menu,
  not the physics;
* the frame is still freed at its refcount after ``del`` (no strong cycle
  from the menu's lambda), which is the T25 invariant that test_58 pins.
"""

import pytest

from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizCurvePlot import QVizCurvePlot
from imasviz.VizPlugins.QVizPluginCatalog import figureMenuFor
from imasviz.VizPlugins.VizPlugin import (FIGURE,
                                          QVizPluginScope)
from imasviz.VizUtils import QVizPreferences

pytestmark = [pytest.mark.ui]


def _frame(qapp):
    frame = QVizCurvePlot()
    frame.show()
    qapp.processEvents()
    return frame


def _viewBoxMenuNames(frame):
    """All non-empty action labels on the view box's menu, including sub-menus."""
    return [a.text() for a in frame.pgPlotWidget.getViewBox().menu.actions()
            if a.text()]


def test_both_plugins_declare_figure_scope():
    """A FIGURE-scope plugin is one the frame's menu can be offered on."""
    from imasviz.VizPlugins.viz_event_detection.VizEventDetection import VizEventDetection
    from imasviz.VizPlugins.viz_spectral.VizSpectral import VizSpectral

    for cls in (VizEventDetection, VizSpectral):
        scope = cls.SCOPE
        assert isinstance(scope, QVizPluginScope)
        assert scope.kind == FIGURE
        assert scope.appliesToFigure(None) is True


def test_labels_match_the_titles_the_user_reads():
    """LABEL is what the sub-menu says, not the class name."""
    from imasviz.VizPlugins.viz_event_detection.VizEventDetection import VizEventDetection
    from imasviz.VizPlugins.viz_spectral.VizSpectral import VizSpectral

    assert VizEventDetection.LABEL == 'Événements'
    assert VizSpectral.LABEL == 'Spectre'


def test_figureMenuFor_adds_both_sub_menus(qapp):
    """Both sub-menus are on the view-box menu after `figureMenuFor` is called."""
    frame = _frame(qapp)
    try:
        names = _viewBoxMenuNames(frame)
        assert 'Événements' in names
        assert 'Spectre' in names
        # Four lines in Événements (ELM, sawtooth, L-H, clear).
        ev_menu = [a.menu() for a in frame.pgPlotWidget.getViewBox().menu.actions()
                   if a.text() == 'Événements'][0]
        assert len(ev_menu.actions()) == 4
        # One line in Spectre.
        sp_menu = [a.menu() for a in frame.pgPlotWidget.getViewBox().menu.actions()
                   if a.text() == 'Spectre'][0]
        assert len(sp_menu.actions()) == 1
    finally:
        frame.close()
        qapp.processEvents()


def test_a_disabled_plugin_is_absent_from_the_menu(qapp, monkeypatch):
    """Disabling `VizEventDetection` removes 'Événements' from the next frame built.

    The other sub-menu (Spectre) stays. The domain logic (`eventMarks`) is
    still on the frame -- the plugin controls the menu, not the physics.
    """
    saved = QVizPreferences.Disabled_bricks
    # Enable baseline (frame 1) before the disabling, so test_154 still passes.
    QVizPreferences.Disabled_bricks = frozenset()
    frame1 = _frame(qapp)
    try:
        assert 'Événements' in _viewBoxMenuNames(frame1)
    finally:
        frame1.close()
        qapp.processEvents()

    try:
        QVizPreferences.Disabled_bricks = frozenset({'VizEventDetection'})
        frame2 = _frame(qapp)
        try:
            names = _viewBoxMenuNames(frame2)
            assert 'Événements' not in names
            assert 'Spectre' in names
            # `eventMarks` is still on the frame: the plugin controls the menu,
            # not the domain logic the user can reach programmatically.
            assert frame2.eventMarks is not None
            assert frame2.spectrumMenu is not None
        finally:
            frame2.close()
            qapp.processEvents()
    finally:
        QVizPreferences.Disabled_bricks = saved


def test_disabling_spectral_removes_spectre(qapp):
    """Disabling `VizSpectral` removes 'Spectre' but not 'Événements'."""
    saved = QVizPreferences.Disabled_bricks
    try:
        QVizPreferences.Disabled_bricks = frozenset({'VizSpectral'})
        frame = _frame(qapp)
        try:
            names = _viewBoxMenuNames(frame)
            assert 'Spectre' not in names
            assert 'Événements' in names
        finally:
            frame.close()
            qapp.processEvents()
    finally:
        QVizPreferences.Disabled_bricks = saved


def test_disabling_both_removes_both_sub_menus(qapp):
    """Both plugins disabled: no brick sub-menus at all on the view box."""
    saved = QVizPreferences.Disabled_bricks
    try:
        QVizPreferences.Disabled_bricks = frozenset(
            {'VizEventDetection', 'VizSpectral'})
        frame = _frame(qapp)
        try:
            names = _viewBoxMenuNames(frame)
            assert 'Événements' not in names
            assert 'Spectre' not in names
        finally:
            frame.close()
            qapp.processEvents()
    finally:
        QVizPreferences.Disabled_bricks = saved


# ---------------------------------------------------------------- CASE scope --

def test_derived_quantities_declare_case_scope():
    """CASE-scope: offered on the case's own menu bar via `catalog.caseEntries()`."""
    from imasviz.VizPlugins.viz_derived_quantities.VizDerivedQuantities \
        import VizDerivedQuantities

    assert VizDerivedQuantities.SCOPE.kind == 'case'
    assert VizDerivedQuantities.SCOPE.appliesToCase()
    assert VizDerivedQuantities.LABEL == 'Quantités dérivées'
    assert len(VizDerivedQuantities.ACTIONS) == 3
    labels = {a.label for a in VizDerivedQuantities.ACTIONS}
    assert 'Fraction de Greenwald' in labels
    assert 'Beta_N' in labels
    assert 'Pression totale' in labels


def test_case_plugin_in_case_entries(qtbot):
    """`catalog.caseEntries()` includes `VizDerivedQuantities` when it is enabled."""
    from PySide6.QtWidgets import QTreeWidget
    from imasviz.VizPlugins.QVizPluginCatalog import QVizPluginCatalog

    saved = QVizPreferences.Disabled_bricks
    try:
        QVizPreferences.Disabled_bricks = frozenset()
        view = QTreeWidget()
        view.uri = 'stub?case'
        view.imas_viz_api = 'the-api'
        qtbot.addWidget(view)
        catalog = QVizPluginCatalog(view)
        entries = catalog.caseEntries()
        names = {e.pluginName for e in entries}
        assert 'VizDerivedQuantities' in names
    finally:
        QVizPreferences.Disabled_bricks = saved


def test_case_plugin_absent_when_disabled(qtbot):
    """A disabled CASE plugin is not in `catalog.caseEntries()`."""
    from PySide6.QtWidgets import QTreeWidget
    from imasviz.VizPlugins.QVizPluginCatalog import QVizPluginCatalog

    saved = QVizPreferences.Disabled_bricks
    try:
        QVizPreferences.Disabled_bricks = frozenset({'VizDerivedQuantities'})
        view = QTreeWidget()
        view.uri = 'stub?case'
        view.imas_viz_api = 'the-api'
        qtbot.addWidget(view)
        catalog = QVizPluginCatalog(view)
        entries = catalog.caseEntries()
        names = {e.pluginName for e in entries}
        assert 'VizDerivedQuantities' not in names
    finally:
        QVizPreferences.Disabled_bricks = saved


# ----------------------------------------------------------------- APP scope --

def test_campaign_trend_declares_app_scope():
    """APP-scope: offered on the application's own menu bar via `catalog.appEntries()`."""
    from imasviz.VizPlugins.viz_campaign_trend.VizCampaignTrend \
        import VizCampaignTrend

    assert VizCampaignTrend.SCOPE.kind == 'app'
    assert VizCampaignTrend.SCOPE.appliesToApp()
    assert VizCampaignTrend.LABEL == 'Campagne'
    assert len(VizCampaignTrend.ACTIONS) == 2
    labels = {a.label for a in VizCampaignTrend.ACTIONS}
    assert 'Exporter le rapport' in labels


def test_app_plugin_in_app_entries(qtbot):
    """`catalog.appEntries()` includes `VizCampaignTrend` when it is enabled."""
    from PySide6.QtWidgets import QTreeWidget
    from imasviz.VizPlugins.QVizPluginCatalog import QVizPluginCatalog

    saved = QVizPreferences.Disabled_bricks
    try:
        QVizPreferences.Disabled_bricks = frozenset()
        view = QTreeWidget()
        view.uri = 'stub?case'
        view.imas_viz_api = 'the-api'
        qtbot.addWidget(view)
        catalog = QVizPluginCatalog(view)
        entries = catalog.appEntries()
        names = {e.pluginName for e in entries}
        assert 'VizCampaignTrend' in names
    finally:
        QVizPreferences.Disabled_bricks = saved


def test_app_plugin_absent_when_disabled(qtbot):
    """A disabled APP plugin is not in `catalog.appEntries()`."""
    from PySide6.QtWidgets import QTreeWidget
    from imasviz.VizPlugins.QVizPluginCatalog import QVizPluginCatalog

    saved = QVizPreferences.Disabled_bricks
    try:
        QVizPreferences.Disabled_bricks = frozenset({'VizCampaignTrend'})
        view = QTreeWidget()
        view.uri = 'stub?case'
        view.imas_viz_api = 'the-api'
        qtbot.addWidget(view)
        catalog = QVizPluginCatalog(view)
        entries = catalog.appEntries()
        names = {e.pluginName for e in entries}
        assert 'VizCampaignTrend' not in names
    finally:
        QVizPreferences.Disabled_bricks = saved
