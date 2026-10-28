# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""Writing the IDSs this shot view has open into another case.

The manual says what this does: the IDSs currently opened in the tree view are
written to a case the user names, and the database has to exist already. Three
things had to be measured to write it, because the entry of a previous release
did none of them and reported no reason:

* an entry built from an URI is open from the moment it is built. Calling
  ``open()`` on it answers ``RuntimeError: This DBEntry is already open``, which
  is exactly what the old code did -- into a bare ``except:`` that logged the
  failure at *info* level and returned. Measured: the click left one file behind
  (a 1912-byte ``master.h5``) and **0** IDSs, and the reason was gone.
* the write entry has to be built at the data dictionary the exported IDSs were
  read at. Without that pin, the first ``put`` answers ``RuntimeError: Provided
  IDS uses DD 3.35.0 which has a different major version than the Data Entry
  (-1)``. With it, the same two IDSs came out as ``master.h5`` 2000 bytes and
  ``pulse_schedule.h5`` 83662 bytes, and reading the case back listed
  ``pulse_schedule`` at occurrence 0.
* a ``put`` that fails leaves the entry open. Nothing here is closed unless a
  ``finally`` closes it.

What is written is what is **open** -- the occurrences the plots read -- and each
IDS is written on its own occurrence, one IDS that the target refuses not
costing the user the others: it is named in the log and the rest goes on.

What is written, though, has to be a copy that holds its data. The views read
their IDSs lazily (``QVizIMASDataSource.LAZY_READS``), and the Access Layer
refuses to write such a handle: ``put`` answers ``ValueError: Lazy loaded IDSs
cannot be used in put or put_slice.`` and filling it in place is refused too
(``get(destination=...)`` answers ``ValueError: Lazy-loaded IDSs are
read-only.``). Measured, a view of ``equilibrium`` and ``pulse_schedule``
exported as it stood left one file behind -- a 1 912-byte ``master.h5`` -- and
the case read back answered ``IDS 'equilibrium', occurrence 0 is empty``. So the
export asks the open entry for a whole copy of each occurrence it writes:
**3,8 s and +125 Mo** for ``equilibrium`` occurrence 0 of the reference case,
against 0,06 s and +1,9 Mo for the lazy read the view keeps. That price is paid
when the export is asked for, not on every load of the session, and the copy is
handed straight to the write rather than put back in the cache -- the tree keeps
reading through its own handle, and 125 Mo per IDS is not what a session should
carry for a command the user asked for once.
"""

import logging

import imas

from imasviz.VizGUI.VizGUICommands.QVizAbstractCommand import QVizAbstractCommand
from imasviz.VizGUI.VizGUICommands.VizDataExport.QVizExportDialog import \
    QVizExportDialog


class QVizExportToIDS(QVizAbstractCommand):
    """Copy the IDSs opened in this shot view into the case that is asked for."""

    def __init__(self, dataTreeView, target=None, ddVersion=None):
        """
        Arguments:
            target (QVizExportTarget) : where to write; when it is left out the
                user is asked, as the manual describes it.
            ddVersion (str) : the data dictionary to write at; by default the
                one this case was read at, which is the only one the loaded IDS
                instances are valid for.
        """
        QVizAbstractCommand.__init__(self, dataTreeView)
        self.target = target
        self.ddVersion = ddVersion
        self.uri = None

    def execute(self):
        """Write every opened IDS into the target case.

        Returns the URI written to. A shot view with nothing open, or a case the
        Access Layer will not open, raises with the reason -- the menu slot says
        that in the log panel, where the manual tells the user to look.
        """
        loaded = self.loadedIds()
        if not loaded:
            raise ValueError('Nothing to export: no IDS is open in this tree '
                             'view. Open the IDSs to export first.')

        target = self.target if self.target is not None else self.ask()
        if target is None:
            return None

        readAt = self.dataDictionaryOf(self.dataTreeView.dataSource, loaded)
        ddVersion = self.ddVersion or readAt
        if not target.dataVersion:
            target.dataVersion = ddVersion
        if target.dataMajor() != str(ddVersion).split('.')[0]:
            raise ValueError('The opened IDSs were read at data dictionary %s, '
                             'which cannot be written into a case named at '
                             'version %s: the Access Layer stores an IDS under '
                             'the major version it was read at.'
                             % (ddVersion, target.dataMajor()))

        uri = target.uri()
        self.uri = uri
        log = logging.getLogger(self.dataTreeView.uri)
        log.info('Exporting %d IDS(s) to "%s" (data dictionary %s)...'
                 % (len(loaded), uri, ddVersion))

        entry = None
        try:
            entry = self.openForWriting(uri, ddVersion)
            written, refused = self.write(entry, loaded)
        except ValueError:
            raise
        except Exception as e:
            raise ValueError('Cannot export to "%s": %s' % (uri, e))
        finally:
            if entry is not None:
                entry.close()

        for name, occurrence, why in refused:
            log.error('"%s" occurrence %d was not written: %s'
                      % (name, occurrence, why))
        log.info('Export finished: %d of %d IDS(s) written to "%s".'
                 % (written, len(loaded), uri))
        if not written:
            raise ValueError('Nothing was written to "%s": every IDS was '
                             'refused; see the log above for each reason.'
                             % uri)
        return uri

    def ask(self):
        """The dialog the manual shows; None when the user cancels."""
        dialog = QVizExportDialog(self.dataTreeView.parent,
                                  QVizExportTarget.fromCase(
                                      self.dataTreeView.dataSource))
        if not dialog.exec():
            return None
        return dialog.target()

    def loadedIds(self):
        """[(name, occurrence, ids instance)] for what this case has open.

        The occurrences are the ones the plots read -- the cache of the view --
        so exporting does not reopen the case and writes no occurrence the user
        did not open. What each one is made of, though, is a copy that holds its
        data: the views read lazily, and a lazy handle is a window on the open
        file, which the Access Layer refuses to write (see this module's header).
        """
        entries = self.dataTreeView.dataSource.data_entries
        loaded = []
        for key, idsInstance in entries.items():
            name, _, occurrence = key.rpartition('/')
            occurrence = int(occurrence)
            if getattr(idsInstance, '_lazy', False):
                idsInstance = self.wholeCopyOf(name, occurrence)
            loaded.append((name, occurrence, idsInstance))
        return sorted(loaded)

    def wholeCopyOf(self, name, occurrence):
        """One occurrence read whole, for the write to have something to write.

        Asked of the entry the case is already open with, and not cached: the
        tree goes on reading through the lazy handle it drew, and holding a
        whole copy of every opened IDS for the rest of the session would cost
        125 Mo per IDS for a command asked for once.
        """
        entry = self.dataTreeView.dataSource.db_entry
        if entry is None:
            raise ValueError('Cannot export %s occurrence %d: the case %s is not '
                             'open, and what this view holds of it is a lazy '
                             'handle, which the Access Layer refuses to write.'
                             % (name, occurrence, self.dataTreeView.uri))
        logging.getLogger(self.dataTreeView.uri).info(
            'Reading %s occurrence %d whole for the export: what the tree holds '
            'is read lazily, and a lazily read IDS cannot be written.'
            % (name, occurrence))
        try:
            return entry.get(name, occurrence)
        except Exception as error:
            raise ValueError('Cannot re-read %s occurrence %d of %s whole for the '
                             'export: %s: %s'
                             % (name, occurrence, self.dataTreeView.uri,
                                type(error).__name__, error))

    @staticmethod
    def dataDictionaryOf(dataSource, loaded):
        """The full data dictionary version the export has to be written at.

        Not a preference: the Access Layer refuses to store an IDS at a major
        version other than the one it was read at (measured, ``RuntimeError:
        Provided IDS uses DD 3.35.0 which has a different major version than the
        Data Entry (-1)``), and it refuses a version given as a bare major
        (``UnknownDDVersion: Data dictionary version '3' cannot be found``). So
        the number here is the complete one.

        The pin the case was opened with is the answer when there is one: every
        loaded IDS has already been validated against it. Otherwise the IDSs
        themselves say it, and IDSs reading at two different major versions
        cannot share one case.
        """
        majors = set()
        versions = set()
        for name, occurrence, idsInstance in loaded:
            version = str(idsInstance.ids_properties.version_put.
                          data_dictionary or '')
            if version:
                versions.add(version)
                majors.add(version.split('.')[0])
        if len(majors) > 1:
            raise ValueError('The IDSs open in this tree view were read at '
                             'different data dictionary major versions (%s): '
                             'they cannot be written into one case.'
                             % ', '.join(sorted(majors)))
        if dataSource.dd_version:
            return str(dataSource.dd_version)
        if len(versions) == 1:
            return versions.pop()
        if not versions:
            raise ValueError('The data dictionary of the opened IDSs is '
                             'unknown, so the export has nowhere to write them.')
        raise ValueError('The opened IDSs were read at different data '
                         'dictionary versions (%s) and this case was not opened '
                         'at a version of its own: say which one to export at.'
                         % ', '.join(sorted(versions)))

    @staticmethod
    def openForWriting(uri, ddVersion):
        """An entry the export can write, already open.

        No ``open()`` call: an entry built from an URI opens at construction and
        refuses a second open. The dictionary version is pinned here because
        IMAS-Python settles it at construction, and an entry without it refuses
        every IDS read at another one.
        """
        if ddVersion:
            return imas.DBEntry(uri, 'w', dd_version=ddVersion)
        return imas.DBEntry(uri, 'w')

    def write(self, entry, loaded):
        """Put each IDS on its own occurrence. Returns (written, refused)."""
        written = 0
        refused = []
        for name, occurrence, idsInstance in loaded:
            try:
                entry.put(idsInstance, occurrence)
                written += 1
            except Exception as e:
                refused.append((name, occurrence, str(e)))
        return written, refused
