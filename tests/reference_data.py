"""Where the tests and tools/ find the reference data that is not in the repository.

Every table and track they read is in tests/golden/. The footage is too large for git and
lives in one folder: $MCDONALD_DATA, or, when that is unset, data/mcdonald beside this
repository (/models/mcdonald -> /models/data/mcdonald). Its layout:

    pursue/    PURSUE clips, under the file names the shipped catalog gives them
    galileo/   the Galileo Project flyer clips of the PR135 paper (flyer1_*.mp4 ... flyer5_*.mp4)
    footage/   other footage: tl8_etApsro.mp4, the WA9ONY-5 balloon

The folder's README.md says where each file came from. A PURSUE clip that is not in pursue/
is looked for where the active catalog keeps it (the storage folder `mcdonald` downloads into,
or a mirror named by MCDONALD_CATALOG). MCDONALD_GALILEO and MCDONALD_FOOTAGE still name the
galileo/ and footage/ folders directly, for anyone who has them elsewhere.
"""
import os
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
GOLDEN = REPO / "tests" / "golden"


def root():
    env = os.environ.get("MCDONALD_DATA", "").strip()
    return Path(env).expanduser() if env else REPO.parent / "data" / "mcdonald"


def galileo():
    env = os.environ.get("MCDONALD_GALILEO", "").strip()
    return Path(env).expanduser() if env else root() / "galileo"


def footage():
    env = os.environ.get("MCDONALD_FOOTAGE", "").strip()
    return Path(env).expanduser() if env else root() / "footage"


def pursue_clip(record_id):
    """(path, None) for a PURSUE record id, or (None, why it is not here)."""
    from mcdonald import catalog
    active = catalog.active()
    hits = [] if isinstance(active, catalog.NullCatalog) else active.by_id(record_id)
    names = [Path(h.get("path", "")).name for h in hits] or \
            [Path(h["path"]).name for h in catalog.ShippedCatalog().by_id(record_id)]
    if not names:
        return None, f"{record_id} is in no catalog"
    for name in names:
        p = root() / "pursue" / name
        if p.exists():
            return p, None
    for h in hits:
        p = Path(h.get("path", ""))
        if p.exists():
            return p, None
    return None, f"{record_id} ({names[0]}) is neither in {root() / 'pursue'} nor in the {active.name} catalog's folder"
