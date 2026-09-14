import urllib.request
import json

GITHUB_REPO = "fahadkhan-91/concrete-mix-design-app"
CURRENT_VERSION = "4.0.0"


def check_for_update():
    """
    GitHub se latest release check karta hai. Agar naya version mile to
    (True, latest_version, release_url) return karta hai, warna (False, None, None).
    Network fail ho ya koi issue ho to bhi chup chap (False, None, None) return karta hai —
    app ko block nahi karna.
    """
    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
        req = urllib.request.Request(url, headers={"User-Agent": "ConcreteMixDesignApp"})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())

        latest_tag = data.get("tag_name", "").lstrip("v")
        release_url = data.get("html_url", "")

        if latest_tag and _is_newer(latest_tag, CURRENT_VERSION):
            return True, latest_tag, release_url

    except Exception:
        pass

    return False, None, None


def _is_newer(latest, current):
    # simple version comparison - "4.1.0" vs "4.0.0"
    try:
        latest_parts = [int(x) for x in latest.split(".")]
        current_parts = [int(x) for x in current.split(".")]
        return latest_parts > current_parts
    except ValueError:
        return False
