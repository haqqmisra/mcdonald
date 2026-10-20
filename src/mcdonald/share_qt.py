"""The shared file's card, in the right column (share.py has what the file is).

Opened from a file someone sent (`ShareCard(window, manifest, folder, check)`): who sent it and when, everything
said about it so far, whether the video found here is the one they measured, a button for each stretch they asked to
be looked at -- it goes there and plays it, and stops at its end -- the files that came with it, and a box for the
answer, which is saved as a file to send back: their results and yours, and the thread with your note added.

Made with nothing opened (`ShareCard(window)`, File -> Share for review...): the same box, to send this video's
results to someone with what to look at.

Jacob's three rules for the window (2026-10-07) hold here: no pop-up window -- it is a card in the column; one button
does the job; and what was concluded comes first -- the newest note is at the top of the thread.
"""
import threading
from datetime import datetime
from html import escape
from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt

from . import rerun, share

MUTED = "#898781"
WARN = "#e0b04a"
GOOD = "#7fc48f"


def _small(text, colour=MUTED):
    lab = QtWidgets.QLabel(text)
    lab.setWordWrap(True)
    lab.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored, QtWidgets.QSizePolicy.Policy.Preferred)
    lab.setStyleSheet(f"color: {colour};")
    return lab


def _who(note):
    return escape(str(note.get("by") or "someone")) + (" (an AI agent)" if note.get("agent") else "")


class ShareCard(QtWidgets.QFrame):
    """The card. `saved` is the last file it wrote, or None."""

    def __init__(self, window, manifest=None, folder=None, check=None):
        super().__init__()
        from .mark_qt import PRIMARY, QUIET, heading, settings
        self.window_, self.m, self.folder, self.saved, self.check = window, manifest, Path(folder) if folder else None, None, check
        self.setObjectName("shared")
        self.setStyleSheet("QFrame#shared { border: 1px solid #3d6f73; border-radius: 8px; }")
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 10)
        lay.setSpacing(6)
        caption = _small("SHARED WITH YOU" if manifest else "SHARE FOR REVIEW")
        caption.setStyleSheet(f"color: {MUTED}; font-size: 10px; letter-spacing: 1px;")
        lay.addWidget(caption)
        self.looks = []
        if manifest:
            made = manifest.get("made") or {}
            lay.addWidget(heading(f"From {_who(made)}", 1.1))
            thread = list(manifest.get("thread") or [])
            for i, note in enumerate(reversed(thread)):        # the newest first: what is asked now
                text = escape(str(note.get("text") or "(no note)")).replace("\n", "<br>")
                lab = QtWidgets.QLabel(f"<b>{_who(note)}</b> <span style='color:{MUTED}'>· "
                                       f"{escape(share.local_time(note.get('when')))}</span><br>{text}")
                lab.setWordWrap(True)
                lab.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored, QtWidgets.QSizePolicy.Policy.Preferred)
                lab.setTextFormat(Qt.TextFormat.RichText)
                lab.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                if i:
                    lab.setStyleSheet(f"color: {MUTED};")
                lay.addWidget(lab)
            if check is not None:
                same, said = check
                lay.addWidget(_small(("✓ " if same else "⚠ ") + said, GOOD if same else WARN))
            look = manifest.get("look") or []
            if look:
                lay.addWidget(_small("Look at:"))
            for s in look:                             # the button short, what is there beside it and wrapped: a long
                row = QtWidgets.QHBoxLayout()          # button would make the column wider than the window
                b = QtWidgets.QPushButton(f"▶  {s['first']}–{s['last']}")
                b.setStyleSheet("QPushButton { text-align: left; padding: 5px 8px; }")
                b.setToolTip(f"go to frame {s['first']} and play to frame {s['last']}, where it stops")
                b.setAutoDefault(False)
                b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
                b.clicked.connect(lambda _=False, a=s["first"], z=s["last"]: window.play_stretch(a, z))
                row.addWidget(b, 0, Qt.AlignmentFlag.AlignTop)
                what = QtWidgets.QLabel(escape(str(s.get("what") or "")))
                what.setWordWrap(True)
                what.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored, QtWidgets.QSizePolicy.Policy.Preferred)
                row.addWidget(what, 1)
                lay.addLayout(row)
                self.looks.append(b)
            objs = manifest.get("objects") or {}
            if objs:
                lay.addWidget(_small("Objects: " + ", ".join(f"{k} {escape(str(v))}" for k, v in sorted(objs.items(), key=lambda kv: int(kv[0])))))
            self.measured = [p for p in rerun.objects(self.folder) if next(p.glob("*_case.json"), None)] if self.folder else []
            if self.measured:                          # what `mcdonald share rerun` does: each object measured again
                self.again = QtWidgets.QPushButton("Measure it again")
                self.again.setStyleSheet(QUIET)
                self.again.setAutoDefault(False)
                self.again.setFocusPolicy(Qt.FocusPolicy.NoFocus)
                same = check is None or check[0]
                self.again.setEnabled(same)
                self.again.setToolTip("measure each object it holds again, as its report says it was measured, and see whether "
                                      "the numbers come back the same -- minutes for each object" if same else
                                      "the video here is not the one they measured, so its numbers cannot come back the same")
                self.again.clicked.connect(self.measure_again)     # a method, not a lambda holding the card (mark_qt.Collector)
                lay.addWidget(self.again)
                self.again_said = _small("")
                self.again_said.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                self.again_said.hide()
                lay.addWidget(self.again_said)
            self.attached = share.attached(self.folder) if self.folder else []
            for p in self.attached:
                b = QtWidgets.QPushButton(f"Open {p.name}")
                b.setStyleSheet(QUIET)
                b.setAutoDefault(False)
                b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
                b.setToolTip("sent with it: opens in the program this computer uses for it")
                b.clicked.connect(lambda _=False, p=p: QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(p))))
                lay.addWidget(b)
        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        line.setStyleSheet("color: #34343a;")
        lay.addWidget(line)
        lay.addWidget(_small("Your answer" if manifest else "What should they look at, and why?"))
        self.note = QtWidgets.QPlainTextEdit()
        self.note.setPlaceholderText("What you saw, and what you would like them to look at" if manifest else
                                     "What you found, and what you would like them to check")
        self.note.setFixedHeight(84)
        lay.addWidget(self.note)
        lay.addWidget(_small("Stretches to look at, one a line: first frame – last frame, then what is there"))
        self.stretches = QtWidgets.QPlainTextEdit()
        clip = window.clip
        prior = [f"{s['first']}-{s['last']}: {s.get('what', '')}" for s in (manifest or {}).get("look") or []]
        self.stretches.setPlainText("\n".join(prior) if prior else (f"{clip.n0}-{clip.n1}: " if clip is not None else ""))
        self.stretches.setFixedHeight(56)
        lay.addWidget(self.stretches)
        row = QtWidgets.QHBoxLayout()
        who = QtWidgets.QLabel("Your name")                  # not _small: a label beside a box keeps its width
        who.setStyleSheet(f"color: {MUTED};")
        row.addWidget(who)
        self.name = QtWidgets.QLineEdit(str(settings().value("share/name") or ""))
        self.name.setPlaceholderText("so they know who it is from")
        row.addWidget(self.name, 1)
        lay.addLayout(row)
        self.go = QtWidgets.QPushButton("Save a file to send back" if manifest else "Save a file to send")
        self.go.setStyleSheet(PRIMARY)
        self.go.setAutoDefault(False)
        self.go.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.go.setToolTip("one file with this video's results, the stretches, and the notes; the video itself is not in it")
        self.go.clicked.connect(self.save)
        lay.addWidget(self.go)
        self.result = _small("")
        self.result.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        lay.addWidget(self.result)
        self.show_it = QtWidgets.QPushButton("Show it in its folder")
        self.show_it.setStyleSheet(QUIET)
        self.show_it.setAutoDefault(False)
        self.show_it.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.show_it.hide()
        self.show_it.clicked.connect(lambda _=False: self.saved and QtGui.QDesktopServices.openUrl(
            QtCore.QUrl.fromLocalFile(str(self.saved.parent))))
        lay.addWidget(self.show_it)

    def look(self):
        """The stretches in the box, as (first, last, what); ValueError names a line that is not one."""
        out = []
        for line in self.stretches.toPlainText().splitlines():
            if line.strip():
                try:
                    out.append(share._span(line.strip()))
                except Exception:
                    raise ValueError(f"“{line.strip()}” is not a stretch: write it as 3300-3500: what is there")
        return out

    def save(self):
        """Save the marks as they are, then the file: this video's results folder, the stretches, the thread with
        this note added. It goes beside the results folder, named for the video, who sent it and when."""
        from .mark_qt import settings
        w = self.window_
        if w.clip is None:
            return
        try:
            look = self.look()
        except ValueError as ex:
            self.result.setText(str(ex))
            self.result.setStyleSheet(f"color: {WARN};")
            return
        name = self.name.text().strip()
        settings().setValue("share/name", name)
        w.finish(show_strip=False)                     # what is on the screen is what is sent
        base = Path(w.several_base())
        tag = (self.m or {}).get("tag") or w.ms.tag
        out = base.parent / share.default_name(tag, name or "someone")
        try:
            self.saved = share.make(out, w.ms.video, folder=base, part=(w.clip.n0, w.clip.n1), look=look,
                                    note=self.note.toPlainText().strip(), by=name or "someone", agent=False,
                                    identity=(self.m or {}).get("video") if self._same_video() else None)
        except (OSError, share.ShareError) as ex:
            self.result.setText(f"It was not saved: {ex}")
            self.result.setStyleSheet(f"color: {WARN};")
            return
        self.result.setText(f"Saved {self.saved.name} ({self.saved.stat().st_size / 2 ** 10:.0f} KB) in {self.saved.parent}. "
                            "Send that file; they open it with File → Open a shared file.")
        self.result.setStyleSheet(f"color: {GOOD};")
        self.show_it.show()

    def _same_video(self):
        """The video's identity from the file it came in, when the file here was checked to be that one (its size and
        SHA-256, when it was opened): it saves hashing it again."""
        return bool(self.m and self.check and self.check[0])

    def measure_again(self):
        """Each object the file holds measured again, in a thread behind a wait's card, and the answer on this card:
        whether its numbers come back the same (`mcdonald share rerun`)."""
        if getattr(self, "_again", None) is not None or not self.measured:
            return None
        self.again.setEnabled(False)
        self.again_said.hide()
        self._again = Again(self, self.window_.ms.video)
        self._again.start()
        return self._again

    def said_again(self, got):
        """What measuring it again found, in plain words, under the button."""
        self._again = None
        self.again.setEnabled(True)
        if isinstance(got, BaseException):
            text, colour = f"It could not be measured again: {got}", WARN
        elif got.get("reruns"):
            n = len(got["objects"])
            text, colour = (f"✓ Its numbers come back the same: {'its object' if n == 1 else f'each of its {n} objects'}, measured "
                            "again as its report says, matches the report number for number."), GOOD
        else:
            off = [(k, o["differences"]) for k, o in got["objects"].items() if o.get("differences")]
            text = ("⚠ Its numbers do not all come back the same: " + "; ".join(
                f"{k}, {len(d)} number{'s' if len(d) != 1 else ''} ({', '.join(str(w) for w, _, _ in d[:3])}"
                f"{', …' if len(d) > 3 else ''})" for k, d in off) + f". Measured again in {Path(got['folder']).name}-rerun.")
            colour = WARN
        self.again_said.setText(text)
        self.again_said.setStyleSheet(f"color: {colour};")
        self.again_said.show()


class Again(QtCore.QObject):
    """A shared file's objects measured again (`rerun.rerun_folder`), from the card's button to the card's answer."""
    step = QtCore.Signal(int, str)                    # objects begun, and the one now
    done = QtCore.Signal(object)                      # what rerun_folder returned, or the exception that ended it

    def __init__(self, card, video):
        super().__init__()
        from .mark_qt import BusyCard
        self.card_, self.video, self.dropped = card, str(video), False
        n = len(card.measured)
        self.busy = BusyCard(card.window_, "Measuring it again",
                             f"Each of its {n} object{'s' if n != 1 else ''}, as its report says it was measured, and then held "
                             "against the report, number for number. Minutes for each object.", n,
                             fmt="%v of %m objects", command="share")      # `share rerun`
        self.busy.cancel_button.setToolTip("stop waiting, and show nothing")
        self.busy.cancel_button.clicked.connect(self.drop)
        self.step.connect(self._step)
        self.done.connect(self._done)

    def start(self):
        from .mark_qt import show_busy
        show_busy(self.card_.window_, self.busy)
        folder, video, step, done = self.card_.folder, self.video, self.step, self.done

        def job():
            try:
                got = rerun.rerun_folder(folder, video, say=lambda *a: None, progress=lambda k, name: step.emit(k, name))
            except BaseException as e:                # whatever it is goes to the window, not to a dead thread
                got = e
            try:
                done.emit(got)
            except RuntimeError:                       # the window went meanwhile
                pass
        threading.Thread(target=job, daemon=True, name="mcdonald-rerun").start()

    def drop(self):
        """Cancel: the card goes now, and what the thread finds later is let go."""
        self.dropped = True
        self.busy.close()
        self.card_._again = None
        self.card_.again.setEnabled(True)

    @QtCore.Slot(int, str)
    def _step(self, k, name):
        if not self.dropped:
            self.busy.setValue(k)
            self.busy.label.setText(f"Measuring {name} again, then holding it against its report: minutes for each object.")

    @QtCore.Slot(object)
    def _done(self, got):
        if self.dropped:
            return
        self.busy.close()
        self.card_.said_again(got)
