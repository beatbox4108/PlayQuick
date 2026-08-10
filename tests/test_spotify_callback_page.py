from pathlib import Path

SITE = Path(__file__).parents[1] / "site" / "spotify-callback"


def test_callback_page_has_no_external_resources() -> None:
    html = (SITE / "index.html").read_text(encoding="utf-8")

    assert "Content-Security-Policy" in html
    assert 'name="referrer" content="no-referrer"' in html
    assert "https://" not in html
    assert "http://" not in html


def test_callback_script_copies_then_removes_query() -> None:
    script = (SITE / "callback.js").read_text(encoding="utf-8")

    assert "window.location.href" in script
    assert "navigator.clipboard.writeText" in script
    assert "window.history.replaceState" in script
    assert "fetch(" not in script
    assert "localStorage" not in script
