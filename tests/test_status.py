from datetime import date

from src.status import detect_status

TODAY = date(2026, 9, 25)


def test_closed_mats_phrase():
    text = "Applications for the Winter 2027 cohort are now closed. Sign up for updates."
    assert detect_status(text, today=TODAY)[0] == "closed"


def test_closed_beats_open():
    text = "Applications are now closed for this cycle. Applications open again in January."
    assert detect_status(text, today=TODAY)[0] == "closed"


def test_open_phrase():
    assert detect_status("Applications are now open for the 2027 cohort.", today=TODAY)[0] == "open"


def test_deadline_gate():
    assert detect_status("blah", deadline="2026-01-15", today=TODAY)[0] == "closed"
    assert detect_status("blah", deadline="2026-12-15", today=TODAY)[0] == "open"


def test_rolling():
    assert detect_status("We review applications on a rolling basis.", today=TODAY)[0] == "rolling"


def test_unknown():
    assert detect_status("", today=TODAY)[0] == "unknown"
    assert detect_status("A research lab studying alignment.", today=TODAY)[0] == "unknown"
