"""Tests for extract-palette utilities."""
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from PIL import Image

from arttools.palette import extract_colors, to_css, render_terminal
from arttools.extract_palette import cli
from click.testing import CliRunner


def _make_test_image(tmp_path: Path) -> Path:
    """Create a small test PNG with known colors."""
    img = Image.new("RGB", (100, 100), color=(200, 50, 50))  # solid red-ish
    # Add a blue region
    for x in range(50):
        for y in range(50):
            img.putpixel((x, y), (50, 50, 200))
    p = tmp_path / "test.png"
    img.save(p)
    return p


def test_extract_colors_returns_list(tmp_path):
    img_path = _make_test_image(tmp_path)
    colors = extract_colors(img_path, n=4)
    assert isinstance(colors, list)
    assert len(colors) == 4
    for c in colors:
        assert "hex" in c
        assert c["hex"].startswith("#")
        assert "frequency" in c
        assert 0 <= c["frequency"] <= 100


def test_extract_colors_hex_format(tmp_path):
    img_path = _make_test_image(tmp_path)
    colors = extract_colors(img_path, n=2)
    for c in colors:
        assert len(c["hex"]) == 7
        int(c["hex"][1:], 16)  # should not raise


def test_to_css_output(tmp_path):
    img_path = _make_test_image(tmp_path)
    colors = extract_colors(img_path, n=3)
    css = to_css(colors, "test-palette", names=["red", "blue", "white"])
    assert ":root {" in css
    assert "--test-palette-1" in css
    assert "red" in css


def test_render_terminal(tmp_path):
    img_path = _make_test_image(tmp_path)
    colors = extract_colors(img_path, n=3)
    output = render_terminal(colors, names=["Crimson", "Cobalt", "Snow"])
    assert "#" in output
    assert "Crimson" in output


def test_cli_no_ai_terminal(tmp_path):
    img_path = _make_test_image(tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, [str(img_path), "--no-ai", "--colors", "3"])
    assert result.exit_code == 0, result.output
    assert "#" in result.output


def test_cli_no_ai_json(tmp_path):
    img_path = _make_test_image(tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, [str(img_path), "--no-ai", "--format", "json", "--colors", "3"])
    assert result.exit_code == 0, result.output
    # Strip progress lines (start with whitespace), keep only the JSON block
    json_text = "\n".join(l for l in result.output.splitlines() if l.startswith("{") or l.startswith(" ") and not l.strip().startswith("Extracting"))
    # Simpler: find the JSON object by locating the first '{'
    start = result.output.find("{")
    data = json.loads(result.output[start:])
    assert "colors" in data
    assert len(data["colors"]) == 3


def test_cli_no_ai_css(tmp_path):
    img_path = _make_test_image(tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, [str(img_path), "--no-ai", "--format", "css", "--colors", "3"])
    assert result.exit_code == 0, result.output
    assert ":root {" in result.output


def test_cli_writes_file(tmp_path):
    img_path = _make_test_image(tmp_path)
    out_file = tmp_path / "palette.css"
    runner = CliRunner()
    result = runner.invoke(cli, [
        str(img_path), "--no-ai", "--format", "css", "--output", str(out_file)
    ])
    assert result.exit_code == 0
    assert out_file.exists()
    assert ":root {" in out_file.read_text()
