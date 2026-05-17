"""image-describe — generate 2-3 sentence descriptions of images using local BLIP captioning.

Accepts a local directory of images or a web page URL (scrapes img tags).
Writes a markdown file with one entry per image: filename + three-sentence
description covering subject, color/light, and mood/style.

No external API calls — runs entirely locally.
Requires a venv at <project-root>/.venv-copy-audit with numpy<2, torch,
transformers, and Pillow installed. The CLI auto-detects and re-execs into it.
"""

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urljoin, urlparse

import click


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".tiff", ".tif", ".bmp"}

VENV_PYTHON = Path(__file__).parent.parent / ".venv-copy-audit" / "bin" / "python"

# Prompts for BLIP conditional captioning — each targets a different aspect
PROMPTS = [
    "",                                   # unconditional — subject/content
    "the colors and lighting in this image are",   # palette and light
    "the mood and style of this image is",         # feeling and aesthetic
]


def _reexec_in_venv():
    """Re-exec inside the copy-audit venv if not already there."""
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
        [str(VENV_PYTHON), "-m", "arttools.image_describe"] + sys.argv[1:],
        env=env,
        stdin=sys.stdin,
        stdout=sys.stdout,
        stderr=sys.stderr,
    )
    sys.exit(result.returncode)


def load_blip():
    """Load BLIP processor and model."""
    from transformers import BlipProcessor, BlipForConditionalGeneration

    click.echo("  Loading BLIP model…", err=True)
    processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
    model = BlipForConditionalGeneration.from_pretrained(
        "Salesforce/blip-image-captioning-base"
    )
    model.eval()
    return processor, model


def describe_image(image_path: Path, processor, model) -> str:
    """Return a 2-3 sentence description by running BLIP with multiple prompts."""
    import torch
    from PIL import Image

    image = Image.open(image_path).convert("RGB")
    sentences = []

    for prompt in PROMPTS:
        inputs = processor(image, text=prompt or None, return_tensors="pt")
        with torch.no_grad():
            out = model.generate(**inputs, max_new_tokens=80)
        caption = processor.decode(out[0], skip_special_tokens=True).strip()
        # Strip the prompt prefix from conditional captions
        if prompt and caption.lower().startswith(prompt.lower()):
            caption = caption[len(prompt):].strip()
        if caption:
            # Capitalise and ensure ends with a period
            caption = caption[0].upper() + caption[1:]
            if not caption.endswith((".", "!", "?")):
                caption += "."
            sentences.append(caption)

    return " ".join(sentences)


def collect_local_images(directory: Path) -> list[tuple[str, Path]]:
    """Return (name, path) pairs for all images in a directory (non-recursive)."""
    images = []
    for f in sorted(directory.iterdir()):
        if f.is_file() and f.suffix.lower() in IMAGE_EXTS:
            images.append((f.name, f))
    return images


def collect_url_images(url: str, tmp_dir: Path) -> list[tuple[str, Path]]:
    """Scrape img tags from a URL, download images, return (name, path) pairs."""
    try:
        import urllib.request
        from html.parser import HTMLParser
    except ImportError:
        click.echo("urllib / html.parser unavailable — cannot scrape URL.", err=True)
        sys.exit(1)

    class ImgScraper(HTMLParser):
        def __init__(self):
            super().__init__()
            self.srcs = []

        def handle_starttag(self, tag, attrs):
            if tag == "img":
                attrs_dict = dict(attrs)
                src = attrs_dict.get("src") or attrs_dict.get("data-src")
                if src:
                    self.srcs.append(src)

    click.echo(f"  Fetching {url}…", err=True)
    headers = {"User-Agent": "Mozilla/5.0 (image-describe/1.0)"}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        click.echo(f"  Failed to fetch URL: {e}", err=True)
        sys.exit(1)

    scraper = ImgScraper()
    scraper.feed(html)

    images = []
    seen = set()
    for i, src in enumerate(scraper.srcs):
        abs_src = urljoin(url, src)
        # Skip data URIs and duplicates
        if abs_src.startswith("data:") or abs_src in seen:
            continue
        seen.add(abs_src)

        # Derive a filename
        parsed = urlparse(abs_src)
        raw_name = Path(parsed.path).name or f"image-{i:03d}"
        # Strip query strings from extension check
        stem = Path(raw_name).stem
        suffix = Path(raw_name).suffix.split("?")[0].lower()
        if suffix not in IMAGE_EXTS:
            suffix = ".jpg"
        filename = re.sub(r"[^\w\-.]", "_", stem) + suffix
        dest = tmp_dir / filename

        try:
            req2 = urllib.request.Request(abs_src, headers=headers)
            with urllib.request.urlopen(req2, timeout=15) as resp2:
                dest.write_bytes(resp2.read())
            images.append((filename, dest))
            click.echo(f"  Downloaded {filename}", err=True)
        except Exception as e:
            click.echo(f"  Skip {abs_src}: {e}", err=True)

    return images


@click.command()
@click.argument("source")
@click.option(
    "--output", "-o",
    type=click.Path(path_type=Path),
    default=None,
    help="Output markdown file (default: image-descriptions.md next to source, "
         "or in current dir for URLs)",
)
@click.option(
    "--recursive", "-r",
    is_flag=True,
    default=False,
    help="Walk subdirectories (local directories only).",
)
def cli(source: str, output: Path | None, recursive: bool):
    """Generate 2-3 sentence descriptions of images using local BLIP captioning.

    SOURCE can be a local directory or a web page URL.

    For a directory, all images in it are described.
    For a URL, img tags are scraped and each image is downloaded and described.

    Examples:\n
      image-describe ~/Desktop/inspo/\n
      image-describe ~/Desktop/art-staging/ready/ --output ~/Desktop/descriptions.md\n
      image-describe https://example.com/gallery/ -o gallery.md\n
      image-describe ~/art/ --recursive
    """
    _reexec_in_venv()

    is_url = source.startswith("http://") or source.startswith("https://")
    tmp_dir_obj = None

    if is_url:
        tmp_dir_obj = tempfile.TemporaryDirectory()
        tmp_dir = Path(tmp_dir_obj.name)
        images = collect_url_images(source, tmp_dir)
        default_out = Path.cwd() / "image-descriptions.md"
    else:
        source_path = Path(source).expanduser().resolve()
        if not source_path.exists():
            click.echo(f"Directory not found: {source_path}", err=True)
            sys.exit(1)
        if recursive:
            images = []
            for f in sorted(source_path.rglob("*")):
                if f.is_file() and f.suffix.lower() in IMAGE_EXTS:
                    images.append((f.relative_to(source_path).as_posix(), f))
        else:
            images = collect_local_images(source_path)
        default_out = source_path / "image-descriptions.md"

    if not images:
        click.echo("No images found.", err=True)
        sys.exit(1)

    out_path = output or default_out
    click.echo(f"\n  {len(images)} images to describe\n", err=True)

    processor, model = load_blip()

    lines = [
        "# Image Descriptions\n",
        f"Source: `{source}`  \n",
        f"Images: {len(images)}\n",
        "---\n",
    ]

    for i, (name, img_path) in enumerate(images, 1):
        click.echo(f"  [{i}/{len(images)}] {name}…", err=True)
        try:
            description = describe_image(img_path, processor, model)
        except Exception as e:
            description = f"[error: {e}]"

        lines.append(f"## {name}\n")
        lines.append(f"{description}\n")
        lines.append("---\n")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    click.echo(f"\n  Written to {out_path}\n", err=True)

    if tmp_dir_obj:
        tmp_dir_obj.cleanup()
