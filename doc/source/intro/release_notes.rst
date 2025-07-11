.. _IMASViz_release_notes:

.. My notes:
.. use >>> git log --oneline -b master
.. git log $from_commit..$to_commit --pretty=oneline | wc -l
.. git diff --stat $from_commit $to_commit -- . ':!*enerated*' ':!*.xml'

.. from_commit = d25c4b8bddf
.. to_commit = d9253fedf12d63761299a61c6930bc77f0d9b90c

=============
Release notes
=============

-------------
Version 2.8.0
-------------
Released 12/15/2023

- IMAS-4887: Update AL API usage in VIZ (fix)
- IMAS-4996: equilibrium.time_slice[i].time not written out (fix)
- IMAS-5025: Allow viz install without access to submodules (ETS-VIZ) (fix)
- IMAS-4974: Incorrect plotting of wall thickness (feature)


-------------
Version 2.7.2
-------------
Released 08/31/2023

- IMAS-4838: Plugin feature broken in version 2.7.1
- Improving the Profiles plugin to work on any IDS occurrence

-------------
Version 2.7.1
-------------
Released 07/25/2023

- IMAS-4655: data availability (missing time slices)
- IMAS-4808: handling max handled occurrences
- Fixing non reported bugs

-------------
Version 2.7.0
-------------
Released 07/20/2023

- IMAS-4325 : Refactor Viz to use PySide6 rather than PyQt5
- IMAS-4470: fix
- Replacing map by a stack in code generator

-------------
Version 2.6.1
-------------
Released 11/29/2022

- IMAS-4405: fixing issues of the new profiles plugin and improvements
- Fixing regressions on StackedPlots and TablePlots

-------------
Version 2.6.0
-------------
Released 11/15/2022

- IMAS-4394: fix
- IMAS-3183: 'VizProfiles' plugin development, adding documentation
- IMAS-4380: fix
- IMAS-2696: fix
- IMAS-3823: implementation
- Fixing imports for pyQtGraph 0.13.1
- Viz documentation update
- Remove automatically generated parser files if too old
- DB Browser: asynchoneous loading of database entries
- Improvements of the time/coordinate1 display value when using slider with several plots

-------------
Version 2.5.0
-------------
Released 09.07.2022

- IMAS-4303: apply auto range automatically for the preview plot window
- IMAS-2696: option for plotting incertainty intervals
- IMAS-3845: fix
- IMAS-4142: printing requirements of the equilibrium plugins in the log window
- IMAS-3824: closing 1D outline plots when closed=1
- IMAS-4186: support of STR_1D data type	
- IMAS-4264: update shots browser for hdf5 support
- IMAS-4014: adding 'public' user in the browser
- Updating Makefile: removing useless code generation at install	
- 'ignore_ggd' user preference bug fix
- Import fixes such as QtGui->QtWidgets to work with PyQtGraph == 0.11.1 or PyQtGraph == 0.12.4 and matplotlib == 3.5.1 or matplotlib == 3.3.3

IMPORTANT NOTE:

if you are using Viz before 2.5.0, you need to clean Viz cache before to start the tool in order to see the expected change by IMAS-4186 fix:
rm -rf ~/.imasviz/VizGeneratedCode/\*.py

-------------
Version 2.4.7
-------------

Released 01.20.2021

- IMAS-3967: fixing display of popup menus
- IMAS-3115: enable plot of 1D static data

-------------
Version 2.4.5
-------------

Released 10.18.2021

- Bug fix for IMAS-3658: setting x and y ranges manually for 1D plots (workaround)   
- Displaying help for Viz (IMAS-3386)
- IMAS-3386: Option to specify user/device/shot/run on the command line    
- IMAS-3601: Warning running Viz/1.4.4 (fix)

-------------
Version 2.4.4
-------------

Released 25.03.2021

- Bug fix for IMAS-3564, IMAS-3552
- Added patch to prevent plotting 2D arrays located in dynamic AOS (a feature not yet supported)
- Added patch to warn users (at IDS loading time) that NBC management is not available for pulse files created with DD version < 3.26.0

-------------
Version 2.4.3
-------------

Released 16.12.2020

IMASViz parsers: Remove all IMAS data dictionaries from the installation. Use only parser files that are generated in ~/.imasviz/VizGeneratedCode

- IMAS database browser:
    - Fix display of cases with run number larger than 5 digits eg. 10001. Add strategy for displaying cases found in /1, /2, ..., /9 directory
    - Fix display of cases with run number larger than 5 digits eg.10001
    - Add strategy for displaying cases found in /1, /2, ..., /9 directory

-------------
Version 2.4.2
-------------

Released 28.7.2020

- IMAS database browser:
    - Rename "IDS case browser" to "IMAS database browser"
    - Improved tooltip
    - Add try/except statement in case a non-valid .datafile name is found.

- Makefile: included "git submodule init" and "git submodule update"
  (necessary for plugins-submodules such as ETSViz)
- PlotConfigUI:

    - Improved Text Properties tab
    - Introduced Legend Properties tab
    - Fix "show/hide legend" feature
    - Enable editing plot title and axes (text size, bold, italic)
    - Improve the interface to recognize the current text styles
    - Improved margins and overall design
    - Bugfixes and improvements concerning TablePlotView and StackedPlotView
    - Improve the strategy of accessing the correct target plot when
      opening the **Configure Plot** menu

-------------
Version 2.4.1
-------------

Released 18.5.2020

- Fix bug when .imasviz/VizgeneratedCode directory is missing
  (for generation of parser files) (IMAS-3113)
- Add new widget - IDS case browser (similar to 'imasdbs' command). At startup
  shows the available IDSs (in a form of a tree view). Browsing and double
  clicking the 'run' parameter will update the IDS parameters text boxes above.
  For searching IDS cases of other users fist an existing username must be
  set in the Username textbox and confirmed (either by pressing enter key or
  by clicking anywhere else outside the text box). The available IDS cases for
  given users will be extracted and added to the IDS case browser widget.
  Note that this widget searches for IDS cases only in 'username/public/imasdb'.

-------------
Version 2.4.0
-------------

Released: 15.5.2020

- Introduced tooltips and status bar
- Support for visualization of 2D arrays
- Improved the strategy for generating parser files to use the IDSDef.xml
  files found in $IMAS_PREFIX. This offers automatic support for any IMAS
  version (including the future releases). The path for generated parser files
  was changed to $HOME/.imasviz/VizGeneratedCode
- Fixed crash when looking into transport_solver_numerics (IMAS-2934)
- Plugins:

    - Improved plugin strategy
    - Removed ETSplugin source code and Setting ETS Viz submodule
      (where the source code is now present).
    - Plugins documentation update

-------------
Version 2.3.8
-------------

Released: 18.3.2020

- Plugins documentation update
- Major GUI and feature improvements to the ETS plugin (remains work in progress):

    - Added debug options, added in-code debug checks
    - Enabled '<<', '<', '>' and '>>' buttons
    - Display actual tmin and tmax values to labels right and left from the slider
    - Display number of time slices
    - Improved handling the widgets update on time index value change
    - Improved widgets functionality (use of the 'enter' key etc.)
    - Added status bar at the bottom of the window
    - Included  the Equilibrium IDS quantities
    - Added 'Main 0-D Parameters' and 'Main 1-D Parameters' tabs (the second one
      is not yet fully finished)

- Transition from using 'device/machine' to 'database'
- Added the missing strategy for displaying contents of the static tree items
  in the Node Documentation Widget
- Added support for DD 3.27.0
- Improved exception catching
- Fixed coordinate1/time slider bug
- Fixed default strategy on StackedPlots
- Fixed progress bar when loading shots from UDA
- Fixed issue with UDA_DISABLED flag
- Fixed some parser issues

-------------
Version 2.3.7
-------------

Released: 23.1.2020

- Added strategies for plotting data
- Added support for DD3.26.0
- Fixed regressions
- Added all parser versions
- GGD can now be ignored or not according to user preferences
- Fixed bugs in xlabels of plots
- Fixed regression after refactoring
- Fixed bug on documentation display of 0D nodes
- Fixed regression for preview plots

-------------
Version 2.3.6
-------------

Released: 12.12.2019

- Code refactoring: renaming functions and other improvements
- Tofu plugin: fixed import
- Added MDI feature for windows management
- Added comments to VIZ_API
- Prevent to overlap data with different time vectors when using the time slider
- Prevent to overlap data with different coordinates when using the coord. slider
- Bugs fixes

-------------
Version 2.3.5
-------------

Released: 18.11.2019

- Fixed issue when mixing 0D and 1D data on stacked plots
- Automatically adding sliders for plots of multiple data selection
- Fixed bug which modifies user selection order
- Improved time/coordinate1 sliders labels
- Added occurrence in labels when occurrence > 0
- Fixed bug when applying selection with occurrence > 0

-------------
Version 2.3.4
-------------

Released: 15.11.2019

- Converting exception to warning when 0D data under dynamic AOS are plotted
  along a coordinate1 dimension
- Set warning message in red in the log output
- Removed old code in comments

-------------
Version 2.3.3
-------------

Released: 13.11.2019

Released on GW as RC version (08.11.2019)

- Added logic for plotting 1D and 0D data as function of time or coordinate1D
- Added support to DD3.25.0
- Fixed bugs related to overlapped plots with available slider on time or coordinate1
- Removed unwanted print command to console output
- Fixed minor issue when checking if data plots are compatibles

-------------
Version 2.3.2
-------------

Released: 29.10.2019

Changes:

- Improvement of plugins interface making plugins integration much easier
- Code refactoring
- Still improvement on nodes colours management according to their state and their types
- Check that a shot view is opened only once
- Menu added in menu bar of shots views for plots windows management
- The list of plugins can be now displayed from right-click menu (more convenient)
- Reducing font size of documentation widget to display more text
- Added log widget on the main panel - The logging mechanism is the same that shots views, uses the same logging handler (singleton)

-------------
Version 2.3.1
-------------

Released: 25.10.2019

Changes:

- Equilibrium plugin displays prints now requirements in the log
- Equilibrium plugin raises an error if requirements are not satisfied
- Fixed IMASViz menu items of shot views management when using UDA
- Check prerequisites for using UDA
- UDA: removed MAST from available remote machines
- Available UDA remote servers can now be configured from a configuration file
- User preferences available now for colors of nodes containing data and for data selection
- Fixed bug preventing time arrays to be previewed or plotted
- Code refactoring around IMAS path handling
- Update of the README file

-------------
Version 2.3.0
-------------

Released: 18.10.2019

Changes:

- IMAS-2640: Introduced IMASViz variant of Matplotlib exporter (overwrite the
  faulty pyqtgraph default Matplotlib exporter).
- Add Makefile for generating the IDSDef_Parser.py files instead of keeping them
  in the project GIT repository.
- Improved logging messages.
- IMAS-2629: Enabled creating plots for 0D signals.
- IMAS-2651: Improvement of the time required to build the tree view.
- IMAS-2641: Added display of size for 2D signals.
- IMAS-2630: Fixed wrong units.
- Plot Configuration UI improvements:

  - Overall UI improvement
  - Replaced plot line number (marked with #) with colored plot marker.

-------------
Version 2.2.5
-------------

Released: 3.9.2019

Changes:

- Add support for IMAS versions 3.24.0
- Patches for the generation of IDSDef_XMLParser.py files.
- **Documentation Widget** fix related to 'Contents' component.
- Optimization of the display of the node/signal contents in the
  **Documentation Widget**.
- Fixed bug when clicking twice on the root node resulted in a crash
- Additional checks while plotting added (disabled mixing plots of quantities
  with different units).
- Added a new command for displaying current selection as IMAS paths.
- Added time unit label for the time slider value in plots as a function of
  coordinate1.

-------------
Version 2.2.4
-------------

Released: 1.8.2019

Changes:

- Minor code improvements and fixes.

-------------
Version 2.2.3
-------------

Released: 30.7.2019

Changes:

- Improved customization of legend labels in the plot configuration UI.
- IMAS-2475: Fixed display of multi-line strings (e.g. ids_properties.comment).

-------------
Version 2.2.2
-------------

Released: 5.7.2019

Changes:

- Add support for IMAS versions 3.23.3
- Improved data handling and checks for the signal paths and occurrences.

----------------------
Versions 2.1.0 - 2.2.1
----------------------

Released: 2.7.2019

Changes:

- Add support for IMAS versions 3.22.0, 3.23.1, 3.23.2
- Improvements for the features:
  - Export IDS,
  - 1D plotting,
  - UDA,
  - plot legend labels (in case when using UDA)
- Introduce development of standalone UI plugins (using QtDesigner) in a way
  that they can be also embedded within IMASViz (HowTo documentation included)
- Addition of SOLPS plugin (suitable for reading Edge Profiles IDSs written by
  SOLPS-ITER)
- Patch for handling Core Profiles IDS profiled_1d array
- Work done tickets:

  - IMAS-2387: Changed string on IMASviz display from 'IMAS database name' to
    'TOKAMAK'.
  - IMAS-2404: Highlight/Enable only populated IDSs in the IMAS tree.

-------------
Version 2.0.0
-------------

Released: 4.2.2019

Changes:

- **Full GUI migration from wxPython and wxmPlot to PyQt and pyqtgraph Python**
  **libraries** (including Equilibrium overview plugin)
- Basic plot feature performance improved greatly.
  Quick comparison for plotting 17 plots to a single panel using default
  plotting options:
  - wxPython IMASViz: ~13s
  - PyQt5 IMASViz:  less than 1s (more than **13x speed improvement**!)
- Improved tree view build performance (wxPython IMASViz was practically
  unable to build tree view for arrays containing 1500+ time slices)
- Superior plot export possibilities
- GUI improvements
- Database tree browser interface display improvements
- Added first 'node contents display' feature (displayed in the
  :guilabel:`Node Documentation` Widget)
- Reduced the number of separate windows, introduce docked widgets
- Introduce first GUI icons
- MultiPlot feature relabeled to TablePlotView
- SubPlot feature relabeled to StackedPlotView
- Add support for IMAS versions 3.19.0, 3.20.0, 3.21.0 and 3.21.1
- Included **documentation + manual** (~60 pages in PDF) in a form of
  reStructuredText source files for document generation (single source can be
  generated into multiple formats e.g. PDF, HMTL...)
- In-code documentation greatly improved and extended
- and more...

Short summary of files and line changes count (ignoring generated files and
scripts):

- 193 commits,
- 268 files changed,
- 13316 insertions(+),
- 10162 deletions(-)

.. Note::
   The migration to PyQt5 due to IMASViz containing a large code sets is not
   yet fully complete.
   List of known features yet to migrate to IMASViz 2.0:
   ``Add selected nodes to existing TablePlotView``, and
   ``StackedPlotView manager``.

A quick GUI comparison between the **previous** and the **new** IMASViz GUI is
shown below.

Overview of IMASViz 1.2 GUI:

.. image:: images/GUI_overview_old.png
   :align: center
   :width: 550px

Overview of IMASViz 2.0 GUI:

.. image:: images/GUI_overview_2.0.png
   :align: center
   :width: 550px

-----------
Version 1.2
-----------

Released: 24.8.2018

Changes:

- New functionality: selection command of nodes belonging to same parent AOS
  (Array of Structures)
- MultiPlot and SubPlot design improvements
- Added support for IMAS versions 3.19.0

-----------
Version 1.1
-----------

Released: 8.6.2018

Changes (since March 2017):

- Bugs fixes & performance improvement
- Code migration to Python3
- GUI improvements
- UDA support for visualizing remote shots data
- Reuse of plots layout (multiplots customization can be saved as a script file
  to be applied for any shot)
- A first plugins mechanism has been developed which allows developers to
  integrate their plugins to IMASViz
- The 'Equilibrium overview plugin' developed by Morales Jorge has been
  integrated into IMASViz
- Concerning UDA, WEST shots can be accessed if a SSH tunnel can be established
  to the remote WEST UDA server.
- Introducing MultiPlot and SubPlot features
- Add support for IMAS version 3.18.0


.. - From our first tests, SSH tunnel cannot be established from the Gateway. The issue will be analyzed during this Code Camp.
