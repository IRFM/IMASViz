# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""Where a plugin comes from, and whether this user may change it.

Two origins, and the whole point of the distinction is what may be written:

* **builtin** -- the `RegisteredPlugins` table of `VizPlugin.py`, whose code sits
  under `$VIZ_HOME/imasviz/VizPlugins/`. Offered to the user like any other, and
  never written. An installed IMASViz lives in a module tree the run does not own
  (and often cannot write), and a run that edited the code it was shipped with
  would leave the next one -- and every other user of that installation -- with
  the edit.
* **user** -- a folder of the user's own, `$HOME/.imasviz/plugins`, next to the
  preferences and the `.pcfg` files the application already owns. What is in it
  is *discovered by looking*, not registered: the layout the howto already
  documents (a folder holding a module whose class bears the module's name),
  asked at run time. So a plugin created a minute ago is on the menu at the next
  right click, and a folder copied in from outside needs no edit of any file of
  the package.

Why looking and not a manifest: a manifest is one more file that can disagree
with the code it describes, and the catalog already asks each plugin what it
offers. What the scan must not do is **import** -- importing is what costs (the
shipped set alone is where matplotlib comes in), and the plugin manager lists the
folder before anything is run. So a folder is a plugin when it holds a module
that declares a class of that module's name, read out of the *source* with `ast`.

Two things this module owns because they are disk boundaries, not menu detail:
the name a plugin may take (`checkPluginName`), and the fact that a saved source
has to parse before it replaces what is running (`compileCheck`).
"""

import ast
import keyword
import os
import re
import shutil
import sys
import types

from imasviz.VizPlugins.VizPlugin import getRegisteredPlugins

BUILTIN = 'builtin'
USER = 'user'

# The name the user's plugin folder is imported under. A synthetic package rather
# than a `sys.path` entry: `sys.path` is process-wide and this application already
# mutates it at import time, while one package name gives every plugin a stable
# import name -- which is what taking a module out again needs, and what lets a
# plugin keep its own sub-package and relative imports.
USER_PACKAGE = 'imasviz_user_plugins'


def userPluginsFolder():
    """The folder this user's own plugins live in.

    Resolved **when asked**, not at import: `HOME` is what a test points at
    `tmp_path` to get a folder of its own (`tests/test_39_configurations.py` does
    the same for the configurations), and a folder frozen at import time would be
    the real one for the rest of the process.
    """
    return os.path.join(os.environ.get('HOME', os.getcwd()), '.imasviz',
                        'plugins')


class QVizPluginSource:
    """One plugin, and where it came from.

    `registration` keeps the shape the table already uses: a dotted
    `<folder>.<module>` for a Python plugin, the `UiFile`/`dir`/`targetIDSroot`
    dictionary for one drawn in Qt Designer. What is added is the origin, and the
    two paths the editor asks for.
    """

    def __init__(self, name, registration, origin, folder=None, fileName=None):
        self.name = name
        self.registration = registration
        self.origin = origin
        self.folder = folder
        self.fileName = fileName

    def __repr__(self):
        return '<%s plugin %s (%s)>' % (self.origin, self.name,
                                        self.registration)

    @property
    def writable(self):
        """Whether IMASViz will let this user change this plugin.

        Read from the origin and nothing else, so the editor's `setReadOnly` and
        the guard that refuses to write cannot disagree with each other.
        """
        return self.origin == USER

    @property
    def isUi(self):
        return isinstance(self.registration, dict)

    @property
    def importName(self):
        """The name this plugin's module is imported under.

        A shipped plugin keeps living under `imasviz.VizPlugins`; the user's keeps
        the package name it was found under, which is what lets it be dropped and
        read again without touching anything else.
        """
        if self.isUi:
            raise ValueError('%s is a window drawn from a .ui file: there is no '
                             'module to import' % self.name)
        if self.origin == USER:
            return USER_PACKAGE + '.' + self.registration
        return 'imasviz.VizPlugins.' + self.registration

    @property
    def packagePrefix(self):
        """The import name whose whole subtree belongs to this plugin."""
        return (USER_PACKAGE + '.'
                + self.registration.rsplit('.', 1)[0])


def builtinSource(name, registration):
    """A row of the shipped table, as a plugin with an origin.

    The path is spelled from the table itself, which is how a shipped plugin can
    be *shown* to the user -- read-only -- instead of being a name on a list.
    """
    if isinstance(registration, dict):
        directory = registration.get('dir')
        uiFile = registration.get('UiFile')
        return QVizPluginSource(name, registration, BUILTIN,
                                folder=directory,
                                fileName=(directory.rstrip('/') + '/' + uiFile
                                          if directory and uiFile else None))
    package = registration.rsplit('.', 1)[0]
    module = registration.rsplit('.', 1)[-1]
    directory = os.path.join(_packageFolder(), package)
    return QVizPluginSource(name, registration, BUILTIN, folder=directory,
                            fileName=os.path.join(directory, module + '.py'))


def builtinSources():
    """Every plugin IMASViz ships, in the order the table holds them."""
    return [builtinSource(name, registration)
            for name, registration in getRegisteredPlugins().items()]


def _packageFolder():
    """`<VIZ_HOME>/imasviz/VizPlugins` -- where the shipped plugins live."""
    vizHome = os.environ.get('VIZ_HOME', os.getcwd())
    return os.path.join(vizHome, 'imasviz', 'VizPlugins')


def userSources(folder=None):
    """The plugins this user's folder holds, without importing any of them.

    A folder counts as a plugin when it holds a module that declares a class of
    that module's name -- the rule the howto documents ("<Plugin main class name>
    and <plugin_py_file> must be the same"), read off the source with `ast` so
    that listing costs nothing. A folder that holds no such module is a folder
    holding something else, and is left alone.
    """
    folder = userPluginsFolder() if folder is None else folder
    sources = []
    try:
        entryNames = sorted(os.listdir(folder))
    except OSError:
        # No folder yet is the normal state of a first run: there is nothing of
        # this user's yet, and that is not an error.
        return sources
    for entryName in entryNames:
        directory = os.path.join(folder, entryName)
        if not os.path.isdir(directory) or not entryName.isidentifier():
            continue
        for fileName in sorted(os.listdir(directory)):
            if not fileName.endswith('.py'):
                continue
            moduleName = fileName[:-3]
            if moduleName.startswith('_') or not moduleName.isidentifier():
                continue
            path = os.path.join(directory, fileName)
            if declaresClass(path, moduleName):
                sources.append(QVizPluginSource(moduleName,
                                                entryName + '.' + moduleName,
                                                USER, folder=directory,
                                                fileName=path))
    return sources


def declaresClass(path, className):
    """Whether this file declares a class of that name at module level.

    Read with `ast`, not by importing: the manager lists plugins before running
    them, and importing the shipped set is where seconds go. A file that no longer
    parses still counts: a plugin the user broke in the editor is the one they most
    need to *open*, and hiding it from the list would leave nothing to fix. The
    catalog names it when it fails to import.
    """
    try:
        with open(path, encoding='utf-8') as handle:
            tree = ast.parse(handle.read(), filename=path)
    except SyntaxError:
        return True
    except (OSError, ValueError):
        return False
    return any(node.name == className
               for node in tree.body if isinstance(node, ast.ClassDef))


def pluginNameFor(name):
    """The plugin name a phrase the user typed turns into.

    One rule, asked by whoever makes a plugin -- the creator and *copy into my
    plugins* alike -- because the name is a folder, a module and a class at once:
    two spellings of it is how a plugin ends up with a module whose class has
    another name, which is the one thing the catalog cannot read.
    """
    words = [word for word in (name or '').replace('_', ' ').split() if word]
    if not words:
        raise ValueError('a plugin needs a name, for example "my_analysis"')
    stem = ''.join(word[0].upper() + word[1:] for word in words)
    if not stem.endswith('Plugin'):
        stem += 'Plugin'
    return checkPluginName(stem)


def checkPluginName(name):
    """Refuse a plugin name IMASViz cannot use, before anything is written.

    A name is a folder, a module and a class at once, so it has to be an
    identifier that is not a keyword; and it may not be a name IMASViz already
    ships -- two plugins of one name is not something the menu can answer, and a
    user plugin silently replacing a shipped one is the worse of the two
    outcomes.
    """
    asked = (name or '').strip()
    if not asked:
        raise ValueError('a plugin needs a name')
    if not asked.isidentifier() or keyword.iskeyword(asked):
        raise ValueError('%r is not a name IMASViz can use: it is the name of a '
                         'folder, a module and a class at once, so it has to be '
                         'a plain name -- a letter or underscore, then letters, '
                         'digits or underscores' % asked)
    shipped = getRegisteredPlugins()
    if asked in shipped:
        raise ValueError('%s is a plugin IMASViz already ships. Your plugin needs '
                         'its own name -- the shipped one is not replaced'
                         % asked)
    return asked


def compileCheck(text, path):
    """Refuse a source that will not parse, naming where it stopped.

    Asked before a file is written and before a module is replaced, which is what
    keeps a half-typed plugin from taking down the entry that works today.
    """
    try:
        compile(text, path, 'exec')
    except SyntaxError as error:
        where = '%s line %s' % (path, error.lineno)
        raise ValueError('%s: %s' % (where, error.msg))


def readSource(source):
    """The source the editor shows. None when there is no file to show."""
    if not source.fileName:
        return None
    try:
        with open(source.fileName, encoding='utf-8') as handle:
            return handle.read()
    except OSError as error:
        raise ValueError('%s could not be read: %s: %s'
                         % (source.fileName, type(error).__name__, error))


def writeSource(source, text):
    """Put a new source in place -- and only if it parses and belongs to this user.

    The read-only boundary is asked here and not only in the editor: a greyed-out
    text area is what the user sees, this is what makes it true.
    """
    if not source.writable:
        raise ValueError('%s is a plugin IMASViz ships. It can be read, not '
                         'changed -- copy it into your own plugins to edit it'
                         % source.name)
    if source.isUi:
        raise ValueError('%s is drawn from %s: the interface is not Python IMASViz '
                         'can edit' % (source.name, source.fileName))
    compileCheck(text, source.fileName)
    try:
        with open(source.fileName, 'w', encoding='utf-8') as handle:
            handle.write(text)
    except OSError as error:
        raise ValueError('%s could not be written: %s: %s'
                         % (source.fileName, type(error).__name__, error))
    return source.fileName


def attachUserPackage(folder=None):
    """Give the user's plugin folder a name Python can import under.

    Idempotent, and re-pointed when the folder moves -- which is what a test with
    its own `HOME` needs, and what a second run in one process would meet.
    """
    folder = userPluginsFolder() if folder is None else folder
    package = sys.modules.get(USER_PACKAGE)
    if package is None:
        package = types.ModuleType(USER_PACKAGE)
        package.__path__ = [folder]
        sys.modules[USER_PACKAGE] = package
    elif list(package.__path__) != [folder]:
        forgetUserModules()
        package.__path__ = [folder]
    return package


def forgetUserModules(prefix=None):
    """Drop the user's plugin modules so the next import reads the disk again.

    `prefix` is a dotted import name -- a plugin's `packagePrefix`, or nothing for
    every plugin of the folder at once. `importlib.reload` is not enough: it
    re-executes one module and leaves the others of the same folder on the old
    code, and a plugin is a folder before it is a module (the Profiles plugin is
    one module and a sub-package of four). So the whole subtree goes, the folder's
    own package with it, or that parent would hand back the module attribute it
    already cached.
    """
    prefix = USER_PACKAGE if prefix is None else prefix
    forgotten = [name for name in list(sys.modules)
                 if name == prefix or name.startswith(prefix + '.')]
    for name in forgotten:
        del sys.modules[name]
    return sorted(forgotten)


def findUserSource(name, folder=None):
    """The user's plugin of that name, or None."""
    for source in userSources(folder):
        if source.name == name:
            return source
    return None


def copyIntoUserFolder(source, newName, folder=None):
    """Copy a shipped plugin into this user's folder, under a name of their own.

    Reading a shipped plugin is only half of what makes the read-only boundary
    useful: what a user usually wants is to start from one. The whole folder comes
    along, so a plugin built out of a sub-package still hangs together, and every
    spelling of the old class name becomes the new one -- the name is a folder, a
    module and a class at once, so a rename has to reach all three. The copy is a
    starting point, not a port: it says which file to open, and what it draws is
    still what the shipped plugin draws.
    """
    if source.origin != BUILTIN:
        raise ValueError('%s is already one of your plugins' % source.name)
    if source.isUi or not source.folder:
        raise ValueError('%s is drawn from a .ui file: there is no source of it to '
                         'copy' % source.name)
    newName = pluginNameFor(newName)
    folder = userPluginsFolder() if folder is None else folder
    # The folder of the copy is named after the plugin, not after the shipped one
    # it came from, so two copies of one shipped plugin can live side by side. It
    # is spelled in lower case for the same reason the creator spells it that way:
    # the file system this folder may live on is not promised to be case-aware.
    target = os.path.join(folder, 'viz_' + newName.lower())
    if os.path.exists(target):
        raise ValueError('%s already holds a plugin named %s'
                         % (folder, newName))
    try:
        # The byte-code of the plugin it came from is not part of the copy: it
        # names modules the copy no longer holds, and a folder the user reads to
        # fix is better without files they never wrote.
        shutil.copytree(source.folder, target,
                        ignore=shutil.ignore_patterns('__pycache__'))
    except (OSError, shutil.Error) as error:
        raise ValueError('%s could not be copied into %s: %s'
                         % (source.folder, target, error))

    oldName = source.registration.rsplit('.', 1)[-1]
    # The file first, then the words inside it. Renaming afterwards would leave
    # the answer this function gives pointing at a path that no longer exists --
    # and `touched` is what the manager tells the user to go and open.
    moduleFile = os.path.join(target, oldName + '.py')
    if os.path.exists(moduleFile):
        os.rename(moduleFile, os.path.join(target, newName + '.py'))
    renamed = renameIdentifier(target, oldName, newName)
    return QVizPluginSource(newName, os.path.basename(target) + '.' + newName,
                            USER, folder=target,
                            fileName=os.path.join(target, newName + '.py')), renamed


def renameIdentifier(directory, oldName, newName):
    """Rewrite one identifier across a copied plugin, and say which files changed.

    Word-boundary, identifier to identifier -- never a substring of another name.
    """
    pattern = re.compile(r'\b%s\b' % re.escape(oldName))
    touched = []
    for dirpath, _dirNames, fileNames in os.walk(directory):
        for fileName in fileNames:
            if not fileName.endswith('.py'):
                continue
            path = os.path.join(dirpath, fileName)
            try:
                with open(path, encoding='utf-8') as handle:
                    text = handle.read()
            except (OSError, UnicodeDecodeError):
                continue
            changed = pattern.sub(newName, text)
            if changed != text:
                with open(path, 'w', encoding='utf-8') as handle:
                    handle.write(changed)
                touched.append(path)
    return touched
