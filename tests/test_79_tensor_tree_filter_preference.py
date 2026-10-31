# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

import pytest
import os
from imasviz.VizUtils import QVizPreferences

def test_tensor_tree_filter_preference(monkeypatch, tmp_path):
    pref_dir = tmp_path / ".imasviz"
    pref_dir.mkdir()
    pref_file = pref_dir / "preferences"
    pref_file.write_text("Show_only_tensors_rank_ge_1=1\n")
    monkeypatch.setenv("HOME", str(tmp_path))
    
    QVizPreferences.userPreferencesInitialized = False
    QVizPreferences().build()
    
    assert QVizPreferences.Show_only_tensors_rank_ge_1 == 1
