from PIL import Image, ImageDraw, ImageFont
import random
import io

def generate_captcha(length=5):
    # Characters for captcha
    chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    text = "".join(random.choice(chars) for _ in range(length))

    # Create an image
    image = Image.new('RGB', (150, 50), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)

    # Use a basic font
    try:
        font = ImageFont.truetype("arial.ttf", 36)
    except:
        font = ImageFont.load_default()

    draw.text((10,5), text, font=font, fill=(0,0,0))

    # Save to BytesIO
    image_bytes = io.BytesIO()
    image.save(image_bytes, format='PNG')
    image_bytes.seek(0)

    return text, image_bytes