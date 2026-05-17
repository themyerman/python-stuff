"""copy-audit — compare print page copy against actual images using BLIP captioning.

Walks every print directory in the myerman.art site, generates a one-sentence
visual description of each display image using a local BLIP model, extracts the
current piece-story copy from index.html, and writes a markdown report so the
copy can be reviewed against what's actually in each image.

No external API calls — runs entirely locally.
Requires a venv at <project-root>/.venv-copy-audit with numpy<2, torch,
transformers, and Pillow installed. The CLI auto-detects and re-execs into it.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

import click


SKIP_DIRS = {
    "abstracts", "best-sellers", "cayuga-language", "futurism",
    "land-sky", "medicine-story", "wildlife",
    # Cayuga Language Series individual pieces — not for sale, copy is final
    "cayuga-hello-how-are-you", "cayuga-i-am-six-nations", "cayuga-i-love-you",
    "cayuga-i-understand", "cayuga-lets-eat", "cayuga-we-are-all-warriors",
    "cayuga-what-a-beautiful-day", "cayuga-what-is-your-name",
}

PIECE_STORY_RE = re.compile(r'<p class="piece-story">(.*?)</p>', re.DOTALL)

VENV_PYTHON = Path(__file__).parent.parent / ".venv-copy-audit" / "bin" / "python"


def _reexec_in_venv():
    """Re-exec this CLI inside the copy-audit venv if not already there."""
    if os.environ.get("COPY_AUDIT_VENV") == "1":
        return
    if not VENV_PYTHON.exists():
        click.echo(
            f"Venv not found at {VENV_PYTHON}\n"
            "Set it up with:\n"
            "  python3 -m venv .venv-copy-audit\n"
            "  .venv-copy-audit/bin/pip install 'numpy<2' torch transformers Pillow click",
            err=True,
        )
        sys.exit(1)
    env = {**os.environ, "COPY_AUDIT_VENV": "1"}
    result = subprocess.run(
        [str(VENV_PYTHON), "-m", "arttools.copy_audit"] + sys.argv[1:],
        env=env,
        stdin=sys.stdin,
        stdout=sys.stdout,
        stderr=sys.stderr,
    )
    sys.exit(result.returncode)


def load_blip():
    """Load BLIP processor and model."""
    from transformers import BlipProcessor, BlipForConditionalGeneration

    click.echo("  Loading BLIP model (first run downloads ~900 MB)…", err=True)
    processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
    model = BlipForConditionalGeneration.from_pretrained(
        "Salesforce/blip-image-captioning-base"
    )
    model.eval()
    return processor, model


def describe_image(image_path: Path, processor, model) -> str:
    """Return a one-sentence BLIP caption for the image."""
    import torch
    from PIL import Image

    image = Image.open(image_path).convert("RGB")
    inputs = processor(image, return_tensors="pt")
    with torch.no_grad():
        out = model.generate(**inputs, max_new_tokens=60)
    return processor.decode(out[0], skip_special_tokens=True).strip()


def extract_piece_story(html_path: Path) -> str | None:
    """Pull the piece-story paragraph text from an index.html file."""
    text = html_path.read_text(encoding="utf-8")
    match = PIECE_STORY_RE.search(text)
    if not match:
        return None
    raw = match.group(1)
    return re.sub(r"<[^>]+>", "", raw).strip()


def find_display_image(print_dir: Path) -> Path | None:
    """Find the display image for a print directory."""
    slug = print_dir.name
    for ext in (".jpg", ".jpeg", ".png"):
        candidate = print_dir / f"{slug}-display{ext}"
        if candidate.exists():
            return candidate
    # Fallback: first non-thumb, non-hero jpg
    for f in sorted(print_dir.glob("*.jpg")):
        if "thumb" not in f.name and "hero" not in f.name:
            return f
    return None


@click.command()
@click.argument(
    "site_root",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default="/Users/myerman/Desktop/code/myerman-art",
)
@click.option(
    "--output", "-o",
    type=click.Path(path_type=Path),
    default=None,
    help="Output markdown file (default: <site_root>/copy-audit.md)",
)
@click.option(
    "--only", "-s",
    multiple=True,
    help="Only audit these slugs (repeatable). Useful for spot-checks.",
)
def cli(site_root: Path, output: Path | None, only: tuple[str, ...]):
    """Audit print page copy against actual images using local BLIP captioning.

    Generates copy-audit.md in the site root (or --output).
    Each entry shows the BLIP image caption alongside the current piece-story
    so mismatches are easy to spot.

    Examples:\n
      copy-audit\n
      copy-audit ~/Desktop/code/myerman-art\n
      copy-audit --output ~/Desktop/audit.md\n
      copy-audit --only blood-crow --only dawn-eagle
    """
    _reexec_in_venv()

    prints_dir = site_root / "prints"
    if not prints_dir.exists():
        click.echo(f"No prints/ directory found under {site_root}", err=True)
        sys.exit(1)

    out_path = output or (site_root / "copy-audit.md")

    dirs = sorted(
        d for d in prints_dir.iterdir()
        if d.is_dir() and d.name not in SKIP_DIRS
    )
    if only:
        dirs = [d for d in dirs if d.name in only]

    eligible = []
    for d in dirs:
        img = find_display_image(d)
        html = d / "index.html"
        if not img or not html.exists():
            continue
        story = extract_piece_story(html)
        if not story:
            continue
        eligible.append((d.name, img, story))

    if not eligible:
        click.echo("No eligible print directories found.", err=True)
        sys.exit(1)

    click.echo(f"\n  {len(eligible)} prints to audit\n", err=True)

    processor, model = load_blip()

    lines = [
        "# Copy Audit — myerman.art\n",
        f"Generated against {len(eligible)} prints.\n",
        "---\n",
    ]

    for i, (slug, img_path, story) in enumerate(eligible, 1):
        click.echo(f"  [{i}/{len(eligible)}] {slug}…", err=True)
        try:
            caption = describe_image(img_path, processor, model)
        except Exception as e:
            caption = f"[error: {e}]"

        lines.append(f"## {slug}\n")
        lines.append(f"**Image:** {caption}\n")
        lines.append(f"**Copy:** {story}\n")
        lines.append("---\n")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    click.echo(f"\n  Report written to {out_path}\n", err=True)
