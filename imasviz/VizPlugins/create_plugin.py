# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""Scaffolding a plugin of this user's own.

What the scaffold writes used to land in `$VIZ_HOME/imasviz/VizPlugins/` -- the
package IMASViz is shipped as. Two things were wrong about that: an installed
IMASViz lives in a tree the run does not own, so the write simply fails; and when
it did work, the package was left holding a file its owner never chose, in a
checkout that had diverged from what upstream has. The plugin goes to
`$HOME/.imasviz/plugins/` instead, next to the preferences and the plot
configurations the application already owns, where `QVizPluginSource` finds it
without anyone editing `RegisteredPlugins`.

The template used to end in `dataSource.getImasEntry(occurrence)` and a `print`.
Neither works here: `getImasEntry` is not a method of a data source -- the
accessor the two shipped plugins use is `dataSource.get(<ids>, <occurrence>)` --
and `print` goes to stdout, which is nowhere a user of the GUI looks; the log
panel shows what is logged under the URI of the case. So the scaffold now draws
through the same command the tree's own *Plot* gesture uses (`QVizPlotOneNode`):
one right click on the target IDS and there is a window on screen, registered
like any other figure, before a single line of the plugin has been written by
hand.

That is the point of the shape: the first click on a freshly created plugin has to
*do* something, because "it is in the menu" is not evidence that the plugin runs.
"""

import os

from imasviz.VizPlugins.QVizPluginSource import (QVizPluginSource, USER,
                                                 compileCheck, pluginNameFor,
                                                 userPluginsFolder)

LICENSE = '''# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************
'''

PLUGIN_TEMPLATE = LICENSE + '''
"""{description}

Written by IMASViz. This plugin answers the Plugins menu of the **{idsName}**
IDS root of the case under the cursor, and draws a real figure through the same
command the tree's own *Plot* gesture uses.

The contract it honours is declarative:
- ``SCOPE`` declares where it is offered: here, the {idsName} IDS root.
- ``ACTIONS`` declares what it offers and how each is run.
- The ``QVizPluginContext`` it reads carries the api, the case, and the node
  the menu was built on -- it has no other attributes to set or bind.
"""

import logging

from imasviz.VizPlugins.VizPlugin import (IDS as _IDS, QVizPluginAction,
                                          QVizPluginScope, VizPlugin)


class {className}(VizPlugin):
    """{description}"""

    IDS = "{idsName}"
    OCCURRENCE = 0

    def _run(self, context):
        """Draw one quantity of this IDS, in a figure of IMASViz's own.

        ``context`` carries the api, the case, and the node the menu was built
        on. ``context.answers`` is what a saved session hands back in the user's
        place -- ``None`` from the menu -- and is used to honour a figure key.
        """
        from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotOneNode \\
            import QVizPlotOneNode

        log = logging.getLogger(context.view.uri)
        node = context.node
        if node is None:
            raise ValueError('nothing was under the cursor to draw')

        vizAPI = context.api

        if node.isIDSRoot() or node.isStructure() or node.isArrayOfStructure():
            if not vizAPI.IDSDataAlreadyFetched(context.view, self.IDS,
                                                self.OCCURRENCE):
                vizAPI.LoadIDSData(context.view, self.IDS, self.OCCURRENCE)
            _loaded, signals = vizAPI.getAll_0D_1D_Nodes(node)
            if not signals:
                raise ValueError('the %s IDS of this case holds no 1D signal '
                                 'to draw' % self.IDS)
            node = signals[0]
            log.info('%s draws %s, the first 1D signal of the %s IDS.',
                     self.__class__.__name__,
                     node.getParametrizedDataPath(), self.IDS)

        subWindow = None
        command = QVizPlotOneNode(dataTreeView=context.view, treeNode=node)
        frame = command.execute()
        if frame is None:
            raise ValueError('the figure for this node could not be opened: '
                             'see the log of this case for the reason')
        if command.builtFigure:
            subWindow = vizAPI.addPlotWidgetToMDI(frame)
        frame.show()
        if subWindow is not None:
            subWindow.raise_()
            subWindow.activateWindow()

    def __init__(self):
        super().__init__()
        self.SCOPE = QVizPluginScope(_IDS, ids=(self.IDS,))
        self.ACTIONS = (QVizPluginAction(0, "{menuTitle}",
                                         run=self._run),)
'''

INIT_TEMPLATE = LICENSE + '''
# A plugin of this user's own. IMASViz finds it by looking in its own plugins
# folder: nothing has to be added to RegisteredPlugins for it to be offered.

from .{className} import {className}
'''


def createPlugin(name, targetIds='equilibrium', description=None,
                 menuTitle=None, folder=None):
    """Write a working plugin of this user's own, and answer what was written.

    The returned `QVizPluginSource` is what the caller hands to the file watcher
    and to the editor: the folder it lives in, the file to show, and the fact that
    it is writable.
    """
    # One naming rule for whoever makes a plugin, the creator and *copy into my
    # plugins* alike: the folder, the module and the class have to bear one name.
    className = pluginNameFor(name)
    idsName = (targetIds or '').strip()
    if not idsName:
        raise ValueError('a plugin needs the name of the IDS it is for, for '
                         'example "equilibrium"')
    description = (description or '').strip() or ('%s: a plugin of my own.'
                                                  % className)
    menuTitle = (menuTitle or '').strip() or '%s...' % className

    folder = userPluginsFolder() if folder is None else folder
    package = 'viz_' + className.lower()
    directory = os.path.join(folder, package)
    if os.path.exists(directory):
        raise ValueError('%s already holds a plugin called %s'
                         % (folder, className))

    modulePath = os.path.join(directory, className + '.py')
    source = PLUGIN_TEMPLATE.format(className=className, idsName=idsName,
                                    description=description,
                                    menuTitle=menuTitle)
    # Checked before any of it is on disk: a template that stopped parsing must
    # not become a folder the menu then refuses every time it is built.
    compileCheck(source, modulePath)
    initSource = INIT_TEMPLATE.format(className=className)
    compileCheck(initSource, os.path.join(directory, '__init__.py'))

    os.makedirs(directory)
    try:
        with open(modulePath, 'w', encoding='utf-8') as handle:
            handle.write(source)
        with open(os.path.join(directory, '__init__.py'), 'w',
                  encoding='utf-8') as handle:
            handle.write(initSource)
    except OSError as error:
        raise ValueError('%s could not be written: %s: %s'
                         % (directory, type(error).__name__, error))

    return QVizPluginSource(className, package + '.' + className, USER,
                            folder=directory, fileName=modulePath)
