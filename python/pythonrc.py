"""
pythonrc.py - runs on Houdini startup (this dir is on PYTHONPATH via the
package manifest). Registers the tool into the shared CGA Tools shelf.
"""
try:
    from character_mat_tool import shelf_register
    shelf_register.register()
except Exception as e:
    import sys
    sys.stderr.write("CGA Char Mat: shelf registration skipped: %s\n" % e)
