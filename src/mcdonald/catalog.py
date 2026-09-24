"""Where a clip's provenance comes from — and what to do when there is none.

The toolkit runs on any video file. A *catalog* is optional context: a table
that, given a file, can say what the releasing body called it, whether the
release disclosed an alteration, and how many of its clips carry such a
disclosure. With no catalog the tools still run; the report simply has no
provenance section, and record ids do not resolve.

This is the module that keeps the rest of the package corpus-independent. The
PURSUE (war.gov/UFO) release is one backend, not a built-in assumption.

The package ships the PURSUE videos' list (`pursue_videos.csv`, written by
tools/ship_catalog.py): with nothing configured, that is the catalog, so that
PR113 means something on a computer with no mirror of the release, and a video
that is not on it yet is downloaded from DVIDS into the storage folder
(`mcdonald.storage`) the first time it is named. A clip that is not in it gets
"no record for this file" and nothing borrowed.

Configuring a catalog
    export MCDONALD_CATALOG=/path/to/pursue_index/records.csv   # a mirror of your own
    export MCDONALD_CATALOG=none                                # no catalog at all

or in Python::

    from mcdonald import catalog
    catalog.use(catalog.PursueCatalog("~/research/uap/pursue_index/records.csv"))

Writing another backend: subclass Catalog and implement videos(). Each record
is a plain dict; every field is optional and consumers must tolerate its
absence. The fields the toolkit looks for are

    path        str   location of the media file, absolute or relative to root
    title       str   what the releasing body calls it
    id          str   short record id, e.g. "PR144" (else derived from title)
    release     str   tranche/batch label
    blurb       str   the release's own description — scanned for disclosures
    redacted    str   whatever the source says about redaction
    url         str   where the file can be downloaded, if `path` is not there
    bytes       int   its size, which a download must come to

Nothing here should ever be imported for its side effects; a catalog is only
consulted when a tool asks.
"""
import csv
import os
import re
from pathlib import Path

from . import storage

# Sentences in which a releasing body admits the imagery is not a plain
# recording. Kept here rather than in integrity.py: it is a statement about
# release text, not about pixels.
DISCLOSURE = re.compile(
    r"[^.]*\b(digitally altered|altered before|recreation|re-creation|animation|"
    r"artificial intelligence|AI[- ]generated|no edits|alterations)\b[^.]*\.", re.I)


class Catalog:
    """A source of provenance records. Subclass and implement videos()."""

    name = "catalog"

    @property
    def label(self):
        """The name as a person reads it; `name` is what the reports' JSON records."""
        return self.name

    def videos(self):
        """All video records, as dicts (see the module docstring)."""
        return []

    def by_path(self, path):
        """The record for a media file, matched on basename, or None."""
        name = Path(path).name
        return next((r for r in self.videos() if Path(r.get("path", "")).name == name), None)

    def by_id(self, key, release=None):
        """Records whose id matches `key`, optionally within one release.

        Accepts a bare id (PR144) or a fully qualified one (FBI-UAP-PR005).
        The distinction matters: bare ids are not unique across releasing
        bodies — PR001-PR004 each exist under two prefixes in the PURSUE
        corpus — so a bare key returns every match and lets the caller report
        the ambiguity rather than silently taking the first."""
        key = key.upper().strip()
        m = re.search(r"[A-Z]*\d+$", key)
        bare = m.group(0) if m else key
        qualified = bare != key
        out = []
        for r in self.videos():
            if (r.get("id") or "").upper() != bare:
                continue
            if release and str(r.get("release", "")) != release:
                continue
            if qualified and not (r.get("title") or "").upper().startswith(key):
                continue
            out.append(r)
        return out

    def disclosure(self, rec):
        """The release's own alteration statement for this record, or None."""
        m = DISCLOSURE.search(rec.get("blurb") or "") if rec else None
        return m.group(0).strip() if m else None

    def disclosure_rate(self):
        """(clips carrying a disclosure, clips in the catalog) — context for a
        report. Only meaningful for the catalog the clip actually came from."""
        recs = self.videos()
        flagged = [r for r in recs
                   if re.search(r"digitally altered|recreation", r.get("blurb") or "", re.I)]
        return len(flagged), len(recs)


class NullCatalog(Catalog):
    """No provenance available. The default."""

    name = "none"


class PursueCatalog(Catalog):
    """The U.S. DoW PURSUE releases, via the local mirror's `records.csv`.

    Expects the column layout that repository's build_index.py produces:
    type, title, release, redacted, blurb, out_path. Paths in `out_path` are
    relative to the mirror root (two levels above records.csv)."""

    name = "pursue"
    label = "PURSUE"

    def __init__(self, records_csv):
        self.csv = Path(records_csv).expanduser().resolve()
        self.root = self.csv.parent.parent
        self._cache = None

    def videos(self):
        if self._cache is None:
            self._cache = []
            if self.csv.exists():
                with open(self.csv, newline="") as f:
                    for r in csv.DictReader(f):
                        if r.get("type") != "video":
                            continue
                        title = r.get("title", "")
                        m = re.search(r"PR\d+", title)
                        self._cache.append({
                            "path": str(self.root / r["out_path"]) if r.get("out_path") else "",
                            "title": title,
                            "id": m.group(0) if m else "",
                            "release": r.get("release", ""),
                            "blurb": r.get("blurb", ""),
                            "redacted": r.get("redacted", ""),
                        })
        return self._cache


class ShippedCatalog(Catalog):
    """The PURSUE videos, as the package knows them without a mirror: `pursue_videos.csv`
    beside this file. A record's path is where the storage folder keeps it once it has
    been downloaded (under the mirror's file name, so by_path knows a copy from either)."""

    name = "pursue"
    label = "PURSUE"
    CSV = Path(__file__).with_name("pursue_videos.csv")

    def __init__(self):
        self._cache = None

    def videos(self):
        if self._cache is None:
            with open(self.CSV, newline="", encoding="utf-8") as f:
                self._cache = [dict(path=str(storage.videos() / r["file"]), title=r["title"],
                                    id=(re.search(r"PR\d+", r["title"]) or [""])[0], release=r["release"],
                                    blurb=r["blurb"], redacted=r["redacted"], url=r["url"], bytes=int(r["bytes"]))
                               for r in csv.DictReader(f)]
        return self._cache


_active = None


def use(catalog):
    """Install a catalog for this process. Pass None to clear."""
    global _active
    _active = catalog
    return _active


def active():
    """The catalog in force, configuring one from the environment on first use.

    MCDONALD_CATALOG may name a PURSUE-style records.csv, or be "none". Unset,
    or naming a file that is not there, it is the list the package ships. A clip
    in no catalog is a normal condition, not an error: most clips are in none."""
    global _active
    if _active is None:
        env = os.environ.get("MCDONALD_CATALOG", "").strip()
        _active = (NullCatalog() if env.lower() == "none" else
                   PursueCatalog(env) if env and Path(env).expanduser().exists() else ShippedCatalog())
    return _active
