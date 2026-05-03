"""Tests for mood-board utilities."""
from pathlib import Path
from unittest.mock import patch, MagicMock

from arttools.mood_board import cli, _render_html, _search_images
from click.testing import CliRunner


SAMPLE_IMAGES = [
    {"url": "https://example.com/img1.jpg", "thumb": "https://example.com/t1.jpg",
     "title": "Wolf in Snow", "source": "https://example.com/page1", "width": 800, "height": 600},
    {"url": "https://example.com/img2.jpg", "thumb": "https://example.com/t2.jpg",
     "title": "Crow at Dusk", "source": "https://example.com/page2", "width": 1200, "height": 900},
]


def _mock_ddgs(results):
    mock = MagicMock()
    mock.__enter__ = lambda s: s
    mock.__exit__ = MagicMock(return_value=False)
    mock.images.return_value = results
    return mock


DDG_RESULTS = [
    {"image": "https://img.com/a.jpg", "thumbnail": "https://img.com/ta.jpg",
     "title": "Wolf", "url": "https://source.com/1", "width": 800, "height": 600},
    {"image": "https://img.com/b.jpg", "thumbnail": "https://img.com/tb.jpg",
     "title": "Crow", "url": "https://source.com/2", "width": 800, "height": 600},
]


# ── _render_html tests ─────��──────────────────────────────────────────────────

def test_render_html_contains_query():
    html = _render_html("stormy crow", SAMPLE_IMAGES)
    assert "stormy crow" in html


def test_render_html_contains_images():
    html = _render_html("test query", SAMPLE_IMAGES)
    assert "t1.jpg" in html
    assert "t2.jpg" in html


def test_render_html_links_to_source():
    html = _render_html("test query", SAMPLE_IMAGES)
    assert "https://example.com/page1" in html
    assert "https://example.com/page2" in html


def test_render_html_image_count_in_footer():
    html = _render_html("test", SAMPLE_IMAGES)
    assert "2 images" in html


def test_render_html_is_valid_html():
    html = _render_html("test", SAMPLE_IMAGES)
    assert html.startswith("<!DOCTYPE html>")
    assert "</html>" in html


# ── _search_images tests ──────────────────────────────────────────────────────

def test_search_images_returns_mapped_results():
    with patch("arttools.mood_board.DDGS", return_value=_mock_ddgs(DDG_RESULTS)):
        results = _search_images("wolf", 5, "moderate")
    assert len(results) == 2
    assert results[0]["title"] == "Wolf"
    assert results[0]["thumb"] == "https://img.com/ta.jpg"
    assert results[0]["source"] == "https://source.com/1"


def test_search_images_returns_empty_when_ddgs_none():
    with patch("arttools.mood_board.DDGS", None):
        results = _search_images("wolf", 5, "moderate")
    assert results == []


# ── CLI tests ─────────────────────────────────────────────────────────────────

def test_cli_saves_file(tmp_path):
    out = tmp_path / "board.html"
    with patch("arttools.mood_board.DDGS", return_value=_mock_ddgs(DDG_RESULTS)), \
         patch("arttools.mood_board.webbrowser.open"):
        result = CliRunner().invoke(cli, ["wolf in snow", "--output", str(out), "--no-open"])
    assert result.exit_code == 0, result.output
    assert out.exists()
    content = out.read_text()
    assert "wolf in snow" in content
    assert "Wolf" in content


def test_cli_no_results_exits(tmp_path):
    out = tmp_path / "board.html"
    with patch("arttools.mood_board.DDGS", return_value=_mock_ddgs([])):
        result = CliRunner().invoke(cli, ["nothing", "--output", str(out), "--no-open"])
    assert result.exit_code != 0


def test_cli_opens_browser_by_default(tmp_path):
    out = tmp_path / "board.html"
    with patch("arttools.mood_board.DDGS", return_value=_mock_ddgs(DDG_RESULTS)), \
         patch("arttools.mood_board.webbrowser.open") as mock_open:
        CliRunner().invoke(cli, ["wolf", "--output", str(out)])
    mock_open.assert_called_once()


def test_cli_no_open_skips_browser(tmp_path):
    out = tmp_path / "board.html"
    with patch("arttools.mood_board.DDGS", return_value=_mock_ddgs(DDG_RESULTS)), \
         patch("arttools.mood_board.webbrowser.open") as mock_open:
        CliRunner().invoke(cli, ["wolf", "--output", str(out), "--no-open"])
    mock_open.assert_not_called()


def test_cli_default_output_on_desktop(tmp_path):
    (tmp_path / "Desktop").mkdir()
    with patch("arttools.mood_board.DDGS", return_value=_mock_ddgs(DDG_RESULTS)), \
         patch("arttools.mood_board.webbrowser.open"), \
         patch("arttools.mood_board.Path.home", return_value=tmp_path):
        result = CliRunner().invoke(cli, ["wolf", "--no-open"])
    assert result.exit_code == 0, result.output
    html_files = list(tmp_path.glob("Desktop/moodboard-*.html"))
    assert len(html_files) == 1
