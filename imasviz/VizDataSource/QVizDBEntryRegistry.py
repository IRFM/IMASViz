# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************
import threading


class QVizDBEntryRegistry:
    """The imas.DBEntry objects currently in use, one per case.

    A case is opened once whatever asks for it: the shot view, a plugin, a
    second selection. Callers acquire a reference when they need the entry and
    release it when they are done; the entry is closed, and the IDS instances
    read from it are dropped, when the last reference goes. Keeping a closed
    entry around is what used to make the next load fail, since IMAS-Python
    refuses to re-open an entry built from an URI.

    The key carries the mode and the data dictionary pin because IMAS-Python
    settles both when the entry is built: the same case cannot be shared
    between a reader and a writer, nor between two dictionary versions.
    """

    _records = {}
    _lock = threading.Lock()

    @staticmethod
    def _key(uri, mode, dd_version):
        return (uri, mode, dd_version)

    @staticmethod
    def acquire(uri, mode='r', dd_version=None, build=None):
        """Returns the entry for this case, building it when none is open.

        build() has to return an entry that is already usable: an AL5 entry
        opens at construction and cannot be opened again, while an AL4 entry
        needs an explicit open(). Which of the two applies is the data source's
        business, not this registry's.
        """
        key = QVizDBEntryRegistry._key(uri, mode, dd_version)
        with QVizDBEntryRegistry._lock:
            record = QVizDBEntryRegistry._records.get(key)
            if record is None:
                record = {'entry': None, 'count': 0, 'ids': {}}
                QVizDBEntryRegistry._records[key] = record
            if record['entry'] is None:
                if build is None:
                    raise ValueError(
                        'No entry is open for ' + str(uri) +
                        ' and no build callable was given to create one.')
                record['entry'] = build()
            record['count'] += 1
            return record['entry']

    @staticmethod
    def release(uri, mode='r', dd_version=None):
        """Gives back one reference; the last one closes the case.

        Releasing more often than acquiring is ignored: a caller that lost its
        reference must not close the file under another user's feet.

        The IDS instances read from the entry outlive it on purpose. An entry
        loads a whole IDS into memory, so those instances stay valid, and the
        views and the export go on reading what has been loaded. They are
        dropped by drop(), when nobody displays the case any more.
        """
        key = QVizDBEntryRegistry._key(uri, mode, dd_version)
        with QVizDBEntryRegistry._lock:
            record = QVizDBEntryRegistry._records.get(key)
            if record is None or record['count'] <= 0:
                return 0
            record['count'] -= 1
            if record['count'] > 0:
                return record['count']
            if record['entry'] is not None:
                record['entry'].close()
                record['entry'] = None
            return 0

    @staticmethod
    def drop(uri, mode='r', dd_version=None):
        """Forgets the case and the IDS instances loaded from it.

        Closes the entry if it happens to be open. This is what a shot view
        calls when it goes away: until then the loaded IDSs are kept in memory,
        as they were when each data source owned its own cache.
        """
        key = QVizDBEntryRegistry._key(uri, mode, dd_version)
        with QVizDBEntryRegistry._lock:
            record = QVizDBEntryRegistry._records.pop(key, None)
            if record is None:
                return False
            if record['entry'] is not None:
                record['entry'].close()
            return True

    @staticmethod
    def ids_cache(uri, mode='r', dd_version=None):
        """IDS instances loaded from this case, shared by all its users.

        Keyed IDSName/occurrence. Empty and throwaway for a case never opened:
        it is only writable once an entry has been acquired for it.
        """
        key = QVizDBEntryRegistry._key(uri, mode, dd_version)
        with QVizDBEntryRegistry._lock:
            record = QVizDBEntryRegistry._records.get(key)
            return record['ids'] if record is not None else {}

    @staticmethod
    def count(uri, mode='r', dd_version=None):
        """Number of references currently held on this case."""
        key = QVizDBEntryRegistry._key(uri, mode, dd_version)
        with QVizDBEntryRegistry._lock:
            record = QVizDBEntryRegistry._records.get(key)
            return record['count'] if record is not None else 0

    @staticmethod
    def live_entries():
        """The entries currently open, one per case."""
        with QVizDBEntryRegistry._lock:
            return [record['entry'] for record in QVizDBEntryRegistry._records.values()
                    if record['entry'] is not None]

    @staticmethod
    def known_cases():
        """The cases the registry holds something for, open or not."""
        with QVizDBEntryRegistry._lock:
            return list(QVizDBEntryRegistry._records.keys())

    @staticmethod
    def reset():
        """Forgets every entry without closing them; for tests only."""
        with QVizDBEntryRegistry._lock:
            QVizDBEntryRegistry._records = {}
