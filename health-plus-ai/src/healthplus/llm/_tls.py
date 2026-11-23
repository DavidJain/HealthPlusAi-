"""TLS trust bundle shared by every LLM adapter.

Lives in its own module so the OpenAI/OpenRouter adapters can use it
without importing claude_client — which would load the Anthropic SDK
(~6 s on a cold start) even when Claude is never used.
"""

from __future__ import annotations

import subprocess
import tempfile

import certifi

_CA_BUNDLE_PATH: str | None = None


def _get_ca_bundle() -> str:
    """Return a CA bundle path that includes certifi roots + macOS system keychain certs.

    The bundle is built once and cached for the process lifetime.  On non-macOS
    or when the `security` command is unavailable the plain certifi bundle is
    returned so the function is always safe to call.
    """
    global _CA_BUNDLE_PATH
    if _CA_BUNDLE_PATH is not None:
        return _CA_BUNDLE_PATH
    try:
        result = subprocess.run(
            ["security", "find-certificate", "-a", "-p", "/Library/Keychains/System.keychain"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        system_pem = result.stdout
    except Exception:
        _CA_BUNDLE_PATH = certifi.where()
        return _CA_BUNDLE_PATH

    if not system_pem.strip():
        _CA_BUNDLE_PATH = certifi.where()
        return _CA_BUNDLE_PATH

    with tempfile.NamedTemporaryFile(suffix=".pem", delete=False, mode="w") as tmp:
        with open(certifi.where()) as cf:
            tmp.write(cf.read())
        tmp.write(system_pem)
        _CA_BUNDLE_PATH = tmp.name

    logger.debug("CA bundle built: %s", _CA_BUNDLE_PATH)
    return _CA_BUNDLE_PATH
