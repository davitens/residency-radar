from datetime import date

from src.filters import is_eligible, is_open, is_residency, parse_deadline
from src.models import Program

TODAY = date(2026, 9, 25)


def test_deadline_variants_never_crash():
    assert parse_deadline("Rolling", TODAY) is None
    assert parse_deadline("", TODAY) is None
    assert parse_deadline("this is garbage", TODAY) is None
    assert parse_deadline("open until filled", TODAY) is None
    assert parse_deadline("15 Jan 2026", TODAY) == date(2026, 1, 15)
    assert parse_deadline("2026-12-01", TODAY) == date(2026, 12, 1)


def test_expired_is_ineligible():
    expired = Program("O", "T", "https://a", text="x" * 300, deadline="15 Jan 2026")
    rolling = Program("O", "T", "https://b", text="x" * 300, deadline="Rolling")
    assert not is_eligible(expired, TODAY, "phd")
    assert is_eligible(rolling, TODAY, "phd")


def test_us_only_gate():
    p = Program("O", "T", "https://a", text="must be authorized to work in the us. " * 10)
    assert not is_eligible(p, TODAY, "phd in Spain")
    assert is_eligible(p, TODAY, "phd, authorized to work in the us")


def test_is_open():
    assert is_open(Program("O", "T", "https://a", status="open"))
    assert is_open(Program("O", "T", "https://a", status="unknown"))
    assert not is_open(Program("O", "T", "https://a", status="closed"))


def test_is_residency():
    assert is_residency(Program("O", "MATS Program", "https://a", source="curated"))
    assert is_residency(Program("O", "AI Residency 2026", "https://a", source="ashby"))
    assert is_residency(Program("O", "Research Fellow", "https://a", source="greenhouse"))
    assert not is_residency(Program("O", "Senior Backend Engineer", "https://a", source="ashby"))
    assert not is_residency(Program("O", "Early Careers & Interns Specialist", "https://a", source="ashby"))
    assert is_residency(Program("O", "Research Internship (Winter 2027)", "https://a", source="ashby"))


def test_phd_required_gate():
    p = Program("O", "T", "https://a", text="phd required. " * 30)
    assert not is_eligible(p, TODAY, "master degree holder")
    assert is_eligible(p, TODAY, "machine learning phd")
