# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""What a plugin is, and which ones IMASViz ships.

The contract is **declarative**. A plugin class states, at the top of its body,
two things and none other are asked of it:

* **where it is offered** -- ``SCOPE``, one of the four scopes ``IDS``,
  ``NODE``, ``CASE`` or ``APP``; for ``IDS`` it may name which IDS, for ``NODE``
  a predicate over the node; and
* **what it can do** -- ``ACTIONS``, a tuple of :class:`QVizPluginAction`, each
  with a stable key, the words the menu says, and the call that does the work.

The framework reads those two attributes, offers the plugin at that place and
nowhere else, and -- a line clicked -- calls the action with a
:class:`QVizPluginContext` that already holds the api, the case, the node it was
offered on, the occurrence to draw, and -- when a saved session is replaying --
the answers the session already gave. A plugin no longer tests
``self.selectedTreeNode`` to work out where it applies, and it no longer
dispatches on an opaque number: where it applies is declared where it sits, and
each action owns the work of its own line.

What the old contract made the plugin write -- ``isEnabled``, ``getEntries``,
``getAllEntries``, ``getPluginsConfiguration`` and ``execute`` -- is gone.
``isEnabled`` became "a ``SCOPE`` is declared at all"; the split of
``getEntries`` + ``getAllEntries`` + ``execute(number)`` became the ``ACTIONS``
tuple; and the two that nobody read -- ``getPluginsConfiguration`` and
``getDescription`` -- are said as words on an action instead of returned by a
method.

Also kept here: :class:`QVizPluginWindow`, the record a plugin stamps on the
frame it draws so a session can put that window back;
:class:`QVizPluginAnswers`, what a session hands back in the user's place; and
``RegisteredPlugins``, the table of the plugins IMASViz itself ships.
"""

from collections import namedtuple

# The four places a plugin may be offered. A plugin class names exactly one of
# them in its ``SCOPE``: where it applies is declared, and the framework reads
# that instead of asking a method which node to gate on.
IDS, NODE, CASE, APP, FIGURE = 'ids', 'node', 'case', 'app', 'figure'
SCOPES = (IDS, NODE, CASE, APP, FIGURE)


class QVizPluginScope:
    """Where one plugin is offered -- and which of them.

    ``kind`` is one of the four scopes. For ``IDS``, ``ids`` names the IDS roots
    it applies to; an empty set means **any** IDS root. For ``NODE``, ``where``,
    when given, is a ``callable(node)`` saying whether that quantity node is one
    the plugin handles; ``None`` means any. ``CASE`` and ``APP`` take no filter
    -- the answer of a case, or of the whole application, is not something to
    match, so passing one is refused.
    """

    def __init__(self, kind, ids=(), where=None):
        if kind not in SCOPES:
            raise ValueError('%r is not a scope -- one of %s'
                             % (kind, ', '.join(SCOPES)))
        if kind in (CASE, APP, FIGURE):
            if ids or where is not None:
                raise ValueError(
                    'a %s scope has nothing to match: drop the names/predicate'
                    % kind)
        self.kind = kind
        self.ids = frozenset(ids)
        self.where = where

    def __repr__(self):
        if self.kind == IDS:
            which = 'any IDS' if not self.ids else 'IDS %s' \
                    % ', '.join(sorted(self.ids))
            return '<scope IDS on %s>' % which
        if self.kind == NODE and self.where is not None:
            return '<scope NODE where %s>' % getattr(self.where, '__name__',
                                                     self.where)
        return '<scope %s>' % (self.kind.upper(),)

    def appliesToNode(self, node):
        """Whether this scope takes part at that node's gesture.

        ``IDS`` is only an IDS root -- a quantity has no IDS to name -- and, when
        names are declared, only one of them. ``NODE`` is only a quantity, and,
        when a predicate is declared, only one it passes. ``CASE`` and ``APP``
        never take part on a node.
        """
        if self.kind == IDS:
            if not node.isIDSRoot():
                return False
            return (not self.ids) or (node.getIDSName() in self.ids)
        if self.kind == NODE:
            if node.isIDSRoot():
                return False
            return self.where is None or bool(self.where(node))
        return False

    def appliesToCase(self):
        """Whether this scope takes part on a case's own menu bar."""
        return self.kind == CASE

    def appliesToApp(self):
        """Whether this scope takes part on the application's own menu bar."""
        return self.kind == APP

    def appliesToFigure(self, frame):
        """Whether this scope takes part on a figure's own menu box.

        A frame is not asked which IDS or which node to gate on -- every
        figure of curves is a candidate, the plugin says so by declaring it.
        The `frame` argument is there so callers can pass it and be read
        correctly; no filtering over the frame is done here.
        """
        return self.kind == FIGURE


class QVizPluginAction:
    """One thing a plugin can do, and the line it earns on a menu.

    ``key`` is a stable identifier the plugin picks and the menu, the session
    and the agent all key it by; ``label`` is what the line says;
    ``description`` is the line's tooltip (defaulting to the label); ``run`` is
    the callable that does the work, handed the :class:`QVizPluginContext`.

    A window a plugin draws is stamped with its ``key`` for the session, the way
    ``QVizPluginWindow.entry`` always was.
    """

    def __init__(self, key, label, run=None, description=None):
        self.key = key
        self.label = label
        self.run = run
        self.description = description or label

    def __repr__(self):
        return '<action %s "%s">' % (self.key, self.label)

    def __eq__(self, other):
        return isinstance(other, QVizPluginAction) and self.key == other.key \
            and self.label == other.label

    def __hash__(self):
        return hash((self.key, self.label))


class QVizPluginContext:
    """What a plugin can read while it runs, from the place it was offered from.

    ``api`` is always the session's own. ``view``, when the plugin was offered
    from a case, is that shot view; ``node``, from a node's gesture, that node.
    ``scope`` names the place -- so ``run`` can tell a node-run from a case-run
    from an app-run. ``occurrence`` is the one to draw -- from a session replay
    it is the one the file named, from the menu the first the case holds -- and
    ``answers`` is the full ``QVizPluginAnswers`` a session gave in the user's
    place, ``None`` from the menu.

    A plugin offered on an IDS or a quantity reads its case and node from here
    rather than reaching them off ``self``; a plugin offered on the case or the
    application finds ``view`` / ``node`` are ``None`` and ``api`` the one it is
    meant to work with.
    """

    def __init__(self, api=None, view=None, node=None, scope=CASE,
                 occurrence=0, answers=None, figure=None):
        self.api = api
        self.view = view
        self.node = node
        self.scope = scope
        self.occurrence = occurrence
        self.answers = answers
        # When the plugin ran from a figure's own menu box, the frame it was
        # offered on. A FIGURE-scoped action reaches the frame's domain objects
        # (eventMarks, spectrumMenu) through this attribute rather than through
        # `self` -- the frame is the argument the menu handed over.
        self.figure = figure

    @property
    def uri(self):
        """The case this ran on, or ``None`` when it ran on the application."""
        return self.view.uri if self.view is not None else None

    @property
    def idsName(self):
        """The IDS this node sits under, read off the node when there is one.

        A plugin offered on a case without a node under the cursor cannot know a
        single IDS, so the answer is ``None`` rather than a guess.
        """
        if self.node is not None:
            return self.node.getIDSName()
        return None


# What a plugin says about the window it registered, so a session can put that
# window back. Measured on the reference case, neither registered window answers
# where it came from: the Profiles panel has no `figureKey` and no `key`
# attribute, and the Equilibrium chart has neither either -- only the api's
# `figureframes` bookkeeping knows the key, and only the plugin knew the entry
# number and the occurrence its own dialog had answered. So the plugin stamps
# this record on the frame it registers, and the session writes it. `time` is
# the instant one entry answered -- `equilibriumsurfaces` entry 1 asks which
# time to draw, and a restore must put back that instant rather than ask again;
# it is `None` for an entry that asks no time.
QVizPluginWindow = namedtuple('QVizPluginWindow',
                              'uri plugin entry ids occurrence time',
                              defaults=(None,))

# The answers a session hands back to a plugin entry it is replaying, so the
# entry draws the window without asking the user a second time. The Profiles
# plugin asked which occurrence to plot through a modal `QInputDialog`: measured,
# a probe left to answer that dialog sat in `askForOccurrence` for 240 s until a
# watchdog killed it, which is why a restore cannot go through the question.
# `figureKey` is here for the same reason the plot commands take one: the key is
# the identity the *Windows* menu and its *Delete* sub-menu address the window
# by. `time` is the instant an entry answered -- a session replaying
# `equilibriumsurfaces` entry 1 hands it the number the file held instead of
# opening the dialog a second time; it is `None` when the entry asks no time.
QVizPluginAnswers = namedtuple('QVizPluginAnswers',
                               'occurrence figureKey time',
                               defaults=(None,))


RegisteredPlugins = {'equilibriumcharts': 'viz_equi.equilibriumcharts',
                     'equilibriumsurfaces': 'viz_equi.equilibriumsurfaces',
                     # 'ToFuPlugin': 'viz_tofu.viz_tofu_plugin',
                     # 'viz_example_plugin': 'viz_example_plugin.viz_example_plugin',
                     # 'viz_spectrometer_plugin': 'viz_spectrometer.viz_spectrometer_plugin',
                     'VizProfiles_plugin': 'viz_Profiles.VizProfiles_plugin',
                     'VizEventDetection': 'viz_event_detection.VizEventDetection',
                     'VizSpectral': 'viz_spectral.VizSpectral',
                     'VizDerivedQuantities': 'viz_derived_quantities.VizDerivedQuantities',
                     'VizCampaignTrend': 'viz_campaign_trend.VizCampaignTrend',
                     # 'simplePlotPluginExample': 'viz_simple_plot_example.simplePlotPluginExample',
                     # 'ETSpluginIMASViz': 'viz_ETS.ETSpluginIMASViz',
                     # A plugin drawn in Qt Designer registers the window it is
                     # drawn from instead of a module path. Kept as the shape,
                     # not as an offer: this one is refused at the menu, because
                     # the .ui is drawn around an exampleWidget class this Qt
                     # cannot build -- see QVizPluginCatalog.
                     # 'example_UiPlugin': {'UiFile': 'examplePlugin.ui',
                     #                      'dir': os.environ['VIZ_HOME'] +
                     #                             '/imasviz/VizPlugins/viz_example/',
                     #                      'targetIDSroot': 'magnetics',
                     #                      'targetOccurrence': 0},
                     }


def getRegisteredPlugins():
    """The plugins this application ships, name to where they come from.

    A name mapped to a dotted path is a Python plugin under `imasviz.VizPlugins`,
    its class named after the key. A name mapped to a dictionary is a window
    drawn in Qt Designer, described by `UiFile`, `dir`, `targetIDSroot` and
    `targetOccurrence`.

    This is the table of what IMASViz *ships*, and nothing else. What a user wrote
    is not added here: it lives in a folder of their own and is found by looking,
    which is what makes a plugin created in the middle of a session show up
    without anyone editing a file of the package -- see `QVizPluginSource`. A
    previous `registerPlugin` did the opposite, writing into this table at run
    time, and that cannot work twice over: a catalog is built once per shot view,
    so a plugin injected after the first right click would sit on that view's menu
    for ever and on no other view's at all -- and it would make a shipped name look
    editable, when nothing in this table is.
    """
    return RegisteredPlugins


class VizPlugin:
    """What a plugin is, declared.

    Name a ``SCOPE`` and list your ``ACTIONS``. The default -- neither present
    -- is **no line**: a plugin that declares neither is not offered, and it is
    named in the log of the case it would have sat in, like a plugin that used
    not to honour the contract was. A plugin that names a scope offers, by
    default, every action it lists; override :meth:`offered` to offer a subset
    of them for one place and not another.

    The work of a line is the ``run`` of the action it names: it is handed the
    :class:`QVizPluginContext` and says what it did through the case's log --
    ``logging.getLogger(context.uri)`` -- or, when it ran on the application and
    nothing to log about, by raising a ``ValueError`` with the reason in words,
    which the catalog puts in the log of the case.
    """

    SCOPE = None
    ACTIONS = ()
    # The sub-menu title a FIGURE-scoped plugin earns on a frame's view-box menu.
    # When None the registered name is used; a plugin with a French-facing menu
    # sets this to the words the user reads (e.g. 'Événements').
    LABEL = None

    def offered(self, context):
        """Which of your ACTIONS apply in this context. Default: all of them.

        The framework offers this many lines, in that order. Override it to offer
        a subset (a feature that does not apply here) or to refuse -- raise a
        ``ValueError`` and the framework says so in the log of the case and
        drops the line, rather than show one that only does nothing.
        """
        return list(self.ACTIONS)
