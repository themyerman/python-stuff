"""Organize files in a directory into type-based subfolders."""

import os
from pathlib import Path

SUBDIRECTORIES = {
    "DOCUMENTS": [".pdf", ".rtf", ".txt"],
    "AUDIO": [".m4a", ".m4b", ".mp3"],
    "VIDEOS": [".mov", ".avi", ".mp4"],
    "IMAGES": [".jpg", ".jpeg", ".png"],
}


def pick_directory(suffix):
    """Return a folder name based on a file extension."""
    for category, suffixes in SUBDIRECTORIES.items():
        if suffix in suffixes:
            return category
    return "MISC"


def organize_directory(base_path="."):
    """Move files from base_path into categorized subdirectories."""
    base = Path(base_path)
    for item in os.scandir(base):
        item_path = Path(item.path)
        if item.is_dir() or item_path.name.startswith("."):
            continue
        target_dir = base / pick_directory(item_path.suffix.lower())
        target_dir.mkdir(exist_ok=True)
        item_path.rename(target_dir / item_path.name)


if __name__ == "__main__":
    organize_directory()