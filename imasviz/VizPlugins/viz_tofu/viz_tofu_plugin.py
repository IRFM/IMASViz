# Built-in
import warnings
import traceback
import threading
import sys, os, logging
from PyQt5.QtWidgets import QApplication

# Common
import matplotlib.pyplot as plt

# IMAS
from imasviz.VizPlugins.VizPlugins import VizPlugins

# tofu
import sys
import tofu as tf

class ToFuPlugin(VizPlugins):
    def __init__(self):
        VizPlugins.__init__(self)
        self.lidsok = ['wall', 'bolometer', 'interferometer',
                  'bremsstrahlung_visible', 'soft_x_rays',
                  'ece', 'polarimeter',
                  'spectrometer_visible']
        self.lidsok_overview = ['%s_overview'%ids
                                for ids in self.lidsok]

    def execute(self, vizAPI):

        view = self.dataTreeView
        vizNode = self.selectedTreeNode
        pluginsConfiguration = self.getPluginsConfiguration()

        dids = {'shot':view.dataSource.shotNumber,
                'user':view.dataSource.userName,
                'tokamak':view.dataSource.machineName,
                'run':view.dataSource.runNumber}
        ids = vizNode.getIDSName()

        try:
            print('ToFuPlugin to be executed...')
            if ids not in self.lidsok:
                msg = ids + " IDS not supported by tofu plugin\n"
                warnings.warn(msg)
                return None

            plt.ioff()
            figure = None

            # load config
            lids = list(set(['wall', ids]))
            multi = tf.imas2tofu.MultiIDSLoader(ids=lids, **dids)
            if ids == 'wall':
                obj = multi.to_Config(plot=False)
                lax = obj.plot(draw=True)
                figure = lax[0].get_figure()
            else:
                if pluginsConfiguration.get('geom'):
                    obj = multi.to_Cam(ids=ids, plot=False)
                    lax = obj.plot(draw=True)
                    figure = lax[0].get_figure()
                elif pluginsConfiguration.get('data'):
                    obj = multi.to_Data(ids=ids, indch_auto=True,
                                        plot=False)
                    kh = obj.plot(draw=True)
                    figure = kh.can.figure
            figure.show()
        except :
            traceback.print_exc()
            logging.error(traceback.format_exc())


    def getEntriesPerSubject(self):
        return {ids_over: [0, 1] for ids_over in self.lidsok_overview}

    def getAllEntries(self):
        #(config number, description)
        return [(0, 'tofu - geom...'), (1, 'tofu - data')]

    def getPluginsConfiguration(self):
        return [{'geom': True}, {'data': True}]

    def isEnabled(self):
        if 'WEST' in os.environ:
            return True
        return False
