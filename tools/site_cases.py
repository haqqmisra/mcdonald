"""The website's cases page, from the reference case files: one card a video, one page a video, each object's report.

    python3 tools/site_cases.py                       # from $MCDONALD_DATA/cases (tests/reference_data.py finds it)
    python3 tools/site_cases.py --cases DIR           # from another folder of .mcdonald files

Writes docs/cases/ (git ignores it, as it does every cases/ folder): index.md, a page for each file, and under
<tag>/object-N/ each object's report as the toolkit wrote it (<tag>_case.md) with its figures and tables -- every file in the
object's folder but the track sheet's every-frame picture, which is tens of megabytes; the report says where it is.
cases/pages.txt is the order for the site's menu (tools/site_hooks.py reads it): the order of the folder README's
table, which is the Technical Note's cases and then the bird paper's.

Nothing is measured: the words and numbers are the files', and the folder README's row for each video is set
under its conclusions as "Against the paper".
"""
import argparse
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tests"))

import reference_data  # noqa: E402

OUT = HERE.parent / "docs" / "cases"
SHEET = "_all_frames.jpg"
FIGURES = ("track_frame", "size_speed", "beat")      # the report's own "Figures", in its order
THUMB = 720                                          # the card's picture, in pixels across


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--cases", type=Path, default=reference_data.root() / "cases")
    args = parser.parse_args(argv)
    readme = (args.cases / "README.md").read_text(encoding="utf-8") if (args.cases / "README.md").exists() else ""
    rows = {m[1]: (m[2].strip(), m[3].strip()) for m in re.finditer(r"^\| `(\w+)` \|(.*?)\|(.*?)\|$", readme, re.M)}
    files = sorted(args.cases.glob("*.mcdonald"))
    files.sort(key=lambda f: list(rows).index(f.stem) if f.stem in rows else len(rows))
    if not files:
        sys.exit(f"no .mcdonald files in {args.cases}")
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    cards = [case_page(f, rows.get(f.stem)) for f in files]
    (OUT / "index.md").write_text(index_page(cards), encoding="utf-8")
    (OUT / "pages.txt").write_text("".join(f"cases/{c['tag']}.md\n" for c in cards), encoding="utf-8")
    print(f"{len(cards)} cases, {sum(len(c['objects']) for c in cards)} objects -> {OUT}")


def case_page(path, row):
    z = zipfile.ZipFile(path)
    share = json.loads(z.read("share.json"))
    tag, video = share["tag"], share["video"]
    catalog = video.get("catalog") or {}
    labels = share.get("objects") or {}
    objects = []
    for n in sorted({int(m[1]) for m in (re.match(r"case/object-(\d+)/", name) for name in z.namelist()) if m}):
        folder = f"case/object-{n}/"
        report = z.read(f"{folder}{tag}_case.md").decode("utf-8")
        to = OUT / tag / f"object-{n}"
        to.mkdir(parents=True)
        for name in z.namelist():
            if name.startswith(folder) and not name.endswith(SHEET) and not name.endswith("/"):
                (to / name[len(folder):]).write_bytes(z.read(name))
        (to / f"{tag}_case.md").write_text(site_report(report, tag), encoding="utf-8")
        label = labels.get(str(n), str(n))
        objects.append({"n": n, "name": f"Object {label}", "frames": frames(report),
                        "headline": headline(report), "conclusion": conclusion(report),
                        "figures": [f for f in FIGURES if (to / f"{tag}_{f}.png").exists()]})
    thumb = thumbnail(OUT / tag / "object-1" / f"{tag}_track_frame.png", OUT / f"{tag}.jpg")

    title = catalog.get("title") or video["name"]
    lines = [f"# {catalog.get('id', tag.upper())}", "", f"**{title}**", ""]
    lines += [f"`{video['name']}`, {video['width']}x{video['height']}, {len(objects)} "
              f"object{'s' if len(objects) != 1 else ''}."]
    if catalog.get("url"):
        lines[-1] += f" [The video]({catalog['url']}) ({video['bytes'] / 1e6:.0f} MB)."
    for note in share.get("thread", []):
        lines += ["", "!!! note \"What this file is\"", "", "    " + note["text"]]
    if row:
        lines += ["", "## Against the paper", "", "| | the numbers |", "|---|---|",
                  f"| the toolkit's report | {row[0]} |", f"| the paper | {row[1]} |"]
    for o in objects:
        lines += ["", f"## {o['name']}" + (f" — frames {o['frames']}" if o["frames"] else ""), "",
                  o["conclusion"], ""]
        lines += [f"![{o['name']}: {f.replace('_', ' ')}]({tag}/object-{o['n']}/{tag}_{f}.png)" for f in o["figures"]]
        lines += ["", f"[The whole report]({tag}/object-{o['n']}/{tag}_case.md){{ .md-button }}"]
    lines += ["", "## Open it yourself", "", "With mcdonald installed, the case file opens in the window with every "
              "object's track drawn, and measures each object again:", "", "```bash",
              f"mcdonald share open {tag}.mcdonald", f"mcdonald share rerun {tag}.mcdonald --strict", "```", ""]
    (OUT / f"{tag}.md").write_text("\n".join(lines), encoding="utf-8")
    return {"tag": tag, "id": catalog.get("id", tag.upper()), "title": title, "objects": objects, "thumb": thumb,
            "row": row, "bird": any("bird paper" in note["text"] for note in share.get("thread", []))}


def index_page(cards):
    lines = ["# Cases", "",
             "What mcdonald says about the PURSUE videos that two papers rest on: the Technical Note's cases, and the "
             "bird paper's flock and its Table 1. Each card is one video's reference case file, with every object "
             "followed, measured and reported. The words are the reports' own, and each video's page sets its numbers "
             "beside the paper's.", "",
             "!!! info \"Provisional\"", "",
             "    These reports were written by an agent's run, and nobody has yet said the track was on the object in "
             "every frame. Until someone does, each report calls its numbers provisional.", "",
             ""]
    groups = {"From the Technical Note": [c for c in cards if not c["bird"]],
              "From the bird paper": [c for c in cards if c["bird"]]}
    for group, these in groups.items():
        if not these:
            continue
        lines += [f"## {group}", "", '<div class="grid cards" markdown>', ""]
        for c in these:
            heads = sorted({o["headline"] for o in c["objects"] if o["headline"]},
                           key=[o["headline"] for o in c["objects"]].index)
            lines += [f"-   [![{c['id']}]({c['thumb']})]({c['tag']}.md)" if c["thumb"] else f"-   **{c['id']}**", "",
                      f"    **[{c['id']}]({c['tag']}.md)** · {len(c['objects'])} object{'s' if len(c['objects']) != 1 else ''}",
                      "", f"    *{' · '.join(heads) or '—'}*", ""]
            if c["row"]:
                lines += [f"    {c['row'][0]}", ""]
        lines += ["</div>", ""]
    return "\n".join(lines)


def section(report, name):
    m = re.search(rf"^## {name}\n(.*?)(?=^## |\Z)", report, re.M | re.S)
    return m[1].strip() if m else ""


def conclusion(report):
    return section(report, "Conclusion")


def headline(report):
    m = re.match(r"\*\*(.+?)\*\*", conclusion(report))
    return m[1].rstrip(".") if m else ""


def frames(report):
    m = re.search(r"frames (\d+)-(\d+)", report.splitlines()[2] if len(report.splitlines()) > 2 else "")
    return f"{m[1]}–{m[2]}" if m else ""


def site_report(report, tag):
    # the track sheet's every-frame picture stays in the case file
    return re.sub(rf"!\[([^\]]*)\]\({re.escape(tag)}{SHEET}\)",
                  rf"*The track sheet, every frame with the object circled: `{tag}{SHEET}` in the case file.*", report)


def thumbnail(png, jpg):
    if not png.exists():
        return ""
    try:
        from PIL import Image
    except ImportError:
        return f"{png.parent.parent.name}/{png.parent.name}/{png.name}"
    im = Image.open(png).convert("RGB")
    im.thumbnail((THUMB, THUMB * 2))
    im.save(jpg, quality=85)
    return jpg.name


if __name__ == "__main__":
    main()
