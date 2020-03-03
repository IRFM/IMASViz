# Built-in
import warnings
import traceback
import threading
import sys, os, logging
from PyQt5.QtWidgets import QApplication

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

        dargs = {'shot':dataSource.shotNumber,
                'user':dataSource.userName,
                'database':dataSource.machineName,
                'run':dataSource.runNumber}
        ids = vizNode.getIDSName()

        if ids not in self.lidsok:
            msg = ids + " IDS not supported by tofu plugin\n"
            warnings.warn(msg)
            return None

        """
        idssByNames (dict) # key = IDS name, value = IDS object
        """
        # idssByNames = vizAPI.loadRequiredIDSs(view, vizNode, [vizNode.getIDSName(), 'wall'])
        # dids = {key: {'ids': val, 'isget':True} for key, val in idssByNames.items()}

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
            logging.error(traceback.format_exc())


    def getEntries(self):
        if self.selectedTreeNode.getIDSName() in self.lidsok:
            return [0, 1]
        else:
            return []

    def getAllEntries(self):
        return [(0, 'tofu - geom...'), (1, 'tofu - data')] #(config number, description)

    def isEnabled(self):
        if tf.__version__ >= '1.4.2':
            return True
        return False
