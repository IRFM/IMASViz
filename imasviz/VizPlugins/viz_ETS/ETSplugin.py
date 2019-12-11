#  Name   : ETSplugin
#
#           Initial ETS plugin.
#
#  Author :
#         Dejan Penko
#         Jorge Ferreira
#  E-mail :
#         dejan.penko@lecad.fs.uni-lj.si
#         jferreira@ipfn.tecnico.ulisboa.pt
#
#****************************************************
#     Copyright(c) 2019- D. Penko, J. Ferreira

import logging, os, sys
import matplotlib.pyplot as plt
import imas

def checkArguments():
    """ Check arguments when running plugin from the terminal (standalone).
    """

    if (len(sys.argv) > 1):
        import argparse
        from argparse import RawTextHelpFormatter
        description = """ETS plugin. Example for running it from terminal:
>> python3 ETSplugin.py --shot=36440 --run=1 --user=penkod --device=aug
"""

        parser = argparse.ArgumentParser(description=description,
                                         formatter_class=RawTextHelpFormatter)

        parser.add_argument("-s", "--shot", type=int, required=True,
                            help="Case parameter: shot")
        parser.add_argument("-r", "--run", type=int, required=True,
                            help="Case parameter: run")
        parser.add_argument("-u", "--user", type=str, required=True,
                            help="Case parameter: username")
        parser.add_argument("-d", "--device", type=str, required=True,
                            help="Case parameter: device")

        args = parser.parse_args()
        IDS_parameters = {  "shot": args.shot,
                            "run": args.run,
                            "user": args.user,
                            "device": args.device}
    else:
        # Default parameters
        print("Using default parameters")
        IDS_parameters = {  "shot": 36440,
                            "run": 1,
                            "user": "penkod",
                            "device": "aug"}

    return IDS_parameters

class ETSplugin():
    def __init__(self, IDS_parameters, ids=None):
        """
        Arguments:
            IDS_parameters (Dictionary) : Dictionary containing IDS parameters
                                          (shot, run, user, device)
            ids            (obj)        : IDS object
        """
        self.ids = ids
        self.IDS_parameters = IDS_parameters

    def setIDS(self):
        try:
            self.ids = imas.ids(self.IDS_parameters["shot"],self.IDS_parameters["run"])
            self.ids.open_env(self.IDS_parameters["user"], self.IDS_parameters["device"], '3')
        except:
            self.ids = None
            print("Error when trying to get() the IDS. Data for given IDS " \
                  "parameters either doesn't exist or is corrupted.")

    def getCoreProfiles(self):
        if self.ids != None:
            self.ids.core_profiles.get()
            # Second method of opening slice
            # ts = 2.0
            # self.ids.core_profiles.getSlice(ts, imas.imasdef.CLOSEST_SAMPLE)

    def plot(self):

        if self.ids == None:
            print("IDS object is None!")
            return

        # Displaying basic information
        print('Reading data...')
        print('Shot    =', self.IDS_parameters["shot"])
        print('Run     =', self.IDS_parameters["run"])
        print('User    =', self.IDS_parameters["user"])
        print('Device =', self.IDS_parameters["device"])
        # print('ts =', ts)

        # Extrat and plot data
        cp = self.ids.core_profiles.profiles_1d[0]

        plt.figure()
        plt.subplot(2,2,1)
        plt.plot(cp.grid.rho_tor_norm, 1.0e-3*cp.electrons.temperature, label='el')
        for i in range(len(cp.ion)):
            if cp.ion[i].multiple_states_flag == 0 :
                plt.plot(cp.grid.rho_tor_norm, 1.0e-3*cp.ion[i].temperature, label='ion %d'%(i+1))
        plt.title('temperature')
        plt.ylabel('[keV]')
        plt.legend()

        plt.subplot(2,2,2)
        plt.plot(cp.grid.rho_tor_norm, 1.0e-19*cp.electrons.density_thermal, label='el')
        for i in range(len(cp.ion)):
            if cp.ion[i].multiple_states_flag == 0 :
                plt.plot(cp.grid.rho_tor_norm, 1.0e-19*cp.ion[i].density_thermal, label='ion %d'%(i+1))
        plt.title('density')
        plt.ylabel('[10^19 m-3]')
        plt.legend()

        plt.subplot(2,2,3)
        plt.plot(cp.grid.rho_tor_norm, 1.0e-6*cp.j_total, label='j_tor')
        plt.title('current')
        plt.ylabel('[MA m-2]')
        plt.xlabel('rhon')
        plt.legend()

        plt.subplot(2,2,4)
        plt.plot(cp.grid.rho_tor_norm, cp.q, label='q')
        plt.xlabel('rhon')
        plt.twinx()
        plt.plot(cp.grid.rho_tor_norm, cp.magnetic_shear, color='C1', label='shear')
        plt.title('safety factor / shear')
        plt.ylabel('[-]')
        plt.legend()

        plt.show()

if  __name__ == "__main__":
    # Set mandatory arguments
    IDS_parameters = checkArguments()

    ets = ETSplugin(IDS_parameters)
    ets.setIDS()
    ets.getCoreProfiles()
    ets.plot()
