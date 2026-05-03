"""Tests for publish-print utilities."""
import json
import re
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from arttools.site_updater import update_search, update_feed
from arttools.publish_print import cli
from click.testing import CliRunner


# ── site_updater tests ────────────────────────────────────────────────────────

def _make_search_json(tmp: Path, items: list) -> Path:
    p = tmp / "search.json"
    p.write_text(json.dumps(items, indent=2))
    return p


def _make_feed_xml(tmp: Path) -> Path:
    p = tmp / "feed.xml"
    p.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0">\n'
        '  <channel>\n'
        '  <item>\n'
        '    <title>Existing Print</title>\n'
        '    <link>https://myerman.art/prints/existing/</link>\n'
        '  </item>\n'
        '  </channel>\n'
        '</rss>\n'
    )
    return p


def test_update_search_adds_entry(tmp_path, monkeypatch):
    p = _make_search_json(tmp_path, [{"slug": "old", "title": "Old"}])
    monkeypatch.setattr("arttools.site_updater.SEARCH_JSON", p)
    result = update_search("new-print", "New Print", ["tag1"], "A story.", "2026-05-01")
    assert result is True
    data = json.loads(p.read_text())
    assert data[0]["slug"] == "new-print"
    assert data[0]["tags"] == ["tag1"]


def test_update_search_skips_duplicate(tmp_path, monkeypatch):
    p = _make_search_json(tmp_path, [{"slug": "existing", "title": "Existing"}])
    monkeypatch.setattr("arttools.site_updater.SEARCH_JSON", p)
    result = update_search("existing", "Existing", [], "story", "2026-05-01")
    assert result is False


def test_update_feed_adds_item(tmp_path, monkeypatch):
    p = _make_feed_xml(tmp_path)
    monkeypatch.setattr("arttools.site_updater.FEED_XML", p)
    result = update_feed("new-print", "New Print", "A description.")
    assert result is True
    xml = p.read_text()
    assert "new-print" in xml
    assert "New Print" in xml


def test_update_feed_skips_duplicate(tmp_path, monkeypatch):
    p = _make_feed_xml(tmp_path)
    monkeypatch.setattr("arttools.site_updater.FEED_XML", p)
    result = update_feed("existing", "Existing", "story")
    assert result is False


# ── CLI dry-run test ──────────────────────────────────────────────────────────

def test_cli_dry_run(tmp_path):
    """Dry run should produce output and exit cleanly without touching any files."""
    # Create a minimal PNG-like file (sips not called in dry-run)
    fake_png = tmp_path / "test.png"
    fake_png.write_bytes(b"\x89PNG\r\n\x1a\n")  # PNG magic bytes

    search = tmp_path / "search.json"
    search.write_text("[]")
    feed = tmp_path / "feed.xml"
    feed.write_text('<rss><channel>\n  <item><title>X</title><link>https://myerman.art/prints/x/</link></item>\n</channel></rss>')
    prints_dir = tmp_path / "prints"
    prints_dir.mkdir()

    with patch("arttools.publish_print.PRINTS_DIR", prints_dir), \
         patch("arttools.site_updater.SEARCH_JSON", search), \
         patch("arttools.site_updater.FEED_XML", feed), \
         patch("arttools.publish_print.generate_description", return_value=("A description.", ["tag"])):

        runner = CliRunner()
        result = runner.invoke(cli, [
            "--file", str(fake_png),
            "--title", "Test Print",
            "--sku", "TEST-1",
            "--size", "12x12",
            "--prompt", "a test prompt",
            "--dry-run",
        ])

    assert result.exit_code == 0, result.output
    assert "dry-run" in result.output.lower() or "DRY RUN" in result.output
    # No files should have been created in prints_dir
    assert not list(prints_dir.iterdir())
