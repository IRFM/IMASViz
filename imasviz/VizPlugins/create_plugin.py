# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""CLI and utility tool to scaffold a new IMASViz plugin."""

import os
import sys

PLUGIN_TEMPLATE = '''# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************
# CeCILL-C open source license

"""{description}"""

import logging
from imasviz.VizPlugins.VizPlugin import VizPlugin


class {className}(VizPlugin):
    """{description}"""

    def __init__(self):
        super().__init__()

    def isEnabled(self):
        return True

    def getEntries(self):
        if self.selectedTreeNode and self.selectedTreeNode.getIDSName() == "{target_ids}":
            return [0]
        return []

    def getAllEntries(self):
        return [(0, "{menu_title}")]

    def execute(self, vizAPI, pluginEntry=None, answers=None):
        dataSource = vizAPI.GetDataSource(self.dataTreeView)
        uri = dataSource.uri
        occurrence = 0

        if not vizAPI.IDSDataAlreadyFetched(self.dataTreeView, '{target_ids}', occurrence):
            logging.getLogger(dataSource.uri).info('Loading {target_ids} IDS...')
            vizAPI.LoadIDSData(self.dataTreeView, '{target_ids}', occurrence)

        ids = dataSource.getImasEntry(occurrence)
        print('Plugin {className} executed successfully on URI:', uri)
        # TODO: Add your visualization or data processing logic here
'''


def createPlugin(pluginName, targetIds='equilibrium', description='A custom IMASViz plugin.', menuTitle=None):
    vizHome = os.environ.get('VIZ_HOME', os.getcwd())
    pluginsDir = os.path.join(vizHome, 'imasviz', 'VizPlugins')
    if not os.path.exists(pluginsDir):
        os.makedirs(pluginsDir, exist_ok=True)

    dirName = f'viz_{pluginName.lower()}'
    pluginDir = os.path.join(pluginsDir, dirName)
    os.makedirs(pluginDir, exist_ok=True)

    # Class name PascalCase
    className = ''.join(word.capitalize() for word in pluginName.replace('_', ' ').split())
    if not className.endswith('Plugin'):
        className += 'Plugin'

    if not menuTitle:
        menuTitle = f'{pluginName} plugin action'

    # 1. Write plugin file
    pyFilePath = os.path.join(pluginDir, f'{className}.py')
    content = PLUGIN_TEMPLATE.format(
        className=className,
        description=description,
        target_ids=targetIds,
        menu_title=menuTitle
    )
    with open(pyFilePath, 'w') as f:
        f.write(content)

    # 2. Write __init__.py
    initPath = os.path.join(pluginDir, '__init__.py')
    initContent = f'''# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************
from .{className} import {className}
'''
    with open(initPath, 'w') as f:
        f.write(initContent)

    print(f'Successfully created plugin {className} at {pyFilePath}')
    return className, dirName


if __name__ == '__main__':
    name = sys.argv[1] if len(sys.argv) > 1 else 'sample'
    ids = sys.argv[2] if len(sys.argv) > 2 else 'equilibrium'
    createPlugin(name, targetIds=ids)
