"""Port legacy post-publish readiness without pretending 3h scans were 1h/24h checkpoints."""
from domain.post_publish_observations import assess


def row(hours, views):
    return {"ageHours": hours, "views": views}


def test_actual_observed_interval_is_labeled_and_not_an_exact_checkpoint():
    data = assess([row(3, 100), row(9, 450), row(21, 950), row(30, 1200)])
    assert data["status"] == "observed-interval"
    assert data["snapshotCount"] == 4
    assert data["firstDaySnapshots"] == 3
    interval = data["observedFirstDayRate"]
    assert interval["fromHours"] == 3
    assert interval["toHours"] == 21
    assert interval["observedViewGain"] == 850
    assert interval["viewsPerHour"] == round(850 / 18, 2)
    assert data["exactCheckpointsVerified"] is False
    assert data["quotaUsed"] == 0


def test_single_24h_snapshot_cannot_be_called_first_day_growth():
    data = assess([row(24, 5000)])
    assert data["status"] == "limited"
    assert data["observedFirstDayRate"] is None


def test_first_observation_after_24h_cannot_infer_earlier_24h_performance():
    data = assess([row(30, 1200), row(48, 2300)])
    assert data["firstDaySnapshots"] == 0
    assert data["observedFirstDayRate"] is None


def test_decreasing_counters_trigger_review_instead_of_fake_negative_velocity():
    data = assess([row(3, 4000), row(10, 3500)])
    assert data["status"] == "limited"
    assert data["observedFirstDayRate"] is None


def test_duplicate_missing_nan_or_invalid_points_do_not_inflate_coverage():
    data = assess([row(2, 100), row(2, 100), row(-1, 5),
                   row(float("nan"), 900), row(7, -3),
                   row(10, "500"), {"ageHours": True, "views": 40}])
    assert data["snapshotCount"] == 1
    assert data["status"] == "limited"


def test_unknown_input_is_not_empty_archive():
    data = assess(None)
    assert data["status"] == "unavailable"
    assert data["snapshotCount"] is None


def test_uncollected_video_is_insufficient():
    data = assess([])
    assert data["status"] == "insufficient"
    assert data["snapshotCount"] == 0
