"""A shared file: one file to send someone, that opens where its sender left off (share.py).

    python3 tests/test_share.py

Jacob, 2026-10-15: "it would be useful if I had a single file that I could send him that contained the information
that he could immediately pick up where I left off". What this holds the file to, with no window:

- what goes in comes out: the marks (each still saying who placed it), the tracks, every object's folder, the files
  sent with it, the stretches to look at and the thread of notes, oldest first;
- the video is named, not carried: by its file's name, size and SHA-256, and found again by name next to the file
  or in a folder it is told of; a different file of the same name is said to be different;
- opening never writes over anything: each opening is a folder of its own, and a file whose names would land
  outside it is refused before anything is written; only data and pictures come out;
- an answer carries the thread on: the second file has both notes, the first's first;
- an agent's file, made from tracks alone (`--object LABEL=TRACK.csv`), says it is an agent's, and so do its marks;
- the command line: `share make`, `share show` and `share open --no-window`, each with --json.

Portable: needs ffmpeg, and no video data (test_cli's drawn video).
"""
import json
import os
import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

FAIL = []


def check(cond, label, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}" + (f"  [{detail}]" if detail else ""))
    if not cond:
        FAIL.append(label)


def main():
    import shutil
    if shutil.which("ffmpeg") is None:
        print("SKIP: ffmpeg is not installed")
        return 0
    import test_cli
    from test_cli import mcdonald, planted_video, as_json
    from mcdonald import share
    from mcdonald.mark import MarkSet
    with tempfile.TemporaryDirectory(prefix="mcdonald-share-test-") as td:
        td = Path(td)
        test_cli.TMP[:] = [str(td)]
        os.environ["MCDONALD_HOME"] = str(td / "home")
        os.environ.pop("MCDONALD_CATALOG", None)
        _, video = planted_video(td)
        tag = video.stem.lower()

        print("\nmaking one from a results folder")
        case = td / "sender" / tag
        (case / "object-1").mkdir(parents=True)
        ms = MarkSet(tag, str(video), 30000 / 1001)
        ms.add("object", 3, 100.0, 120.0)                                  # a hand's
        ms.add("object", 9, 160.0, 150.0, how="agent: candidate 1 of 4")   # an agent's
        ms.save(case / f"{tag}_marks.json")
        ms.save(case / "object-1" / f"{tag}_marks.json")
        (case / "object-1" / f"{tag}_autotrack.csv").write_text("frame,x_px,y_px\n3,100,120\n4,110,125\n", encoding="utf-8")
        (case / "object-1" / f"{tag}_case.md").write_text("# a report\n", encoding="utf-8")
        (case / "frames").mkdir()
        (case / "frames" / "f00001.png").write_bytes(b"not a result")       # frames never go in
        (case / "big.bin").write_bytes(b"\0" * 10)                           # nor anything that is not data or a picture
        fig = td / "figure.png"
        fig.write_bytes(b"\x89PNG\r\n\x1a\n")
        out = td / "one.mcdonald"
        share.make(out, video, folder=case, part=(2, 20), look=[(3, 9, "the beat")], note="Bird? Look at 3-9.",
                   by="Jacob", attach=[fig], objects={1: "the bright one"}, when="2026-10-15T08:00:00+00:00")
        m = share.read(out)
        names = set(zipfile.ZipFile(out).namelist())
        check(m["format"] == share.FORMAT and m["video"]["name"] == video.name and m["video"]["bytes"] == video.stat().st_size
              and len(m["video"]["sha256"]) == 64, "it names the video by its file's name, size and SHA-256",
              f"{m['video']['name']}, {m['video']['bytes']} bytes")
        check(not any(n.endswith(video.suffix) for n in names) and f"case/{tag}_marks.json" in names
              and f"case/object-1/{tag}_autotrack.csv" in names and "attached/figure.png" in names,
              "the video is not in it; the marks, every object's folder and the figure are", ", ".join(sorted(names)))
        check(not any("frames/" in n or n.endswith(".bin") for n in names), "frames and files that are not data stay out")
        check(m["part"] == [2, 20] and m["look"] == [{"first": 3, "last": 9, "what": "the beat"}]
              and m["objects"] == {"1": "the bright one"} and m["thread"][0]["text"] == "Bird? Look at 3-9."
              and m["thread"][0]["by"] == "Jacob" and m["thread"][0]["agent"] is False,
              "the part, the stretch to look at, the object's name and the note are in it")

        print("\nopening it")
        recv = td / "receiver"
        folder, m2 = share.unpack(out, recv)
        back = MarkSet(tag, str(video), 30000 / 1001).load(folder / f"{tag}_marks.json")
        check(folder.parent == recv and folder.name.startswith(f"{tag}-from-jacob") and (folder / "object-1" / f"{tag}_case.md").exists()
              and (folder / "attached" / "figure.png").exists(), "it opens into a folder of its own, with what came in it", folder.name)
        check(back.kind("object", 3) == "hand" and back.kind("object", 9) == "agent",
              "each mark still says who placed it: a hand's is a hand's, an agent's an agent's")
        again, _ = share.unpack(out, recv)
        check(again != folder and folder.exists(), "opening it twice makes a second folder, never writing over the first", again.name)
        check(share.find_video(m2, also=[video.parent]) == video and share.check_video(video, m2["video"])[0],
              "the video is found by its name where it is, and is the same file")
        other = td / "elsewhere" / video.name
        other.parent.mkdir()
        other.write_bytes(video.read_bytes()[:-10] + b"0123456789")
        same, said = share.check_video(other, m2["video"])
        check(not same and "SHA-256" in said, "a different file of the same name and size is said to be different", said[:70])

        print("\nwhat is refused")
        for bad, why in (("case/../../escape.txt", "a name with .. in it"), ("/etc/escape.txt", "an absolute name")):
            evil = td / "evil.mcdonald"
            with zipfile.ZipFile(evil, "w") as z:
                z.writestr("share.json", json.dumps(m))
                z.writestr("case/ok.json", "{}")
                z.writestr(bad, "x")
            try:
                share.unpack(evil, td / "evil-cases")
                refused = False
            except share.ShareError:
                refused = True
            check(refused and not (td / "evil-cases").exists() and not (td / "escape.txt").exists(),
                  f"{why} is refused before anything is written")
        notzip = td / "notzip.mcdonald"
        notzip.write_text("hello", encoding="utf-8")
        try:
            share.read(notzip)
            said = ""
        except share.ShareError as ex:
            said = str(ex)
        check("not a shared mcdonald file" in said, "a file that is not one is said not to be", said[:60])

        print("\nanswering it")
        ans = td / "two.mcdonald"
        share.make(ans, video, folder=folder, note="Looks like a bird to me.", by="Ravi", when="2026-10-15T09:00:00+00:00")
        m3 = share.read(ans)
        check([n["by"] for n in m3["thread"]] == ["Jacob", "Ravi"] and m3["thread"][1]["text"] == "Looks like a bird to me."
              and m3["look"] == m["look"] and m3["part"] == m["part"] and "attached/figure.png" in m3["attached"],
              "the answer carries the thread on, oldest first, with the stretches, the part and the figure",
              " -> ".join(n["by"] for n in m3["thread"]))

        print("\nthe command line")
        track = td / "track.csv"
        track.write_text("# a track\nframe,x_px,y_px\n" + "".join(f"{n},{100 + 3 * n},{120 + n}\n" for n in range(2, 22)), encoding="utf-8")
        rc, outp, err = mcdonald("share", "make", video, "--object", f"left point={track}", "--look", "5-15:flapping",
                                 "--note", "agent's look", "--by", "Claude", "--agent", "--out", td / "agent.mcdonald",
                                 "--json", cwd=td)
        d = as_json(outp)
        ok = rc == 0 and d is not None
        check(ok and d["manifest"]["thread"][-1]["agent"] is True and d["manifest"]["part"] == [2, 21]
              and d["manifest"]["objects"] == {"1": "left point"}, "`share make --object` from a track alone: an agent's file, "
              "the part from the track", (err or "")[-200:])
        rc, outp, err = mcdonald("share", "show", td / "agent.mcdonald", cwd=td)
        check(rc == 0 and "Claude (an AI agent)" in outp and "Look at frames 5–15: flapping" in outp,
              "`share show` says who it is from, that it is an agent, and what to look at", outp.splitlines()[1][:70] if outp else err[-200:])
        shutil.copy(video, td / video.name) if not (td / video.name).exists() else None
        rc, outp, err = mcdonald("share", "open", td / "agent.mcdonald", "--no-window", "--cases", td / "opened", "--json", cwd=td)
        d = as_json(outp)
        ok = rc == 0 and d is not None
        folder = Path(d["folder"]) if ok else None
        mk = MarkSet(tag, str(video), 30000 / 1001).load(next(folder.glob(f"object-1/*_marks.json"))) if ok else None
        check(ok and d["same"] and mk is not None and all(mk.kind("object", n) == "agent" for n in mk.marks["object"]),
              "`share open --no-window` unpacks it, finds the video beside it, and the marks made from the track are an agent's",
              (err or "")[-200:])
    print(f"\n{'FAILED: ' + str(len(FAIL)) if FAIL else 'all passed'}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
