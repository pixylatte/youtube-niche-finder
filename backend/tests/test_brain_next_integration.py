"""Unified Brain Next: no extra quota or DB mutation for archive evidence."""
from datetime import datetime, timedelta, timezone

from application import search as QUERY


NOW = datetime.now(timezone.utc)


class _NicheResult:
    def __init__(self, row):
        self.row = row

    def fetchone(self):
        return self.row


class _Connection:
    def __init__(self, row):
        self.row = row
        self.closed = False

    def execute(self, sql, values):
        assert "FROM niches" in sql and values == ("history-archive",)
        return _NicheResult(self.row)

    def close(self):
        self.closed = True


def _mock_database(monkeypatch, rows):
    db_connection = _Connection({
        "query": "history archive",
        "last_collected_at": NOW.isoformat(),
    })
    monkeypatch.setattr(QUERY.db, "get_conn", lambda: db_connection)
    monkeypatch.setattr(QUERY.trends, "load_window", lambda **_kwargs: rows)
    return db_connection


def test_niche_overview_no_archive_is_a_truthful_no_signal(monkeypatch):
    conn = _mock_database(monkeypatch, [])
    result = QUERY.niche_overview("history-archive", period="30d")
    assert conn.closed
    assert result["found"] is False
    assert result["evidenceQuality"]["status"] == "no-signal"
    assert result["evidenceQuality"]["quotaUsed"] == 0


def test_niche_overview_adds_coverage_without_replacing_existing_scores(monkeypatch):
    rows = [
        {"video_id": "abcdefghijk", "channel_id": "UC-A",
         "published_at": (NOW - timedelta(days=2)).isoformat(), "outlierScore": 3.2},
        {"video_id": "lmnopqrstuv", "channel_id": "UC-B",
         "published_at": (NOW - timedelta(days=4)).isoformat(), "outlierScore": 1.1},
        {"video_id": "0123456789A", "channel_id": "UC-B",
         "published_at": (NOW - timedelta(days=8)).isoformat(), "outlierScore": 0.9},
    ]
    conn = _mock_database(monkeypatch, rows)
    monkeypatch.setattr(QUERY, "_overview_from_rows",
                        lambda _rows, top_n=5: {"score": 42, "video_count": 3})
    monkeypatch.setattr(QUERY.SAT, "niche_saturation",
                        lambda _niche: {"status": "existing-score"})
    result = QUERY.niche_overview("history-archive", period="30d")
    assert conn.closed
    assert result["found"] is True
    assert result["score"] == 42
    assert result["saturation_v2"]["status"] == "existing-score"
    assert result["evidenceQuality"]["status"] == "supported-sample"
    assert result["evidenceQuality"]["distinctChannels"] == 2
    assert result["evidenceQuality"]["rankingsChanged"] is False
    assert result["evidenceQuality"]["quotaUsed"] == 0
