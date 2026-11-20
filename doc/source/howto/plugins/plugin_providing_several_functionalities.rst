..
   Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
   and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
   CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
   The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

.. _plugin_providing_several_functionalities:

Example of a plugin providing several functionalities
=====================================================

Each feature a plugin offers is a ``QVizPluginAction`` in the ``ACTIONS`` tuple.
The framework shows one line in the :guilabel:`Plugins` menu per action; clicking
a line calls only that action's ``run`` method, with the :guilabel:`QVizPluginContext`.

For example, a plugin with two features:

.. code-block:: python

    from imasviz.VizPlugins.VizPlugin import (IDS, QVizPluginAction,
                                              QVizPluginScope, VizPlugin)

    class myPlugin(VizPlugin):
        def __init__(self):
            self.SCOPE = QVizPluginScope(IDS, ids=('equilibrium',))
            self.ACTIONS = (
                QVizPluginAction(0, 'Prints some node attributes to log...',
                                 run=self._printInfo),
                QVizPluginAction(1, 'Shows a 2D plot...',
                                 run=self._show2D),
            )

        def _printInfo(self, context):
            import logging
            logging.getLogger(context.uri).info(
                'equilibrium: %s', context.node.getParametrizedDataPath())

        def _show2D(self, context):
            # ... draw the 2D plot here ...
            pass

Each ``run`` method is independent: one cannot know the presence of the other.
A saved session that names a particular line by its action ``key`` replays only
that line, not both.

