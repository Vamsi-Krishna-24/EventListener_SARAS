from pystray import Icon, Menu, MenuItem
from PIL import Image, ImageDraw

def create_big_dot_icon():
    size = 64  # Icon canvas size
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))  # Transparent background
    draw = ImageDraw.Draw(image)

    # Maximize dot size, leaving a tiny margin
    padding = 4
    draw.ellipse(
        (padding, padding, size - padding, size - padding),
        fill=(66, 133, 244, 255)  # Bright blue
    )

    return image

# --- Toggle logic ---
is_active = False

def toggle_action(icon, item):
    global is_active
    is_active = not is_active
    print(f"Status: {'ON' if is_active else 'OFF'}")

def quit_app(icon, item):
    icon.stop()

# --- Tray icon ---
icon = Icon("SARAS", create_big_dot_icon(), menu=Menu(
    MenuItem("Active", toggle_action, checked=lambda item: is_active),
    MenuItem("Quit", quit_app)
))

icon.run()
