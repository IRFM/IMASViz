# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The case an export writes: who, where, which pulse, on which backend.

The dialog asks for four things -- user, database, shot, run -- and they spell
one IMAS URI. Getting that spelling right matters more than it looks: the
Access Layer puts the pulse under
``<database>/<data version>/<shot>/<run>/``, and the data version comes out of
this class. The old dialog passed the Access Layer's own major version there
(``IMAS_MAJOR_VERSION``), and measured on this stack that made the Access Layer
create ``no_such_db/5/1/0/`` while every case this application reads lives under
``west/3/54924/0`` -- the bytes were written, into a directory nothing looks in.
So the version written here is the version of the data dictionary the exported
IDSs were read with, which is also the version the entry has to be opened at.

Nothing here talks to the Access Layer: the values are checked when they are
typed, and the URI is built once, here.
"""

import os

HDF5 = 13
MDSPLUS = 12

BACKENDS = {HDF5: 'hdf5', MDSPLUS: 'mdsplus'}


class QVizExportTarget:
    """Where to write: the four fields the manual lists, plus the backend.

    `dataVersion` is the version of the data dictionary the exported IDSs were
    read at -- the full number, ``3.35.0``, because that is what the Access Layer
    takes when an entry is built. The URI carries only its major part: measured
    on this stack, an entry built with ``dd_version='3'`` answers
    ``UnknownDDVersion: Data dictionary version '3' cannot be found``, while the
    same case written at ``3.35.0`` came out as ``master.h5`` plus
    ``pulse_schedule.h5`` and read back with ``pulse_schedule`` at occurrence 0.
    Two different numbers, and the Access Layer wants both of them.

    `uri` overrides everything: a case named by a path
    (``imas:hdf5?path=/…/west/3/54924/0``) is a case that can be written to, and
    that is the only spelling a scripted caller -- or a test -- needs.
    """

    def __init__(self, user='', database='', shot=None, run=None,
                 backend=HDF5, dataVersion=None, uri=None):
        self.user = (user or '').strip()
        self.database = (database or '').strip()
        self.shot = shot
        self.run = run
        self.backend = backend
        self.dataVersion = dataVersion
        self._uri = uri

    @staticmethod
    def fromCase(dataSource, run=None):
        """The case a shot view has open, as a place to write to.

        Prefilling from the opened case is what the dialog should offer: the
        old one prefilled ``/`` for the user and the database, which is not a
        user and not a database, and a URI naming a user literally called ``/``
        is only ever a mistake. A case named by a path says no user, so the
        login stands in for it -- an empty box there is a field the export would
        have to refuse.
        """
        from imasviz.VizDataSource.QVizIMASDataSource import _readCaseFromUri
        database, shot, caseRun = _readCaseFromUri(dataSource.uri)
        return QVizExportTarget(user=_userFromUri(dataSource.uri)
                                or os.environ.get('USER', ''),
                                database=database or '',
                                shot=_integer(shot),
                                run=run if run is not None else _integer(caseRun),
                                dataVersion=dataSource.dd_version)

    def uri(self):
        """The URI the Access Layer is asked to write.

        Raises with the reason when a field is missing or wrong -- the manual
        says these four name the pulse, so a half-filled set is refused rather
        than sent to the Access Layer to answer in its own words. The spelling
        is the data layer's, shared with the command line and the plugin that
        open a case the same way: one place spells a case, and it is the place
        ``_readCaseFromUri`` reads it back.
        """
        from imasviz.VizDataSource.QVizIMASDataSource import caseUri
        if self._uri:
            return self._uri
        for label, value in (('user', self.user), ('database', self.database)):
            if not value:
                raise ValueError('The %s is empty: it names part of the case '
                                 'to export to.' % label)
            if '/' in value or ';' in value:
                raise ValueError('The %s "%s" cannot be used to name a case: '
                                 'it holds a separator.' % (label, value))
        if not isinstance(self.shot, int) or self.shot < 1:
            raise ValueError('The shot number has to be a positive number, '
                             'got %r.' % (self.shot,))
        if not isinstance(self.run, int) or self.run < 0:
            raise ValueError('The run number has to be a number, got %r.'
                             % (self.run,))
        if self.backend not in BACKENDS:
            raise ValueError('Unknown backend %r: the export writes to HDF5 '
                             '(%d) or MDSplus (%d).' % (self.backend, HDF5,
                                                        MDSPLUS))
        if not self.dataVersion:
            raise ValueError('The data version is unknown: the export writes '
                             'under <database>/<version>/<shot>/<run>, so the '
                             'version the data was read with has to be known.')
        return caseUri(self.backend, self.user, self.database, self.shot,
                       self.run, self.dataMajor())

    def dataMajor(self):
        """The major of `dataVersion`: all that goes after ``version=``.

        The directory on disk is ``<database>/<major>/<shot>/<run>`` -- measured
        on the real cases, which sit under ``west/3/54924/0`` -- while the entry
        is built at the full ``3.35.0``. ``version=3.35.0`` is not a thing the
        reader of that path expects.
        """
        return str(self.dataVersion).split('.')[0]

    def __str__(self):
        return '%s %s.%s (%s)' % (self.database or '?', self.shot,
                                  0 if self.run is None else self.run,
                                  BACKENDS.get(self.backend, '?'))


def _userFromUri(uri):
    """The user a case URI names, empty when it is named by a path."""
    question = uri.find('?')
    if question == -1:
        return ''
    for term in uri[question + 1:].split(';'):
        if term.startswith('user='):
            return term[len('user='):]
    return ''


def _integer(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
