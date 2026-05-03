"""extract-palette CLI — extract dominant colors from an artwork image."""
import json
import sys
from pathlib import Path

import click

from .palette import extract_colors, name_palette, render_terminal, to_css


@click.command()
@click.argument("source")
@click.option("--colors", "-n", default=6, show_default=True, help="Number of colors to extract")
@click.option("--context", "-c", default="", help="Brief description of the artwork (improves AI naming)")
@click.option("--format", "-f", "fmt",
              type=click.Choice(["terminal", "css", "json"]), default="terminal",
              show_default=True, help="Output format")
@click.option("--no-ai", is_flag=True, help="Skip AI color naming (faster, no API call)")
@click.option("--output", "-o", type=click.Path(), default=None, help="Write output to file")
def cli(source, colors, context, fmt, no_ai, output):
    """Extract a dominant color palette from an image file or URL.

    SOURCE can be a local file path or an https:// URL.

    Examples:\n
      extract-palette blood-crow-display.jpg\n
      extract-palette blood-crow-display.jpg --format css --output palette.css\n
      extract-palette https://myerman.art/prints/blood-crow/blood-crow-display.jpg -c "a crow, blood red accents"
    """
    click.echo(f"\n  Extracting {colors} colors from {source}...", err=True)

    try:
        palette = extract_colors(source, n=colors)
    except Exception as e:
        click.echo(f"Error loading image: {e}", err=True)
        sys.exit(1)

    names = None
    css_prefix = "palette"
    mood = None

    if not no_ai:
        click.echo("  Naming colors via Claude...", err=True)
        try:
            ai = name_palette(palette, context)
            names = ai.get("names")
            css_prefix = ai.get("css_name", "palette")
            mood = ai.get("mood")
        except Exception as e:
            click.echo(f"  (AI naming failed: {e} — showing hex only)", err=True)

    # Build output
    if fmt == "terminal":
        result = _terminal_output(palette, names, mood, css_prefix)
    elif fmt == "css":
        result = to_css(palette, css_prefix, names)
    elif fmt == "json":
        result = _json_output(palette, names, mood, css_prefix)

    if output:
        Path(output).write_text(result, encoding="utf-8")
        click.echo(f"  Saved to {output}", err=True)
    else:
        click.echo(result)


def _terminal_output(palette, names, mood, css_prefix):
    lines = [f"\n  Palette: --{css_prefix}-*\n"]
    lines.append(render_terminal(palette, names))
    if mood:
        lines.append(f"\n  {mood}")
    lines.append("")
    return "\n".join(lines)


def _json_output(palette, names, mood, css_prefix):
    out = {
        "css_prefix": css_prefix,
        "mood": mood,
        "colors": [
            {**c, "name": names[i] if names and i < len(names) else None}
            for i, c in enumerate(palette)
        ],
    }
    return json.dumps(out, indent=2)
