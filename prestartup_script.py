"""
Optional: run comfy-env setup if available before the plugin is loaded.

ComfyUI invokes this script before loading the custom node package. If comfy_env
is not installed (ImportError), we do nothing. If setup_env() raises any other
exception, we log a warning so environment setup failures are visible.
"""

import logging

logger = logging.getLogger(__name__)

try:
    from comfy_env import setup_env

    setup_env()
except ImportError:
    pass
except Exception as e:
    logger.warning("ComfyUI-UML: comfy_env.setup_env() failed: %s", e)
