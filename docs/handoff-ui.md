# Handoff: two ways in — the command line alone, and the window alone

Written 2026-09-20 at the end of the session that built the Qt marking window,
and **brought current at the end of the next session, the same day**, which did
§4.1–4.3 and the agents' half of §4.5. Everything below was checked on this
machine unless it says otherwise. `docs/handoff-gui.md` is the record of how the
window got here; this is the brief for what comes next.

## Where things stand (2026-09-20, end of the UI session)

Both audiences can now do the whole of the *marking* job alone, and PR113 comes
back both ways: through `mcdonald-gui`'s flow the two documented clicks give
141.0 px/frame and the link 4 of 4 frames; through `look` and `mark --set` an
agent's two marks give 141.4, against the published 142. What is left is the
other half of "GUI only" — the measurements from the window (§4.4) — and giving
the six measuring commands results as fields rather than prose.

Done, in three commits (`89a5c68`, `9bcc3d8`, and the one that carries this):

1. **One table of actions** (`actions.py`). The Qt menus and shortcuts, Help →
   Keys, the matplotlib key handler and `mark --help` are made from it.
   `QtMarker.keyPressEvent` is gone; every key is a `QAction`'s shortcut.
2. **The window alone.** `mcdonald-gui` (a gui-script) and `--desktop-entry`;
   `mark_qt.open_session`, the one way in for it and for `mcdonald mark`;
   `RangeChooser`, with a preview and `Clip.cost()` said before anything is
   extracted; the case directory shown and changeable, `Documents/mcdonald/<tag>`
   from the desktop; File → Open a clip / by catalog id / Open marks / Save to a
   different folder; every failure on the way in a dialog, in the command
   line's words.
3. **The command line alone.** `mcdonald look` (overview without extracting;
   a frame's candidates ringed, numbered, enlarged, and as JSON; `--at` the
   loupe); `mcdonald mark --set … --no-window --link --json`; `Link.concerns()`
   and `to_dict()`; one `--json` envelope (`report.envelope`) from every
   command; exit codes 0–5 (`clip.EXIT_CODES`, `clip.Stop`); `docs/agents.md`.

**Jacob's decisions (2026-09-20), which §5 asked for:**

1. "GUI only" covers the **whole job, staged**: the measurements and the report
   from the window are in scope, built last, as a shell over code that is by
   then callable.
2. An agent **may** decide which thing is the object, **recorded as the
   agent's**: `how = "agent: <why>"`, excluded from `by_hand()`, and a report
   built on it says so on its face. Implemented: `MarkSet.kind()`,
   `not_by_hand()`, `Case.identified()`.
3. Platforms for the person at the window: **Linux and macOS.** macOS is
   *unverified*: nothing here has run on a Mac (see "Next", 3).
4. Installation: **`pip install` once is acceptable**; no bundled app for now,
   so the licence question stays where `handoff-gui.md` §4 left it.
5. Commits: each finished step straight to `main` and pushed, for that session.

## Next, in the order I would do it

1. **The measurements from the window (§4.4)** — the largest gap left, and the
   audit's table in §3 still reads ✘ for "measure" and "read the results". The
   obstacle found this session: **`run.py` is not a thin driver.** Its docstring
   says each stage "is the same code the standalone subcommand runs", but
   layers, scale and kinematics are computed inline in `run._main`, and verify
   and integrity are run by swapping `sys.argv` and calling the other module's
   `main()`. There is no `stage(clip, track, …) -> result` to put a window
   over. So the first move is a refactor with no interface in it: one function
   per stage returning `(result, no_power, needs)`, which `run`, the standalone
   command and a Measure menu all call. `report.Case` and `report.envelope`
   are already the shape to return into.
2. **Results as fields for the six measuring commands.** Today `--json` on
   `layers`, `integrity`, `tracksheet`, `symbology`, `comotion`, `kinematics`
   is an envelope made *round* the command (`cli._enveloped`): files found by
   looking, `results.said` the prose as lines. Honest, and the numbers are
   still prose. It falls out of 1: a stage function's result *is* the fields.
   `tests/test_golden.py` parsing prose with regexes is the same debt.
3. **A Mac.** Untested there: the menu roles (only "Save and quit" may move to
   the application menu), single-letter shortcuts in a native menu bar, the
   tool windows, `QStandardPaths` Documents, and the process pool under spawn.
   `gui.desktop_entry` refuses on macOS with a sentence; what a Mac person
   double-clicks is undecided (a `.command` file? briefcase?).
4. **The first-run page in Help (§4.5, the person's half).** The start dialog
   says three sentences; Help → Keys lists keys. Nothing yet walks a person
   through "find it, two clicks, l, look at the strip, s".
5. Smaller, noticed and not done: the start dialog and the catalog chooser are
   modal and no test drives them; `contact_strip` draws a mark at
   `(x - x0) * zoom`, which is a third of a pixel up and left of the pixel's
   centre at zoom 3 (`look.crop_view` does it right and is pinned by a red
   pixel — the strip should be made to agree, and `vf.track_strip` checked);
   cases-folder and range are not remembered between starts (only the catalog
   and the last clip folder are); `mark --set` always records an agent — a
   person typing coordinates has no way to say so, and perhaps should not.

---

## 0. The brief, in Jacob's words

> In the next session, I'd like to focus on UI improvements. The tool should be
> usable with CLI only (in case users want their AI agents to do the work) but
> also in GUI-mode only (for human users with no AI).

Two audiences, then, and each must be able to do the *whole job* without the
other's interface:

- **an agent at a command line** — no display, cannot click, reads text and
  JSON, can look at an image file if one is written for it;
- **a person at a window** — no terminal, no flags, no AI to ask what the keys
  are.

His verdict on the window as it stands: "a nice feel", "all works great". So
this is not a rescue. It is finding out how far each audience actually gets
today, and closing the distance.

## 1. Where the package stands

`mcdonald` 0.2.0, eight commands (`mcdonald --help`): `run`, `mark`, `layers`,
`integrity`, `tracksheet`, `symbology`, `comotion`, `kinematics`.

The one input the package needs from outside itself is **which thing in the
frame is the object** (`handoff-gui.md` §1). Today that arrives as hand marks
from `mcdonald mark`, which has two windows over one `MarkSet`:

| | |
|---|---|
| `mark.py` | `MarkSet` (all state, with per-mark provenance `how`), `contact_strip`, the matplotlib `Marker`, `save_all`, `status_line`, `choose_gui`, `main` |
| `mark_qt.py` | the Qt window: timeline, true-speed playback, overview, detector candidates, loupe, undo, link (`l`), snap, nudge, extraction progress |
| `autolink.py` | marks → detector choice → candidates on a process pool → `link_track` both ways from every mark → residuals, arrivals, disputed frames. **No Qt in it.** |
| `--marks FILE` | `layers`, `integrity`, `run` link the track from a marks file first |

The pattern that made all of this testable, and the thing to keep: **one core
with no interface in it, thin shells over it, and one list of checks run
against every shell** (`tests/test_gui.py`'s rigs). Both of the new audiences
are, in that sense, just two more shells.

## 2. Audit: the command line alone (an agent)

*As it stood at the start of the UI session. Since closed: every row but the
last two columns of "read the results" (the six measuring commands' numbers
are still prose inside the envelope). `docs/agents.md` is the worked session.*

Walked through the PR113 job — find the object, mark it, link, measure — asking
at each step what an agent with no display can do *today*.

| step | today | gap |
|---|---|---|
| open a clip | ✔ path or catalog id; ffmpeg checked up front, exit code 3 with instructions if missing | — |
| **look at the clip** | ✘ nothing writes an image an agent could open to find the object. `tracksheet` needs a track first; the overview, the candidates overlay and the loupe exist only inside the Qt window | **the largest gap.** An agent cannot see |
| ask the detector | ✘ `forensics.frame_candidates` is Python only; no command prints a frame's candidates | no `candidates` command, no JSON |
| **place marks** | ✘ `mark` always opens a window (`mark.py` is the only `plt.show()` in the package, and `mark_qt` the only Qt). ✔ *but* a marks file is four lines and can simply be written: `{"classes": {"object": {"408": [1009, 313], "411": [702, 604]}}}` loads and links (checked; whole numbers are coerced) | no `mark --set … --no-window`; the file format is undocumented outside `MarkSet.to_dict` |
| link | ✔ `layers/integrity/run --marks FILE`; on PR113 all 4 frames where `--auto-track` gets 1 | the link is only reachable *through* another command; no `mcdonald link` of its own |
| check the link | ◐ `<tag>_autotrack_strip.png` is written, and an agent that can view images can look at it; the CSV header carries residuals, arrivals, disputed frames | nothing machine-readable says "this link is suspect" |
| measure | ✔ all six measuring commands run headless | — |
| **read the results** | ◐ `run` → `<tag>_case.json`, `integrity` → `_integrity_report.json`. `layers`, `kinematics`, `comotion`, `symbology` print prose and write CSV/PNG | **no `--json` anywhere**; an agent parses prose, as `tests/test_golden.py` does with regexes |
| know it failed | ◐ exit 2 unknown command, 3 no ffmpeg; anything else is a Python traceback and exit 1 | no table of exit codes; expected failures (no such clip, no track) are not distinguished from bugs |
| learn the tool | ✔ `--help` everywhere, `docs/method.md` for meaning | nothing written *for* an agent: no worked session, no statement of which judgments are the agent's to make |

**The question underneath the table, and it is Jacob's to answer (§5):** the
package's founding claim is that no detector can say which thing is the
object — a person looking can. If an agent places the marks, *the agent* is
making that judgment. The honest treatment already has a home: `MarkSet.how`.
A mark an agent chose must say so ("agent: candidate 2 of 9 at 21 px dark on
frame 408"), `by_hand()` must go on excluding it, and every file downstream
already carries `how` through. Do not let an agent's marks pass as hand marks.

## 3. Audit: the window alone (a person)

*As it stood at the start of the UI session. Since closed: start it, open a
clip (by id, and a second one), choose a frame window, choose where results go,
continue earlier work, find out what the keys are, told when something is
wrong. **Still open: measure, and read the results.***

Same job, asking what someone with no terminal can do *today*.

| step | today | gap |
|---|---|---|
| **start it** | ✘ `[project.scripts]` has only `mcdonald`; no `[project.gui-scripts]`, no desktop entry. Starting the window means typing `mcdonald mark` | **they cannot get in.** And PySide6 is an optional extra they must know to ask for |
| open a clip | ✔ with no clip named, a file dialog | ✘ no opening by catalog id (PR113), which is how the corpus is actually addressed; ✘ no opening a *second* clip without restarting |
| choose a frame window | ✘ `--n0/--n1` are flags only; the window opens the whole clip and extracts all of it (PR148: 1793 frames, 1.3 GB) | no range chooser; no warning of the cost before it starts |
| choose where results go | ✘ `--out` is a flag only; default `./<tag>` relative to a working directory the person never chose and cannot see | nothing on screen says where `s` writes |
| continue earlier work | ✘ `--load` is a flag only (it does reload `./<tag>/<tag>_marks.json` by itself if it is there) | no File → Open marks |
| **find out what the keys are** | ✘ **there is no menu bar at all** (0 `QMenu`/`QAction` in `mark_qt.py`). The key list is in `--help` and a docstring. A few buttons have tooltips | **the second largest gap.** `l`, `o`, `c`, `t`, `[` `]`, shift+click and ctrl+arrows are undiscoverable |
| mark, link, check | ✔ this is what the window is, and it is good | — |
| told when something is wrong | ✘ one dialog in the whole window (unsaved marks). ffmpeg missing, not a video, extraction failed, the link raised: all go to a terminal this person does not have | errors need dialogs with the same instructions the CLI prints |
| **measure** | ✘ `layers`, `integrity`, `tracksheet`, `symbology`, `comotion`, `kinematics`, `run`: no window of any kind | **the largest gap.** The window ends where the measurements begin |
| read the results | ✘ `<tag>_case.md` is a file on disk | no report viewer |

## 4. What follows, in the order I would do it

The rule to hold to: **a thing a person can do in the window and an agent
cannot do from the command line is a bug, and the other way about.** Build each
capability once, in a module with no interface in it, and give it two shells.

1. **One table of actions.** Every window action — key, name, one line of
   help, the function it calls — in one place, from which the menus, the
   Help → Keys page and the `--help` epilog are all generated. Today the key
   list exists three times by hand (`mark.py` docstring, `mark_qt.py`
   docstring, `keyPressEvent`) and they will drift. Cheap, and it makes 2 easy.
2. **The window, for someone who has only the window.** Menu bar (File, Edit,
   View, Track, Help) from that table; Help → Keys; File → Open clip / Open by
   catalog id / Open marks / Save / Save as; the case directory shown and
   changeable; a frame-range chooser that says what extraction will cost;
   error dialogs carrying the CLI's own messages; `[project.gui-scripts]
   mcdonald-gui` and a desktop entry. None of this is deep, all of it is
   between this person and the door.
3. **The command line, for something that cannot click.**
   `mcdonald look CLIP` → an overview sheet (the `o` tiles) as one PNG;
   `--frame N` → that frame with the candidates ringed and numbered, plus the
   same as JSON; `--at x,y` → the loupe's crop. `mcdonald mark CLIP --set
   object@408=1009,313 --set object@411=702,604 [--link] --no-window` → the
   same three files the window saves, plus the autotrack. Marks placed this
   way carry `how` (§2). Then `--json` on every command, one shape: inputs,
   files written, results, `no_power`, `needs` — `report.Case` already has that
   structure, so reuse it rather than invent another. And a table of exit
   codes, with expected failures told apart from bugs.
4. **The measurements, from the window.** A "Measure" menu that runs the same
   stage functions `run.py` calls, off the GUI thread with the progress
   pattern `extract_with_progress` and the link already use, and shows
   `<tag>_case.md` in a viewer. This is the big one; do it after 1–3 so that it
   is a shell over something already callable, not a fork of `run.py`.
5. **Two short documents.** `docs/agents.md`: PR113 done start to finish with
   commands only, what each JSON field means, and which judgments are the
   agent's and must be recorded as such. And a first-run page inside the
   window's Help for the person.

Testing: extend the rig idea. A `CliRig` that does "place a mark", "link",
"save" through subprocess calls, run against the *same* checks as `MplRig` and
`QtRig`, would hold the command line to the windows' standard — and the saved
files of all three can be compared, as the two windows' already are.

## 5. Decisions to put to Jacob before writing code

*Answered 2026-09-20; the answers are at the top.*

1. **How much of the job does "GUI only" cover?** Marking and linking (step 2
   above is then nearly the whole of it), or the measurements and the report
   too (step 4, several sessions)?
2. **May an agent decide which thing is the object,** or only operate the tools
   on marks a person placed? If it may: is `how = "agent: …"` with exclusion
   from `by_hand()` the right record, and should a report built on agent marks
   say so on its face?
3. **Which platforms matter for the person at the window?** The Qt window has
   never been run on Windows or macOS. If those are the audience, that comes
   before polish.
4. **How do they install it?** `pip install "mcdonald[gui]"` assumes a terminal
   once. If that is unacceptable the answer is an installer or a bundled app
   (PyInstaller / briefcase), which is its own piece of work and brings the
   licence question (`handoff-gui.md` §4) to a head, since a bundle ships Qt.

## 6. Traps already paid for

All in `handoff-gui.md` §0 ("New traps") and §8. The ones that bear on this
work:

- **Send events where real ones go** (`fig.canvas.callbacks`,
  `QApplication.sendEvent`), never to a handler. Four matplotlib defects and
  the GIL/`qWait` confusion were found, or hidden, by exactly this.
- **`QTest.qWait()` holds the GIL**; worker threads starve under it. Wait in
  `qWait(10)` slices (`QtRig.wait_for`).
- **Qt aborts without a display**; it does not raise. `choose_gui` checks first.
  A `mcdonald-gui` launcher must too, and must say so in a dialog if it can.
- **Never fork** from the window: the pool is `forkserver`/`spawn`, and the
  children import `__main__` by path — a console-script or gui-script launcher
  is fine, `python -` is not (`autolink` then runs inline).
- **Pixel centres at integers.** Any new view of a frame (an agent's annotated
  PNG included) has to agree with the red-pixel test's convention, or
  coordinates read off it are half a pixel out.
- **A check printed inside `redirect_stdout` is a check nobody sees.**
- **Counting checks:** count `  PASS` lines; the `ALL PASS` line is not one.
- **A `QKeyEvent` sent straight to a widget never meets the shortcut map.**
  Every key in the Qt window is now a `QAction` shortcut, so the rig sends keys
  with `QTest.keyClick` to the focus widget, and makes the window active first:
  an X server with no window manager activates nothing by itself, and shortcuts
  are live only in the active window (or a `Qt.Tool` child of it — which is why
  the strips and the Help page are tool windows). A synthetic key has no
  keyboard layout behind it: send `<` as `<`, not as shift+`,`.
- **Two `QAction`s with one shortcut cancel each other silently.** Qt calls it
  ambiguous and runs neither. `drive_every_key` fails naming both rows.
- **Text into a `QTextBrowser` is HTML.** An unescaped `<` (a key, here) ate a
  line of the Help page. `html.escape`.
- **`textwrap` breaks at hyphens**, so `mcdonald-gui` became `mcdonald-` /
  `gui` in `--help`. `break_on_hyphens=False`.
- **A clip is not required to know its video's name.** The linker asks a clip
  for n0, n1, W, H, fps, rgb, grey, and the test clips give no more. Reaching for
  `clip.video` in shared code broke the window's save under test; pass the
  MarkSet's.
- **A trial script needs `if __name__ == "__main__":`.** Without it every
  forkserver child re-runs the script, window and all, and the link fails with
  Python's "bootstrapping phase" error. Met again this session.
- **A planted object leaves the frame.** `PlantedClip` moves 41 px a frame in a
  540 px frame: after frame 12 every frame is the same, and a link of 11 frames
  is the right answer. Two "failures" in `test_cli.py` were this.
- **A mark copied from the detector cannot check the detector**, whoever copied
  it. An agent that sets marks at candidates' coordinates gets "within 0.0 px of
  all marks", which is circular. `docs/agents.md` says so; nothing enforces it.
- Use **Technical Note clips** for real trials: PR113 (`--n0 400 --n1 420`, marks
  408 → (1009, 313), 411 → (702, 604), must give 142 px/frame) and PR144
  (`--n0 300 --n1 500`, vendored track in `tests/golden/`). PR148 is a poor
  demo: its object is far larger than the default detector scale.

## 7. First moves

1. Read the top of this file, then `docs/agents.md` (the agent's job, worked)
   and `src/mcdonald/run.py`'s `_main`, which is what "Next, 1" has to take
   apart.
2. Run the suites (§8). About three minutes together; `test_golden` five more.
3. Start `mcdonald-gui` on the desktop and open PR113 by its id, as the person
   would: nobody has yet used the new way in with a real hand.
4. Then "Next, 1": stage functions first, with `run`'s numbers unchanged
   (`test_golden`, and a before/after `_case.json` on PR144, are the check).

## 8. State at handoff

- `main` is pushed and clean. This session's commits: `89a5c68` (the table of
  actions; menus; keys become shortcuts), `9bcc3d8` (the way in with no
  terminal), and the one that carries this file (the command line alone).
- Suites, all passing: `test_measurement` 82 checks, `test_reduction` 85,
  `test_published` 32, `test_gui` 369 with only WxAgg skipping (was 322),
  `test_cli` 37 (new; about a minute), and `test_golden` 11 on the corpus
  (PR113's two clicks; PR144's layer rates).
- Real trials on PR113 (`--n0 400 --n1 420`): the window's flow under Xvfb, two
  clicks → 141.0 px/frame, `l` → 4 of 4 frames at 21 px dark; the agent's flow,
  `look` → candidate 1 of 6 at (1010.9, 313.0), `mark --set … --link` → 141.4
  px/frame, no concerns; `run --marks … --json` → the case, with "decided by an
  agent" above its bottom line (4 min, integrity included).
- Environment: as before (Fedora 44, Python 3.14.7, PySide6-Essentials 6.11.2).
  The package is an editable install and was reinstalled (`pip install --user
  --no-deps --no-build-isolation -e .`) so that `mcdonald-gui` is on the PATH.
  `MCDONALD_CATALOG` is **not** exported in a fresh shell:
  `export MCDONALD_CATALOG=/hugespace/local/research/uap/pursue_index/records.csv`
- No desktop entry was written on this machine: `mcdonald-gui --desktop-entry`
  was exercised only into a temporary directory. Run it, or Help → Add mcdonald
  to the applications menu, to have one.
- Cleaned up at the end of the session, all of it this session's own: 31
  `mcdonald-test-config-*` directories that `test_gui.py` left in `/tmp`, one a
  run (fixed: removed at exit); a `planted` frame cache that `test_cli.py` wrote
  into the shared `/tmp/mcdonald` through a command given no `--workdir` (fixed:
  the suite's subprocesses get their own `TMPDIR`); two empty window
  directories from launcher trials ended with `timeout`, which no close event
  follows; and the 40 frames `look --frame 408` had added to PR113's cache, which
  is back to its 21 (400–420). `/tmp` is a tmpfs here: all of that was memory.
- Not done, on purpose: an FFT route through `source_candidates`
  (`handoff-gui.md` §0.2), and any run on macOS or Windows.
