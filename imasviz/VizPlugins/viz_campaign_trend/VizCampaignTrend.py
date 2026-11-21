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

"""The trend of one leaf across the shots currently open in this session.

APP scope: offered on the application's own menu bar (via
`catalog.appEntries()`), since a campaign by definition spans more than
one case and the application is the place where they are all open at the
same time.

The campaign reads the same leaf from every open shot in the order the
session holds them, computes the least-squares trend (`imasviz/
VizAnalysis/trend`, pinned in `test_159`), and shows the answer in a
window. The second action writes a self-contained HTML report under
`~/.imasviz/reports` and names the path in the window.

Both actions use the open cases via `context.api.DTVlist` -- the session
itself is the campaign: the shots the physicist has opened, in the order
they were opened, nothing more.
"""

from imasviz.VizPlugins.VizPlugin import (
    APP,
    QVizPluginAction,
    QVizPluginScope,
    VizPlugin,
)

# The path the campaign reads from every shot. A leaf that is stable across
# a campaign of shots is what a campaign physicist asks about; the default
# is the plasma current over time, the one leaf that every shot holds.
_DEFAULT_PATH = 'equilibrium.time_slice[0].global_quantities.ip'


def _show(title, text, error=False):
    from PySide6.QtWidgets import QMessageBox
    if error:
        QMessageBox.warning(None, title, text)
    else:
        QMessageBox.information(None, title, text)


def _campaign_cases(context):
    """The shot URIs in the session, in the order they were opened."""
    dvtlist = list(getattr(context.api, 'DTVlist', None) or [])
    return [view.uri for view in dvtlist
            if getattr(view, 'uri', None)]


def _campaign_run(context):
    """Compute the trend of the default leaf across the open shots."""
    from imasviz.VizAgent.core import McpGuiCore
    cases = _campaign_cases(context)
    if len(cases) < 2:
        _show('Campagne',
              'A trend needs at least 2 open cases; the session holds %d.'
              % len(cases), error=True)
        return
    core = McpGuiCore(api=context.api)
    try:
        result = core.campaign(cases, _DEFAULT_PATH)
    except ValueError as err:
        _show('Campagne', str(err), error=True)
        return
    trend = result['trend']
    lines = ['Campagne — %d jeu(x)' % len(cases), '',
             'direction : %s' % trend['direction'],
             'variation : %g' % trend['change'],
             'pente     : %g / jeu' % trend['slope']]
    for row in result['rows']:
        lines.append('  %s : %g' % (row['uri'], row['value']))
    _show('Campagne', '\n'.join(lines))


def _campaign_report_run(context):
    """Write the HTML report and name the path in the window."""
    from imasviz.VizAgent.core import McpGuiCore
    cases = _campaign_cases(context)
    if len(cases) < 2:
        _show('Campagne',
              'A trend needs at least 2 open cases; the session holds %d.'
              % len(cases), error=True)
        return
    core = McpGuiCore(api=context.api)
    try:
        result = core.campaign_report(cases, _DEFAULT_PATH)
    except ValueError as err:
        _show('Campagne', str(err), error=True)
        return
    _show('Campagne',
          'Rapport écrit dans :\n%s' % result['saved_to'])


class VizCampaignTrend(VizPlugin):
    """The trend of the current session's shots, on the application menu bar.

    SCOPE: APP -- offered on the application's own menu bar, found by
    `catalog.appEntries()`. The campaign is the shot list the session
    already holds; the user does not name the shots, the session holds
    them.
    """
    SCOPE = QVizPluginScope(APP)
    LABEL = 'Campagne'
    ACTIONS = (
        QVizPluginAction(0, 'Tendance (%s)' % _DEFAULT_PATH.split('.')[-1],
                         run=_campaign_run),
        QVizPluginAction(1, 'Exporter le rapport', run=_campaign_report_run),
    )
