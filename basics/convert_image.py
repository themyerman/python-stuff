"""Convert a photo into sketch-like line art."""

import argparse
from pathlib import Path

import cv2


def create_line_art(image_path):
    """Convert a source image to a line-art sketch image."""
    img = cv2.imread(str(image_path))
    if img is None:
        raise ValueError(f"Could not read image from {image_path}")

    gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    inverted_gray_img = 255 - gray_img
    blurred_img = cv2.GaussianBlur(inverted_gray_img, (21, 21), 0)
    return cv2.divide(gray_img, 255 - blurred_img, scale=256.0)


def parse_args():
    """Parse command line options."""
    parser = argparse.ArgumentParser(description="Generate line-art image from photo.")
    parser.add_argument("input_image", help="Path to input image")
    parser.add_argument(
        "-o",
        "--output-image",
        default="line_art_sketch.png",
        help="Path to output image file",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Show original and converted image windows",
    )
    return parser.parse_args()


def main():
    """Generate and optionally show the line-art image."""
    args = parse_args()
    input_path = Path(args.input_image)
    output_path = Path(args.output_image)
    line_art_image = create_line_art(input_path)
    cv2.imwrite(str(output_path), line_art_image)
    print(f"Line art image saved as {output_path}")

    if args.show:
        cv2.imshow("Original Image", cv2.imread(str(input_path)))
        cv2.imshow("Line Art Sketch", line_art_image)
        cv2.waitKey(0)
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()

