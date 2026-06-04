import datetime
from game.aging import get_stage, JUVENILE_DAYS, ELDER_DAYS


def _iso(days_ago: float) -> str:
    t = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days_ago)
    return t.isoformat()


# ── stage boundaries ───────────────────────────────────────────────────────────


def test_just_caught_is_juvenile():
    assert get_stage(_iso(0)) == "juvenile"


def test_one_day_old_is_juvenile():
    assert get_stage(_iso(1)) == "juvenile"


def test_just_before_juvenile_cutoff_is_juvenile():
    assert get_stage(_iso(JUVENILE_DAYS - 0.01)) == "juvenile"


def test_exactly_at_juvenile_cutoff_is_adult():
    assert get_stage(_iso(JUVENILE_DAYS)) == "adult"


def test_midrange_adult():
    assert get_stage(_iso(10)) == "adult"


def test_just_before_elder_cutoff_is_adult():
    assert get_stage(_iso(ELDER_DAYS - 0.01)) == "adult"


def test_exactly_at_elder_cutoff_is_elder():
    assert get_stage(_iso(ELDER_DAYS)) == "elder"


def test_very_old_is_elder():
    assert get_stage(_iso(365)) == "elder"


# ── bad input falls back to adult ─────────────────────────────────────────────


def test_none_input_returns_adult():
    assert get_stage(None) == "adult"


def test_empty_string_returns_adult():
    assert get_stage("") == "adult"


def test_garbage_string_returns_adult():
    assert get_stage("not-a-date") == "adult"


# ── timezone-aware caught_at ───────────────────────────────────────────────────


def test_tz_aware_caught_at_works():
    tz_aware = (
        datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1)
    ).isoformat()
    assert get_stage(tz_aware) == "juvenile"


def test_tz_aware_elder():
    tz_aware = (
        datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=60)
    ).isoformat()
    assert get_stage(tz_aware) == "elder"
