# Changelog

## 1.1.2
- Fixed material assignment failing (0 assigned) when a character has indexed
  meshes like Runner_A_Teeth_0/1/2. The trailing _N index no longer collapses
  the character prefix, and the prefix falls back to the material prefix if
  detection is weak.

## 1.1.1
- Reliable startup: shelf registration via scripts/python/ready.py.

## 1.1.0
- Shared "CGA Tools" shelf; updater refreshes the manifest.

## 1.0.3
- UI: update button styling; custom shelf icon.

## 1.0.2
- Support FBX-via-SOP imports (ancestry name resolution).

## 1.0.1
- Fixed assignment for shader-path-named subsets.

## 1.0.0
- Initial release.
