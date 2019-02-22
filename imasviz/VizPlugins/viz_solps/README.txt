Full procedure of converting .ui (made by QtDesigner) to .py plugin which can be used in IMASViz:

$ python3 -m PyQt5.uic.pyuic -x designer_SOLPSPlugin.ui -o designer_SOLPSPlugin.py
$ python3 qtDesigner_py_to_IMASViz.py --filename=designer_SOLPSPlugin.py --outfile=SOLPSPlugin.py

export PYTHONPATH=${VIZ_HOME}/imasviz/VizPlugins/viz_solps:${PYTHONPATH}

