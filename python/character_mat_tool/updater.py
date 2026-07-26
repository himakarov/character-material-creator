"""
updater.py - self-update from a public GitHub repo over HTTP.
No git, no third-party deps (standard library only).
"""

import os
import ssl
import shutil
import tempfile
import zipfile
import urllib.request

# ---------------------------------------------------------------------------
# REPOSITORY SETTINGS - CHANGE TO YOUR OWN
# ---------------------------------------------------------------------------
GITHUB_USER = "himakarov"
GITHUB_REPO = "character-material-creator"
GITHUB_BRANCH = "main"
# subfolder inside the repo that holds the package (empty = repo root)
REPO_SUBDIR = ""
# ---------------------------------------------------------------------------

RAW_BASE = "https://raw.githubusercontent.com/%s/%s/%s" % (
    GITHUB_USER, GITHUB_REPO, GITHUB_BRANCH)
ZIP_URL = "https://github.com/%s/%s/archive/refs/heads/%s.zip" % (
    GITHUB_USER, GITHUB_REPO, GITHUB_BRANCH)


def _tool_root():
    """Local package folder (where VERSION lives)."""
    # updater.py -> character_mat_tool -> python -> CharacterMaterialTool
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(here, "..", ".."))


def local_version():
    try:
        with open(os.path.join(_tool_root(), "VERSION")) as f:
            return f.read().strip()
    except Exception:
        return "0.0.0"


def _http_get(url, timeout=15):
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, headers={"User-Agent": "CharMatTool"})
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
        return r.read()


def _remote_file(relpath):
    """Fetch a text file from the repo. Returns None on network error."""
    sub = (REPO_SUBDIR + "/") if REPO_SUBDIR else ""
    url = "%s/%s%s" % (RAW_BASE, sub, relpath)
    try:
        return _http_get(url).decode("utf-8")
    except Exception:
        return None


def remote_version():
    """Version on GitHub. None on network error."""
    txt = _remote_file("VERSION")
    return txt.strip() if txt is not None else None


def remote_changelog():
    """CHANGELOG.md contents from GitHub, or None."""
    return _remote_file("CHANGELOG.md")


def _ver_tuple(v):
    parts = []
    for x in str(v).split("."):
        try:
            parts.append(int(x))
        except ValueError:
            parts.append(0)
    return tuple(parts)


def has_update():
    """(update_available, local, remote). remote=None on network error."""
    loc = local_version()
    rem = remote_version()
    if rem is None:
        return False, loc, None
    return _ver_tuple(rem) > _ver_tuple(loc), loc, rem


def update():
    """Download repo ZIP, extract the package subfolder over the local one.
    Returns (success, message)."""
    root = _tool_root()
    try:
        data = _http_get(ZIP_URL, timeout=60)
    except Exception as e:
        return False, "Download failed: %s" % e

    tmp = tempfile.mkdtemp(prefix="charmat_upd_")
    try:
        zpath = os.path.join(tmp, "repo.zip")
        with open(zpath, "wb") as f:
            f.write(data)

        with zipfile.ZipFile(zpath) as z:
            z.extractall(tmp)

        # archive contains a folder like REPO-branch/
        entries = [d for d in os.listdir(tmp)
                   if os.path.isdir(os.path.join(tmp, d)) and d != "__MACOSX"]
        if not entries:
            return False, "Empty archive"
        extracted = os.path.join(tmp, entries[0])
        src = os.path.join(extracted, REPO_SUBDIR) if REPO_SUBDIR else extracted
        if not os.path.isdir(src):
            return False, "Package folder '%s' not found in archive" % REPO_SUBDIR

        _copy_over(src, root)

        # also update the package manifest, which lives OUTSIDE the tool folder
        # (directly in packages/). The updater's file-copy above can't reach it,
        # so handle it explicitly.
        _update_manifest(root)

        return True, "Updated to %s. Restart Houdini to apply." % local_version()
    except Exception as e:
        return False, "Extract error: %s" % e
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _update_manifest(tool_root):
    """Refresh character_mat_tool.json in packages/ from the repo copy.

    tool_root is .../packages/CharacterMaterialTool ; the manifest sits one
    level up at .../packages/character_mat_tool.json. The repo stores the
    manifest at its root, so fetch it raw and, if changed, rewrite the local
    one (adjusting CHARMAT_ROOT so it still points at the tool folder)."""
    try:
        packages_dir = os.path.dirname(tool_root)
        local_manifest = os.path.join(packages_dir, "character_mat_tool.json")
        if not os.path.isfile(local_manifest):
            return  # unusual layout; leave it alone

        remote = _remote_file("character_mat_tool.json")
        if not remote:
            return

        with open(local_manifest, "r", encoding="utf-8") as f:
            current = f.read()
        if current.strip() == remote.strip():
            return  # already up to date

        with open(local_manifest, "w", encoding="utf-8") as f:
            f.write(remote)
    except Exception:
        # manifest refresh is best-effort; never fail the whole update over it
        pass


def _copy_over(src, dst):
    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.isdir(s):
            if not os.path.isdir(d):
                os.makedirs(d)
            _copy_over(s, d)
        else:
            shutil.copy2(s, d)
