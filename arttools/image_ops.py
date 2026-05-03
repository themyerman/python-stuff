"""Image optimization using macOS sips — no dependencies required."""
import subprocess
import shutil
from pathlib import Path


def optimize_print(src: Path, dest_dir: Path, slug: str) -> dict[str, Path]:
    """
    Convert a source PNG into the three image variants needed for a print page.
    Returns a dict of {variant: output_path}.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)

    display = dest_dir / f"{slug}-display.jpg"
    thumb   = dest_dir / f"{slug}-thumb.jpg"
    hero    = dest_dir / f"{slug}-hero.jpg"

    # --- display: max 2400px wide, 85% quality ---
    _sips_convert(src, display, max_width=2400, quality=85)

    # --- thumb: 480x480 square crop from center ---
    _sips_square_thumb(src, thumb, size=480, quality=80)

    # --- hero: 1600x900 crop (16:9) for home page ---
    _sips_hero(src, hero, width=1600, height=900, quality=85)

    return {"display": display, "thumb": thumb, "hero": hero}


def _sips_convert(src: Path, dest: Path, max_width: int, quality: int) -> None:
    tmp = dest.with_suffix(".tmp.jpg")
    shutil.copy2(src, tmp)
    subprocess.run([
        "sips", "-s", "format", "jpeg",
        "-s", "formatOptions", str(quality),
        "--resampleWidth", str(max_width),
        str(tmp), "--out", str(dest),
    ], check=True, capture_output=True)
    tmp.unlink(missing_ok=True)


def _sips_square_thumb(src: Path, dest: Path, size: int, quality: int) -> None:
    """Crop to square from center, then resize."""
    tmp = dest.with_suffix(".tmp.png")
    shutil.copy2(src, tmp)

    # Get dimensions
    result = subprocess.run(
        ["sips", "-g", "pixelWidth", "-g", "pixelHeight", str(tmp)],
        check=True, capture_output=True, text=True,
    )
    w = h = 0
    for line in result.stdout.splitlines():
        if "pixelWidth" in line:
            w = int(line.split()[-1])
        if "pixelHeight" in line:
            h = int(line.split()[-1])

    side = min(w, h)
    offset_x = (w - side) // 2
    offset_y = (h - side) // 2

    # Crop to square
    subprocess.run([
        "sips", "--cropToHeightWidth", str(side), str(side),
        "--cropOffset", str(offset_y), str(offset_x),
        str(tmp), "--out", str(tmp),
    ], check=True, capture_output=True)

    # Convert + resize to final thumb
    subprocess.run([
        "sips", "-s", "format", "jpeg",
        "-s", "formatOptions", str(quality),
        "--resampleWidth", str(size),
        str(tmp), "--out", str(dest),
    ], check=True, capture_output=True)

    tmp.unlink(missing_ok=True)


def _sips_hero(src: Path, dest: Path, width: int, height: int, quality: int) -> None:
    """Crop to 16:9 from center for hero use."""
    tmp = dest.with_suffix(".tmp.png")
    shutil.copy2(src, tmp)

    result = subprocess.run(
        ["sips", "-g", "pixelWidth", "-g", "pixelHeight", str(tmp)],
        check=True, capture_output=True, text=True,
    )
    w = h = 0
    for line in result.stdout.splitlines():
        if "pixelWidth" in line:
            w = int(line.split()[-1])
        if "pixelHeight" in line:
            h = int(line.split()[-1])

    # Scale down to fit width, then crop height to 16:9
    scale = width / w
    scaled_h = int(h * scale)
    crop_h = min(height, scaled_h)
    offset_y = max(0, (scaled_h - crop_h) // 2)

    subprocess.run([
        "sips", "--resampleWidth", str(width), str(tmp), "--out", str(tmp),
    ], check=True, capture_output=True)

    subprocess.run([
        "sips", "--cropToHeightWidth", str(crop_h), str(width),
        "--cropOffset", str(offset_y), "0",
        str(tmp), "--out", str(tmp),
    ], check=True, capture_output=True)

    subprocess.run([
        "sips", "-s", "format", "jpeg",
        "-s", "formatOptions", str(quality),
        str(tmp), "--out", str(dest),
    ], check=True, capture_output=True)

    tmp.unlink(missing_ok=True)
