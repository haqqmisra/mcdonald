"""Does this install measure correctly? Synthetic scenes with known answers.

These tests ship with the package and need no video data: each builds a scene
whose true answer is known by construction, then checks the library recovers
it. Run them after installing, before trusting a number from a real clip.

    python3 tests/test_measurement.py        # or: pytest tests/

The separate tests/test_golden.py checks the published results of real clips,
and needs the corpus.
"""
import os
import sys
import tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from mcdonald import catalog, clip as clipmod, forensics as vf  # noqa: E402

RNG = np.random.default_rng(20260919)
FAIL = []


def check(cond, label, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}{'  ' + detail if detail else ''}")
    if not cond:
        FAIL.append(label)
    return cond


def isotropic(h, w, scale=3.0):
    """Cloud-like texture: smoothed noise, no preferred direction."""
    from scipy import ndimage
    return ndimage.gaussian_filter(RNG.normal(0, 1, (h, w)), scale) * 400 + 128


def striated(h, w):
    """Sea-like texture: wave crests along one axis, so the correlation peak is
    much flatter along the crests (the aperture problem, on purpose)."""
    from scipy import ndimage
    a = ndimage.gaussian_filter(RNG.normal(0, 1, (h, w)), (1.0, 9.0))
    return a * 700 + 128


def roll(a, dx, dy):
    return np.roll(np.roll(a, dy, axis=0), dx, axis=1)


# ---------------------------------------------------------------- registration
def test_recovers_a_known_shift():
    """The ruler itself: shift a real-looking scene by a known amount."""
    print("\nregistration: a known rigid shift")
    base = isotropic(600, 900)
    bad = np.zeros(base.shape, bool)
    for dx, dy in ((20, 0), (-37, 11), (5, -23)):
        f = vf.shift_field(base, roll(base, dx, dy), bad, bad, tpl=128, stride=96, reach=120)
        con = vf.consensus(vf.good(f)[:, 3:5])
        ok = con is not None and abs(con[0][0] - dx) < 0.5 and abs(con[0][1] - dy) < 0.5
        check(ok, f"recovers ({dx:+d}, {dy:+d})",
              f"got ({con[0][0]:+.2f}, {con[0][1]:+.2f}) from {con[1]} templates" if con else "no consensus")


def test_two_layers_are_not_averaged():
    """The PR144 failure: two backgrounds at different ranges. A single
    consensus would return a blend of the two and name neither."""
    print("\nlayers: two backgrounds moving differently")
    h, w = 600, 900
    scene_a, scene_b = striated(h, w), isotropic(h, w)
    split = 300
    f0 = np.vstack([scene_b[:split], scene_a[split:]])
    f1 = np.vstack([roll(scene_b, 12, 0)[:split], roll(scene_a, 40, 0)[split:]])
    bad = np.zeros(f0.shape, bool)
    g = vf.good(vf.shift_field(f0, f1, bad, bad, tpl=128, stride=64, reach=120))
    lay = vf.layers_of(g)
    check(lay["groups"] == 2, "two motion groups, not one blended rate",
          f"groups={lay['groups']}, gap={lay.get('group_gap', 0):.1f} px")
    iso, stri = lay["isotropic"], lay["striated"]
    check(iso is not None and abs(iso[0][0] - 12) < 2, "the isotropic (cloud-like) layer",
          f"{iso[0][0]:+.1f} px from {iso[1]} templates (truth +12)" if iso else "not found")
    check(stri is not None and abs(stri[0][0] - 40) < 2, "the striated (sea-like) layer",
          f"{stri[0][0]:+.1f} px from {stri[1]} templates (truth +40)" if stri else "not found")
    if iso and stri:
        check(abs((stri[0][0] - iso[0][0]) - 28) < 3, "layer against layer",
              f"{stri[0][0] - iso[0][0]:.1f} px apart (truth 28)")
    mixed = vf.consensus(g[:, 3:5])
    if mixed is not None:
        print(f"         (a single consensus over both would have said {mixed[0][0]:+.1f} px "
              "-- a rate against neither layer)")


def test_striation_is_classified():
    """Sea and cloud must be told apart by peak anisotropy, or the two layers
    cannot be named."""
    print("\nlayers: texture classes")
    bad = np.zeros((600, 900), bool)
    for name, scene, want_striated in (("striated (sea-like)", striated(600, 900), True),
                                       ("isotropic (cloud-like)", isotropic(600, 900), False)):
        g = vf.good(vf.shift_field(scene, roll(scene, 25, 0), bad, bad, tpl=128, stride=96, reach=120))
        ani = float(np.median(g[:, 7]))
        check((ani < 0.25) == want_striated, f"{name} classified",
              f"median anisotropy {ani:.3f}")


def test_windowed_correlation_would_have_been_biased():
    """Documents why the library searches for a whole template: the
    same-position windowed estimate under-reads a large shift."""
    print("\nregistration: whole-template search has no taper bias")
    base = isotropic(600, 900)
    bad = np.zeros(base.shape, bool)
    dx = 30
    f = vf.shift_field(base, roll(base, dx, 0), bad, bad, tpl=128, stride=96, reach=120)
    con = vf.consensus(vf.good(f)[:, 3:5])
    err = abs(con[0][0] - dx) / dx if con else 1.0
    check(err < 0.01, "large shift recovered to better than 1 %", f"error {err:.3%}")


# ---------------------------------------------------------------- cadence
def test_repeated_frames_are_found():
    """Clips that repeat ~7 % of frames make per-frame differences meaningless."""
    print("\ncadence: repeated frames")
    n, d = np.arange(1, 61), np.full(60, 4.0) + RNG.normal(0, 0.1, 60)
    planted = [11, 23, 24, 47]
    d[[p - 1 for p in planted]] = 0.001
    found = vf.repeats(np.column_stack([n, d]))
    check(found == planted, "finds exactly the planted repeats", f"{found}")


# ---------------------------------------------------------------- detection
def test_a_compact_source_is_found_and_linked():
    """A bright disc on a known path: detection, then linking into a track."""
    print("\ndetection: a compact source on a known path")
    h, w = 400, 700
    truth = {n: (60 + 9.0 * n, 150 + 3.0 * n) for n in range(1, 21)}
    cands = {}
    yy, xx = np.mgrid[0:h, 0:w]
    for n, (x, y) in truth.items():
        g = isotropic(h, w, scale=6.0) * 0.2 + 60
        g += 900 * np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * 3.0 ** 2))
        cands[n] = vf.source_candidates(g, np.zeros(g.shape, bool), size=6.0)
    found = sum(1 for n in truth if any(
        np.hypot(c[0] - truth[n][0], c[1] - truth[n][1]) < 2.0 for c in cands.get(n, [])))
    check(found == len(truth), "the object is among the candidates in every frame",
          f"{found} of {len(truth)}")
    trk = vf.link_track(cands, 1, 20)
    check(len(trk) >= 18, "the linker covers the path", f"{len(trk)} of 20 frames")
    if trk:
        err = max(np.hypot(xy[0] - truth[n][0], xy[1] - truth[n][1])
                  for n, xy in trk.items() if n in truth)
        check(err < 2.0, "and lands on the object", f"worst error {err:.2f} px")


# ---------------------------------------------------------------- masks
def test_a_redaction_block_is_masked_but_a_dark_scene_is_not():
    """Masking every dark pixel takes an object's sharpening halo with it. A
    block is large, static and black; a night sky is merely dark."""
    print("\nmasks: redaction blocks vs a dark scene")

    class Fake:
        def __init__(self, frames):
            self._f = frames
            self.n0, self.n1 = 1, len(frames)
            self.H, self.W = frames[0].shape[:2]

        def frames(self):
            return range(self.n0, self.n1 + 1)

        def rgb(self, n):
            return self._f[n - 1]

        def grey(self, n):
            return self._f[n - 1].mean(2)

    blocked = []
    for i in range(12):
        f = np.repeat(isotropic(300, 500, 4.0)[:, :, None], 3, axis=2).clip(0, 255)
        f[20:120, 30:200] = 0.0                      # a static black block
        blocked.append(f.astype(np.float32))
    m = vf.static_masks(Fake(blocked), n_sample=8)
    frac = m["blocks"][20:120, 30:200].mean()
    check(frac > 0.9, "a static black block is masked", f"{frac:.0%} of it")

    dark = []
    for i in range(12):
        f = np.repeat((isotropic(300, 500, 4.0) * 0.06 + 6).clip(0, 40)[:, :, None], 3, axis=2)
        dark.append(np.ascontiguousarray(roll(f, 3 * i, 0)).astype(np.float32))
    m2 = vf.static_masks(Fake(dark), n_sample=8)
    check(m2["blocks"].mean() < 0.10, "a dark moving scene is not",
          f"{m2['blocks'].mean():.0%} masked")


# ---------------------------------------------------------------- packaging
def test_output_never_lands_in_the_package():
    """The defect this package was split out to fix: a tool must not write into
    its own source tree because that is where the code happens to live."""
    print("\npackaging: where results go")
    pkg = Path(vf.__file__).resolve().parent
    with tempfile.TemporaryDirectory() as td:
        cwd = os.getcwd()
        try:
            os.chdir(td)
            os.environ.pop("MCDONALD_CASES", None)
            p = clipmod.out_prefix(None, "somecase")
            check(Path(td).resolve() in p.resolve().parents, "default case dir is under the cwd", str(p))
            check(pkg not in p.resolve().parents, "and nowhere near the package", str(pkg))
            check(p.parent.is_dir(), "the case dir is created")
            os.environ["MCDONALD_CASES"] = str(Path(td) / "cases")
            p2 = clipmod.out_prefix(None, "somecase")
            check(p2.parent.parent.name == "cases", "MCDONALD_CASES is honoured", str(p2))
            os.environ.pop("MCDONALD_CASES", None)
            p3 = clipmod.out_prefix(Path(td) / "explicit", "somecase")
            check(p3.parent.name == "explicit", "--out wins", str(p3))
        finally:
            os.chdir(cwd)


def test_no_catalog_is_a_normal_condition():
    """Most clips are not in any catalog. That must not be an error, and must
    not silently borrow another release's provenance."""
    print("\npackaging: the catalog is optional")
    catalog.use(None)
    os.environ.pop("MCDONALD_CATALOG", None)
    cat = catalog.active()
    check(isinstance(cat, catalog.NullCatalog), "defaults to no catalog", cat.name)
    check(cat.videos() == [], "which has no records")
    check(cat.by_path("/anything/at/all.mp4") is None, "and matches nothing")
    check(cat.disclosure_rate() == (0, 0), "and reports no disclosure rate")

    with tempfile.TemporaryDirectory() as td:
        idx = Path(td) / "pursue_index"
        idx.mkdir()
        (idx / "records.csv").write_text(
            "type,title,release,redacted,blurb,out_path\n"
            "video,\"DOW-UAP-PR999, Test Clip\",06,no,\"This video was digitally altered before being reported.\",data/x.mp4\n"
            "video,\"DOW-UAP-PR998, Other\",06,no,\"Nothing unusual stated.\",data/y.mp4\n"
            "document,\"A document\",06,no,\"text\",data/d.pdf\n")
        c = catalog.PursueCatalog(idx / "records.csv")
        check(len(c.videos()) == 2, "a PURSUE catalog reads only videos", f"{len(c.videos())} records")
        check(c.disclosure_rate() == (1, 2), "and counts disclosures", str(c.disclosure_rate()))
        rec = c.by_id("PR999")
        check(len(rec) == 1 and "digitally altered" in (c.disclosure(rec[0]) or ""),
              "and quotes the release's own sentence")
        catalog.use(None)


def test_an_ambiguous_record_id_is_reported_not_guessed():
    """Bare ids are not unique across releasing bodies: PR001-PR004 each exist
    under two prefixes in the PURSUE corpus. Returning the first match would
    quietly analyse the wrong clip."""
    print("\npackaging: ambiguous record ids")
    with tempfile.TemporaryDirectory() as td:
        idx = Path(td) / "pursue_index"
        idx.mkdir()
        (idx / "records.csv").write_text(
            "type,title,release,redacted,blurb,out_path\n"
            "video,\"FBI-UAP-PR001, One\",03,no,\"x\",data/a.mp4\n"
            "video,\"LLE-UAP-PR001, Two\",06,no,\"x\",data/b.mp4\n"
            "video,\"DOW-UAP-PR144, Three\",06,no,\"x\",data/c.mp4\n")
        c = catalog.PursueCatalog(idx / "records.csv")
        check(len(c.by_id("PR001")) == 2, "a bare ambiguous id returns both",
              f"{len(c.by_id('PR001'))} records")
        check(len(c.by_id("FBI-UAP-PR001")) == 1, "a qualified id picks one")
        check(len(c.by_id("PR001", release="06")) == 1, "a release qualifier picks one")
        check(len(c.by_id("PR144")) == 1, "an unambiguous bare id still works")
        check(c.by_id("DOW-UAP-PR144")[0]["title"].startswith("DOW-UAP-PR144"),
              "and so does its qualified form")
        catalog.use(None)


def test_ffmpeg_is_checked_up_front():
    print("\npackaging: runtime dependencies")
    try:
        clipmod.require_ffmpeg()
        check(True, "ffmpeg and ffprobe are present")
    except clipmod.MissingTool as e:
        check(False, "ffmpeg and ffprobe are present", str(e))


def main():
    print("McDonald UAP Toolkit — measurement self-check")
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print(f"\n{'ALL PASS' if not FAIL else str(len(FAIL)) + ' FAILED: ' + ', '.join(FAIL)}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
