"""Write the PURSUE list that ships inside the package, from a mirror's records.csv.

Someone who installs mcdonald has no mirror of the PURSUE release, so a name such as PR113
could not be looked up, and the video behind it would have to be found and fetched by hand.
`src/mcdonald/pursue_videos.csv` is what the package knows without one: every video's title,
release and the release's own words about it, the file it is (the mirror's file name, so that
a copy already on disk is recognised), and where DVIDS serves it, with its size, which is how
a download is known to be whole (`mcdonald.storage.download`).

    python3 tools/ship_catalog.py /hugespace/local/research/uap/pursue_index/records.csv

Run it when a new release is added to the mirror. Most records name the file on DVIDS's file
server; the rest name its page (www.dvidshub.net/video/N), and the page is read for the one
.mp4 it links. Every address is then asked for its size. On 2026-09-24 all 144 answered, each
page linked exactly one file, and the 85 file addresses were the same size as the mirror's
copies. Of the 59 from pages, 32 were the same size; 18 were a few kB larger (PR113 among
them: 67179987 bytes against the mirror's 67174905, the same 5291 frames, bit for bit, by
`ffmpeg -f framemd5`); 9 (FBI-UAP-PR001-006, NASA-UAP-D023-025) had been fetched by yt-dlp
and are other encodings, so their frames are not the mirror's.
"""
import argparse
import csv
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "src" / "mcdonald" / "pursue_videos.csv"
FILE = re.compile(r"https://d34w7g4gy10iej\.cloudfront\.net/[^\"'\s<>]+?\.mp4")
COLUMNS = ["title", "release", "redacted", "blurb", "file", "url", "bytes", "page"]


def fetch(args):
    return subprocess.run(["curl", "-sL", "-m", "60", "-A", "Mozilla/5.0", *args], capture_output=True, text=True).stdout


def resolve(r):
    """(the file's address, its size in bytes) for one record, or an exception's worth of why not."""
    url = r["source_url"]
    if "dvidshub.net/video/" in url:
        found = sorted(set(FILE.findall(fetch([url]))))
        if len(found) != 1:
            raise RuntimeError(f"{r['title']}: {url} links {len(found)} video files")
        url = found[0]
    head = fetch(["-I", url])
    m = re.search(r"content-length:\s*(\d+)", head, re.I)
    if not head.startswith("HTTP") or " 200" not in head.split("\n")[0] or not m:
        raise RuntimeError(f"{r['title']}: {url} answered {head.splitlines()[:1]}")
    return url, int(m.group(1))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("records", help="the mirror's pursue_index/records.csv")
    args = ap.parse_args()
    rows = [r for r in csv.DictReader(open(args.records, newline="")) if r.get("type") == "video"]
    got = list(ThreadPoolExecutor(8).map(resolve, rows))
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, COLUMNS)
        w.writeheader()
        for r, (url, size) in zip(rows, got):
            w.writerow(dict(title=r["title"], release=r["release"], redacted=r["redacted"], blurb=r["blurb"],
                            file=Path(r["out_path"]).name, url=url, bytes=size,
                            page=r.get("dvids") or (r["source_url"] if "dvidshub" in r["source_url"] else "")))
    print(f"wrote {len(rows)} videos, {sum(s for _, s in got) / 1e9:.1f} GB in all, to {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
