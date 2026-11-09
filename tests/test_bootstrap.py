from grant_finder_rag.bootstrap import refuse_threshold


def test_refuse_threshold_default(monkeypatch):
    monkeypatch.delenv("REFUSE_THRESHOLD", raising=False)
    assert refuse_threshold() == 0.05


def test_refuse_threshold_from_env(monkeypatch):
    monkeypatch.setenv("REFUSE_THRESHOLD", "0.1")
    assert refuse_threshold() == 0.1
