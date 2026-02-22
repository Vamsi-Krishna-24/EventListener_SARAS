from pystray import Icon, Menu, MenuItem
from PIL import Image, ImageDraw, ImageFont

def create_dot_with_transparent_s():
    size = 64
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))  # Transparent canvas
    draw = ImageDraw.Draw(image)

    # Draw solid blue circle
    padding = 4
    draw.ellipse(
        (padding, padding, size - padding, size - padding),
        fill=(66, 133, 244, 255)  # Blue fill
    )

    # Create transparent "S"
    font_size = 36
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        font = ImageFont.load_default()

    # Create text mask
    txt_mask = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(txt_mask)

    # Get text bounding box (more accurate than textsize)
    bbox = d.textbbox((0, 0), "S", font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    # Center the text
    text_x = (size - text_width) // 2
    text_y = (size - text_height) // 2

    d.text((text_x, text_y), "S", font=font, fill=255)

    # Make the "S" area transparent
    alpha = image.getchannel("A")
    alpha.paste(0, mask=txt_mask)
    image.putalpha(alpha)

    return image

# --- State toggle logic ---
is_active = False

def toggle(icon, item):
    global is_active
    is_active = not is_active
    print("Active:", is_active)

def quit(icon, item):
    icon.stop()

# --- Tray Icon Setup ---
icon = Icon("SARAS", create_dot_with_transparent_s(), menu=Menu(
    MenuItem("Toggle", toggle, checked=lambda item: is_active),
    MenuItem("Quit", quit)
))

icon.run()
