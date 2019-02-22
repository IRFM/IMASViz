#! /usr/bin/env python3
import sys
import os

def qtDesPy2IMASViz(filename, outfile):
    with open(filename, "rt") as fin:
        with open(outfile, "wt") as fout:
            for line in fin:
                fout.write(line)
                if 'from PyQt5 import QtCore, QtGui, QtWidgets' in line:
                    fout.write(
"""import sys
import os
# Add imasviz source path
sys.path.append((os.environ['VIZ_HOME'] + '/imasviz/VizPlugins/viz_solps'))
""")
                if 'self.centralwidget.setObjectName("centralwidget")' in line:
                    fout.write('        self.centralwidget.parent = MainWindow\n')

if __name__ == '__main__':
    import getopt

    # For launching python script directly from terminal with python command
    Help = """
    This script is used to make the .py plugin file, converted from QtDesigner
    .ui file, compatible with IMASViz.

    python3 qtDesigner_py_to_IMASViz.py --filename=designer_SOLPSPlugin.py
    --out=SOLPSPlugin.py
    """
    try:
        opts, args = getopt.getopt(sys.argv[1:], "srudvh", ["filename=",
                                                            "outfile=",
                                                            "help"])
        for opt, arg in opts:
            if opt in ("-F", "--filename"):
                filename = arg
            elif opt in ("-O", "--outfile"):
                outfile = arg

            if opt in ("-h", "--help"):
                print(Help)
                sys.exit()

        qtDesPy2IMASViz(filename, outfile)

    except Exception:
        print('Supplied option not recognized!')
        print('For help: -h / --help')
        sys.exit(2)


