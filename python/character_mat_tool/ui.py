"""
ui.py - Qt dialog for the tool. Entry point: show().
"""

import hou

try:
    from PySide6 import QtWidgets, QtCore
except ImportError:
    from PySide2 import QtWidgets, QtCore

from character_mat_tool import core, updater

# Minimum Houdini version this tool was tested against (major, minor).
MIN_HOU_VERSION = (20, 0)


def _hou_version_ok():
    try:
        v = hou.applicationVersion()  # (major, minor, build)
        return v[:2] >= MIN_HOU_VERSION
    except Exception:
        return True


class CharMatDialog(QtWidgets.QDialog):

    def __init__(self, parent=None):
        super(CharMatDialog, self).__init__(parent)
        self.setWindowTitle("Character Material Tool  v%s" % updater.local_version())
        self.setMinimumWidth(540)
        self._build_ui()
        self._load_settings()
        self._version_warning()
        # silent background update check on open
        QtCore.QTimer.singleShot(200, self._check_update_silent)

    def _build_ui(self):
        lay = QtWidgets.QVBoxLayout(self)

        form = QtWidgets.QFormLayout()
        h = QtWidgets.QHBoxLayout()
        self.folder_edit = QtWidgets.QLineEdit()
        b = QtWidgets.QPushButton("Browse...")
        b.clicked.connect(self._pick_folder)
        h.addWidget(self.folder_edit)
        h.addWidget(b)
        form.addRow("Materials folder:", h)
        lay.addLayout(form)

        self.assign_cb = QtWidgets.QCheckBox("Assign materials to meshes / subsets")
        self.assign_cb.setChecked(True)
        lay.addWidget(self.assign_cb)

        btns = QtWidgets.QHBoxLayout()
        self.build_btn = QtWidgets.QPushButton("Build")
        self.build_btn.setDefault(True)
        self.build_btn.clicked.connect(self._do_build)
        btns.addWidget(self.build_btn)
        btns.addStretch()
        close = QtWidgets.QPushButton("Close")
        close.clicked.connect(self.close)
        btns.addWidget(close)
        lay.addLayout(btns)

        self.status = QtWidgets.QLabel("")
        self.status.setWordWrap(True)
        lay.addWidget(self.status)

        # bottom row: version + changelog + update
        bottom = QtWidgets.QHBoxLayout()
        self.ver_label = QtWidgets.QLabel("v%s" % updater.local_version())
        self.ver_label.setStyleSheet("color: #888;")
        bottom.addWidget(self.ver_label)
        bottom.addStretch()
        self.changelog_btn = QtWidgets.QPushButton("Changelog")
        self.changelog_btn.clicked.connect(self._show_changelog)
        bottom.addWidget(self.changelog_btn)
        self.update_btn = QtWidgets.QPushButton("Check for updates")
        self.update_btn.clicked.connect(self._do_update)
        bottom.addWidget(self.update_btn)
        lay.addLayout(bottom)

    # --- settings ---
    def _load_settings(self):
        s = getattr(hou.session, "charmat_settings", {})
        self.folder_edit.setText(s.get("folder", ""))
        self.assign_cb.setChecked(s.get("assign", True))

    def _save_settings(self):
        hou.session.charmat_settings = {
            "folder": self.folder_edit.text(),
            "assign": self.assign_cb.isChecked(),
        }

    def _version_warning(self):
        if not _hou_version_ok():
            self.status.setText(
                "Warning: this tool targets Houdini %d.%d or newer. "
                "Some features may not work in this build."
                % MIN_HOU_VERSION)

    def _pick_folder(self):
        d = hou.ui.selectFile(
            title="Folder with per-material subfolders",
            file_type=hou.fileType.Directory,
            chooser_mode=hou.fileChooserMode.Read,
        )
        if d:
            self.folder_edit.setText(d.rstrip("/\\"))

    def _do_build(self):
        folder = self.folder_edit.text().strip()
        if not folder:
            self.status.setText("Specify a materials folder")
            return
        self._save_settings()
        self.status.setText("Building...")
        QtWidgets.QApplication.processEvents()

        res = core.build(folder, assign=self.assign_cb.isChecked())
        if "error" in res:
            self.status.setText("Error: %s" % res["error"])
            return

        msg = "Created: %d, assigned: %d" % (len(res["created"]), res["assigned"])
        if res["skipped"]:
            msg += "\nSkipped (no textures): %d" % len(res["skipped"])
        if res["unmatched"]:
            msg += "\nUnmatched geometry: %s" % ", ".join(res["unmatched"][:8])
        self.status.setText(msg)

    # --- changelog ---
    def _show_changelog(self):
        self.status.setText("Fetching changelog...")
        QtWidgets.QApplication.processEvents()
        txt = updater.remote_changelog()
        if not txt:
            self.status.setText("Changelog unavailable (offline or not published)")
            return
        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle("Changelog")
        dlg.setMinimumSize(480, 400)
        v = QtWidgets.QVBoxLayout(dlg)
        view = QtWidgets.QPlainTextEdit()
        view.setReadOnly(True)
        view.setPlainText(txt)
        v.addWidget(view)
        ok = QtWidgets.QPushButton("Close")
        ok.clicked.connect(dlg.close)
        v.addWidget(ok)
        self.status.setText("")
        dlg.exec_() if hasattr(dlg, "exec_") else dlg.exec()

    # --- update ---
    def _check_update_silent(self):
        try:
            avail, loc, rem = updater.has_update()
        except Exception:
            return
        if avail:
            self.update_btn.setText("Update to %s !" % rem)
            self.update_btn.setStyleSheet("font-weight: bold; color: #4a9;")

    def _do_update(self):
        self.update_btn.setEnabled(False)
        self.status.setText("Checking...")
        QtWidgets.QApplication.processEvents()

        avail, loc, rem = updater.has_update()
        if rem is None:
            self.status.setText("No connection to GitHub (check internet / repo settings)")
            self.update_btn.setEnabled(True)
            return
        if not avail:
            self.status.setText("You are on the latest version (%s)" % loc)
            self.update_btn.setEnabled(True)
            return

        self.status.setText("Downloading %s..." % rem)
        QtWidgets.QApplication.processEvents()
        ok, msg = updater.update()
        self.status.setText(msg)
        self.update_btn.setEnabled(True)


def show():
    if hasattr(hou.session, "charmat_dialog"):
        try:
            hou.session.charmat_dialog.close()
        except Exception:
            pass
    d = CharMatDialog(hou.qt.mainWindow())
    hou.session.charmat_dialog = d
    d.show()
