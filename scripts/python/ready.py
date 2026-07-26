"""
ready.py - runs on Houdini startup once the UI is available (Houdini looks for
scripts/python/ready.py on the HOUDINI_PATH). We defer the actual shelf
registration until the event loop is idle, because shelf objects aren't safe
to touch during early startup.
"""

def _register_cga_shelf():
    try:
        from character_mat_tool import shelf_register
        shelf_register.register()
    except Exception as e:
        import sys
        sys.stderr.write("CGA shelf registration failed: %s\n" % e)


try:
    import hdefereval
    hdefereval.executeDeferred(_register_cga_shelf)
except Exception:
    # no UI / hdefereval unavailable (e.g. hython) -> run directly
    _register_cga_shelf()
