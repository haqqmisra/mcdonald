# Handoff: two ways in — the command line alone, and the window alone

Written 2026-09-20 at the end of the session that built the Qt marking window,
brought current at the end of the UI session the same day, and **again at the
end of the third session that day ("the measurements")**, which did "Next" 1, 2
and 4 of the list that stood here. Everything below was checked on this machine
unless it says otherwise. `docs/handoff-gui.md` is the record of how the window
got here; this is the brief for what comes next.

## Where things stand (2026-09-20, end of the measurements session)

**Both audiences can now do the whole job alone.** The audit's two ✘ rows in §3
— measure, and read the results — are closed: Measure → Measure this clip makes
a case from the window and shows the report. And the agent's last gap is
closed: every command's `--json` has its numbers as fields.

How, in one paragraph: `run.py` was taken apart. Each stage is now a function
with no interface in it that returns a `report.Found` (fields, the report's
lines, no_power, needs, files): `layers.measure` and `layers.glance`,
`integrity.examine`, `tracksheet.sheet`, `comotion.measure`,
`symbology.measure`, and `stages.survey / scale / kinematics`. Each command's
`main()` is argparse over one of them and prints prose *written from the
fields*; `stages.run_case` runs them in order into a `Case`; `mcdonald run` is
argparse over `run_case`, and the window's Measure panel (`measure_qt.py`) is a
form over it. `cli._enveloped` and the `sys.argv` swapping are gone.

**The refactor was checked against a baseline, not assumed.** Before anything
was edited, the committed source was exported (`git archive HEAD`) and every
measuring command and three `run`s were run from it on the two Technical Note
windows (PR144 300–500 with the vendored track; PR113 400–420 from the two
documented clicks), from work directories of symlinked frames so that no cache
was shared. Then the same from the refactored source. `layers`, `kinematics`,
`comotion`, `symbology`, `tracksheet`: prose identical line for line,
`_layers.csv`, `_north.csv` and the track sheet JPEG byte-identical.
`integrity`: `_integrity_report.md` byte-identical and the JSON identical but
for one new field. `comotion` with an annulus that holds templates (D = 60):
prose and CSV identical, 36.5 D at 8.76 D/s. Inside `run`, integrity's JSON is
unchanged on PR144 and changed on PR113 only as item 2 below says it should.
The case reports differ from the baseline only where listed next.

### Found on the way: six things that were wrong, each fixed

1. **`mcdonald run` called the sea's screen speed the object's rate.** On PR144
   300–500 its bottom line read "The object moves 340 px/s against the
   striated" — with the vendored track, and *also with no track at all*. 340 is
   the striated layer's screen speed over one frame pair (n0 → n0+5), which
   `run` computed inline and `Case.bottom_line` printed under the object's
   name. The object against the sea on those frames is 599 px/s (and 500
   against the cloud tops): `mcdonald layers` said so all along. No test
   covered the sentence. Now: the bottom line reads the stages' fields, calls a
   rate the object's only where a stage measured the object, and says "No
   object was tracked" when none was (`test_reduction` pins all three); and
   with a track `run`'s layers stage *is* `layers.measure`.
2. **`run` and `integrity --marks` looked for a bright 9 px object whatever the
   marks had chosen.** The link knows the detector's size and polarity; only
   its track was passed on. On PR113 (21 px, dark) integrity's smear test had
   "0 usable frames" and halo "0 frames"; told 21 px dark they have 2 and 4
   (still NO POWER on a four-frame transit, and rightly). `run_case` and
   `integrity` now take them from the link (`autolink.link_from_marks_file`
   returns the Link); `run` has `--size/--dark` for a `--track`.
3. **`run --workdir` was not passed to the verify and integrity stages** (they
   were other modules' `main()` behind a swapped `sys.argv`, given only some of
   the options), so those stages opened the clip in the shared cache and
   extracted there. Gone with the refactor: one Clip is handed to every stage.
4. **The `layers` template cache did not know what it was made from.** Its name
   had k, step, n0, n1 and *whether* there was a track: a second run with a
   different track, `--mask-rows` or `--max-shift` silently reused the first's
   templates. And `test_golden`'s PR144 window had been finding templates left
   in `/tmp/mcdonald` on 2026-09-19 — 25 s instead of five minutes, testing the
   masks, the classes and the consensus and no registration at all. Now the
   name carries a hash of reach, rows and the track; `layers --fresh` measures
   again; `test_golden` passes it.
5. **The report's "Reproduce" section did not reproduce**: no `--n0/--n1`, no
   `--mask-rows`, no `--step 2` on the co-motion line, no size or polarity.
   `run_case` now writes each command with what it was actually given.
6. **Exit 1 for a result that is not a bug.** `comotion` with no usable pair and
   `symbology` with no pointer returned 1, which `clip.EXIT_CODES` reserves for
   a traceback. They exit 5 now, with the sentence in the envelope, and
   `kinematics` on a track too short exits 5 rather than 4.

### Decisions: one put to Jacob and answered, three that are mine to confirm

- **With a track, `run`'s layers stage is the whole `layers` measurement** —
  about a second per frame pair, so minutes where it was seconds. It is what
  `run`'s docstring always claimed ("the same code the standalone subcommand
  runs") and it is the toolkit's headline number, but it changes how long `run`
  takes. `--skip layers` is the quick run; without a track it is still the
  one-pair look (`layers.glance`). **Put to Jacob on 2026-09-20, against "only
  on request behind a flag": he chose to keep the full measurement.** He also
  chose, for this session, each finished step committed to `main` and pushed.
- *Not asked, so still mine:* `run` gained `--names` and `--dark-below` (layers' own), so the bottom line
  can say "against the sea", and `--size/--dark`.
- The window's track sheet is laid out six tiles across (`measure_qt.
  sheet_layout`), not the command line's thirty: thirty is one 11,520 px row to
  scroll sideways. What the sheet measures does not depend on it, and the test
  that compares the window's case with the command line's compares fields.
- A sheet closed without an answer is "no". The default button is "No, or I
  cannot tell".

## Next, in the order I would do it

1. **A real hand on Measure.** Nobody has used the panel with a mouse: start
   `mcdonald-gui`, open PR113 by id (400–420), two clicks, `l`, `m`. Under Xvfb
   it has been driven end to end on the planted clip and looked at in
   screenshots, which is not the same thing. Things I would watch: whether the
   form's eleven fields are too many at once (they are `stages.KNOWN`, the same
   rows as `run --help`); whether minutes of `layers` with only a line of text
   for progress is tolerable (`layers.measure` has no per-pair progress hook —
   `Pool.map` — and `imap` would give one cheaply).
2. **A Mac.** Unchanged from before, plus the new panel: the menu roles (only
   "Save and quit" may move to the application menu), single-letter shortcuts
   in a native menu bar (`m` is one more), tool windows, `QStandardPaths`, the
   process pools under spawn (the stages' pools now start from a thread of the
   window, as the link's always did), `QDesktopServices.openUrl` for Open the
   case folder. `gui.desktop_entry` refuses on macOS with a sentence; what a Mac
   person double-clicks is undecided.
3. **The report, for someone who cannot open a folder of PNGs with confidence.**
   The report page shows `_case.md`; the figures it rests on (`_layers.png`, the
   integrity figure, the track sheet, the strips) are files behind "Open the
   folder". Showing them in the page, under the stage they belong to, is the
   obvious next thing (`Found.files` already says which stage wrote which).
4. **Stopping.** "Stop after this stage" is all there is, because a stage is a
   `Pool.map`. Closing the window mid-measure leaves the stage to finish on a
   daemon thread. A `stop` polled between pairs (as `autolink` has) would fix
   both, and the same `imap` gives item 1 its progress.
5. **`symbology` is not a stage of `run`** and never was: a case report has no
   north-pointer reading in it. `symbology.measure` returns a `Found` like the
   others, so adding it is a few lines in `run_case` — and a decision about
   where it goes in the report.
6. **A `Case` cannot be read back from `_case.json`.** So "I have now looked at
   the sheet" means measuring again. With fields in the file it could be
   reloaded, the verify stage amended, and the report rewritten.
7. Smaller, noticed and not done: `contact_strip` still draws a mark a third of
   a pixel up and left at zoom 3 (`look.crop_view` is right and pinned); the
   cases folder and the last range are not remembered between starts;
   `mark --set` always records an agent; the start dialog and the catalog
   chooser are modal and no test drives them; `layers --validate` and
   `--composite` print and are not in the fields; `Case.result` still holds
   formatted strings beside `fields` (the report is printed from them), and
   `Case._num` still parses them for a hand-built case.

**Jacob's decisions (2026-09-20), which §5 asked for** — unchanged:

1. "GUI only" covers the **whole job, staged**. *(Now built.)*
2. An agent **may** decide which thing is the object, **recorded as the
   agent's**: `how = "agent: <why>"`, excluded from `by_hand()`, and a report
   built on it says so on its face.
3. Platforms for the person at the window: **Linux and macOS.** macOS is
   *unverified*: nothing here has run on a Mac.
4. Installation: **`pip install` once is acceptable**; no bundled app for now.
5. Commits: each finished step straight to `main` and pushed, *asked once per
   session*.

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

*As it stood at the start of the UI session. Since closed: every row — the
six measuring commands' numbers became fields in the measurements session.
`docs/agents.md` is the worked session, and lists each command's fields.*

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
wrong — and, in the measurements session, measure and read the results
(Measure → Measure this clip; `measure_qt.py`). Every row is closed.*

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
- **An editable install runs whatever is in the tree at that moment.** A
  "before" baseline started as `mcdonald …` picks up every edit made while it
  runs (this session's first baseline had to be thrown away for that). Export
  the committed source — `git archive HEAD src | tar -x -C somewhere` — set
  `PYTHONPATH` to it and run `python3 -m mcdonald.cli`; snapshot the "after" the
  same way if you mean to go on editing while it measures.
- **A private work directory costs nothing: symlink the frames.** `Clip` asks
  only whether the first and last frame of the window exist, so a directory of
  symlinks into `/tmp/mcdonald/<stem>` is a work directory that extracts
  nothing, shares no `.npz` cache, and cannot grow the shared one. (The same
  fact is why a shared cache holding 90–340, asked for 300–500, extracts
  300–500 again.)
- **A cache beside the frames outlives the code that made it.** `layers`'
  templates did; see "Found on the way", 4. A test documented as five minutes
  that takes 25 s is not testing what it says.
- **`pkill -f pattern` kills the shell that runs it**, when the pattern is in
  that shell's own command line. Kill by pid.
- **A pixmap cannot be taller than 32767 px**, and a track sheet of a long clip
  at six tiles across would be. `measure_qt.sheet_layout` widens it instead,
  and the sheet window says so rather than showing an empty box if it is null.
- **A signal emitted from a thread to a panel that has gone raises
  RuntimeError** in that thread. The measuring thread's `say`, `progress` and
  `done` go through `tell()`, which lets it end quietly.
- **The Measure panel is a plain dialog, not a tool window**, on purpose: the
  tool windows keep the main window's single-letter shortcuts live while they
  have the focus, which is right for a strip and wrong for a form in which
  someone types "sea".
- Use **Technical Note clips** for real trials: PR113 (`--n0 400 --n1 420`, marks
  408 → (1009, 313), 411 → (702, 604), must give 142 px/frame) and PR144
  (`--n0 300 --n1 500`, vendored track in `tests/golden/`). PR148 is a poor
  demo: its object is far larger than the default detector scale.

## 7. First moves

1. Read the top of this file, then `src/mcdonald/stages.py` (its docstring and
   `run_case`) and `src/mcdonald/measure_qt.py`: between them they are what this
   session built.
2. Run the suites (§8). `test_gui` is about three minutes now, `test_golden`
   about seven with `--fresh`.
3. Put the three decisions that are still mine ("Decisions", above) to Jacob:
   `run`'s new options, the window's six-across sheet, and an unanswered sheet
   counting as "no".
4. Start `mcdonald-gui` on the desktop, open PR113 by its id, two clicks, `l`,
   `m`: nobody has yet used Measure with a real hand ("Next", 1).

## 8. State at handoff

- `main` is pushed and clean. This session's commits: `8acd5e9` (run.py taken
  apart into stage functions; fields in every `--json`; the six fixes — tested
  as a unit in a worktree of itself before it was pushed) and the one that
  carries this file (Measure from the window; Help → Getting started).
- Suites, all passing on the final tree: `test_measurement` 82 checks,
  `test_reduction` 93 (was 85), `test_published` 32, `test_cli` 43 (was 37; 90
  s), `test_gui` 396 with only WxAgg skipping (was 369; about two minutes, the
  Qt child's deadline is now 420 s because it measures three cases), and
  `test_golden` 12 on the corpus in 363 s — it measures again now (`--fresh`)
  where it had been reading a cache.
- The baseline this session's refactor was held to, all on the two Technical
  Note windows, committed source against refactored source: see "Where things
  stand". The numbers, for whoever next needs them: PR144 300–500 with the
  vendored track, `--names striated=sea,isotropic=cloud tops --dark-below 100
  --mask-rows 985:1080:1:165`: object against the sea 599 px/s (16–84 %:
  588–606, 82 windows), against the cloud tops 500 (488–508, 172), the cloud
  tops against the sea 99, ratio 6.0, groups 97 px/s apart in 40.3 % of pairs;
  north pointer 67/67 frames, radius 312.82 ± 0.39 px, +0.017 deg/s; co-motion
  at D = 60: MOVES THROUGH, 36.5 D, 8.76 D/s (at D = 12 the annulus is smaller
  than a template: NO POWER, exit 5); `run`: 2 integrity tests pass, none flag,
  9 without power, 18 repeated frames. PR113 400–420 from the two documented
  clicks placed with `--set`: 4 frames linked at 21 px dark, 4269 px/s (142.3
  px/frame), and `layers` has no power on 0.7 s of clip, which it now says.
  Timings on this machine (12 cores, 10 processes): `layers` on 196 pairs 333
  s cold; `run` on PR144 300–500 with integrity and co-motion about 30 min;
  `run` on PR113's 21 frames about 4 min.
- Real trials of the window's Measure: under Xvfb only, on the planted clip as
  a video (`test_cli.planted_video`), and looked at in screenshots — the panel,
  the sheet with its question, the report page. Not yet with a hand, and not yet
  on a corpus clip ("Next", 1).
- Environment: as before (Fedora 44, Python 3.14.7, PySide6-Essentials 6.11.2,
  editable install). There is no linter installed (no ruff, flake8 or
  pyflakes); this session checked for unbound names with a few lines of `ast`.
  `MCDONALD_CATALOG` is **not** exported in a fresh shell:
  `export MCDONALD_CATALOG=/hugespace/local/research/uap/pursue_index/records.csv`
- No desktop entry was written on this machine (as before).
- `/tmp` at the end of the session: everything this session made was in its own
  scratch directory (work directories of symlinks, the exported source trees,
  both baselines, screenshots), removed at the end. The shared frame caches
  under `/tmp/mcdonald` have the frame counts they started with (PR144 1–837,
  PR113 400–420); the one file the session added there, the templates
  `test_golden --fresh` wrote under their new hashed name, was removed. Left
  alone because they were not this session's: four `bg_layers_*_1.npz` from
  2026-09-19/20 under the old naming, which nothing reads any more (4.6 MB).
  No `mcdonald-*` directories were left in `/tmp`. Also not this session's, and
  left: four `/tmp/tmp*` directories of planted-clip frames dated 11:55–12:13 on
  2026-09-20 (19 MB), from an earlier session's trials.
- Not done, on purpose: an FFT route through `source_candidates`
  (`handoff-gui.md` §0.2), and any run on macOS or Windows.
