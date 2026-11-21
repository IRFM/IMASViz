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

"""The derived quantities a case holds, as its own menu.

CASE scope: offered on the case's own menu bar (via
`catalog.caseEntries()`), so a right-click or the case menu on the shot
view surfaces them. The three actions read the case's leaves through
`McpGuiCore` (the same surface the agent and the tests use) and show the
answer in a window -- a refusal names the reason in that window, not a
silent return.

The physics is the one the tests pin (`test_157` for Greenwald, `test_158`
for beta_N and total pressure); the plugin adds the offering, nothing more:
disable it in the preferences and the three lines disappear from the case
menu, the case and its data are unchanged.
"""

from imasviz.VizPlugins.VizPlugin import (
    CASE,
    QVizPluginAction,
    QVizPluginScope,
    VizPlugin,
)

# The default path for the Greenwald triple, following the IMAS standard
# layout. A case that does not hold one of the three is refused by name --
# the same voice the pure formula uses (`test_157`).
_DEFAULT_NE   = 'equilibrium.time_slice[0].global_quantities.n_e'
_DEFAULT_IP   = 'equilibrium.time_slice[0].global_quantities.ip'
_DEFAULT_AREA = 'equilibrium.time_slice[0].global_quantities.area'


def _show_success(title, text):
    from PySide6.QtWidgets import QMessageBox
    QMessageBox.information(None, title, text)


def _show_error(title, message):
    from PySide6.QtWidgets import QMessageBox
    QMessageBox.warning(None, title, message)


def _greenwald_run(context):
    """Read the case's n_e, I_p, A and answer the Greenwald fraction."""
    from imasviz.VizAgent.core import McpGuiCore
    uri = context.uri
    if uri is None:
        _show_error('Quantités dérivées',
                    'No case is open; open one before asking for the Greenwald fraction.')
        return
    core = McpGuiCore(api=context.api)
    try:
        result = core.greenwald(uri, _DEFAULT_NE, _DEFAULT_IP, _DEFAULT_AREA)
    except ValueError as err:
        _show_error('Quantités dérivées', str(err))
        return
    fg = result.get('greenwald_fraction', [])
    lg = result.get('greenwald_limit', [])
    lines = ['Fraction de Greenwald', '']
    if fg:
        lines.append('f_G = %g' % fg[0])
    if lg:
        lines.append('n_G = %g m^-3' % lg[0])
    lines.append('n_e : %s' % result.get('n_e_path', _DEFAULT_NE))
    lines.append('I_p : %s' % result.get('ip_path', _DEFAULT_IP))
    lines.append('A   : %s' % result.get('area_path', _DEFAULT_AREA))
    _show_success('Quantités dérivées', '\n'.join(lines))


def _beta_run(context):
    """Read the case's normalized beta and show its stats."""
    from imasviz.VizAgent.core import McpGuiCore
    uri = context.uri
    if uri is None:
        _show_error('Quantités dérivées', 'No case is open.')
        return
    core = McpGuiCore(api=context.api)
    try:
        result = core.beta_normal(uri)
    except ValueError as err:
        _show_error('Quantités dérivées', str(err))
        return
    _format_and_show('Beta_N', result)


def _pressure_run(context):
    """Read the case's total pressure and show its stats."""
    from imasviz.VizAgent.core import McpGuiCore
    uri = context.uri
    if uri is None:
        _show_error('Quantités dérivées', 'No case is open.')
        return
    core = McpGuiCore(api=context.api)
    try:
        result = core.total_pressure(uri)
    except ValueError as err:
        _show_error('Quantités dérivées', str(err))
        return
    _format_and_show('Pression totale', result)


def _format_and_show(name, result):
    """A human-readable stat block: mean, max, min, points, path."""
    lines = [name, '']
    for key in ('mean', 'max', 'min'):
        val = result.get(key)
        if val is not None:
            lines.append('%s : %g' % (key, val))
    if 'points' in result:
        lines.append('%d point(s)' % result['points'])
    if 'path' in result:
        lines.append('sur : %s' % result['path'])
    _show_success('Quantités dérivées', '\n'.join(lines))


class VizDerivedQuantities(VizPlugin):
    """The three derived quantities of one case, on its own menu bar.

    SCOPE: CASE -- offered on the case's menu bar, found by `catalog.
    caseEntries()`. Each action delegates to the core surface that the
    tests pin (`test_157`, `test_158`); the plugin adds the menu line
    and the dialog, not the physics.
    """
    SCOPE = QVizPluginScope(CASE)
    LABEL = 'Quantités dérivées'
    ACTIONS = (
        QVizPluginAction(0, 'Fraction de Greenwald', run=_greenwald_run),
        QVizPluginAction(1, 'Beta_N', run=_beta_run),
        QVizPluginAction(2, 'Pression totale', run=_pressure_run),
    )
