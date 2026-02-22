from pynput import mouse

def clicked_at(x,y,button,pressed):
    if pressed:
        print(f"{x},{y}")


with mouse.Listener(on_click=clicked_at) as listener:
    listener.join()


