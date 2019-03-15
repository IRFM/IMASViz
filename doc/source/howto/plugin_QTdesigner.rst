.. _plugins_qtdesigner:

Developing custom user interface (UI) plugins with Qt designer
==============================================================

**Qt Designer** is a tool for designing and building **Qt-based graphical user**
**interfaces**. It allows the user to design custom widgets, dialogs, main
windows etc. using on-screen forms and a user-friendly simple drag-and-drop
interface. It also provides the user with convenient ability to preview the
designs to ensure they work as intended.

In general, Qt Designer mainly offers basic QT widgets such as Push Button,
Line Edit, List Widget etc. This list of the QT Designer widgets can be extended
by writing so-called **Qt designer plugins** (do not confuse with
**IMASViz plugins**!). Normally this is done using C++ but PyQt5 also allows
you to write QT Designer plugins in Python.

Most of the time such designer plugin is used to expose a custom widget
(written in Python) to QT Designer so that it appears in Designer’s widget box
just like any other widget. It is possible to change the widget’s properties
and to connect its signals and slots.

.. note::
   For more information on QT Designer and PyQt5 based plugins and widgets
   check `this link <http://pyqt.sourceforge.net/Docs/PyQt5/designer.html>`_.

In this HOWTO section it will be described how to:
  #. How to develop a **custom PyQt5 widget**
  #. How to expose the **custom PyQt5 widget** class to **Qt designer** as a
     **Qt designer plugin**
  #. How to use the **custom PyQt5 widget** as a **Qt designer plugin** within
     the Qt Designer
  #. How to design of a custom **user interface (UI) plugin** (which includes
     the custom **Qt designer plugin**) with Qt designer
  #. How to use of the **UI plugin** in a standalone way as a
     **PyQt5 application**
  #. How to use of the **UI plugin** in **IMASViz**

As a main example to work with, the **Magnetics IDS overview Plugin**, also
referred to as **Example Plugin** (made specially for the purposes of this
HowTo manual section), will be used.

Below is a short demonstration video of **SOLPS overview Plugin**, showing an
example of the processes listed in points **3-6**. More on this plugin (as
IMASViz plugin) can be found in section :ref:`IMASViz_plugins`.

.. only:: html

   .. raw:: html

      <video controls width="600" src="../_static/QtDesigner_and_IMASViz_plugin_short_demo.mp4"></video>


.. only:: latex

   .. TODO: requires the .mp4 file to be in the same directory as the .pdf file

   `Local Video Link <QtDesigner_and_IMASViz_plugin_short_demo.mp4>`_.

Developing custom PyQt5 widget
------------------------------

This section described and demonstrates how to write a complete custom PyQt5
widget dealing with the data stored within the **Magnetics IDS**. The same
widget will be then used to create **Magnetics IDS overview Plugin** using Qt
designer.

The final code can be already
observed and compared here: :ref:`exampleWidget_code`.

.. Note::
   It is recommended to have the finished code opened on the side while going
   through this tutorial for better overall understanding of this section.

.. Note::
   It is recommended to have at least some basic knowledge from programming
   (specially with Python programming language) before proceeding with the widget
   development instructions. A complete beginner might find those instructions
   a bit overwhelming.

This section is split into the next subsections:

  #. Code header
  #. Import statements
  #. Widget Class definition
      #. Widget Constructor definition
      #. Widget base "set" and "get" routines
      #. Widget custom routines
  #. PlotCanvas Class definition
      #. PlotCanvas Constructor definition
      #. PlotCanvas custom plotting routines
  #. Running the code as the main program (standalone)

Code header
^^^^^^^^^^^

Every code should contain a documentation. It either explains what the code
does, how it operates, how to use it etc. Documentation is an important part
of software engineering.

Documentation should be as important to a developer as all other facets of
development. No matter what the code contains, chances are that someday other
users will try to understand and use it. Even code authors don't remember
everything they've done after just few weeks after the last time they worked on
the code in question.

Taking that extra time to write a proper description on the contents of the
code will save huge amounts of time and effort for everybody to understand the
code.

In the case of the custom PyQt5 widget, the header should consist of:
- the .py file name,
- short description what the script is used for,
- author name and
- authors contact (e-mail is most convenient).

.. literalinclude:: ../../../imasviz/VizPlugins/viz_example/exampleWidget.py
   :language: python
   :lineno-start: 1
   :lines: 1-16
   :linenos:

Import statements
^^^^^^^^^^^^^^^^^

The custom PyQt5 widget requires additional sources - modules.

The ones required are:

Common system and OS modules:

.. literalinclude:: ../../../imasviz/VizPlugins/viz_example/exampleWidget.py
   :language: python
   :lineno-start: 18
   :lines: 18-21
   :linenos:

PyQt5 modules:

.. literalinclude:: ../../../imasviz/VizPlugins/viz_example/exampleWidget.py
   :language: python
   :lineno-start: 22
   :lines: 22-24
   :linenos:

Matplotlib modules and setting matplotlib to use the Qt rendering:

.. literalinclude:: ../../../imasviz/VizPlugins/viz_example/exampleWidget.py
   :language: python
   :lineno-start: 25
   :lines: 25-30
   :linenos:
   :emphasize-lines: 3

IMAS modules:

.. literalinclude:: ../../../imasviz/VizPlugins/viz_example/exampleWidget.py
   :language: python
   :lineno-start: 31
   :lines: 31-32
   :linenos:


Widget
^^^^^^

Class definition
""""""""""""""""

Constructor definition
""""""""""""""""""""""

Base "set" and "get" routines
"""""""""""""""""""""""""""""

Custom routines
"""""""""""""""

PlotCanvas
^^^^^^^^^^

Class definition
""""""""""""""""

Constructor definition
""""""""""""""""""""""

Custom plotting routines
""""""""""""""""""""""""

Running the code as the main program (standalone)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. _exampleWidget_code:

Final code of the example PyQt5 widget
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. literalinclude:: ../../../imasviz/VizPlugins/viz_example/exampleWidget.py
   :language: python
   :linenos:




Exposing custom PyQt5 widget to Qt designer
-------------------------------------------


Use of custom PyQt5 widget in Qt designer
-----------------------------------------


Designing custom user interface - plugin creation
-------------------------------------------------


Adding plugin to IMASViz
------------------------




.. image sources (to be used)

.. images/QtDesigner_EmptyMainWindow.png
.. images/QtDesigner_SOLPSwidget_drag.png
.. images/QtDesigner_SOLPSwidget_drop.png
.. images/QtDesigner_SOLPSwidget_objectNameChange_before.png
.. images/QtDesigner_SOLPSwidget_objectNameChange_after.png
.. images/QtDesigner_MainWindow_windowTitleChange_before.png
.. images/QtDesigner_MainWindow_windowTitleChange_after.png
.. images/QtDesigner_widgetBox.png
.. images/QtDesigner_PushButton_drag.png
.. images/QtDesigner_add_3x_PushButton.png
.. images/QtDesigner_PushButton_textEdit_before.png
.. images/QtDesigner_PushButton_textEdit_after.png
.. images/QtDesigner_PushButton_textEdit_finished.png
.. images/QtDesigner_setToGridLayout_menu.png
.. images/QtDesigner_setToGridLayout_finished.png
.. images/QtDesigner_editSignalsSlots_menu.png
.. images/QtDesigner_editSignalsSlots_redColorIndicator.png
.. images/QtDesigner_editSignalsSlots_SetIDS_drag.png
.. images/QtDesigner_editSignalsSlots_SetIDS_conf.png
.. images/QtDesigner_editSignalsSlots_SetIDS_finished.png
.. images/QtDesigner_editSignalsSlots_SetGGDData_conf.png
.. images/QtDesigner_editSignalsSlots_PlotData_conf.png
.. images/QtDesigner_editSignalsSlots_all_finished.png
.. images/QtDesigner_preview_menu.png
.. images/QtDesigner_preview_run.png
.. images/QtDesigner_preview_run_IDSvariables.png
.. images/QtDesigner_preview_run_SpecifyDataToPlot_default.png
.. images/QtDesigner_preview_run_SpecifyDataToPlot_listOfQuantities.png
.. images/QtDesigner_preview_run_PlotData.png
.. images/QtDesigner_saveAs_menu.png
.. images/QtDesigner_saveAs_set.png







