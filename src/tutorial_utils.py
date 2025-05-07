# src/tutorial_utils.py

import os
from PIL import Image, ImageDraw, ImageFont
import numpy as np

def create_mockup_image(title, filename, width=600, height=400):
    """
    Create a mockup image for the tutorial if it doesn't exist.
    
    Args:
        title: Text to display on the mockup
        filename: Path to save the image
        width: Image width
        height: Image height
    """
    # Check if file already exists
    if os.path.exists(filename):
        return
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    # Create a new image with a light gray background
    image = Image.new('RGB', (width, height), color=(240, 240, 240))
    draw = ImageDraw.Draw(image)
    
    # Draw a border
    draw.rectangle(
        [(0, 0), (width-1, height-1)],
        outline=(200, 200, 200),
        width=2
    )
    
    # Add some decorative elements
    for i in range(10):
        x = np.random.randint(50, width-50)
        y = np.random.randint(50, height-50)
        size = np.random.randint(30, 100)
        color = (
            np.random.randint(200, 240),
            np.random.randint(200, 240),
            np.random.randint(200, 240)
        )
        draw.rectangle([(x, y), (x+size, y+size)], fill=color)
    
    # Add the title text
    try:
        # Try to use a system font
        font = ImageFont.truetype("Arial", 24)
    except IOError:
        # Fall back to default font
        font = ImageFont.load_default()
    
    text_width, text_height = draw.textsize(title, font=font) if hasattr(draw, 'textsize') else (200, 30)
    position = ((width - text_width) // 2, (height - text_height) // 2)
    
    # Add shadow for better readability
    draw.text((position[0]+2, position[1]+2), title, font=font, fill=(50, 50, 50))
    draw.text(position, title, font=font, fill=(0, 0, 0))
    
    # Save the image
    image.save(filename)

def ensure_tutorial_mockups():
    """Ensure all tutorial mockup images exist"""
    mockups = [
        ("Video Upload Interface", "saves/upload_mockup.png"),
        ("Detection Mode Selection", "saves/detection_mode_mockup.png"),
        ("Analysis Results Display", "saves/results_mockup.png"),
        ("Video History View", "saves/history_mockup.png")
    ]
    
    for title, filename in mockups:
        create_mockup_image(title, filename)

if __name__ == "__main__":
    ensure_tutorial_mockups()