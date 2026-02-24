"""Optional: run comfy-env setup if available (e.g. for isolated sub-envs)."""

try:
    from comfy_env import setup_env

    setup_env()
except Exception:
    pass
