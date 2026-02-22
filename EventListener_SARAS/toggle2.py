from pystray import Icon, Menu, MenuItem
from PIL import Image, ImageDraw
from main2 import ListenerController  # Changed to main2
import threading

# --- Load icon ---
def create_big_dot_icon():
    size = 64
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    padding = 4
    draw.ellipse((padding, padding, size - padding, size - padding), fill=(66, 133, 244, 255))
    return image

# --- Control ---
is_active = False
listener_controller = ListenerController()

def toggle_action(icon, item):
    global is_active
    is_active = not is_active
    print(f"Status: {'ON' if is_active else 'OFF'}")

    if is_active:
        threading.Thread(target=listener_controller.start, daemon=True).start()
    else:
        listener_controller.stop()

def quit_app(icon, item):
    print("Exiting app...")
    listener_controller.stop()
    icon.stop()

icon = Icon("SARAS", create_big_dot_icon(), menu=Menu(
    MenuItem("Active", toggle_action, checked=lambda item: is_active),
    MenuItem("Quit", quit_app)
))

icon.run()
