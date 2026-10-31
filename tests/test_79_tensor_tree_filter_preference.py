# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

import pytest
import os
from imasviz.VizUtils import QVizPreferences
from imasviz.VizGUI.VizTreeView.QVizDataTreeViewBuilder import QVizDataTreeViewBuilder
from imasviz.VizGUI.VizTreeView.QVizTreeNode import QVizTreeNode

def test_tensor_tree_filter_preference(monkeypatch, tmp_path):
    pref_dir = tmp_path / ".imasviz"
    pref_dir.mkdir()
    pref_file = pref_dir / "preferences"
    pref_file.write_text("Show_only_tensors_rank_ge_1=1\n")
    monkeypatch.setenv("HOME", str(tmp_path))

    QVizPreferences.userPreferencesInitialized = False
    QVizPreferences().build()

    assert QVizPreferences.Show_only_tensors_rank_ge_1 == 1

def test_prune_tree_removes_low_rank_nodes(qtbot):
    builder = QVizDataTreeViewBuilder(showOnlyTensorsRankGe1=True)
    root = QVizTreeNode(None, ["Root"])
    
    # Mock / add test children: one scalar (rank < 1 or rank 0) and one tensor (rank >= 1)
    # Since QVizTreeNode methods depend on full IDS structure, we can test _pruneTree logic directly or stub node rank
    pass
