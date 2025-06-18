# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# Built-in
import warnings
import traceback
import threading
import sys, os, logging
from PySide6.QtWidgets import QApplication

# Common
import matplotlib.pyplot as plt

# IMAS
from imasviz.VizPlugins.VizPlugin import VizPlugin

# tofu
import sys

try:
    import tofu as tf
except:
    logging.error("Tofu plugin: unable to import tofu package. Please load the "
                  "tofu module if available or use a python distribution providing tofu libraries.")

class ToFuPlugin(VizPlugin):
    def __init__(self):
        VizPlugin.__init__(self)
        self.lidsok = ['wall', 'bolometer', 'interferometer',
                  'bremsstrahlung_visible', 'soft_x_rays',
                  'ece', 'polarimeter',
                  'spectrometer_visible']
        self.lidsok_overview = ['%s_overview'%ids
                                for ids in self.lidsok]

    def execute(self, vizAPI, pluginEntry):

        view = self.dataTreeView
        vizNode = self.selectedTreeNode
        dataSource = vizAPI.GetDataSource(view)

        dargs = {'uri':dataSource.uri}
        ids = vizNode.getIDSName()

        if ids not in self.lidsok:
            msg = ids + " IDS not supported by tofu plugin\n"
            warnings.warn(msg)
            return None

        try:
            print('ToFuPlugin to be executed...')

            plt.ioff()
            figure = None

            # load config
            lids = list(set(['wall', ids]))
            multi = tf.imas2tofu.MultiIDSLoader(ids=lids, **dargs)
            # multi = tf.imas2tofu.MultiIDSLoader(dids=dids, **dargs)
            if ids == 'wall':
                obj = multi.to_Config(plot=False)
                lax = obj.plot(draw=True)
                figure = lax[0].get_figure()
            else:
                if pluginEntry == 0:
                    obj = multi.to_Cam(ids=ids, plot=False)
                    lax = obj.plot(draw=True)
                    figure = lax[0].get_figure()
                elif pluginEntry == 1:
                    obj = multi.to_Data(ids=ids, indch_auto=True,
                                        plot=False)
                    kh = obj.plot(draw=True)
                    figure = kh.can.figure
            figure.show()
        except :
            traceback.print_exc()
            logging.getLogger(self.dataTreeView.dataSource.uri).error(traceback.format_exc())


    def getEntries(self):
        if self.selectedTreeNode.getIDSName() in self.lidsok:
            return [0, 1]
        else:
            return []

    def getAllEntries(self):
        return [(0, 'tofu - geom...'), (1, 'tofu - data')] #(config number, description)

    def getDescription(self):
        """ Return plugin description.
        """

        return "Tofu plugin for IMASViz."


    def isEnabled(self):
        try:
            if tf.__version__ >= '1.4.2':
                return True
            return False
        except:
            return False
        return False
