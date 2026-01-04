__version__ = "1.0.0"

import webview
import json
import os


# Get the directory where this script is located
base_path = os.path.dirname(os.path.abspath(__file__))

# Build path to assets folder
assets_path = os.path.join(base_path, "assets")
html_path = os.path.join(assets_path, "empty.html")


class Api:
    def save(self, payload):
        print("Save called from JS")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(payload["text"])
        return "Save successful"


# Debug: List what's in the base directory
if os.path.exists(base_path):
    print(f"Contents of base path: {os.listdir(base_path)}")
    if os.path.exists(assets_path):
        print(f"Contents of assets: {os.listdir(assets_path)}")

window = webview.create_window("Tiddlywiki App", html_path, js_api=Api())
webview.start(window, ssl=True, debug=True)
