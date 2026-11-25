..
   Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
   and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
   CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
   The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

.. _plugin_simple_plot_example:

Developing a simple plugin for plotting data from IDSs
======================================================

.. note::
    Before proceeding with the plugin development instructions make sure that
    you have **cloned IMASViz GIT repository** (for more information see section
    :ref:`running_from_source`)!

This section will cover step by step instructions on how to:

 - write a very simple introductory plugin example (~80 lines of code),
 - how to register the plugin in IMASViz, and
 - how to run the plugin in IMASViz.

This simple plugin can be considered also as a starting template for more
complex plugins with advanced design and functionalities.

The main basic steps which will be covered in this tutorial are as follows:

1. Adding IMASViz home directory to :envvar:`$PYTHONPATH`
2. Setting plugin source structure
3. Writing the code:

   a) Import statements
   b) Class (prescribed name)
   c) Class inheritance
   d) Mandatory method functions

4. Registering plugin in IMASViz

.. note::
    Complete code of the simple plugin (named as **simplePlotPluginExample**) is
    available in IMASViz code source in
    :file:`$VIZ_HOME/imasviz/VizPlugins/viz_simple_plot_example`.

Adding IMASViz sources to $PYTHONPATH
-------------------------------------

In order to have IMASViz sources at our disposal the ``$VIZ_HOME`` must be added
to :envvar:`$PYTHONPATH` environment variable. This can be achieved by running
the next command in the terminal:

.. code-block::

    # bash
    export PYTHONPATH=${VIZ_HOME}:${PYTHONPATH}
    # tcsh
    setenv PYTHONPATH ${VIZ_HOME}:${PYTHONPATH}

.. _plugin_simple_plot_example_setting_dir:

Setting plugin source structure
-------------------------------

A plugin you develop inside the IMASViz sources lives in a directory of its own
under :file:`$VIZ_HOME/imasviz/VizPlugins/<folder_name>`; the name of the
directory should start with "**viz_**".

For the purposes of this tutorial create a new directory with label
**viz_my_example** to distinguish it from other plugins. The full path is then
:file:`$VIZ_HOME/imasviz/VizPlugins/viz_my_plugin`.

Inside the newly created directory create a new Python script file. In this case
name it as :file:`myPlugin.py`. The script can be left empty for now.

.. note::
   A plugin of your own does **not** have to live in the IMASViz sources, and is
   then not registered at all: anything under
   :file:`$HOME/.imasviz/plugins/<folder_name>/<ClassName>.py` is found by
   looking, offered on the next right click, and editable in IMASViz itself --
   see :ref:`your_own_plugins`. The layout asked there is the one this tutorial
   teaches: a folder, a module, and a class bearing that module's name.

Python code
-----------

This subsection will cover the contents of the plugin main Python script file
:file:`$VIZ_HOME/imasviz/VizPlugins/viz_my_plugin/myPlugin.py` (previously
created in :ref:`plugin_simple_plot_example_setting_dir`).

Required import statements
^^^^^^^^^^^^^^^^^^^^^^^^^^

As the first entry in the Python script, the next modules need to be imported
with the use of the import statements.

In your :file:`myPlugin.py` file add:

.. code-block:: python

    # modules for event logging system and for operating system dependent
    # functionality
    import logging, os
    # IMASViz plugin sources
    from imasviz.VizPlugins.VizPlugin import VizPlugin
    # Matplotlib library
    import matplotlib.pyplot as plt

Prescribed class name
^^^^^^^^^^^^^^^^^^^^^

The plugins main Python file must contain a class with the same name as the
name of the Python file. In this case, a class **myPlugin**.

In your :file:`myPlugin.py` file add:

.. code-block:: python

    class myPlugin():

Inheritance
^^^^^^^^^^^

The class must inherit from **VizPlugin class** from the :file:`VizPlugin.py`.
This is required for IMASViz to be able to gather necessary information
required for properly running the plugin.

In your :file:`myPlugin.py` file add:

.. code-block:: python

    class myPlugin(VizPlugin):

The declarative contract
^^^^^^^^^^^^^^^^^^^^^^^^

A plugin class declares **two** things -- and nothing else is asked of it:

* **where it is offered** -- ``SCOPE``, one of five places: ``IDS`` (the root
  of one or more IDS roots in the tree), ``NODE`` (a quantity under the cursor),
  ``CASE`` (the case's own menu bar), ``APP`` (the application's menu bar), or
  ``FIGURE`` (the right-click menu box of a window of curves).
  For ``IDS`` it may name which IDS roots it applies to; an empty set means any.
  For ``NODE`` it may provide a predicate ``callable(node)`` to filter which
  quantities it handles. ``CASE``, ``APP`` and ``FIGURE`` take nothing to match:
  the answer of a case, of the whole application, or of a window of curves is
  not something to filter, and passing a name or a predicate there is refused.

* **what it can do** -- ``ACTIONS``, a tuple of ``QVizPluginAction`` objects.
  Each action has a stable integer ``key``, the ``label`` shown in the menu (and
  used as a tooltip if ``description`` is not set), and the ``run`` callable
  -- the method that does the work, handed a ``QVizPluginContext``.

The framework reads ``SCOPE`` and ``ACTIONS``, offers the plugin at that place,
and calls the action's ``run`` method with the context. The old methods
(``isEnabled``, ``getEntries``, ``getAllEntries``, ``getPluginsConfiguration``,
``execute``) are gone.

import statements
"""""""""""""""""

In your :file:`myPlugin.py` file add:

.. code-block:: python

    import logging
    from imasviz.VizPlugins.VizPlugin import (IDS, QVizPluginAction,
                                              QVizPluginScope, VizPlugin)

Constructor
"""""""""""

Set ``SCOPE`` and ``ACTIONS`` in the constructor.

**Where it applies** -- ``SCOPE``:

.. code-block:: python

    # This plugin answers the magnetics IDS root only:
    self.SCOPE = QVizPluginScope(IDS, ids=('magnetics',))

    # Or, if it answers any IDS root:
    # self.SCOPE = QVizPluginScope(IDS)

    # Or on the right-click menu box of a window of curves. A FIGURE plugin
    # also says what its sub-menu is titled -- LABEL, because the registered
    # class name is not what a user should read:
    # self.SCOPE = QVizPluginScope(FIGURE)
    # self.LABEL = 'Mon outillage'

**What it offers** -- ``ACTIONS``:

.. code-block:: python

    self.ACTIONS = (
        QVizPluginAction(0, 'My plot of magnetics...',
                         run=self._run,
                         description='Draws bpol_probe curves on the magnetics IDS'),
    )

In your :file:`myPlugin.py` file add:

.. code-block:: python

    def __init__(self):
        self.SCOPE = QVizPluginScope(IDS, ids=('magnetics',))
        self.ACTIONS = (
            QVizPluginAction(0, 'My plot of magnetics...',
                             run=self._run,
                             description='Draws bpol_probe curves on the magnetics IDS'),
        )

The ``run`` callable
""""""""""""""""""""

The ``run`` callable is handed a ``QVizPluginContext`` and does the work.
The context already carries the api, the shot view (``context.view``), the node
the menu was built on (``context.node``), and -- when a saved session is replaying
the entry -- ``context.answers`` (a ``QVizPluginAnswers``).

.. note::
   Say what the plugin did through ``logging.getLogger(context.uri)``, not
   ``print``: the log panel of a case shows what is logged under that case's URI,
   and nothing else. Raise a ``ValueError`` to refuse an entry; the framework
   catches it and puts the reason in the log of the case.

**Example -- plotting magnetics.bpol_probe curves:**

.. code-block:: python

    def _run(self, context):
        """Draw one quantity of this IDS, in a figure of IMASViz's own."""
        import matplotlib.pyplot as plt

        uri = context.view.uri
        api = context.api
        view = context.view
        node = context.node

        logging.getLogger(uri).info('Running my plugin on %s...', uri)

        # Load the magnetics occurrence if not yet in memory
        occurrence = 0
        if not api.IDSDataAlreadyFetched(view, 'magnetics', occurrence):
            logging.getLogger(uri).info('Loading magnetics IDS...')
            api.LoadIDSData(view, 'magnetics', occurrence)
        ids = view.dataSource.get('magnetics', occurrence)

        # Read and plot the data
        time_values = ids.magnetics.time
        num_bpol = len(ids.magnetics.bpol_probe)
        fig, ax = plt.subplots()
        for i in range(num_bpol):
            ax.plot(time_values, ids.magnetics.bpol_probe[i].field.data,
                    '-', label='bpol_probe[%d]' % i)
        ax.set(xlabel='time [s]', ylabel='Field', title='Poloidal field probes')
        ax.legend()
        ax.grid()
        plt.show()

.. note::
   ``context.answers`` is ``None`` when the entry was chosen from the menu --
   the user is there to answer anything. It is a ``QVizPluginAnswers`` when
   someone answers **in the user's place**: a saved session being replayed (see
   :ref:`save_load_session`), or a tool call of :ref:`agentics`. It carries the
   ``occurrence``, the ``figureKey`` and the ``time`` the caller named. Read it
   to honour that choice instead of asking a second time -- and refuse by name
   when an answer you need is missing, because a dialog opened where nobody is
   there to answer it stops the session.

.. _plugin_answers_and_sessions:

What your action receives, and what a session replay hands back
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

Your ``run`` callback receives exactly one argument: a ``QVizPluginContext``.
It tells the plugin where it was offered and who is calling: ``context.view``
is the shot view (or ``None`` for ``APP``- or ``FIGURE``-scope plugins),
``context.node`` is the node the gesture was made on (or ``None`` for ``CASE``,
``APP`` or ``FIGURE`` scope), ``context.figure`` is the frame whose menu box the
line was clicked on (``None`` everywhere else), and ``context.scope`` is one of
``IDS``, ``NODE``, ``CASE``, ``APP`` or ``FIGURE``.
``context.api`` is always the running session's own.

.. note::
   ``run(self, context)`` is the only signature the framework calls -- there is
   no second or third argument to worry about. If your action refuses the
   window it is being asked to open, raise a ``ValueError`` with the reason in
   words. The framework keeps the menu standing and writes that reason in the
   log panel of that case, **and hands it back** to whoever asked: a session
   names the plugin and the action that could not be restored, and a tool call
   answers the refusal instead of reporting a window that was never drawn.

Under that rule the framework keeps one more guard, in case an action opens a
dialog anyway: while answers are being handed in the user's place, a modal window
is **closed as it appears**, and the entry is refused with the title of the
question nobody was asked. A dialog runs a nested event loop on the GUI thread, so
on the web surface it holds the whole session until the caller gives up --
measured, the ``equilibrium`` surfaces entry of an earlier release held one until
it answered ``The GUI thread did not answer in 300 s``, and what the model did
next reached the user as an endless loop. Chosen from the menu, the same dialog is
left exactly as it was: there, the question is asked of someone who is there to
answer it.

A window a plugin draws is put back by asking that plugin's action again, not
by rebuilding a widget. For the session to be able to ask it, the plugin says
where the window came from, by stamping the frame it registers:

.. code-block:: python

    from imasviz.VizPlugins.VizPlugin import QVizPluginWindow

    frame.pluginWindow = QVizPluginWindow(uri=uri, plugin='myPlugin',
                                          entry=0, ids='magnetics',
                                          occurrence=occurrence)

The ``entry`` is the key of the ``QVizPluginAction`` that drew the window --
here ``0``, the only action this tutorial's plugin declares. The **figure key**
(e.g. ``Plot1``) is not part of ``QVizPluginWindow``: it is the key the
window is registered under in ``Viz_API.figureframes``, which is what the
:guilabel:`Windows` menu and its :guilabel:`Delete` lines address it by. A
session replay hands it back to your action through ``context.answers.figureKey``.
An entry that **asks an instant** stamps it too --
``QVizPluginWindow(..., time=time_answer)`` -- and the replay hands it back as
``context.answers.time``, which is what keeps a restore from opening that question
a second time; the field is ``None``, and left out of the file, for an entry that
asks none.
A window that is never registered in ``figureframes`` (a plain ``matplotlib``
window, like the one this tutorial draws) is not in the session at all, and the
:guilabel:`Windows` menu does not reach it either.

That same stamp answers a second question, and the answer is what keeps a window
from being drawn twice. The agent's ``plugin(action="run")`` call asks the api
which open window
carries the stamp of the entry it is about to run (``Viz_API.openWindowOfPluginEntry``,
named for the case, the entry, the occurrence, the branch it was asked on and --
for an entry that draws one window per instant -- the instant). When it finds
one, it hands your action that window's key with ``context.answers.reuse`` set:
the ask is the same line asked again, so the window that stands is what has to
answer it -- redrawn from the inside, or put back on the screen if the user had
only hidden it. Drawing a second one leaves two windows saying the same thing,
with one gesture in the transcript. A **session replay** is not a reuse: it names
the key its file gave the window, means to build it, and gets ``reuse`` false --
so keep the strict rule that a key a live window already holds is refused.

.. code-block:: python

    def draw(self, context):
        if context.answers is not None and context.answers.reuse:
            standing = context.api.figureframes[context.answers.figureKey]
            context.api.setWindowVisible(standing, True)
            standing.raise_()
            standing.activateWindow()
            return

That is the whole answer for a window whose content does not change between two
asks -- what the shipped ``equilibriumcharts`` entry and the Profiles panel do.
An entry whose window **re-reads the case** has to take its own drawings back
before laying the new ones down, or the second read is laid under the first;
``QVizEquilibriumFigure.clearDrawings`` is the shipped example of that, and it is
called only once the reads have answered, so an entry that fails leaves the
window exactly as the user left it.

A registered window of your own should follow the same close rule as the rest of
the application. A window inside the MDI area already does: the subwindow it sits
in asks the api what its close box is worth. A top-level window -- one you show
yourself, outside the MDI area -- has to answer that for itself, by mixing in
``QVizClosableWindow`` and answering ``windowApi()`` with the api the window is
registered in::

    from imasviz.Viz_API import QVizClosableWindow

    class MyPanel(QVizClosableWindow, QMainWindow):
        def windowApi(self):
            return self.api

Without that, the close box hides the window and says nothing to anyone: it stays
in ``figureframes``, so the *Windows* menu keeps naming a window that no gesture
on screen can bring back. With it, the box hides the window by default, and closes
it for good when the user sets ``Close_button_deletes=1`` -- see
:ref:`user_preferences`.

Several features in one plugin
""""""""""""""""""""""""""""""


A plugin can offer several features. Each is a ``QVizPluginAction`` in the
``ACTIONS`` tuple. The framework offers every action as a separate line in the
:guilabel:`Plugins` menu; clicking a line calls only that action's ``run``.

.. code-block:: python

    def __init__(self):
        self.SCOPE = QVizPluginScope(IDS, ids=('magnetics',))
        self.ACTIONS = (
            QVizPluginAction(0, 'Print node info...',
                             run=self._printInfo,
                             description='Writes the magnetics node path to the log'),
            QVizPluginAction(1, 'Show 2D bpol plots...',
                             run=self._show2D),
        )

    def _printInfo(self, context):
        logging.getLogger(context.uri).info('magnetics node: %s',
                                            context.node.getParametrizedDataPath())

    def _show2D(self, context):
        # ... draw the plots here ...
        pass

.. note::
   Override :meth:`offered` to offer a subset of the actions for one place and
   not another. If an action cannot do its work in this context, raise a
   ``ValueError`` inside its ``run`` method -- the framework catches it, puts
   the reason in the log of the case, and the other actions keep working.

.. _plugin_figure_scope:

A plugin offered on a window of curves
""""""""""""""""""""""""""""""""""""""

A ``FIGURE`` plugin earns a **sub-menu** on the right-click menu box of a window
of curves -- one sub-menu per plugin, titled by its ``LABEL`` (or by its
registered name when it sets none), one line per offered action. The two the
application ships are *Événements* and *Spectre*; both are documented in
:ref:`IMASViz_plugins <IMASViz_plugins>`, and both are the shape below.

.. code-block:: python
    :caption: A FIGURE-scope plugin, in the shape the application ships
    :linenos:

    from imasviz.VizPlugins.VizPlugin import (FIGURE, QVizPluginAction,
                                              QVizPluginScope, VizPlugin)

    def _measure(context):
        frame = context.figure          # the window the line was clicked on
        if frame is None:
            return
        curve = frame.eventMarks.liveCurve()
        if curve is None:
            raise ValueError('this figure holds no curve following the sliders')
        # ... read the curve, put the answer on the frame ...

    class myFigureTool(VizPlugin):
        SCOPE = QVizPluginScope(FIGURE)
        LABEL = 'Mon outillage'
        ACTIONS = (
            QVizPluginAction(0, 'Mesurer la courbe vivante', run=_measure),
        )

The ``run`` callables come **before** the class, as they do in the shipped
bricks: ``ACTIONS`` is read when the class body runs, so a name defined after it
is not there yet.

Three things belong to this place and to no other:

- **the frame is an argument, not an attribute.** Reach the window through
  ``context.figure``; never keep it on ``self``. The line is built once when the
  frame is, so a callable closing over the frame makes a cycle (frame -> menu ->
  action -> your callable -> frame), and a Qt widget freed by the cyclic
  collector is freed on this stack while it still owes a paint event. The
  framework already holds the frame through a ``weakref`` for exactly that
  reason, and the context is rebuilt at click time.
- **the refusal goes to the window, not to the log of a case.** A ``FIGURE``
  plugin is clicked on a plot, and a case view may not be beside it: the two
  shipped bricks answer in a message box titled by the sub-menu -- a refusal in
  a warning, the count in an information line -- and the dialog is raised by the
  object that stays on the frame, which is why the plugin's ``run`` adds nothing
  to it. A ``ValueError`` out of ``run`` is still caught by the framework.
- **a figure plugin does not own the work.** The shipped ones delegate to objects
  that stay on the frame (``frame.eventMarks``, ``frame.spectrumMenu``), which
  the tools of :ref:`agentics` drive as well. Switching the plugin off therefore
  takes the **menu** away and leaves the window, its curves and everything the
  agent can still ask that window unchanged.

.. warning::
   A ``FIGURE`` plugin is built when the frame is built, not when the menu is
   opened, so a plugin edited mid-session reaches the **next** window of curves
   you open, not the one already on screen. And it is looked for in the table of
   what IMASViz **ships** (``RegisteredPlugins``) only: unlike the other four
   scopes, this one does not scan :file:`$HOME/.imasviz/plugins`, so a plugin of
   your own declaring ``FIGURE`` is offered nowhere. That is a limit of the
   mechanism, not of the contract -- see the *Plugins* window of
   :ref:`IMASViz_plugins <IMASViz_plugins>` for what a plugin of your own does
   reach.

Full Python code
^^^^^^^^^^^^^^^^

Below is the full :file:`myPlugin.py` for this tutorial:

.. code-block:: python
    :caption: myPlugin.py
    :linenos:

    import logging
    import matplotlib.pyplot as plt
    from imasviz.VizPlugins.VizPlugin import (IDS, QVizPluginAction,
                                              QVizPluginScope, VizPlugin)

    class myPlugin(VizPlugin):
        """A simple plugin that plots bpol_probe curves from the magnetics IDS."""

        IDS = 'magnetics'
        OCCURRENCE = 0

        def _run(self, context):
            """Draw one quantity of this IDS, in a figure of IMASViz's own."""
            uri = context.view.uri
            api = context.api
            view = context.view

            logging.getLogger(uri).info('Reading data of %s...', uri)

            if not api.IDSDataAlreadyFetched(view, self.IDS, self.OCCURRENCE):
                logging.getLogger(uri).info('Loading magnetics IDS...')
                api.LoadIDSData(view, self.IDS, self.OCCURRENCE)

            ids = view.dataSource.get(self.IDS, self.OCCURRENCE)

            time_values = ids.magnetics.time
            x = time_values
            num_bpol_probe_AoS = len(ids.magnetics.bpol_probe)

            fig, ax = plt.subplots()
            for i in range(num_bpol_probe_AoS):
                y = ids.magnetics.bpol_probe[i].field.data
                ax.plot(x, y, '-', label='bpol_probe[%d]' % i)
            ax.set(xlabel='time [s]', ylabel='Field [T]',
                   title='Poloidal field probe values')
            ax.legend()
            ax.grid()
            plt.show()

        def __init__(self):
            self.SCOPE = QVizPluginScope(IDS, ids=(self.IDS,))
            self.ACTIONS = (
                QVizPluginAction(0, 'Magnetics overview (simple plot plugin example)...',
                                 run=self._run,
                                 description='Draws bpol_probe curves from the magnetics IDS'),
            )

Registering plugin in IMASViz
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. note::
   This section is for a plugin developed **inside the IMASViz sources** -- the
   one case where the table below is the way in. A plugin of your own under
   :file:`$HOME/.imasviz/plugins` is found by looking and needs no registration
   at all, and is the only kind IMASViz will let you edit while it runs: see
   :ref:`your_own_plugins`.

A plugin added to the sources is registered by a single entry in the
:guilabel:`RegisteredPlugins` dictionary at the top of the
:file:`$VIZ_HOME/imasviz/VizPlugins/VizPlugin.py` file.

Add a key and the value relevant for your plugin, e.g.
:kbd:`'myPlugin' : 'viz_my_plugin.myPlugin'`.

Here the key must match the **py. file** and **class name** while the
corresponding value must match :kbd:`'<plugin_source_path>.<py_file_name>'`:
the plugin is looked up under :file:`imasviz/VizPlugins/`, and the class taken
out of that module bears the key's name. A plugin that is not registered is
never imported; a registered name whose module is gone is reported in the log
panel of the opened case under its own name, and the other plugins keep their
menu entries.

.. code-block:: python
    :emphasize-lines: 12

    RegisteredPlugins = {'equilibriumcharts': 'viz_equi.equilibriumcharts',
                         # 'ToFuPlugin': 'viz_tofu.viz_tofu_plugin',
                         # 'viz_example_plugin': 'viz_example_plugin.viz_example_plugin',
                         # 'viz_spectrometer_plugin': 'viz_spectrometer.viz_spectrometer_plugin',
                         'VizProfiles_plugin': 'viz_Profiles.VizProfiles_plugin',
                         # 'simplePlotPluginExample': 'viz_simple_plot_example.simplePlotPluginExample',
                         # 'ETSpluginIMASViz': 'viz_ETS.ETSpluginIMASViz',
                         # a plugin drawn in Qt Designer registers the window it
                         # is drawn from instead of a module path: {'UiFile':
                         # 'examplePlugin.ui', 'dir': ..., 'targetIDSroot':
                         # 'magnetics', 'targetOccurrence': 0}
                         'myPlugin' : 'viz_my_plugin.myPlugin'
                         }

Nothing else has to be written anywhere: the plugin is asked itself what it
offers, and each registered plugin is imported and built **once per opened
case** -- the first menu that needs it pays, the menus that follow do not.

.. note::
   A **.ui** plugin -- one registered as that dictionary -- is loaded with
   ``PySide6.QtUiTools.QUiLoader`` (this PySide6 has no ``uic`` module), and is
   **refused by name** when its file is drawn around a widget class of its own:
   Qt then answers *"unable to create a custom widget of the class
   'exampleWidget'; defaulting to base class 'QWidget'"* and drops the
   connections the file makes to that class, so the window that comes out is
   hollow. Draw the interface out of Qt classes only, or provide the widget as a
   Python class and register the plugin the way this page shows.

Executing the custom plugin in IMASViz
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To run the plugin in IMASViz while in IMASViz session with opened IDS database,
in :guilabel:`tree view browser`:

- on the IDS named in the plugin's ``SCOPE`` (**Magnetics IDS**) either:

  - hold shift key + right-click on the tree node. A popup menu including the
    menu action (with the label specified in the plugin's ``ACTIONS``) will be shown, or

   .. figure:: images/IMASViz_simple_plot_example_plugin_menu_1.png
     :align: center
     :scale: 90%

     Popup menu on shift + right-click on **Magnetics IDS** showing the
     available action for executing the plugin.

  - just right-click on the tree node. A popup menu including the
    :guilabel:`Plugins` selection will be shown. Hovering on this selection shows
    the menu action (with the label specified in the plugin's ``ACTIONS``).
    The same sub-menu is offered on right-click on a quantity of that IDS, and
    the plugin is asked what it offers **for the node under the cursor**, not
    for the node the view has selected.

   .. figure:: images/IMASViz_simple_plot_example_plugin_menu_2.png
     :align: center
     :scale: 80%

     Popup menu on right-click on **Magnetics IDS** showing the
     available action for executing the plugin.

  When no registered plugin has anything to offer for that node, no
  :guilabel:`Plugins` sub-menu appears at all, and shift + right-click -- which
  offers the plugins and nothing else -- writes one line in the log panel
  (`No plugin offers anything for the magnetics IDS.`) instead of opening an
  empty menu.

- click on the menu action. The plugin will be executed and the results (plot)
  will be shown in a matplotlib plot window.

   .. figure:: images/IMASViz_simple_plot_example_plugin_result.png
     :align: center
     :scale: 80%

     The result of the simple plot plugin execution: plotted poloidal field
     probe values (all available signals).
