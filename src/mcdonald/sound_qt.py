"""The window's page of the sound: what `mcdonald audio` hears in the open video, said plainly first.

Measure -> The sound of this video... reads the video's sound track in a thread, with a wait's card at the top of
the right column (Cancel drops what it finds), then opens a page over the video (nothing pops up): the headline
and a sentence for each thing heard (`audio.plainly`), the picture of the sound, and, folded, the measurement's
own words (`audio.said`), which may use the trade's terms. The picture is saved in the results folder, where
`mcdonald audio VIDEO --out DIR` saves it too, and what was heard is kept for the video: a second look opens at
once. The whole video's sound is read (up to `audio.MAX_S`), as the command reads it, not only the segment open.

`SoundCard` is the same job's card in the right column, under the object's steps (Jacob, 2026-10-16: "If the clip
has audio, then include a 'Measure the sound' box and button"): shown only when the video has sound
(`speaker.sound_of`, asked when it opens), its button the menu's row; once the sound is read it says the page's
headline, and its button opens the page again.
"""
import threading
from html import escape
from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets

from . import actions, audio
from .mark_qt import ACCENT, MUTED, PRIMARY, QUIET, BusyCard, Page, ReadingView, folding_button, heading, muted, show_busy

TITLE = "The sound of this video"


class Listener(QtCore.QObject):
    """One reading of a video's sound, from its wait's card to its page."""
    heard = QtCore.Signal(object)                     # the Found, or the exception that ended it

    def __init__(self, window, video, out):
        super().__init__()
        self.window_, self.video, self.out, self.dropped = window, str(video), out, False
        self.card = BusyCard(window, "Listening to the sound",
                             f"Reading the sound of {Path(video).name}: up to {audio.MAX_S / 60:g} minutes of it, which "
                             "takes a few seconds to a minute.", 0)
        self.card.cancel_button.setToolTip("stop waiting, and show nothing")
        self.card.cancel_button.clicked.connect(self.drop)
        self.heard.connect(self._heard)

    def start(self):
        show_busy(self.window_, self.card)
        Path(self.out).parent.mkdir(parents=True, exist_ok=True)
        video, out, say = self.video, self.out, self.heard

        def job():
            try:
                got = audio.measure(video, out=out)
            except BaseException as e:                # whatever it is goes to the window, not to a dead thread
                got = e
            try:
                say.emit(got)
            except RuntimeError:                       # the window went meanwhile
                pass
        threading.Thread(target=job, daemon=True, name="mcdonald-audio").start()

    def drop(self):
        """Cancel: the card goes now; what the thread finds later is let go."""
        self.dropped = True
        self.card.close()
        self._done()

    def _done(self):
        if getattr(self.window_, "_listener", None) is self:
            self.window_._listener = None
        self.window_.sound_card.button.setEnabled(True)

    @QtCore.Slot(object)
    def _heard(self, got):
        if self.dropped:
            return
        self.card.close()
        self._done()
        w = self.window_
        if isinstance(got, BaseException):
            w.note.setText(f"The sound could not be read: {got}")
            return
        w._sound[self.video] = got
        w.sound_card.say()
        show(w, got)


def listen(window):
    """Measure -> The sound of this video: the page at once if the sound was read before, else read it."""
    video = window.video_path()
    found = window._sound.get(video)
    if found is not None:
        return show(window, found)
    if window._listener is not None:                  # already listening: its card is in the column
        return None
    window._listener = Listener(window, video, window.out)
    window.sound_card.button.setEnabled(False)        # one reading at a time; its card is in the column
    window._listener.start()
    return window._listener


def show(window, found):
    """The page: the headline as a card, a sentence for each thing heard, the picture, and the numbers folded."""
    if getattr(window, "sound_page", None) is not None:
        window.sound_page.close()
    d = window.sound_page = SoundPage(window, found)
    d.closed.connect(lambda: setattr(window, "sound_page", None))
    window.show_page(d)
    return d


class SoundPage(Page):
    def __init__(self, window, found):
        super().__init__(window, TITLE, back=window.back_text())
        f = found.fields
        head, rest = audio.plainly(f)
        picture = next((Path(p) for p in found.files if str(p).endswith("_audio.png") and Path(p).exists()), None)
        self.headline, self.sentences, self.picture = head, rest, picture
        if picture is not None:
            folder = QtWidgets.QPushButton("Open the folder")
            folder.setToolTip("open the results folder, where the picture of the sound is saved")
            folder.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
            folder.setAutoDefault(False)
            where = str(picture.resolve().parent)
            folder.clicked.connect(lambda: QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(where)))
            self.tools.addWidget(folder)
        html = [f"<table width='100%' cellpadding='12' cellspacing='0' bgcolor='#16262a'><tr><td>"
                f"<span style='font-size: large; font-weight: bold;'>{escape(head)}</span></td></tr></table>"]
        html += [f"<p style='line-height: 135%;'>{escape(r)}</p>" for r in rest]
        if picture is not None:
            html.append(f"<p><img src='{escape(picture.name)}'></p>"
                        f"<p style='color: {MUTED};'>How far each tone stands above the noise near it (dashed lines: "
                        "the tones that were explained). Saved as " + escape(picture.name) + " in the results folder.</p>")
        html.append(f"<p style='color: {MUTED};'>The whole video's sound is read, up to {audio.MAX_S / 60:g} minutes "
                    "of it, not only the segment open. A tone is heard here only if it is steady: voices and noise "
                    "are not read.</p>")
        page = self.page = ReadingView()
        page.setOpenLinks(False)
        page.anchorClicked.connect(QtGui.QDesktopServices.openUrl)
        if picture is not None:
            page.setSearchPaths([str(picture.resolve().parent)])
        page.setHtml("".join(html))
        if picture is not None:
            from .measure_qt import fit_pictures
            fit_pictures(page, picture.resolve().parent)
        self.body.addLayout(page.column(), 1)
        # the measurement's own words, as `mcdonald audio` prints them: they may use the trade's terms
        tech = QtWidgets.QWidget()
        tech.setObjectName("technical")
        tl = QtWidgets.QVBoxLayout(tech)
        tl.setContentsMargins(0, 0, 0, 0)
        numbers = self.numbers = QtWidgets.QPlainTextEdit("\n".join(audio.said(f)))
        numbers.setReadOnly(True)
        numbers.setLineWrapMode(QtWidgets.QPlainTextEdit.LineWrapMode.WidgetWidth)
        numbers.setFont(QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.SystemFont.FixedFont))
        numbers.setMaximumHeight(240)
        self.fold = folding_button("The numbers, as the measurement gives them", numbers)
        tl.addWidget(self.fold)
        tl.addWidget(numbers)
        self.body.addWidget(tech)
        self.take_focus = page.setFocus


INTRO = ("This video has sound. Find out what it holds: the hum of the power it was recorded on, which says whether "
         "it plays at its true speed; an aircraft named by its propellers; how many times it was saved.")


class SoundCard(QtWidgets.QFrame):
    """"Measure the sound", in the right column: shown when the video has sound. Its button is Measure -> The sound of
    this video…. Until the sound is read the card is in colour, as a thing still to do (Jacob, 2026-10-17: "Before
    'Measure the sound' has been clicked, it should be another color other than gray"); once it is read, it is done:
    a tick and grey, as a finished wait's card is ("it should show a checkmark and then turn gray"), with the page's
    headline, and its button opens the page again."""
    TITLE = "Measure the sound"

    def __init__(self, window):
        super().__init__()
        self.window_ = window
        self.setObjectName("sound")
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Maximum)
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 10)
        lay.setSpacing(6)
        self.head = heading(self.TITLE, 1.1)
        lay.addWidget(self.head)
        self.line = muted(INTRO)
        lay.addWidget(self.line)
        self.headline = QtWidgets.QLabel()
        self.headline.setWordWrap(True)
        self.headline.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        self.headline.hide()
        lay.addWidget(self.headline)
        self.button = QtWidgets.QPushButton("Measure the sound")
        row = next(a for a in actions.ACTIONS if a.id == "sound")
        self.button.setToolTip(row.help)
        self.button.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.button.setAutoDefault(False)
        self.button.setMinimumHeight(32)
        self.button.clicked.connect(lambda _=False: window.do("sound"))
        lay.addWidget(self.button)
        self.done = None
        self._look(False)
        self.hide()

    def _look(self, done):
        """To do: the teal of a thing to do. Done: a tick, and grey."""
        if done == self.done:
            return
        self.done = done
        self.head.setText(f"✓ {self.TITLE}" if done else self.TITLE)
        self.setStyleSheet(f"QFrame#sound {{ border: 1px solid {'#34343a' if done else ACCENT}; border-radius: 8px; "
                           f"background: {'transparent' if done else '#16262a'}; }}")
        self.button.setStyleSheet(QUIET if done else PRIMARY)

    def say(self, state=None):
        """Shown or not (`state`, from `speaker.sound_of`, when it is given), and what is known of the sound."""
        if state is not None:
            self.setVisible(state == "sound")
        w = self.window_
        found = w._sound.get(w.video_path()) if w.clip is not None else None
        if found is not None:
            self.headline.setText(audio.plainly(found.fields)[0])
            self.button.setText("Show what the sound holds")
        else:
            self.button.setText("Measure the sound")
        self._look(found is not None)
        self.headline.setVisible(found is not None)
        self.line.setVisible(found is None)
