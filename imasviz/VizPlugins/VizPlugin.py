# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""What a plugin is, and which ones this application offers.

The registration table is the only place a plugin is named -- which is what the
howto says ("add the plugin in RegisteredPlugins"). It used to not be: three more
tables lived in this module and named the same plugins again, keyed by plugin name
by hand. Measured, all three answered `KeyError` for the two plugins that *are*
registered -- they only knew the two that are not -- and `getEntriesFor` and
`getAllEntries` were the fallback the menu took for anything that did not inherit
this class, which is how a plugin honouring every documented method stayed
invisible without a word. `getAllEntries` also carried a second meaning, as a
static lookup table declared after the instance method of the same name, so the
base-class contract the howto documents was unreachable: `VizPlugin().getAllEntries()`
answered `TypeError: missing 1 required positional argument: 'pluginsName'`.

`getMenuItem` was worse than unused: it read `self.getSubjects()`, which no class
in the package defines, so calling it answered `AttributeError`.

What is left here is the contract the howto documents and the table that
registration is read from. Deciding what a registered plugin offers, and running
it, is `QVizPluginCatalog`.

The two records below belong to the contract because they are what a plugin and
the framework agree on about a window the plugin drew -- see `QVizPluginWindow`.
"""

from collections import namedtuple

# What a plugin says about the window it registered, so a session can put that
# window back. Measured on the reference case, neither registered window answers
# where it came from: the Profiles panel has no `figureKey` and no `key`
# attribute, and the Equilibrium chart has neither either -- only the api's
# `figureframes` bookkeeping knows the key, and only the plugin knew the entry
# number and the occurrence its own dialog had answered. So the plugin stamps
# this record on the frame it registers, and the session writes it.
QVizPluginWindow = namedtuple('QVizPluginWindow',
                              'uri plugin entry ids occurrence')

# The answers a session hands back to a plugin entry it is replaying, so the
# entry draws the window without asking the user a second time. The Profiles
# plugin asks which occurrence to plot through a modal `QInputDialog`: measured,
# a probe left to answer that dialog sat in `askForOccurrence` for 240 s until a
# watchdog killed it, which is why a restore cannot go through the question.
# `figureKey` is here for the same reason the plot commands take one: the key is
# the identity the Show/Hide and Delete menus address the window by.
QVizPluginAnswers = namedtuple('QVizPluginAnswers', 'occurrence figureKey')

RegisteredPlugins = {'equilibriumcharts': 'viz_equi.equilibriumcharts',
                     # 'ToFuPlugin': 'viz_tofu.viz_tofu_plugin',
                     # 'viz_example_plugin': 'viz_example_plugin.viz_example_plugin',
                     # 'viz_spectrometer_plugin': 'viz_spectrometer.viz_spectrometer_plugin',
                     'VizProfiles_plugin': 'viz_Profiles.VizProfiles_plugin',
                     # 'simplePlotPluginExample': 'viz_simple_plot_example.simplePlotPluginExample',
                     # 'ETSpluginIMASViz': 'viz_ETS.ETSpluginIMASViz',
                     # A plugin drawn in Qt Designer registers the window it is
                     # drawn from instead of a module path. Kept as the shape,
                     # not as an offer: this one is refused at the menu, because
                     # the .ui is drawn around an exampleWidget class this Qt
                     # cannot build -- see QVizPluginCatalog.
                     # 'example_UiPlugin': {'UiFile': 'examplePlugin.ui',
                     #                      'dir': os.environ['VIZ_HOME'] +
                     #                             '/imasviz/VizPlugins/viz_example/',
                     #                      'targetIDSroot': 'magnetics',
                     #                      'targetOccurrence': 0},
                     }


def getRegisteredPlugins():
    """The plugins this application offers, name to where they come from.

    A name mapped to a dotted path is a Python plugin under `imasviz.VizPlugins`,
    its class named after the key. A name mapped to a dictionary is a window
    drawn in Qt Designer, described by `UiFile`, `dir`, `targetIDSroot` and
    `targetOccurrence`.
    """
    return RegisteredPlugins


class VizPlugin:
    """The contract a plugin honours.

    A plugin decides from `self.selectedTreeNode`, the node it was offered on, and
    reaches its case through `self.dataTreeView`; both are set when the menu is
    built, so a plugin keeps no case of its own.
    """

    def __init__(self, *args, **kwargs):
        if len(args) == 2:
            self.selectedTreeNode = args[0]
            self.dataTreeView = args[1]
        else:
            self.selectedTreeNode = None
            self.dataTreeView = None

    def setSelectedTreeNode(self, selectedTreeNode):
        self.selectedTreeNode = selectedTreeNode

    def setDataTreeView(self, dataTreeView):
        self.dataTreeView = dataTreeView

    def isEnabled(self):
        """Whether this plugin takes part at all. A plugin says yes for itself."""
        return False

    def getEntries(self):
        """Which of `getAllEntries` this node earns, by their numbers."""
        raise ValueError('plugin getEntries() method should be implemented!')

    def getAllEntries(self):
        """What this plugin can do, as `[(number, what the menu says)]`."""
        raise ValueError('plugin getAllEntries() method should be implemented!')

    def execute(self, vizAPI, pluginEntry=None, answers=None):
        """Do one of them. `pluginEntry` is the number `getAllEntries` gave it.

        `answers` is what a session already answered in the place of the user --
        a `QVizPluginAnswers`, or None when the entry was chosen from the menu.
        A plugin whose entry asks a question of its own must take the answer from
        here instead of asking it again: the Profiles plugin asks the occurrence
        through a modal `QInputDialog`, and a restore that went through that
        dialog would sit waiting for a click nobody is going to give it. A plugin
        that ignores `answers` is refused by name at the restore, not run blind.
        """
        raise ValueError('plugin execute() method should be implemented!')

    def getPluginsConfiguration(self):
        """Anything extra this plugin needs to run, its own shape. None by default.

        The howto asks a plugin for this; the framework never asked it, and asked
        a per-name table instead -- which knew only plugins that were not
        registered.
        """
        return None
