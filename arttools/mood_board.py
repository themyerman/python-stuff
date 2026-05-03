"""mood-board CLI — search for images and render a visual HTML mood board."""
import json
import sys
import webbrowser
from datetime import date
from pathlib import Path

import click

try:
    from duckduckgo_search import DDGS
except ImportError:
    DDGS = None  # type: ignore[assignment]


_BOARD_CSS = """
* { margin: 0; padding: 0; box-sizing: border-box; }
body { background: #111; font-family: system-ui, sans-serif; color: #eee; padding: 2rem; }
h1 { font-size: 1.2rem; font-weight: 400; color: #888; margin-bottom: 1.5rem; letter-spacing: 0.05em; }
h1 span { color: #eee; font-weight: 600; }
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 8px;
}
.grid a { display: block; overflow: hidden; border-radius: 4px; background: #222; }
.grid img {
  width: 100%; height: 220px;
  object-fit: cover; display: block;
  transition: transform 0.2s ease;
}
.grid a:hover img { transform: scale(1.04); }
.meta { padding: 6px 8px 8px; font-size: 0.72rem; color: #666;
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
footer { margin-top: 2rem; font-size: 0.75rem; color: #444; }
"""


@click.command()
@click.argument("query")
@click.option("--count", "-n", default=10, show_default=True,
              help="Number of images to fetch")
@click.option("--output", "-o", type=click.Path(), default=None,
              help="Path to save the HTML file (default: ~/Desktop/moodboard-<date>.html)")
@click.option("--no-open", is_flag=True, default=False,
              help="Save the file but don't open it in the browser")
@click.option("--safe-search", default="moderate", show_default=True,
              type=click.Choice(["on", "moderate", "off"]),
              help="SafeSearch level")
def cli(query, count, output, no_open, safe_search):
    """Search for images and render a visual HTML mood board.

    Opens the result in your browser by default.

    Examples:\n
      mood-board "moody crow in a stormy sky"\n
      mood-board "Indigenous beadwork patterns" --count 15\n
      mood-board "wolf winter forest" --output ~/Desktop/wolf-ref.html\n
      mood-board "futurism space" --no-open --count 20
    """
    click.echo(f"\n  Searching for: {query}", err=True)

    images = _search_images(query, count, safe_search)

    if not images:
        click.echo("No images found. Try a different search term.", err=True)
        sys.exit(1)

    click.echo(f"  Found {len(images)} images. Building mood board...", err=True)

    html = _render_html(query, images)

    out_path = Path(output) if output else Path.home() / "Desktop" / f"moodboard-{date.today().isoformat()}.html"
    out_path.write_text(html, encoding="utf-8")
    click.echo(f"  Saved to {out_path}", err=True)

    if not no_open:
        webbrowser.open(out_path.as_uri())


def _search_images(query: str, count: int, safe_search: str) -> list[dict]:
    """Fetch image results via DuckDuckGo."""
    if DDGS is None:
        click.echo("Missing dependency: pip install duckduckgo-search", err=True)
        return []

    results = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.images(query, safesearch=safe_search, max_results=count):
                results.append({
                    "url":       r.get("image", ""),
                    "thumb":     r.get("thumbnail", r.get("image", "")),
                    "title":     r.get("title", ""),
                    "source":    r.get("url", ""),
                    "width":     r.get("width", ""),
                    "height":    r.get("height", ""),
                })
    except Exception as e:
        click.echo(f"Search error: {e}", err=True)

    return results


def _render_html(query: str, images: list[dict]) -> str:
    cards = []
    for img in images:
        title = img["title"].replace('"', "&quot;")
        source = img["source"].replace('"', "&quot;")
        thumb = img["thumb"].replace('"', "&quot;")
        cards.append(
            f'<a href="{source}" target="_blank" rel="noopener">'
            f'<img src="{thumb}" alt="{title}" loading="lazy">'
            f'<div class="meta">{title}</div>'
            f'</a>'
        )

    cards_html = "\n    ".join(cards)
    today = date.today().isoformat()

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Mood board — {query}</title>
  <style>{_BOARD_CSS}</style>
</head>
<body>
  <h1>Mood board &mdash; <span>{query}</span></h1>
  <div class="grid">
    {cards_html}
  </div>
  <footer>Generated {today} &middot; {len(images)} images &middot; via DuckDuckGo</footer>
</body>
</html>"""
