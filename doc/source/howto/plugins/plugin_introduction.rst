..
   Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
   and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
   CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
   The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

.. _plugin_introduction:

IMASViz and plugins
===================

IMASViz comes with many features bundled in: database reader and browser,
preview plot feature, multiple different plotting utilities for 0D and 1D data,
adding data to existing plots, different plot views, managing the opened
databases, figures etc. IMASViz allows to add a new functionality through
plugins (Python3).

Plugins can be used to extend IMASViz in several ways:

 - Add a new advanced data visualization utilities for specific IDS or group of
   IDSs, or specific array(s) selection
 - Add a customized user interface (UI) for specifying the necessary parameters
   or for performing various customized actions
 - Add utilities for managing the data, checking the database contents
 - And more…

This section is intended for developers and it will cover the basics on how to
create plugins for IMASViz.

Currently the development and use of non-official plugins is
available only when using **IMASViz from cloned GIT repository** (see section
:ref:`running_from_source`).

The source files of all plugins can be found in ``$VIZ_HOME/imasviz/VizPlugins``.
