"""Install dependencies for ComfyUI-UML (ComFyUML) diagram nodes."""

import subprocess
import sys


def install():
    try:
        from comfy_env import install as comfy_env_install

        comfy_env_install()
        return
    except ImportError:
        pass

    import os

    req = os.path.join(os.path.dirname(os.path.abspath(__file__)), "requirements.txt")
    if os.path.isfile(req):
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", req])


if __name__ == "__main__":
    install()
