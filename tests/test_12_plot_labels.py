# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""Legends, axis labels, units and plot title.

The legend of a curve used to embed the whole IMAS URI, because the data source
returned it from getShortLabel(). The axis units slot was never fed, and the
title of the first curve was erased right after being set.
"""

import pytest

from imasviz.VizDataSource.QVizIMASDataSource import QVizIMASDataSource

PATH_URI = 'imas:hdf5?path=/afs/eufus.eu/g2itmdev/user/g2lfleur/public/imasdb/west/3/54924/0'
LEGACY_URI = 'imas:hdf5?user=g2lfleur;shot=54924;run=0;database=west;version=3'


def test_a_path_uri_yields_a_short_case_label():
    source = QVizIMASDataSource('native', PATH_URI)
    assert source.getShortLabel() == 'west 54924.0'


def test_a_parameter_uri_yields_the_same_short_case_label():
    source = QVizIMASDataSource('native', LEGACY_URI)
    assert source.getShortLabel() == 'west 54924.0'


def test_the_two_uri_forms_describe_the_same_case():
    assert (QVizIMASDataSource('native', PATH_URI).getShortLabel() ==
            QVizIMASDataSource('native', LEGACY_URI).getShortLabel())


def test_an_unparsable_uri_falls_back_to_the_uri():
    source = QVizIMASDataSource('native', 'some odd name')
    assert source.getShortLabel() == 'some odd name'


def test_the_long_label_still_carries_the_full_uri():
    # The menus list cases through getLongLabel(); it must stay unambiguous.
    source = QVizIMASDataSource('native', PATH_URI)
    assert PATH_URI in source.getLongLabel()
    assert source.getShortLabel() != PATH_URI


def test_the_uri_is_the_only_thing_a_label_is_read_from():
    """The Access Layer 4 'legacy attributes' used to win over the URI.

    They were read first, under a key spelled 'database_name' where the URI
    spells it 'database', because that is what an AL4 entry was built from.
    Nothing builds an entry from those numbers any more, so a source that
    cannot read its URI falls back to the URI itself and nothing else.
    """
    source = QVizIMASDataSource('native', 'whatever')
    assert not hasattr(source, 'legacy_attributes')
    assert source.getShortLabel() == 'whatever'
