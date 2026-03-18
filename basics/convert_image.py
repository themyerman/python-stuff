import cv2

def create_line_art(image_path):
    """
    Converts an image to a line art sketch using the OpenCV library.

    Args:
        image_path (str): The path to the input image file.

    Returns:
        numpy.ndarray: The image converted to line art.
    """
    # Read the image
    img = cv2.imread(image_path)
    if img is None:
        print(f"Error: Could not read image from {image_path}")
        return None

    # 1. Convert to grayscale
    gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 2. Invert the grayscale image
    inverted_gray_img = 255 - gray_img

    # 3. Apply a Gaussian blur to the inverted image
    # A larger kernel (e.g., (21, 21)) creates a more pronounced sketch effect
    blurred_img = cv2.GaussianBlur(inverted_gray_img, (21, 21), 0)

    # 4. Dodge the blurred image to the original grayscale image
    # The cv2.divide function performs the sketch effect
    sketch_img = cv2.divide(gray_img, 255 - blurred_img, scale=256.0)

    return sketch_img

# --- Main execution ---
input_image = 'your_photo.jpg'  # Replace with your photo's path
output_image_path = 'line_art_sketch.png'

line_art_image = create_line_art(input_image)

if line_art_image is not None:
    # Display the original and sketch images (optional)
    cv2.imshow('Original Image', cv2.imread(input_image))
    cv2.imshow('Line Art Sketch', line_art_image)

    # Save the result
    cv2.imwrite(output_image_path, line_art_image)
    print(f"Line art image saved as {output_image_path}")

    # Wait indefinitely for a key press to close the windows
    cv2.waitKey(0)
    cv2.destroyAllWindows()

