# Built-in
import warnings
import traceback
import threading
import sys, os, logging
from PyQt5.QtWidgets import QApplication

# Common
import matplotlib.pyplot as plt
#plt.switch_backend('Qt5Agg')

# IMAS
from imasviz.VizPlugins.VizPlugins import VizPlugins

# tofu
import sys
sys.path.insert(0,'/Home/LF218007/tofu/')
#print(sys.path)
import tofu as tf
sys.path.pop(0)
print('load ok')
print(tf.__version__)


class ToFuPlugin(VizPlugins):
    def __init__(self):
        VizPlugins.__init__(self)
        self.lidsok = ['wall', 'bolometer', 'interferometer',
                  'bremsstrahlung_visible', 'soft_x_rays',
                  'ece', 'polarimeter',
                  'spectrometer_visible']
        self.lidsok_overview = ['%s_overview'%ids
                                for ids in self.lidsok]

    def execute(self, pluginsConfiguration, dataTreeView):

        view = pluginsConfiguration.get('imasviz_view')
        node_attributes = pluginsConfiguration.get('node_attributes')

        dids = {'shot':view.dataSource.shotNumber,
                'user':view.dataSource.userName,
                'tokamak':view.dataSource.machineName,
                'run':view.dataSource.runNumber}
        ids = node_attributes.get('IDSName')

        try:
            print ('ToFuPlugin to be executed...')
            if ids not in self.lidsok:
                msg = "Required ids not handled by tofu yet:\n"
                msg += "    - ids requested: %s\n"%ids
                msg += "    - ids avail.: %s"%str(self.lidsok)
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
        a = {ids_over: [0, 1] for ids_over in self.lidsok_overview}
        return a

    def getAllEntries(self):
        #(config number, description)
        return [(0, 'tofu - geom...'), (1, 'tofu - data')]

    def getPluginsConfiguration(self):
        return [{'geom': True}, {'data': True}]

    def isEnabled(self):
        if 'WEST' in os.environ:
            return True
        return False
