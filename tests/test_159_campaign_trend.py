# Copyright holders : Commissariat à l'Energie Atomique et aux Energies
# Alternatives (CEA), France; and Laboratory for Engineering Design - LECAD,
# University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C
# open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted
# upon downloading the software and/or exercising any of the rights granted
# under this.
#
# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The trend of a quantity across a campaign of shots.

`test_152`/`155`/`157` pinned the other feature-3/4 layers; this one is the
last of the four priorities: the *tendance* over a series of shots. Two halves:

* **the arithmetic** -- `trend` is numpy-only and no-case: it takes the
  per-shot values a caller has read and answers the least-squares slope over
  the shot index, first to last, min/max and the shots they came from, and a
  one-word direction. The refusals it earns: one shot, an all-equal campaign,
  a value that is not a finite number, labels that hold a different count.
* **the surface** -- the same leaf read from two real shots of the reference
  database (`CASE_URI` and, when reachable, `RANK3_CASE_URI`); one value per
  shot (here `max` over each read), the trend over the two, and the report
  that writes the per-shot table and the direction. A one-shot campaign or a
  leaf the shot does not hold is refused in words, which is what comes back.

The surface test is the plumbing (two reads, one read per shot, the trend over
them, a report), pinned on the two shots the harness holds -- not the physics
of the specific leaf.
"""

import os

import pytest

from imasviz.VizAnalysis.trend import trend
from mcp_server.core import McpGuiCore
from conftest import (CASE_DATA_DICTIONARY_VERSION, CASE_URI,
                      RANK3_CASE_DATA_DICTIONARY_VERSION, RANK3_CASE_URI,
                      case_uri_or_skip, rank3_case_uri_or_skip)

# A leaf both shots hold, read as a curve by `get_signal` (the value a figure
# of that leaf would draw) -- `ip` over the axis the read settles on.
LEAF = 'equilibrium.time_slice[0].global_quantities.ip'


# -----------------------------------------------------------------------------
# 1. the arithmetic, pinned on known series (no case needed)
# -----------------------------------------------------------------------------

def test_a_rising_series_is_rising_with_its_slope():
    out = trend([1.0, 2.0, 3.0], labels=['a', 'b', 'c'])
    assert out['count'] == 3
    assert out['direction'] == 'rising'
    assert out['first'] == 1.0
    assert out['last'] == 3.0
    assert out['change'] == 2.0
    assert out['slope'] == pytest.approx(1.0)      # +1 per shot index
    assert out['min'] == 1.0
    assert out['max'] == 3.0
    assert out['argmin'] == 0
    assert out['argmax'] == 2


def test_a_falling_series_is_falling_and_names_its_extremes():
    out = trend([3.0, 2.0, 1.0], labels=['s0', 's1', 's2'])
    assert out['direction'] == 'falling'
    assert out['slope'] == pytest.approx(-1.0)
    assert out['argmin'] == 2
    assert out['argmax'] == 0
    assert out['labels'] == ['s0', 's1', 's2']


def test_two_shots_give_their_difference_as_the_change():
    out = trend([10.0, 4.0])
    assert out['direction'] == 'falling'
    assert out['change'] == pytest.approx(-6.0)
    assert out['slope'] == pytest.approx(-6.0)     # over one index step


def test_one_shot_is_a_value_not_a_trend():
    with pytest.raises(ValueError, match='at least two'):
        trend([42.0])
    with pytest.raises(ValueError, match='at least two'):
        trend([])


def test_an_all_equal_campaign_is_refused():
    with pytest.raises(ValueError, match='every shot answers'):
        trend([5.0, 5.0, 5.0])


def test_a_non_number_value_is_refused_by_position():
    with pytest.raises(ValueError, match='nope'):
        trend([1.0, 'nope', 3.0])


def test_a_non_finite_value_is_refused():
    with pytest.raises(ValueError, match='not finite'):
        trend([1.0, float('inf')])


def test_a_none_value_is_refused():
    with pytest.raises(ValueError, match='None'):
        trend([None, 3.0])


def test_labels_of_a_different_count_are_refused():
    with pytest.raises(ValueError, match='same number'):
        trend([1.0, 2.0], labels=['only-one'])


# -----------------------------------------------------------------------------
# 2. the surface: the same leaf on two shots of the reference database
# -----------------------------------------------------------------------------

@pytest.fixture(scope='module')
def campaign_core(qapp, tmp_path_factory):
    if case_uri_or_skip() is None:
        pytest.skip('reference case not reachable: %s' % CASE_URI)
    if rank3_case_uri_or_skip() is None:
        pytest.skip('second case not reachable: %s' % RANK3_CASE_URI)
    home = tmp_path_factory.mktemp('campaignHome')
    patch = pytest.MonkeyPatch()
    patch.setenv('HOME', str(home))
    session = McpGuiCore()
    session.open_case(CASE_URI, CASE_DATA_DICTIONARY_VERSION)
    session.open_case(RANK3_CASE_URI, RANK3_CASE_DATA_DICTIONARY_VERSION)
    session.load_ids(CASE_URI, 'equilibrium', 0)
    session.load_ids(RANK3_CASE_URI, 'equilibrium', 0)
    try:
        yield session
    finally:
        for key in list(getattr(session.api, 'figureframes', []) or {}):
            try:
                session.close_window(key)
            except Exception:
                pass
        patch.undo()


def _max_of(core, uri):
    read = core.get_signal(uri, LEAF, along=None)
    y = list(read['y'])
    return max(v for v in y if v == v)


@pytest.mark.case
@pytest.mark.ui
def test_two_real_shots_carry_a_trend(campaign_core):
    cases = [CASE_URI, RANK3_CASE_URI]
    out = campaign_core.campaign(cases, LEAF, which='max')

    assert len(out['rows']) == 2
    v0 = out['rows'][0]['value']
    v1 = out['rows'][1]['value']
    # the per-shot values are the same reads the surface already gives
    assert v0 == pytest.approx(_max_of(campaign_core, CASE_URI))
    assert v1 == pytest.approx(_max_of(campaign_core, RANK3_CASE_URI))

    trend_block = out['trend']
    assert trend_block['count'] == 2
    assert trend_block['first'] == v0
    assert trend_block['last'] == v1
    assert trend_block['change'] == pytest.approx(v1 - v0)
    # the direction is the sign of the change, nothing more
    assert trend_block['direction'] == ('rising' if v1 > v0
                                        else 'falling')
    assert trend_block['min'] == min(v0, v1)
    assert trend_block['max'] == max(v0, v1)
    if v0 < v1:
        assert trend_block['argmax'] == 1
        assert trend_block['argmin'] == 0
    else:
        assert trend_block['argmax'] == 0
        assert trend_block['argmin'] == 1


@pytest.mark.case
@pytest.mark.ui
def test_the_report_writes_the_table_and_the_direction(campaign_core,
                                                       monkeypatch):
    home = os.environ.get('HOME')
    out = campaign_core.campaign_report([CASE_URI, RANK3_CASE_URI], LEAF,
                                        which='max', name='test_campaign')

    path = out['saved_to']
    assert path == os.path.join(home, '.imasviz', 'reports',
                                'test_campaign.html')
    assert os.path.exists(path)
    html = open(path, encoding='utf-8').read()
    assert 'campaign of ' in html
    assert LEAF in html
    # one row per shot, and the direction the trend settled on
    assert html.count(CASE_URI) >= 1
    assert html.count(RANK3_CASE_URI) >= 1
    assert ('rising' in html) or ('falling' in html)
    assert '<svg' in html and '<polyline' in html


@pytest.mark.case
@pytest.mark.ui
def test_a_single_shot_is_not_a_campaign(campaign_core):
    with pytest.raises(ValueError, match='at least two'):
        campaign_core.campaign([CASE_URI], LEAF, which='max')


@pytest.mark.case
@pytest.mark.ui
def test_shot_without_the_leaf_is_refused(campaign_core):
    with pytest.raises(ValueError):
        campaign_core.campaign([CASE_URI, RANK3_CASE_URI],
                               'not.a.real.leaf', which='max')


def test_naming_both_at_and_which_is_refused(campaign_core):
    with pytest.raises(ValueError, match='one of'):
        campaign_core.campaign([CASE_URI, RANK3_CASE_URI], LEAF,
                               at=0, which='max')
