# Changelog

## 1.1.3
- Fixed the updater: it had placeholder repo settings (YOUR_USERNAME/YOUR_REPO)
  and a wrong subdir, so "Check for updates" always failed with a connection
  error. Now points at the real repository, so self-update works.

## 1.1.2
- Fixed material assignment (0 assigned) for characters with indexed meshes
  like Teeth_0/1/2 collapsing the character prefix.

## 1.1.1
- Reliable startup shelf registration via scripts/python/ready.py.

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
