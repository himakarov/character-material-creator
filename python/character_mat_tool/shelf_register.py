"""
shelf_register.py - registers this tool's button into the shared "CGA Tools"
shelf, creating the shelf if it doesn't exist yet. Idempotent: safe to run on
every Houdini startup. Multiple tools can share the same shelf without clobbering
each other.

This same pattern can be copied into any future CGA tool package - just change
TOOL_NAME, TOOL_LABEL, TOOL_SCRIPT and TOOL_ICON.
"""

import hou

# --- shared shelf identity (keep identical across all CGA tools) ---
SHELF_NAME = "cga_tools"
SHELF_LABEL = "CGA Tools"

# --- this tool's button ---
TOOL_NAME = "cga_charmat_build"
TOOL_LABEL = "Char Mat"
TOOL_ICON = "char_mat"   # resolved via HOUDINI_UI_ICON_PATH
TOOL_HELP = "Character Material Tool - auto-build Karma materials for characters."
TOOL_SCRIPT = "from character_mat_tool import ui\nui.show()"


def _get_shelf():
    """Find the shared shelf, or None."""
    return hou.shelves.shelves().get(SHELF_NAME)


def _get_or_create_shelf():
    shelf = _get_shelf()
    if shelf is None:
        # file_path="" => stored in the user's default shelf location
        shelf = hou.shelves.newShelf(
            file_path="", name=SHELF_NAME, label=SHELF_LABEL)
    return shelf


def _get_or_create_tool():
    tool = hou.shelves.tools().get(TOOL_NAME)
    if tool is None:
        tool = hou.shelves.newTool(
            file_path="",
            name=TOOL_NAME,
            label=TOOL_LABEL,
            script=TOOL_SCRIPT,
            language=hou.scriptLanguage.Python,
            icon=TOOL_ICON,
            help=TOOL_HELP,
        )
    else:
        # keep it up to date on each launch
        try:
            tool.setLabel(TOOL_LABEL)
            tool.setScript(TOOL_SCRIPT)
            tool.setIcon(TOOL_ICON)
        except Exception:
            pass
    return tool


def register():
    """Ensure the shared shelf exists and contains this tool's button."""
    try:
        hou.shelves.beginChangeBlock()
    except Exception:
        pass
    try:
        shelf = _get_or_create_shelf()
        tool = _get_or_create_tool()

        # add the tool to the shelf if not already present
        existing = list(shelf.tools())
        if tool not in existing:
            shelf.setTools(existing + [tool])

        # make sure the shelf is visible in a shelf set
        _ensure_in_shelf_set(shelf)
    except Exception as e:
        # never break Houdini startup because of shelf registration
        try:
            import sys
            sys.stderr.write("CGA shelf register failed: %s\n" % e)
        except Exception:
            pass
    finally:
        try:
            hou.shelves.endChangeBlock()
        except Exception:
            pass


def _ensure_in_shelf_set(shelf):
    """Add the shelf to every user shelf set so it shows up regardless of the
    current desktop (classic Build uses shelf_set_1, Solaris uses solaris_1/2/3,
    etc.). Skips dead references defensively — Houdini can leave stale shelf
    objects around, and touching them raises ObjectWasDeleted."""
    try:
        sets = hou.shelves.shelfSets()
    except Exception:
        return
    if not sets:
        return

    shelf_name = None
    try:
        shelf_name = shelf.name()
    except Exception:
        return

    # Only add to the main desktop shelf sets. Adding to every set (hairtools,
    # TOPs, terrain, etc.) would clutter specialized desktops. These cover the
    # classic Build desktop (shelf_set_1/2) and Solaris (solaris_1/2/3).
    target_sets = ("shelf_set_1", "shelf_set_2",
                   "solaris_1", "solaris_2", "solaris_3")

    for set_name in target_sets:
        s = sets.get(set_name)
        if s is None:
            continue
        try:
            live = []
            already = False
            for sh in s.shelves():
                try:
                    nm = sh.name()
                except Exception:
                    continue  # dead ref -> drop it
                live.append(sh)
                if nm == shelf_name:
                    already = True
            if not already:
                s.setShelves(live + [shelf])
        except Exception:
            continue
