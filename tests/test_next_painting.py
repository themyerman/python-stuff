"""Tests for next-painting utilities."""
import json
from pathlib import Path
from unittest.mock import patch, MagicMock, Mock
from PIL import Image

from arttools.next_painting import cli, _scan_directory, _fetch_from_url
from click.testing import CliRunner


def _make_image_dir(tmp_path: Path, n: int = 5) -> Path:
    d = tmp_path / "paintings"
    d.mkdir()
    colors = [(200, 50, 50), (50, 200, 50), (50, 50, 200), (200, 200, 50), (200, 50, 200)]
    for i in range(n):
        img = Image.new("RGB", (100, 100), color=colors[i % len(colors)])
        img.save(d / f"painting-{i + 1}.png")
    return d


def test_scan_directory_returns_metadata(tmp_path):
    d = _make_image_dir(tmp_path, n=3)
    results = _scan_directory(d, max_count=10)
    assert len(results) == 3
    for r in results:
        assert "filename" in r
        assert "aspect" in r


def test_scan_directory_samples_when_over_limit(tmp_path):
    d = _make_image_dir(tmp_path, n=20)
    results = _scan_directory(d, max_count=5)
    assert len(results) <= 5


def test_scan_directory_missing(tmp_path):
    results = _scan_directory(tmp_path / "nonexistent", max_count=5)
    assert results == []


def test_fetch_from_url_uses_search_json():
    """When /search.json is available, use it."""
    catalog = [
        {"slug": "wolf-moon", "title": "Wolf Moon", "tags": ["wildlife"], "story": "A wolf howls."},
    ]
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(catalog).encode()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_resp):
        results = _fetch_from_url("https://example.com", max_count=10)

    assert len(results) == 1
    assert results[0]["title"] == "Wolf Moon"


def test_fetch_from_url_falls_back_to_scraping():
    """When /search.json fails, scrape <img> tags from the page."""
    html = (
        b'<html><body>'
        b'<img src="/art/wolf-moon.jpg" alt="Wolf Moon">'
        b'<img src="/art/bear-spirit.jpg" alt="Bear Spirit">'
        b'</body></html>'
    )

    def fake_urlopen(req, timeout=10):
        mock_resp = MagicMock()
        mock_resp.read.return_value = html
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        # Raise on search.json, succeed on page
        if hasattr(req, "full_url") and "search.json" in req.full_url:
            raise Exception("404")
        if isinstance(req, str) and "search.json" in req:
            raise Exception("404")
        return mock_resp

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        results = _fetch_from_url("https://example.com", max_count=10)

    assert len(results) == 2
    assert results[0]["title"] == "Wolf Moon"
    assert results[1]["title"] == "Bear Spirit"


def test_fetch_from_url_skips_icons():
    """Icon/logo images should be filtered out during scraping."""
    html = (
        b'<html><body>'
        b'<img src="/img/logo.png" alt="Logo">'
        b'<img src="/art/painting.jpg" alt="My Painting">'
        b'</body></html>'
    )

    def fake_urlopen(req, timeout=10):
        mock_resp = MagicMock()
        mock_resp.read.return_value = html
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        if isinstance(req, str) and "search.json" in req:
            raise Exception("404")
        return mock_resp

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        results = _fetch_from_url("https://example.com", max_count=10)

    assert all("logo" not in r["filename"].lower() for r in results)


def test_cli_with_mocked_ai(tmp_path):
    d = _make_image_dir(tmp_path, n=3)
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Here are 5 suggestions:\n1. Paint a wolf.")]

    with patch("arttools.next_painting._client") as mock_client:
        mock_client.return_value.messages.create.return_value = mock_response
        runner = CliRunner()
        result = runner.invoke(cli, [str(d), "--count", "3"])

    assert result.exit_code == 0, result.output
    assert "wolf" in result.output or "suggestion" in result.output.lower()


def test_cli_style_options(tmp_path):
    d = _make_image_dir(tmp_path, n=3)
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Gaps analysis: you need more wildlife.")]

    with patch("arttools.next_painting._client") as mock_client:
        mock_client.return_value.messages.create.return_value = mock_response
        runner = CliRunner()
        result = runner.invoke(cli, [str(d), "--style", "gaps"])

    assert result.exit_code == 0
