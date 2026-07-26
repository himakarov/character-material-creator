# Changelog

## 1.1.1
- Reliable startup: shelf registration moved to scripts/python/ready.py with
  deferred execution, so the CGA Tools shelf appears on a clean launch without
  any manual step. (1.1.0 registered the shelf but didn't run automatically at
  startup.)

## 1.1.0
- Shared shelf: the tool registers its button into a single "CGA Tools" shelf
  instead of its own tab, added to the Build and Solaris shelf sets.
- The updater now also refreshes the package manifest in packages/.

## 1.0.3
- UI: proper update button styling; custom shelf icon.

## 1.0.2
- Support FBX-via-SOP imports (ancestry name resolution); ignore mesh_N names
  when computing the character prefix.

## 1.0.1
- Fixed assignment when subsets are named after a shader path.

## 1.0.0
- Initial release.
