"""Extract dominant color palettes from artwork images."""
import io
import urllib.request
from pathlib import Path
from PIL import Image

from .ai_writer import _client


def extract_colors(source: str | Path, n: int = 6) -> list[dict]:
    """
    Extract n dominant colors from an image file path or URL.
    Returns list of dicts: {hex, rgb, r, g, b, frequency}
    """
    img = _load_image(source)
    img = img.convert("RGB").resize((300, 300), Image.LANCZOS)

    # Quantize to n colors using median cut
    quantized = img.quantize(colors=n, method=Image.Quantize.MEDIANCUT)
    palette_rgb = quantized.getpalette()[:n * 3]

    # Count pixel frequency per palette index
    freq = {}
    for pixel in quantized.getdata():
        freq[pixel] = freq.get(pixel, 0) + 1

    total = sum(freq.values())
    colors = []
    for i in range(n):
        r, g, b = palette_rgb[i * 3], palette_rgb[i * 3 + 1], palette_rgb[i * 3 + 2]
        pct = round(freq.get(i, 0) / total * 100, 1)
        colors.append({
            "hex": f"#{r:02x}{g:02x}{b:02x}",
            "rgb": f"rgb({r}, {g}, {b})",
            "r": r, "g": g, "b": b,
            "frequency": pct,
        })

    # Sort by frequency descending
    colors.sort(key=lambda c: c["frequency"], reverse=True)
    return colors


def name_palette(colors: list[dict], context: str = "") -> dict:
    """
    Ask Claude to name each color evocatively and describe the overall palette mood.
    Returns {names: [...], mood: str, css_name: str}
    """
    hex_list = ", ".join(c["hex"] for c in colors)
    context_note = f" The artwork is described as: {context}" if context else ""

    prompt = (
        f"You are a color consultant for an Indigenous digital artist.{context_note}\n\n"
        f"These are the dominant colors extracted from one of his artworks: {hex_list}\n\n"
        "Respond with JSON only, no explanation:\n"
        "{\n"
        '  "names": ["evocative name for each color in order"],\n'
        '  "mood": "2-3 sentence description of the palette mood and feel",\n'
        '  "css_name": "a short CSS variable prefix, e.g. prairie-dusk or iron-sky"\n'
        "}"
    )

    import json
    msg = _client().messages.create(
        model="claude-haiku-4-5",
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = msg.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1].lstrip("json").strip()
    return json.loads(raw)


def _load_image(source: str | Path) -> Image.Image:
    src = str(source)
    if src.startswith("http://") or src.startswith("https://"):
        with urllib.request.urlopen(src, timeout=15) as resp:
            return Image.open(io.BytesIO(resp.read()))
    return Image.open(source)


def render_terminal(colors: list[dict], names: list[str] | None = None) -> str:
    """Render a color palette as an ANSI terminal string."""
    lines = []
    for i, c in enumerate(colors):
        r, g, b = c["r"], c["g"], c["b"]
        swatch = f"\033[48;2;{r};{g};{b}m        \033[0m"
        name = f"  {names[i]}" if names and i < len(names) else ""
        lines.append(f"  {swatch}  {c['hex']}  {c['frequency']:5.1f}%{name}")
    return "\n".join(lines)


def to_css(colors: list[dict], prefix: str, names: list[str] | None = None) -> str:
    """Render palette as CSS custom properties."""
    lines = [":root {"]
    for i, c in enumerate(colors):
        var_name = f"--{prefix}-{i + 1}"
        comment = f"  /* {names[i]} */" if names and i < len(names) else ""
        lines.append(f"  {var_name}: {c['hex']};{comment}")
    lines.append("}")
    return "\n".join(lines)
