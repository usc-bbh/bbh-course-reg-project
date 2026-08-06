"""Challenge detection tests."""

from tests.conftest import load_fixture

from usc_catalog_scraper.challenge_detection import detect_challenge


def test_challenge_page_detected():
    challenged, evidence = detect_challenge(load_fixture("challenge.html"))
    assert challenged
    assert any("title" in e for e in evidence)
    assert any("script" in e for e in evidence)


def test_normal_index_not_challenged():
    challenged, _ = detect_challenge(load_fixture("index_normal.html"))
    assert not challenged


def test_noscript_banner_alone_is_not_a_challenge():
    challenged, _ = detect_challenge(load_fixture("index_shell.html"))
    assert not challenged


def test_program_page_not_challenged():
    challenged, _ = detect_challenge(load_fixture("program_simple.html"))
    assert not challenged


def test_title_marker_detected():
    html = "<html><head><title>Just a moment...</title></head><body><p>wait</p></body></html>"
    challenged, _evidence = detect_challenge(html)
    assert challenged


def test_script_marker_detected():
    html = (
        "<html><head><title>Programs</title><script src='/_Incapsula_Resource?x=1'></script></head>"
        "<body><p>short</p></body></html>"
    )
    challenged, _evidence = detect_challenge(html)
    assert challenged


def test_prose_mention_on_rich_page_not_flagged():
    filler = "<p>" + ("Requirements and courses for the degree. " * 150) + "</p>"
    html = (
        "<html><head><title>Program: Security Studies (BA)</title></head><body>"
        + filler
        + "<p>Coursework covers surveillance, captcha design and human verification research.</p>"
        + filler
        + "</body></html>"
    )
    challenged, _ = detect_challenge(html)
    assert not challenged


def test_academic_page_with_challenges_in_title_is_not_a_challenge():
    # Live failure 2026-07-19: "Engineering Innovation for Global Challenges
    # Minor" was deterministically misdetected as a bot-verification wall
    # because the bare word "challenge" was a title marker.
    body = "<p>" + "This minor addresses global engineering problems. " * 120 + "</p>"
    html = (
        "<html><head><title>Program: Engineering Innovation for Global "
        "Challenges Minor - University of Southern California</title></head>"
        f"<body><h1>Engineering Innovation for Global Challenges Minor</h1>{body}</body></html>"
    )
    challenged, evidence = detect_challenge(html)
    assert not challenged, evidence
