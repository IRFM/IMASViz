..
   Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
   and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
   CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
   The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

.. IMASViz documentation master file, created by
   sphinx-quickstart on Tue Nov 27 12:07:15 2018.
   You can adapt this file completely, but it should at least
   contain the root `toctree` directive.

IMASViz
=======

**A graphical browser for plasma data stored in IMAS.**

IMASViz opens a case -- a pulse of a machine, held in an IMAS database on disk or
reached over the network -- and shows what it holds as the tree of IDSs and nodes
the data dictionary describes. From that tree a quantity is selected and drawn:
as a curve against time or against a coordinate, as a picture of a 2D array, as a
table of panels, as a stack of curves; and the selection, the plot and the whole
screen can be written to a file and put back later. The application is scripted
from Python as much as it is driven from the screen, and it is extended by
plugins.

.. list-table::
   :header-rows: 0
   :widths: auto

   * - :doc:`intro/index`
     - What the tool is for, the terms it uses, and what changed in each release.
   * - :doc:`manual/index`
     - How to work with it: opening a case, the tree, selecting, plotting,
       configuring, exporting, preferences.
   * - :doc:`howto/index`
     - Short guided recipes, including how to write a plugin of your own.

.. note::
   The manual assumes a case you can open. On an ITER cluster node that means the
   IMAS stack loaded (``module load IMAS-Python`` and the Qt stack it comes with)
   and a readable database; :doc:`manual/getting_started` starts from there.

.. tip::
   This manual reads in two looks, **light** and **dark**. The control at the top
   of the navigation column switches between them; the browser remembers the
   choice, and with none recorded the manual follows what the machine itself asks
   for. Building it needs nothing but Sphinx -- ``make doc`` from the repository
   root -- because the look lives in ``doc/source/_static/imasviz.css`` rather
   than in a theme that has to be installed first.

.. toctree::
   :maxdepth: 4
   :numbered:
   :caption: Contents:

   intro/index.rst
   manual/index.rst
   howto/index.rst



.. Indices and tables
.. ==================

.. * :ref:`genindex`
.. * :ref:`modindex`
.. * :ref:`search`
