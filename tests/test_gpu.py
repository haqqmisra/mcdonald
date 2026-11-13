"""Checks for computing on a graphics card (`mcdonald.gpu`): the choice of a card, the rules for when one is used, and
the card's arithmetic held to the CPU's, which is the reference.

The card's versions of the band-pass, the shift field and the spot detector are written against three modules a
`gpu.Card` carries (an array module, its FFT, its filters). On a card those are CuPy's; here they are also run with
NumPy's and SciPy's in their place (`gpu.stand_in`), so that the same code is checked on a computer with no card, which
is every one of GitHub's runners. Where this process has a real card (an NVIDIA one, CuPy installed, and inside a batch
job only if the job was given it: `sbatch --gres=gpu:1`), every comparison is made on it too; where it has none, one
line says so.

What "the same" means, and why it is not "to the last bit": the correlations are single precision on the CPU and on the
card, by different transforms in a different order, so the maps differ by a few 1e-7. A template whose peak is nearly
flat along a streak turns that into 1e-3 px along the streak, where its own error is a thousand times larger. The
checks hold what a measurement is made of: the same templates keep their rows, each shift within a hundredth of its
own error and of a pixel, and the agreed shift of a pair within a thousandth of a pixel. Portable: no video data.

    python3 tests/test_gpu.py
"""
import contextlib
import importlib
import io
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

import numpy as np

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))
from mcdonald import cli, forensics as vf, gpu, progress  # noqa: E402

RNG = np.random.default_rng(20261112)
FAIL = []
SHIFT_PX = 0.01         # a template's shift on the card against the CPU's, px ...
SHIFT_SIGMA = 0.01      # ... and in units of the template's own error
AGREED_PX = 1e-3        # a pair's agreed shift (the consensus of its templates)


def check(cond, label, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}{'  ' + detail if detail else ''}")
    if not cond:
        FAIL.append(label)
    return cond


def isotropic(h, w, scale=3.0, rng=RNG):
    from scipy import ndimage
    return (ndimage.gaussian_filter(rng.normal(0, 1, (h, w)), scale) * 400 + 128).astype(np.float32)


def striated(h, w, rng=RNG):
    from scipy import ndimage
    return (ndimage.gaussian_filter(rng.normal(0, 1, (h, w)), (1.0, 9.0)) * 700 + 128).astype(np.float32)


def roll(a, dx, dy):
    return np.roll(np.roll(a, dy, axis=0), dx, axis=1)


@contextlib.contextmanager
def environment(**values):
    """The environment with these set (None: unset), and the card asked for again; both put back after."""
    old = {k: os.environ.get(k) for k in values}
    try:
        for k, v in values.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        gpu.forget()
        yield
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        gpu.forget()


@contextlib.contextmanager
def on(card):
    """Inside the block `card` is this process's card (None: it has none), whatever it would choose itself, and the
    routines with a card version compute on it, as inside a stage's pass (`gpu.on`); its own choice after."""
    gpu.use(card)
    try:
        with gpu.on(card):
            yield card
    finally:
        gpu.forget()


def cards():
    """The cards the comparisons are made on: the stand-in always, and this process's own card where it has a real one."""
    out = [gpu.stand_in()]
    gpu.forget()
    c = gpu.card()
    if c is not None and c.real:
        out.append(c)
    gpu.forget()
    return out


CARDS = None


def the_cards():
    global CARDS
    if CARDS is None:
        CARDS = cards()
        if len(CARDS) == 1:
            with environment():
                gpu.card()
                print(f"  NOTE  no graphics card in this process ({gpu.why()}): the card's arithmetic is checked with the stand-in only")
    return CARDS


def fields_agree(ref, got):
    """(same rows kept, worst shift difference in px, worst in the template's own error, worst peak difference) for two
    fields of `shift_field`."""
    if ref.shape != got.shape or not np.array_equal(ref[:, :3], got[:, :3]):
        return False, np.inf, np.inf, np.inf
    if not len(ref):
        return True, 0.0, 0.0, 0.0
    d = np.abs(ref[:, 3:5] - got[:, 3:5])
    sigma = 1 / np.sqrt(np.maximum(ref[:, 10:12], 1e-12))
    return True, float(d.max()), float((d / sigma).max()), float(np.abs(ref[:, 5:7] - got[:, 5:7]).max())


def agreed(f):
    c = vf.layers_of(f)["all"]
    return None if c is None else (np.array(c[0], float), c[1])


# ---------------------------------------------------------------- the choice
def test_the_choice_is_read_from_the_environment():
    """MCDONALD_GPU, which `mcdonald --gpu` and Preferences set: none, the first card, or a card by name or number."""
    print("\nthe choice of a card")
    said = {}
    for value in ("none", "OFF", "cpu", "No"):
        with environment(MCDONALD_GPU=value):
            said[value] = (gpu.asked(), gpu.card(), gpu.why())
    check(all(a == gpu.NONE and c is None and "CPU only" in w for a, c, w in said.values()),
          "none, off, cpu and no all mean the CPU only, and no card is opened", str({k: v[0] for k, v in said.items()}))
    with environment(MCDONALD_GPU=None):
        first = gpu.asked()
    with environment(MCDONALD_GPU="Auto"):
        auto = gpu.asked()
    with environment(MCDONALD_GPU="GeForce RTX 5070"):
        name = gpu.asked()
    check(first == "" and auto == "" and name == "geforce rtx 5070", "unset or auto is the first card; a name is kept, in lower case",
          f"{first!r}, {auto!r}, {name!r}")
    two = ["NVIDIA GeForce RTX 5070 Ti", "NVIDIA GeForce RTX 5070 Ti", "NVIDIA RTX A2000"]
    got = [gpu.pick(c, two) for c in ("", "1", "nvidia geforce rtx 5070 ti", "NVIDIA GeForce RTX 5070 Ti (2)", "a2000", "5070", "radeon", "7")]
    check(got == [0, 1, 0, 1, 2, 0, None, None],
          "of the cards CUDA lists: the first; a number; a name; \"name (2)\" the second so named; part of a name; and none "
          "for a name that is not there -- 5070 is part of a name, not the 5,071st card", str(got))
    check(gpu.pick("", []) is None, "with no cards there is none to pick")
    with environment(MCDONALD_GPU=gpu.STAND_IN):
        c = gpu.card()
        check(c is not None and not c.real and c.xp is np and "stand-in" in gpu.said(),
              "stand-in puts NumPy in the card's place, and `said` names it", gpu.said())
    with environment(MCDONALD_GPU=None):
        gpu.choose("none")
        chosen = (os.environ.get(gpu.GPU_VAR), gpu.card())
        gpu.choose("")
        cleared = os.environ.get(gpu.GPU_VAR)
    check(chosen == ("none", None) and cleared is None, "`choose` puts the choice in the environment, for this process and "
          "those it starts, and an empty choice takes it out again", f"{chosen}, {cleared}")


def test_a_batch_job_uses_a_card_only_if_it_was_given_one():
    """As `progress.cpus` is the allocation and not the machine: inside a Slurm job a card is used only where the job
    asked for one, which is what sets CUDA_VISIBLE_DEVICES. A job that did not ask could otherwise compute on a card
    that was given to another."""
    print("\na batch job's allocation, not the machine")
    with environment(SLURM_JOB_ID=None, CUDA_VISIBLE_DEVICES=None):
        outside = gpu.given()
    with environment(SLURM_JOB_ID="123", CUDA_VISIBLE_DEVICES=None, MCDONALD_GPU=None):
        without = (gpu.given(), gpu.card(), gpu.why())
    with environment(SLURM_JOB_ID="123", CUDA_VISIBLE_DEVICES="0"):
        with_one = gpu.given()
    with environment(SLURM_JOB_ID="123", CUDA_VISIBLE_DEVICES="NoDevFiles"):
        none_named = gpu.given()
    check(outside and with_one, "outside a batch job a card may be used, and inside one that was given a card")
    check(without[0] is False and without[1] is None and "--gres=gpu:1" in without[2] and none_named is False,
          "inside a job that was given none, no card is opened, and `why` says what to ask the scheduler for", without[2])
    with environment(SLURM_JOB_ID="123", CUDA_VISIBLE_DEVICES=None, MCDONALD_GPU=gpu.STAND_IN):
        check(gpu.card() is not None, "the stand-in is no card: it runs anywhere")


def _asked_in_a_worker(_):
    from mcdonald import gpu as g
    return g.card() is None, g.why()


def test_a_pools_worker_never_computes_on_the_card():
    """Each process that computes on a card holds its own state there, a few hundred MB, and they take turns: a pool
    of workers on one card is slower than one process, and can fill it. `card()` is None in a worker."""
    print("\na pool's worker computes on the CPU")
    with environment(MCDONALD_GPU=gpu.STAND_IN):
        mine = gpu.card()
        pool = progress.new_pool(1)
        try:
            none, why = pool.map(_asked_in_a_worker, [0])[0]
        finally:
            pool.terminate()
            pool.join()
    check(mine is not None and none, "this process has the card it asked for; its pool's worker has none", why)


def test_the_command_line_takes_gpu():
    print("\n--gpu on the command line")
    with environment(MCDONALD_GPU=None):
        rest = cli.take_gpu(["layers", "--gpu", "none", "PR113", "--k", "5"])
        first = os.environ.get(gpu.GPU_VAR)
        rest2 = cli.take_gpu(["--gpu=RTX 5070", "setup"])
        second = os.environ.get(gpu.GPU_VAR)
        errors = []
        for argv in (["layers", "--gpu"], ["--gpu", "--json", "layers"], ["--gpu=", "layers"]):
            try:
                cli.take_gpu(argv)
            except ValueError as e:
                errors.append(str(e))
    check(rest == ["layers", "PR113", "--k", "5"] and first == "none" and rest2 == ["setup"] and second == "RTX 5070",
          "--gpu X and --gpu=X are taken out wherever they are, and put in the environment", f"{rest}, {first!r}, {second!r}")
    check(len(errors) == 3 and all("--gpu needs" in e for e in errors), "with no card named, it says what it needs", str(errors[:1]))
    env = dict(os.environ, PYTHONPATH=str(SRC) + os.pathsep + os.environ.get("PYTHONPATH", ""), MCDONALD_HOME=tempfile.gettempdir())
    env.pop(gpu.GPU_VAR, None)
    r = subprocess.run([sys.executable, "-m", "mcdonald.cli", "--gpu", gpu.STAND_IN, "setup", "--offline", "--no-desktop"],
                       capture_output=True, encoding="utf-8", errors="replace", env=env, timeout=300)
    line = next((ln for ln in (r.stdout + r.stderr).splitlines() if "graphics card" in ln), "")
    check("stand-in" in line, "`mcdonald --gpu stand-in setup` says which card computes", line.strip()[:160])
    r = subprocess.run([sys.executable, "-m", "mcdonald.cli", "--gpu", "none", "setup", "--offline", "--no-desktop"],
                       capture_output=True, encoding="utf-8", errors="replace", env=env, timeout=300)
    line = next((ln for ln in (r.stdout + r.stderr).splitlines() if "graphics card" in ln), "")
    check("CPU only" in line, "and with --gpu none, that the CPU only was chosen", line.strip()[:160])


def test_the_cards_found_say_which_mcdonald_can_use():
    """`found`'s cards say whether they can compute at all and whether mcdonald can compute on them (an NVIDIA card with
    CUDA's library); Preferences offers the second kind."""
    print("\nwhich cards mcdonald can compute on")
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        ids = td / "pci.ids"
        ids.write_text("10de  NVIDIA Corporation\n\t2c05  GB203 [GeForce RTX 5070 Ti]\n1002  Advanced Micro Devices, Inc. [AMD/ATI]\n"
                       "\t744c  Navi 31 [Radeon RX 7900 XT]\n", encoding="utf-8")
        for slot, vendor, device, driver in (("0000_62_00.0", "0x10de", "0x2c05", "nvidia"), ("0000_04_00.0", "0x1002", "0x744c", "amdgpu")):
            dev = td / "pci" / slot
            dev.mkdir(parents=True)
            (dev / "class").write_text("0x030000\n")
            (dev / "vendor").write_text(vendor + "\n")
            (dev / "device").write_text(device + "\n")
            (dev / "uevent").write_text(f"DRIVER={driver}\n")
        vk = [dict(vendor="10de", device="2c05", name="NVIDIA GeForce RTX 5070 Ti"), dict(vendor="1002", device="744c", name="AMD Radeon RX 7900 XT")]
        both = gpu.linux(str(td / "pci"), [str(ids)], ask=lambda: vk, cuda=lambda: True)
        no_cuda = gpu.linux(str(td / "pci"), [str(ids)], ask=lambda: vk, cuda=lambda: False)
    by = {c["name"]: c for c in both}
    check(by["NVIDIA GeForce RTX 5070 Ti"]["cuda"] and by["NVIDIA GeForce RTX 5070 Ti"]["compute"]
          and by["AMD Radeon RX 7900 XT"]["compute"] and not by["AMD Radeon RX 7900 XT"]["cuda"],
          "an NVIDIA card with CUDA's library is one mcdonald can use; an AMD card computes, but not for mcdonald", str(both))
    check([c["name"] for c in gpu.usable(both)] == ["NVIDIA GeForce RTX 5070 Ti"] and gpu.usable(no_cuda) == [],
          "`usable` is the NVIDIA card with CUDA, and nothing where CUDA's library is not there")
    check(by["NVIDIA GeForce RTX 5070 Ti"].get("slot") == "0000_62_00.0", "a card keeps where it sits, to be matched with CUDA's list")
    macs = gpu.mac({"SPDisplaysDataType": [{"sppci_model": "Apple M2", "spdisplays_vendor": "sppci_vendor_Apple (0x106b)",
                                           "spdisplays_mtlgpufamilysupport": "spdisplays_metal3"}]})
    wins = gpu.windows([{"Name": "NVIDIA GeForce RTX 4070", "PNPDeviceID": "PCI\\VEN_10DE&DEV_2786&SUBSYS_1"}], ask=lambda: [], cuda=lambda: True)
    check(macs and macs[0]["compute"] and not macs[0]["cuda"] and gpu.usable(macs) == [] and wins and wins[0]["cuda"],
          "a Mac's card computes and is not yet one mcdonald can use; an NVIDIA card on Windows with CUDA's library is")
    check(isinstance(gpu.installed(), bool), "whether CuPy is installed is asked without importing it", str(gpu.installed()))


# ---------------------------------------------------------------- the add-on, installed for the person
# pip, stood in for: no test installs anything or uses the network. It is started as pip is (`addon.PIP`), prints what
# pip prints, and keeps the arguments it was given. Its first two arguments are the test's: how it should end, and a
# folder to write in. "ok" leaves a file there named installed, as pip leaves a package; "slow" downloads for a minute.
PIP_STAND_IN = r"""
import json, sys, time
from pathlib import Path
mode, folder, args = sys.argv[1], Path(sys.argv[2]), sys.argv[3:]
(folder / "args.json").write_text(json.dumps(args), encoding="utf-8")
c = args[args.index("--constraint") + 1] if "--constraint" in args else ""
(folder / "constraints.txt").write_text(Path(c).read_text(encoding="utf-8") if c else "", encoding="utf-8")
say = lambda *a: print(*a, flush=True)
say("Collecting " + args[-1])
say("  Downloading stand_in-14.2.0-py3-none-any.whl.metadata (6.6 kB)")
if mode == "offline":
    say("WARNING: Retrying (Retry(total=0, connect=None, read=None, redirect=None, status=None)) after connection broken by "
        "'NewConnectionError(\"HTTPSConnection(host='pypi.org', port=443): Failed to establish a new connection: "
        "[Errno -3] Temporary failure in name resolution\")': /simple/stand-in/")
    say("ERROR: Could not find a version that satisfies the requirement " + args[-1] + " (from versions: none)")
    say("ERROR: No matching distribution found for " + args[-1])
    sys.exit(1)
if mode == "conflict":
    say("ERROR: Cannot install stand-in because these package versions have conflicting dependencies.")
    say("The conflict is caused by:")
    say("    stand-in 14.2.0 depends on numpy<2.6 and >=2.0")
    say("    The user requested (constraint) numpy==1.26.4")
    say("ERROR: ResolutionImpossible: for help visit https://pip.pypa.io/en/latest/topics/dependency-resolution/")
    sys.exit(1)
for name, size in (("stand_in-14.2.0-py3-none-any.whl", 300_000_000), ("stand_in_libraries-13.5-py3-none-any.whl", 500_000_000)):
    say(f"Downloading {name} ({size / 1e6:.1f} MB)")
    for k in range(-1, 4):
        say(f"Progress {size * (k + 1) // 4} of {size}")
        time.sleep(15 if mode == "slow" and k >= 0 else 0.02)
say("Installing collected packages: stand-in-libraries, stand-in")
time.sleep(0.2)
(folder / "installed").write_text("yes", encoding="utf-8")
say("Successfully installed stand-in-14.2.0 stand-in-libraries-13.5")
"""


def pip_stand_in(folder, mode):
    """What `addon.PIP` is set to for a test: this Python running the stand-in, which will end as `mode` says."""
    folder = Path(folder)
    (folder / "pip_stand_in.py").write_text(PIP_STAND_IN, encoding="utf-8")
    return [sys.executable, str(folder / "pip_stand_in.py"), mode, str(folder)]


def test_the_add_on_for_this_computers_driver():
    """Which of the two add-ons a computer takes (`addon.which`), from what its driver says (`gpu.cuda`): CUDA 13's
    only where the driver runs CUDA 13 and every card is one CUDA 13's libraries still run."""
    print("\nthe add-on: which one this computer takes")
    from mcdonald import addon
    took = {name: addon.which(seen)[0] for name, seen in (
        ("the driver did not say", None), ("an old card on CUDA 12's driver", dict(driver=(12, 4), cards=[(6, 1)])),
        ("a GTX 1080 on a 580 driver, which reports CUDA 13", dict(driver=(13, 0), cards=[(6, 1)])),
        ("a new card on CUDA 12's driver", dict(driver=(12, 9), cards=[(8, 9)])),
        ("an old card beside a new one", dict(driver=(13, 5), cards=[(12, 0), (6, 1)])),
        ("CUDA 13's driver, the cards not listed", dict(driver=(13, 0), cards=[])))}
    check(set(took.values()) == {"gpu"}, "CUDA 12's add-on wherever CUDA 13's libraries might not run a card here: an older "
          "driver, an older card (whatever its driver reports), or a card the driver did not list", str(took))
    new = [addon.which(dict(driver=d, cards=c))[0] for d, c in (((13, 5), [(12, 0)]), ((13, 0), [(7, 5)]), ((14, 1), [(8, 6), (7, 5)]))]
    check(new == ["gpu-cuda13"] * 3, "CUDA 13's add-on where the driver runs CUDA 13 and every card is of the RTX 2000 "
          "series or later (compute capability 7.5 and up)", str(new))
    none, why = addon.which(dict(driver=(11, 4), cards=[(6, 1)]))
    check(none is None and "11.4" in why and "driver" in why, "a driver older than CUDA 12 takes neither, and it says so", why)
    check(gpu.cuda(ask=lambda: dict(driver=13050, cards=[[12, 0]])) == dict(driver=(13, 5), cards=[(12, 0)])
          and gpu.cuda(ask=lambda: dict(driver=12040, cards=[])) == dict(driver=(12, 4), cards=[])
          and gpu.cuda(ask=lambda: dict(driver=None, cards=[])) == dict(driver=None, cards=[])
          and gpu.cuda(ask=lambda: None) is None and gpu.cuda(ask=lambda: "?") is None,
          "the driver's answer is read as CUDA's version and each card's compute capability, and no answer is no answer")
    real = gpu.cuda()
    check(real is None or (set(real) == {"driver", "cards"} and (real["driver"] is None or real["driver"] >= (1, 0))),
          "and this computer's own driver is asked without a toolkit, in a process of its own", str(real))


def test_the_add_on_is_installed_without_touching_what_is_here():
    """`addon.install` runs pip for the add-on's own requirement, with every installed package pinned, and says how it
    went; `addon.offer` is what the window and `mcdonald setup` read. pip is stood in for: nothing is installed."""
    print("\nthe add-on: installed by pip, with nothing replaced")
    from mcdonald import addon, update
    nvidia = [dict(name="NVIDIA GeForce RTX 5070 Ti", vendor="10de", compute=True, cuda=True)]
    keep = gpu.installed, gpu.found, addon.PIP, addon.shutil.disk_usage
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        try:
            gpu.installed = lambda: False
            addon.PIP = pip_stand_in(td, "ok")        # from here on, the pip there is to run
            o = addon.offer(nvidia, seen=dict(driver=(13, 5), cards=[(12, 0)]))
            o12 = addon.offer(nvidia, seen={})
            check(o and o["extra"] == "gpu-cuda13" and o["requires"] == ["cupy-cuda13x[ctk]>=14"] and o["card"] == nvidia[0]["name"]
                  and not o["cannot"] and o["command"] == [sys.executable, "-m", "pip", "install", "cupy-cuda13x[ctk]>=14"]
                  and o12["extra"] == "gpu" and o12["command"][-1] == "cupy-cuda12x[ctk]>=14" and o["download_mb"] < o12["download_mb"],
                  "where an NVIDIA card waits for CuPy, the offer names the card, the add-on for its driver, its size and "
                  "the command to type by hand: the add-on's own requirement, never mcdonald itself", str(o and o["command"][-1]))
            check(update.said(o["command"]).endswith(' -m pip install "cupy-cuda13x[ctk]>=14"'),
                  "the command is said with its requirement in quotes, as a shell needs it (brackets and >)", update.said(o["command"])[-60:])
            old = addon.offer(nvidia, seen=dict(driver=(11, 4), cards=[(6, 1)]))
            check(old and "driver" in old["cannot"] and "11.4" in old["cannot"],
                  "a driver too old for it is said before anything is downloaded", old and old["cannot"])
            check(addon.offer([dict(name="AMD Radeon RX 7900", vendor="1002", compute=True, cuda=False)], seen={}) is None
                  and addon.offer([], seen={}) is None, "nothing is offered where there is no NVIDIA card with CUDA")
            gpu.installed = lambda: True
            check(addon.offer(nvidia, seen={}) is None, "nor where CuPy is installed already")
            gpu.installed = lambda: False

            pins = addon.pinned()
            check(f"numpy=={np.__version__}" in pins and all("==" in ln and " " not in ln for ln in pins) and len(pins) == len(set(pins)),
                  "every package installed here is pinned at the version it has, each once", f"{len(pins)} packages")

            states, lines = [], []
            addon.PIP = pip_stand_in(td, "ok")
            r = addon.install("gpu-cuda13", progress=states.append, said=lines.append)
            args = json.loads((td / "args.json").read_text(encoding="utf-8"))
            check(r["ok"] and r["code"] == 0 and not r["why"] and (td / "installed").exists() and abs(r["mb"] - 800) < 1,
                  "pip is run and waited for, and the megabytes it downloaded are counted", f"{r['mb']:.0f} MB in {r['seconds']:.1f} s")
            check(args[0] == "install" and args[-1] == "cupy-cuda13x[ctk]>=14" and not any(a.startswith("mcdonald") or a == "." for a in args)
                  and "--upgrade" not in args and "-U" not in args and "-e" not in args
                  and {"--no-input", "--only-binary=:all:", "--no-cache-dir", "--constraint"} <= set(args),
                  "pip is given the add-on's own requirement and nothing of mcdonald's: no upgrade, wheels only, no "
                  "questions, nothing kept in its cache", " ".join(a for a in args if not Path(a).exists()))
            check(f"numpy=={np.__version__}" in (td / "constraints.txt").read_text(encoding="utf-8").split(),
                  "and a constraints file that pins what is installed, so that pip can add packages and replace none")
            phases = list(dict.fromkeys(s["phase"] for s in states))
            mbs = [s["mb"] for s in states]
            check(phases == ["looking", "downloading", "installing"] and mbs == sorted(mbs) and all(s["of"] >= s["mb"] for s in states)
                  and states[-1]["of"] == addon.DOWNLOAD_MB["gpu-cuda13"] and any(0 < s["mb"] < 800 for s in states),
                  "its progress is told as it goes: looking, downloading megabyte by megabyte over all the files, then "
                  "putting it in place", f"{phases}, {len(states)} times")
            check(lines and "pip_stand_in" in lines[0] and not any(ln.startswith("Progress") for ln in lines)
                  and any(ln.startswith("Successfully installed") for ln in lines),
                  "what pip prints is passed on line by line, the command first, without its counts", f"{len(lines)} lines")

            addon.PIP = pip_stand_in(td, "offline")
            r = addon.install("gpu")
            check(not r["ok"] and r["code"] == 1 and "internet" in r["why"] and "pypi.org" in r["why"]
                  and r["pip"] and all(ln.startswith("ERROR") for ln in r["pip"]) and r["command"][-1] == "cupy-cuda12x[ctk]>=14",
                  "with no network it says so in plain words, keeps pip's own errors, and gives the command to type by hand",
                  r["why"])
            addon.PIP = pip_stand_in(td, "conflict")
            r = addon.install("gpu")
            check(not r["ok"] and "replaces nothing" in r["why"] and any("ResolutionImpossible" in ln for ln in r["pip"]),
                  "where the add-on would need an installed package replaced, pip stops before it changes anything, and "
                  "that is said", r["why"])
            (td / "installed").unlink()
            addon.PIP = pip_stand_in(td, "slow")
            stop, t0 = threading.Event(), time.monotonic()
            threading.Timer(1.0, stop.set).start()
            r = addon.install("gpu", stop=stop)
            check(r["stopped"] and not r["ok"] and not (td / "installed").exists() and time.monotonic() - t0 < 10 and "stopped" in r["why"],
                  "stopped while it downloads, pip is ended at once and nothing is installed", f"{time.monotonic() - t0:.1f} s")
            addon.PIP = [str(td / "no-such-program")]
            r = addon.install("gpu")
            check(not r["ok"] and r["code"] is None and "could not be started" in r["why"], "a pip that cannot be started is a "
                  "failure said, not a crash", r["why"])
            addon.shutil.disk_usage = lambda path: type("Usage", (), dict(free=2e9))()
            addon.PIP = pip_stand_in(td, "ok")
            r = addon.install("gpu")
            check(not r["ok"] and r["code"] is None and "free disk space" in r["why"] and "2.0 GB are free" in r["why"]
                  and not (td / "installed").exists(),
                  "with too little room on the disk nothing is downloaded, and it says how much the add-on needs", r["why"])
        finally:
            gpu.installed, gpu.found, addon.PIP, addon.shutil.disk_usage = keep
    for extra, text in (("gpu", "network is unreachable"), ("gpu", "OSError: [Errno 28] No space left on device"),
                        ("gpu", "error: externally-managed-environment"), ("gpu", "ERROR: Could not install packages due to an OSError: [Errno 13] Permission denied"),
                        ("gpu", "ERROR: No matching distribution found for cupy-cuda12x>=14"), ("gpu", "something else")):
        why = addon.explain([text], extra)
        check(why.endswith(".") and len(why.split()) <= 30 and "Errno" not in why, f"pip's failure in plain words: {text[:40]!r}", why)


def test_the_add_on_is_used_without_starting_again():
    """After pip, the same process finds CuPy (`gpu.installed` looks without importing) and opens the card
    (`addon.use_now`): here a package named cupy is put where Python looks only after the process has started."""
    print("\nthe add-on: used by the process that installed it")
    from mcdonald import addon
    had = gpu.installed()
    with tempfile.TemporaryDirectory() as td, environment(MCDONALD_GPU=None):
        sys.path.append(td)
        try:
            gpu.installed()                           # Python has looked in the folder, and found it empty
            (Path(td) / "cupy").mkdir()
            (Path(td) / "cupy" / "__init__.py").write_text("", encoding="utf-8")
            card, why, again = addon.use_now()
            check(gpu.installed() and not again, "a package pip has just put in place is found by the process that was "
                  "already running" + (" (CuPy was here before: the folder made for this adds nothing)" if had else ""))
            check((card is None) == bool(why) and (card is not None or gpu.card() is None),
                  "and the card is asked for again: in use, or said why not", card or why)
        finally:
            sys.path.remove(td)
            if not had:
                sys.modules.pop("cupy", None)
            importlib.invalidate_caches()
    gpu.forget()
    keep = gpu.installed
    try:
        gpu.installed = lambda: False
        card, why, again = addon.use_now()
        check(card is None and again and "opened again" in why, "where pip put it out of this process's sight, it says "
              "that mcDonald has to be opened again", why)
    finally:
        gpu.installed = keep
        gpu.forget()


def test_setup_installs_the_add_on_from_the_command_line():
    """`mcdonald setup --install-gpu`, the same install for an agent or a person at a terminal (the two audiences), and
    setup's own "graphics card" line, which names it. pip is stood in for."""
    print("\nthe add-on: `mcdonald setup --install-gpu`")
    from mcdonald import addon, setup_cli
    nvidia = [dict(name="NVIDIA GeForce RTX 5070 Ti", vendor="10de", compute=True, cuda=True)]
    keep = gpu.installed, gpu.found, gpu.cuda, addon.PIP, addon.room

    def run(*argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = setup_cli.main(list(argv))
        return code, out.getvalue(), err.getvalue()
    with tempfile.TemporaryDirectory() as td, environment(MCDONALD_GPU=None, XDG_DATA_HOME=td, DISPLAY=":0"):
        td = Path(td)
        try:
            gpu.found, gpu.cuda, addon.room = (lambda: nvidia), (lambda: dict(driver=(13, 5), cards=[(12, 0)])), (lambda extra, **k: "")
            gpu.installed = lambda: (td / "installed").exists()
            addon.PIP = pip_stand_in(td, "ok")
            ok, found, fix = setup_cli._graphics_card()
            check(ok is None and "RTX 5070 Ti" in found and "not installed" in found and "mcdonald setup --install-gpu" in fix
                  and 'pip install "cupy-cuda13x[ctk]>=14"' in fix and "mcdonald[gpu]" not in fix,
                  "setup's graphics card line says how to install the add-on: its own command, and by hand the build for "
                  "this computer's driver", fix)
            gpu.cuda = lambda: dict(driver=(11, 4), cards=[(6, 1)])
            ok, found, fix = setup_cli._graphics_card()
            code, out, err = run("--install-gpu", "--json")
            d = json.loads(out)["install_gpu"]
            check("cannot be installed" in fix and "driver" in fix and "11.4" in fix and code == 3 and not d["ok"] and "driver" in d["why"]
                  and not (td / "args.json").exists(),
                  "with a driver too old for it, both say so, and pip is not run", fix)
            gpu.cuda = lambda: dict(driver=(13, 5), cards=[(12, 0)])
            addon.PIP = pip_stand_in(td, "offline")
            code, out, err = run("--install-gpu")
            check(code == 3 and not out and "was not installed" in err and "internet" in err and "by hand:" in err
                  and 'pip install "cupy-cuda13x[ctk]>=14"' in err and "ERROR: No matching distribution" in err,
                  "a failure exits 3, with the reason in plain words, what pip said and the command by hand on stderr",
                  err.strip().splitlines()[-2][:120])
            addon.PIP = pip_stand_in(td, "ok")
            os.environ[gpu.GPU_VAR] = gpu.STAND_IN    # the card that answers once the add-on is in place
            code, out, err = run("--install-gpu", "--json")
            d = json.loads(out)
            check(code == 0 and d["command"] == "setup" and d["install_gpu"]["ok"] and d["install_gpu"]["installed"]
                  and "stand-in" in d["install_gpu"]["card"] and d["install_gpu"]["mb"] == 800.0
                  and "CUDA 13.5" in err and "cupy-cuda13x[ctk]>=14" in err and "Successfully installed" in err,
                  "installed, it exits 0 and says which card computes; --json is one object on stdout, pip's words on stderr",
                  str(d["install_gpu"])[:150])
            check(not (td / "applications").exists(), "and it does nothing else of setup: no entry in the applications menu")
            code, out, err = run("--install-gpu")
            check(code == 0 and "already installed" in err, "asked again, it says the add-on is installed already", err.strip()[-90:])
            (td / "installed").unlink()
            gpu.found = lambda: [dict(name="AMD FirePro 2270", vendor="1002", compute=False, cuda=False)]
            code, out, err = run("--install-gpu")
            check(code == 3 and "nothing to install it for" in err and "AMD FirePro 2270" in err and not (td / "installed").exists(),
                  "with no NVIDIA card there is nothing to install it for, and nothing is downloaded", err.strip()[-110:])
        finally:
            gpu.installed, gpu.found, gpu.cuda, addon.PIP, addon.room = keep
    r = subprocess.run([sys.executable, "-m", "mcdonald.cli", "setup", "--help"], capture_output=True, encoding="utf-8", errors="replace",
                       env=dict(os.environ, PYTHONPATH=str(SRC) + os.pathsep + os.environ.get("PYTHONPATH", "")), timeout=300)
    check(r.returncode == 0 and "--install-gpu" in r.stdout, "`mcdonald setup --help` lists it")


# ---------------------------------------------------------------- the arithmetic
def test_a_card_computes_only_where_a_stage_says_so():
    """Having a card computes nothing by itself. The routines with a card version use it inside `with gpu.on(card):`,
    which a stage enters for a whole pass; anywhere else they are the CPU's arithmetic, to the bit. Otherwise a stage
    run in this process would take its spots from the card and the same stage on a pool from the CPU, and the suites
    hold many stages to "the same on a pool as in one process" (2026-11-12, `groups`, on the first run on a card)."""
    print("\na card computes only where a stage says so")
    scene = isotropic(420, 640)
    ga, gb = scene[20:380, 30:510].copy(), scene[14:374, 41:521].copy()
    none = np.zeros(ga.shape, bool)
    ref = vf.shift_field(ga, gb, none, none, reach=60), vf.bandpass(ga), vf.spot_response(ga, 9.0)
    c = gpu.stand_in()
    gpu.use(c)
    try:
        outside = (gpu.card() is c, gpu.active())
        got = vf.shift_field(ga, gb, none, none, reach=60), vf.bandpass(ga), vf.spot_response(ga, 9.0)
        kept = vf.bandpass_kept(ga)
        with gpu.on(c):
            inside = gpu.active() is c
            with gpu.on(None):
                cpu_inside = gpu.active()
            back = gpu.active() is c
            on_card = vf.shift_field(ga, gb, none, none, reach=60)
        after = gpu.active()
    finally:
        gpu.forget()
    check(outside == (True, None) and all(np.array_equal(r, g) for r, g in zip(ref, got)) and isinstance(kept, np.ndarray),
          "a process with a card, outside a stage's pass: the shift field, the band-pass and the spot detector are the "
          "CPU's, to the bit")
    check(inside and cpu_inside is None and back and after is None,
          "inside `gpu.on(card)` the card is the one computing; `gpu.on(None)` inside it is the CPU again; after it, the CPU")
    check(not np.array_equal(on_card, ref[0]) and fields_agree(ref[0], on_card)[1] <= SHIFT_PX,
          "and inside it the field is the card's: the CPU's within the tolerance, by other arithmetic")
    gpu.begin()
    before = gpu.computed_on()
    gpu.use(c)
    try:
        vf.shift_field(ga, gb, none, none, reach=60)
        unused = gpu.computed_on()
        with gpu.on(c):
            vf.shift_field(ga, gb, none, none, reach=60)
        used = gpu.computed_on()
    finally:
        gpu.forget()
    gpu.begin()
    check(before is None and unused is None and used is not None and "stand-in" in used and gpu.computed_on() is None,
          "`computed_on` names the card once it has done arithmetic, for a case to keep; None while the CPU did it all", str(used))


def test_the_cards_band_pass_is_the_cpus():
    """The band-pass on a card is SciPy's own arithmetic there: along each axis the sums in double, the result kept in
    the frame's precision. So it is the CPU's to the last bit, and everything read from a filtered frame starts equal."""
    print("\nthe band-pass")
    g = isotropic(360, 480) + RNG.normal(0, 3, (360, 480)).astype(np.float32)
    with on(None):
        ref = vf.bandpass(g)
    for c in the_cards():
        with on(c):
            h = vf.bandpass(g)
            kept = vf.bandpass_kept(g)
            back = c.run(c.down, kept)
        differ = int((h != ref).sum())
        check(h.dtype == ref.dtype and differ <= max(2, ref.size // 100000) and float(np.abs(h - ref).max()) < 1e-4,
              f"{c.name}: the CPU's, to the last bit in all but a few pixels of a million",
              f"{differ} of {ref.size} pixels differ, by at most {np.abs(h - ref).max():.1e}")
        check(np.array_equal(back, h) and (c.holds(kept) or not c.real),
              f"{c.name}: `bandpass_kept` is the same frame, left on the card for `shift_field`")


def test_the_cards_shift_field_is_the_cpus():
    """Every template of a pair matched in one batch on the card, against one template at a time on the CPU: the same
    templates keep their rows, the shifts agree to within a hundredth of each template's own error, and the pair's
    agreed shift to a thousandth of a pixel. On cloud and on streaks, with masks, near the frame's edges, with the zone
    about zero left out and allowed, with a reach larger than the frame, with small templates and with some rows only."""
    print("\nthe shift field")
    h, w = 420, 640
    scenes = {"cloud": isotropic(h + 80, w + 80), "streaks": striated(h + 80, w + 80)}
    bad_a = np.zeros((h, w), bool)
    bad_a[150:190, 300:420] = True                                # a block over the picture: some templates are not clear of it
    bad_b = bad_a.copy()
    bad_b[:6], bad_b[-6:], bad_b[:, :6], bad_b[:, -6:] = True, True, True, True
    cases = [("the usual search", dict(reach=60), (17, -9)),
             ("a shift near the reach", dict(reach=40), (38, 12)),
             ("a shift past the reach", dict(reach=24), (40, 0)),
             ("a reach larger than the frame", dict(reach=900, stride=144), (-31, 22)),
             ("64-px templates", dict(reach=60, tpl=64, stride=48), (11, 7)),
             ("two rows of templates only", dict(reach=60, only=[16, 208]), (17, -9)),
             ("a scene held still", dict(reach=60), (0, 0))]
    for c in the_cards():
        worst = dict(px=0.0, sigma=0.0, pk=0.0, agreed=0.0)
        lost, rows, truths = [], 0, 0
        for name, scene in scenes.items():
            for what, kw, (dx, dy) in cases:
                ga = scene[40:40 + h, 40:40 + w] + RNG.normal(0, 2, (h, w)).astype(np.float32)
                gb = scene[40 - dy:40 - dy + h, 40 - dx:40 - dx + w] + RNG.normal(0, 2, (h, w)).astype(np.float32)
                with on(None):
                    ref = vf.shift_field(ga, gb, bad_a, bad_b, a=7, zeros=(4, -1), **kw)
                with on(c):
                    got = vf.shift_field(ga, gb, bad_a, bad_b, a=7, zeros=(4, -1), **kw)
                    one = vf.shift_field(ga, gb, bad_a, bad_b, a=7, zero=4, **kw)
                if not np.array_equal(one, got[0]):
                    lost.append(f"{name}, {what}: one zone is not the first of two")
                for r, g in zip(ref, got):
                    same, px, sigma, pk = fields_agree(r, g)
                    rows += len(r)
                    if not same:
                        lost.append(f"{name}, {what}: {len(r)} rows on the CPU, {len(g)} on the card")
                        continue
                    worst.update(px=max(worst["px"], px), sigma=max(worst["sigma"], sigma), pk=max(worst["pk"], pk))
                    cr, cg = agreed(r), agreed(g)
                    if (cr is None) != (cg is None) or (cr is not None and cr[1] != cg[1]):
                        lost.append(f"{name}, {what}: the agreed shift has other members")
                    elif cr is not None:
                        worst["agreed"] = max(worst["agreed"], float(np.abs(cr[0] - cg[0]).max()))
                        if name == "cloud" and what in ("the usual search", "a reach larger than the frame", "64-px templates"):
                            truths += int(np.abs(cg[0] - (dx, dy)).max() < 0.5) if np.hypot(dx, dy) > 6 else 0
        check(not lost and rows > 300, f"{c.name}: the same templates keep their rows, in every case ({rows} rows)", "; ".join(lost[:3]))
        check(worst["px"] <= SHIFT_PX and worst["sigma"] <= SHIFT_SIGMA,
              f"{c.name}: each template's shift within {SHIFT_PX} px and {SHIFT_SIGMA} of its own error",
              f"worst {worst['px']:.1e} px, {worst['sigma']:.1e} of its error; peaks within {worst['pk']:.1e}")
        check(worst["agreed"] <= AGREED_PX, f"{c.name}: a pair's agreed shift within {AGREED_PX} px", f"worst {worst['agreed']:.1e} px")
        check(truths >= 3, f"{c.name}: and it is the drawn shift", f"{truths} of the cases with one")


def test_the_fused_pass_is_the_plain_pass_to_the_bit():
    """G3 (2026-11-13): on a real card the templates' matches are read by the card's own code, which never makes the
    maps of matches (`forensics._peaks_fused`), where the plain pass makes them and goes over them a dozen times. The
    arithmetic of a match is the same and a tie goes to the same placement, so every field is the plain pass's to the
    last bit: on cloud and on streaks, with masks, near the edges, with the zone left out and allowed, with a reach
    larger than the frame, small templates, some rows only. NumPy cannot stand in for the card's own code: the
    stand-in takes the plain pass, and so does a card that will not take the code."""
    print("\nthe fused pass (the card's own code)")
    check(vf._fused_kernels(gpu.stand_in()) is None, "the stand-in takes the plain pass: NumPy cannot run the card's own code")
    real = [c for c in the_cards() if c.real]
    if not real:
        print("  NOTE  no graphics card in this process: the fused pass runs on a real card only, and is not checked here")
        return
    h, w = 420, 640
    scenes = {"cloud": isotropic(h + 80, w + 80), "streaks": striated(h + 80, w + 80)}
    bad_a = np.zeros((h, w), bool)
    bad_a[150:190, 300:420] = True
    bad_b = bad_a.copy()
    bad_b[:6], bad_b[-6:], bad_b[:, :6], bad_b[:, -6:] = True, True, True, True
    cases = [("the usual search", dict(reach=60), (17, -9)), ("a shift near the reach", dict(reach=40), (38, 12)),
             ("a shift past the reach", dict(reach=24), (40, 0)), ("a reach larger than the frame", dict(reach=900, stride=144), (-31, 22)),
             ("64-px templates", dict(reach=60, tpl=64, stride=48), (11, 7)), ("two rows of templates only", dict(reach=60, only=[16, 208]), (17, -9)),
             ("a scene held still", dict(reach=60), (0, 0)), ("a flat frame", dict(reach=60), None)]
    was = vf.FUSED
    try:
        for c in real:
            apart, rows = [], 0
            for name, scene in scenes.items():
                for what, kw, shift in cases:
                    if shift is None:                              # nothing to match: every template flat
                        ga = gb = np.full((h, w), 90.0, np.float32)
                    else:
                        dx, dy = shift
                        ga = scene[40:40 + h, 40:40 + w] + RNG.normal(0, 2, (h, w)).astype(np.float32)
                        gb = scene[40 - dy:40 - dy + h, 40 - dx:40 - dx + w] + RNG.normal(0, 2, (h, w)).astype(np.float32)
                    got = {}
                    for fused in (True, False):
                        vf.FUSED = fused
                        with on(c):
                            got[fused] = vf.shift_field(ga, gb, bad_a, bad_b, a=7, zeros=(4, -1), **kw)
                    rows += sum(len(f) for f in got[True])
                    if not all(np.array_equal(x, y, equal_nan=True) for x, y in zip(got[True], got[False])):
                        apart.append(f"{name}, {what}")
            vf.FUSED = True
            check(not isinstance(vf._fused.get(id(c)), str) and vf._fused_kernels(c) is not None,
                  f"{c.name} takes the card's own code", str(vf._fused.get(id(c)))[:160])
            check(not apart and rows > 300, f"{c.name}: every field of the fused pass is the plain pass's to the last bit ({rows} rows)",
                  "; ".join(apart[:4]))
            # a card that will not take the code: said once, the plain pass does the work, the same field
            source, kept = vf._FUSED_SOURCE, dict(vf._fused)
            ga = scenes["cloud"][40:40 + h, 40:40 + w].copy()
            gb = scenes["cloud"][49:49 + h, 23:23 + w].copy()
            with on(c):
                ref = vf.shift_field(ga, gb, bad_a, bad_b, a=7, reach=60)
            err = io.StringIO()
            try:
                vf._FUSED_SOURCE, sys.stderr = "this is not the card's language", err
                vf._fused.clear()
                with on(c):
                    plain = vf.shift_field(ga, gb, bad_a, bad_b, a=7, reach=60)
                    again = vf.shift_field(ga, gb, bad_a, bad_b, a=7, reach=60)
            finally:
                vf._FUSED_SOURCE, sys.stderr = source, sys.__stderr__
                vf._fused.clear()
                vf._fused.update(kept)
            check(np.array_equal(ref, plain) and np.array_equal(ref, again) and err.getvalue().count("would not take the fused pass") == 1
                  and not c.stopped,
                  f"{c.name}: code the card refuses is said once, the plain pass does the work with the same field, and the card is still in use",
                  err.getvalue().strip()[:120])
    finally:
        vf.FUSED = was


def test_the_card_takes_the_filtered_frames_it_left_there():
    """`shift_field` given the two frames band-passed already (`ha`, `hb`) -- the CPU's arrays, or the card's own left by
    `bandpass_kept` -- reads the same field as when it filters them itself; `shift_field_auto` and its verdict too."""
    print("\nfiltered frames handed over")
    scene = isotropic(500, 700)
    ga, gb = scene[40:400, 40:520].copy(), scene[36:396, 51:531].copy()
    none = np.zeros(ga.shape, bool)
    with on(None):
        ref, still_ref = vf.shift_field_auto(ga, gb, none, none, a=3, reach=60)
    for c in the_cards():
        with on(c):
            own = vf.shift_field(ga, gb, none, none, a=3, reach=60)
            cpus = vf.shift_field(ga, gb, none, none, a=3, reach=60, ha=vf.bandpass(ga), hb=vf.bandpass(gb))
            kept = vf.shift_field(ga, gb, none, none, a=3, reach=60, ha=vf.bandpass_kept(ga), hb=vf.bandpass_kept(gb))
            auto, still = vf.shift_field_auto(ga, gb, none, none, a=3, reach=60)
        same, px, sigma, _ = fields_agree(ref, auto)
        check(np.array_equal(own, cpus) and np.array_equal(own, kept), f"{c.name}: the same field whoever filtered the frames")
        check(same and px <= SHIFT_PX and still == still_ref, f"{c.name}: `shift_field_auto` reads the CPU's field and its verdict",
              f"{len(auto)} rows, worst {px:.1e} px, held still {still}")


def test_the_cards_batches_change_nothing():
    """A card with little memory free takes a pair's templates in several batches; one that runs out while computing
    halves what it sends and goes on. Either way each template's numbers are what one batch gives."""
    print("\nbatches")
    scene = isotropic(520, 760)
    ga, gb = scene[40:460, 40:680].copy(), scene[33:453, 52:692].copy()
    none = np.zeros(ga.shape, bool)
    with on(gpu.stand_in()):
        ref = vf.shift_field(ga, gb, none, none, reach=60, zeros=(4, -1))

    class Small(gpu.Card):
        """The stand-in with room for a few templates at a time, and an FFT that fails when given more than `most`."""
        most, sent = 6, []

        def room(self):
            return int(self.less * 40e6)

    small = gpu.stand_in()
    small.__class__ = Small

    class Fft:
        def __init__(self, fft):
            self.fft = fft

        def rfftn(self, x, s=None, axes=None):
            if x.ndim == 3 and x.shape[1] == 128:                 # the templates of a batch
                Small.sent.append(x.shape[0])
                if x.shape[0] > Small.most:
                    raise MemoryError("out of memory (a drawn one)")
            return self.fft.rfftn(x, s=s, axes=axes)

        def irfftn(self, x, s=None, axes=None):
            return self.fft.irfftn(x, s=s, axes=axes)
    small.fft, small.errors = Fft(small.fft), (MemoryError, RuntimeError)
    with on(small):
        got = vf.shift_field(ga, gb, none, none, reach=60, zeros=(4, -1))
        still_on = gpu.card() is small and gpu.active() is small
    check(all(np.array_equal(r, g) for r, g in zip(ref, got)) and len(ref[0]) >= 12,
          "several batches give each template the numbers one batch does, to the bit", f"batches of {Small.sent}")
    check(still_on and small.less < 1.0 and max(Small.sent) > Small.most and Small.sent[-1] <= Small.most,
          "out of memory halves what is sent at once, and the card is kept", f"room now {small.less:g} of what it was")


def test_a_card_that_stops_hands_over_to_the_cpu():
    """Never required, and never a crash: when the card refuses, it is said once, the CPU computes what was asked, and
    the process computes on the CPU from then on. The numbers are the CPU's own, to the bit."""
    print("\na card that stops")
    scene = isotropic(520, 760)
    ga, gb = scene[40:460, 40:680].copy(), scene[33:453, 52:692].copy()
    none = np.zeros(ga.shape, bool)
    with on(None):
        ref = vf.shift_field(ga, gb, none, none, reach=60)
        ref_h, ref_r = vf.bandpass(ga), vf.spot_response(ga, 9.0)

    class Broken:
        def __getattr__(self, name):
            def fail(*a, **kw):
                raise RuntimeError("cuFFT_INTERNAL_ERROR (a drawn one)")
            return fail

    def broken():
        c = gpu.stand_in()
        c.fft, c.errors = Broken(), (MemoryError, RuntimeError)
        return c
    err = io.StringIO()
    gpu._told = False
    with contextlib.redirect_stderr(err):
        with on(broken()):
            kept = vf.bandpass_kept(ga)                           # made while the card still answered
            got = vf.shift_field(ga, gb, none, none, reach=60, ha=kept)
            after, why = gpu.card(), gpu.why()
            again = vf.shift_field(ga, gb, none, none, reach=60)
        with on(broken()):
            resp = vf.spot_response(ga, 9.0)
    said = err.getvalue()
    check(np.array_equal(got, ref) and np.array_equal(again, ref), "the field is the CPU's, to the bit, then and afterwards")
    check(after is None and "stopped" in why, "from then on this process computes on the CPU, and `why` says the card stopped", why[:90])
    check(np.array_equal(resp, ref_r), "the spot detector likewise")
    check(said.count("the graphics card stopped") == 1 and "The CPU does the rest" in said, "said once on stderr, in a sentence",
          said.strip()[:140])
    gpu._told = False

    class BadFilter:
        def gaussian_filter1d(self, *a, **kw):
            raise RuntimeError("the filter failed (a drawn failure)")
    c = gpu.stand_in()
    c.ndimage, c.errors = BadFilter(), (MemoryError, RuntimeError)
    with contextlib.redirect_stderr(io.StringIO()):
        with on(c):
            h = vf.bandpass(ga)
    check(np.array_equal(h, ref_h), "and the band-pass")
    gpu._told = False


def test_the_cards_spot_detector_is_the_cpus():
    """The spot detector's response (a disc less a ring about it) by FFT on the card at every size, in double: the direct
    sum's numbers, which the CPU makes directly under 9 px and by a single-precision FFT from there. The same spots come
    out, in the same order, at the same places."""
    print("\nthe spot detector")
    from scipy import ndimage
    h, w = 400, 560
    g = (60 + RNG.normal(0, 3, (h, w))).astype(np.float32)
    yy, xx = np.mgrid[0:h, 0:w]
    spots = [(120.3, 90.6, 5.0, 150), (300.2, 210.9, 9.0, 120), (410.7, 330.1, 21.0, 90), (200.5, 60.2, 9.0, 60)]
    for x, y, size, amp in spots:
        g += (amp * np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * (size / 2.355) ** 2))).astype(np.float32)
    bad = np.zeros((h, w), bool)
    for c in the_cards():
        worst, same_spots, moved = 0.0, True, 0.0
        for size in (5.0, 9.0, 21.0):
            exact = ndimage.correlate(g.astype(np.float64), vf._kernel(size), mode="nearest")
            with on(None):
                ref = vf.source_candidates(g, bad, size=size, n_max=None, min_resp=12.0)
            with on(c):
                resp = vf.spot_response(g, size)
                got = vf.source_candidates(g, bad, size=size, n_max=None, min_resp=12.0)
            worst = max(worst, float(np.abs(resp - exact).max()))
            same_spots = same_spots and len(ref) == len(got) and len(ref) >= 1
            if len(ref) == len(got) and ref:
                moved = max(moved, float(np.abs(np.array(ref) - np.array(got))[:, :2].max()))
        check(resp.dtype == g.dtype and worst < 1e-4, f"{c.name}: the response is the direct sum's, in the frame's precision",
              f"worst {worst:.1e} of a grey level")
        check(same_spots and moved < 1e-3, f"{c.name}: the same spots, in the same order, at the same places", f"worst {moved:.1e} px")


def test_one_thread_talks_to_the_card_and_nothing_collects_elsewhere():
    """CuPy keeps its FFT plans in a cache of each thread's own, and that cache runs Python's cycle collector when it is
    cleared and when its thread ends. The window runs the collector in its own thread and nowhere else (a widget freed
    in Measure's thread is a crash), and its suite caught the card's first version collecting in Measure's thread. So
    every routine on a card is handed to one thread that never ends (`Card.run`), and letting the plans go
    (`Card.tidy`) collects nothing. Here a pass is made as the window makes one: in a thread of its own, automatic
    collection off, the thread ended after."""
    print("\none thread talks to the card")
    import gc
    import threading
    scene = isotropic(420, 640)
    ga, gb = scene[20:380, 30:510].copy(), scene[14:374, 41:521].copy()
    none = np.zeros(ga.shape, bool)
    for c in the_cards():
        seen, where, made = [], [], []

        def watch(phase, info):
            if phase == "start" and threading.current_thread() is not threading.main_thread():
                seen.append(threading.current_thread().name)

        def a_pass():
            with gpu.on(c):
                made.append(vf.shift_field_auto(ga, gb, none, none, reach=60))
                made.append(vf.shift_field(ga, gb, none, none, reach=40, stride=48))      # another size: another plan
                made.append(vf.spot_response(ga, 21.0))
                where.append(c.run(lambda: threading.current_thread().name))
            c.tidy()
        was = gc.isenabled()
        gc.collect()
        gc.disable()
        gc.callbacks.append(watch)
        try:
            for _ in range(2):                                    # twice: the second thread finds the first one's plans
                t = threading.Thread(target=a_pass, name="a-stage")
                t.start()
                t.join()
            gc.collect()
        finally:
            gc.callbacks.remove(watch)
            if was:
                gc.enable()
        check(len(made) == 6 and len(made[0][0]) >= 8, f"{c.name}: two passes, each in a thread of its own that then ends")
        check(where == (["mcdonald-card"] * 2 if c.real else ["a-stage"] * 2),
              f"{c.name}: the arithmetic is done in " + ("the one thread that talks to the card, whichever thread asks" if c.real
                                                         else "the asking thread (NumPy needs no thread of its own)"), str(where))
        check(not seen, f"{c.name}: and the cycle collector ran in no thread but the main one, through the passes, the "
              "plans let go and the threads' ends", str(seen))


# ---------------------------------------------------------------- the stages
def test_frames_are_read_ahead_in_any_order():
    """`progress.Ahead`: threads read what a loop in this process will ask for, in its order and as often as it will ask;
    each read is made once, a result is let go after its last asking, and a key nobody foresaw is read there and then."""
    print("\nreading ahead")
    import threading
    reads, lock = [], threading.Lock()

    def read(n):
        with lock:
            reads.append(n)
        return n * n
    asks = [n for a in range(1, 41) for n in (a, a + 5)]
    with progress.Ahead(read, asks, threads=4) as ahead:
        got = [ahead.get(n) for n in asks]
        held = len(ahead.out)
        extra = ahead.get(999), ahead.get(3)                      # not foreseen; and asked once more than was said
    check(got == [n * n for n in asks], "every asking gets its frame, in the loop's order")
    check(sorted(reads[:-2]) == sorted(set(asks)) and extra == (999 * 999, 9) and reads[-2:] == [999, 3],
          "each frame is read once however often it is asked for; one nobody foresaw is read there and then",
          f"{len(reads)} reads for {len(asks)} askings")
    check(held == 0, "and nothing is held once the last asking is answered", str(held))
    with progress.Ahead(read, list(range(100, 140)), threads=2, depth=4) as ahead:
        first = ahead.get(100)
        waiting = len(ahead.out)
    check(first == 10000 and waiting <= 4, "no more than `depth` frames are read ahead of the loop", str(waiting))
    asks = [n for a in range(200, 230) for n in (a, a + 5)]
    with progress.Ahead(read, asks, threads=1, depth=2) as ahead:      # one thread: still two frames ahead, with six held for
        got = [ahead.get(n) for n in asks[:20]]                          # their second asking
        ahead_now, held = len(ahead.fresh), len(ahead.out)
    check(got == [n * n for n in asks[:20]] and ahead_now == 2 and held > ahead_now,
          "frames held for a second asking do not count against the reads ahead", f"{ahead_now} ahead, {held} held")
    ahead = progress.Ahead(read, [1, 2, 3], threads=2)
    ahead.close()
    check(ahead.get(2) == 4, "after `close`, a frame is read where it is asked for")


def _square(n):
    return n, n * n


def _nothing():
    pass


def _stops_at_5(n):
    """A job during which the card stops, at the sixth: in this process, as `gpu.gave_up` leaves things."""
    c = gpu.active()
    if n == 5 and c is not None:
        c.stopped = "a drawn stop"
    return _square(n)


def test_a_stage_whose_card_stops_goes_on_in_a_pool():
    """`forensics.pooled_or_on_card`: with no card it is `pooled`; with one, the jobs run in this process; and when the
    card stops part-way the jobs not yet done go to a pool of CPUs."""
    print("\na stage on a card, and when the card stops")
    jobs = list(range(12))
    said = []
    with on(None):
        cpu = vf.pooled_or_on_card({}, _square, [], 2, _square, jobs, _nothing, ())
    G = {}
    with on(gpu.stand_in()):
        here = vf.pooled_or_on_card(G, lambda n: n, [], 2, _square, jobs, _nothing, (), progress=lambda *a: said.append(a))
    check(cpu == here == [(n, n * n) for n in jobs] and "ahead" not in G and said[0] == ("", 0, 12) and said[-1] == ("", 12, 12),
          "the same results in the same order from the pool and in this process, the progress counted to the end")

    said = []
    with on(gpu.stand_in()):
        mixed = vf.pooled_or_on_card({}, lambda n: n, [], 2, _stops_at_5, jobs, _nothing, (), progress=lambda *a: said.append(a))
    check(mixed == [(n, n * n) for n in jobs] and said[-1] == ("", 12, 12),
          "a card that stops at the sixth job: the other six come from the pool, and the count goes on to the end", str(said[-1]))

    def halts():
        return len(said) >= 3
    said = []
    try:
        with on(gpu.stand_in()):
            vf.pooled_or_on_card({}, lambda n: n, [], 2, _square, jobs, _nothing, (), progress=lambda *a: said.append(a), stop=halts)
        stopped = False
    except progress.Stopped:
        stopped = True
    check(stopped, "and it stops when asked, between jobs")


def _sliding_clip(td, v, name, frames=36, h=420, w=640):
    """A lossless clip of a cloud-like scene sliding by v px a frame, with noise new in every frame, and its Clip."""
    from PIL import Image
    from scipy import ndimage
    from mcdonald import clip as clipmod
    rng = np.random.default_rng(1112)
    src = Path(td) / f"src-{name}"
    src.mkdir()
    big = ndimage.gaussian_filter(rng.normal(0, 1, (h + 80, w + 300)), 3.0)
    big = 30.0 * big / big.std()
    for n in range(1, frames + 1):
        scene = ndimage.shift(big, (v[1] * n, v[0] * n), order=1, mode="wrap")[40:40 + h, 150:150 + w]
        Image.fromarray(np.clip(120.0 + scene + rng.normal(0, 1.0, (h, w)), 0, 255).astype(np.uint8)).save(src / f"f{n:05d}.png")
    video = Path(td) / f"{name}.mkv"
    subprocess.run(["ffmpeg", "-v", "error", "-framerate", "30", "-i", str(src / "f%05d.png"), "-c:v", "ffv1", "-pix_fmt", "gray",
                    str(video)], check=True)
    return clipmod.Clip(video, Path(td) / f"frames-{name}")


def test_layers_and_integrity_on_the_card_are_the_cpus():
    """The two slow checks of a Measure, whole: `layers` (both its rounds: every pair, and the pairs held still measured
    again over a second) and `integrity`'s background motion, on a drawn clip, by the CPU and by the card's code in this
    process with the frames read ahead. The same pairs are read the same way, and the rates agree."""
    print("\nlayers and integrity, whole")
    import shutil
    if shutil.which("ffmpeg") is None:
        print("  SKIP  ffmpeg is not installed")
        return
    from mcdonald import integrity, layers
    with tempfile.TemporaryDirectory() as td:
        clips = {"a scene sliding 3 px a frame": _sliding_clip(td, (3.0, 1.0), "moving"),
                 "a scene sliding 0.3 px a frame": _sliding_clip(td, (0.3, 0.1), "slow")}
        for what, clip in clips.items():
            none = np.zeros((clip.H, clip.W), bool)
            masks = dict(blocks=none, graphics=none, colour=True, tinted=False)

            def run(card):
                with on(card):
                    found = layers.measure(clip, masks, procs=0, fresh=True, say=lambda *a: None)
                    cache = max(clip.dir.glob("bg_layers_k5_*.npz"), key=lambda p: p.stat().st_mtime_ns)
                    tpl = np.load(cache)["tpl"]
                    bg, note = integrity.per_frame_background(clip, masks, None, None, set(), procs=0)
                return found.fields, tpl, bg, note
            f0, t0, b0, n0 = run(None)
            for c in the_cards():
                f1, t1, b1, n1 = run(c)
                same = t0.shape == t1.shape and np.array_equal(t0[:, [0, 1, 2, -2, -1]], t1[:, [0, 1, 2, -2, -1]])
                d = float(np.abs(t0[:, 3:5] - t1[:, 3:5]).max()) if same and len(t0) else np.inf
                check(same and len(t0) > 100 and d <= SHIFT_PX,
                      f"{c.name}, layers, {what}: the same templates of the same pairs, read the same way (moved, again or still)",
                      f"{len(t0)} rows, worst shift difference {d:.1e} px; held still in {f0['held_still']['share_of_pairs']:.0%} of pairs")
                r0, r1 = f0["px_per_s"]["all"], f1["px_per_s"]["all"]
                check(f0["held_still"] == f1["held_still"] and (r0 is None) == (r1 is None)
                      and (r0 is None or abs(r0["median"] - r1["median"]) <= 0.01),
                      f"{c.name}, layers, {what}: the same share held still, and the scene's rate within 0.01 px/s",
                      "no rate: the window is under a second" if r0 is None else f"{r0['median']:.3f} and {r1['median']:.3f} px/s")
                both = sorted(set(b0) & set(b1))
                db = max((float(np.abs(np.array(b0[n][0]) - np.array(b1[n][0])).max()) for n in both), default=np.inf)
                check(sorted(b0) == sorted(b1) and all(b0[n][1] == b1[n][1] for n in both) and db <= AGREED_PX and n0 == n1,
                      f"{c.name}, integrity, {what}: the same pairs read on the same layer, each shift within {AGREED_PX} px",
                      f"{len(both)} pairs, worst {db:.1e} px")
        moving = clips["a scene sliding 3 px a frame"]
        none = np.zeros((moving.H, moving.W), bool)
        with on(gpu.stand_in()):
            found = layers.measure(moving, dict(blocks=none, graphics=none, colour=True, tinted=False), procs=0, fresh=True, say=lambda *a: None)
        v = found.fields["px_per_s"]["all"]
        check(v is not None and abs(v["median"] - 30 * np.hypot(3.0, 1.0)) < 2.0, "and the rate is the drawn one",
              f"{v['median']:.1f} px/s against {30 * np.hypot(3.0, 1.0):.1f}" if v else "none")
        check("ahead" not in layers._G and "filtered" not in layers._G and "ahead" not in integrity._G,
              "nothing of the card's round is left behind: no reading threads, no frames kept on the card")
        kept = sorted(p.name for p in moving.dir.glob("bg_layers_k5_*.npz"))
        said = []
        gpu.begin()
        with on(None):
            layers.measure(moving, dict(blocks=none, graphics=none, colour=True, tinted=False), procs=0, say=said.append)
            from_cpu = gpu.computed_on()
        with on(gpu.stand_in()):
            layers.measure(moving, dict(blocks=none, graphics=none, colour=True, tinted=False), procs=0, say=said.append)
            from_card = gpu.computed_on()
        gpu.begin()
        check(len(kept) == 2 and sum("measured earlier" in x for x in said) == 2 and from_cpu is None and "stand-in" in str(from_card),
              "the card's templates are kept beside the frames apart from the CPU's: a run on the CPU reads its own back, "
              "a run on the card its own, and that one still says a card took part", f"{kept}; {from_card}")


class _Shaken:
    """A textured scene of 150 frames, the whole picture moved `jitter` px along x at 6 Hz (a cooler's or a gimbal's
    shake) and sliding `pan` px a frame, with one bright point on it: what `flicker.scene_shift` registers."""
    W, H, fps, n0, n1 = 320, 240, 30.0, 1, 150

    def __init__(self, jitter, pan=0.0):
        from scipy import ndimage
        self.jitter, self.pan = jitter, pan
        big = ndimage.gaussian_filter(np.random.default_rng(3).normal(0, 1, (self.H, self.W + 200)), 2.5)
        self.scene = np.clip(big * 80 + 60, 20, 110)
        self.cache = {}

    def at(self, n):
        return 90.0 + 0.37 * n, 80.0 + 0.21 * n

    def rgb(self, n):
        if n not in self.cache:
            from scipy import ndimage
            dx = self.jitter * np.sin(2 * np.pi * 6.0 * n / self.fps) + self.pan * n
            g = ndimage.shift(self.scene, (0, dx), order=3, mode="nearest")[:, :self.W] + np.random.default_rng(n).normal(0, 1.0, (self.H, self.W))
            x, y = self.at(n)
            yy, xx = np.mgrid[:self.H, :self.W]
            g = g + 120 * (1 + 0.25 * np.sin(2 * np.pi * 6.0 * n / self.fps)) * np.exp(-((xx - x - dx) ** 2 + (yy - y) ** 2) / 2.0)
            self.cache[n] = np.clip(g, 0, 255)[..., None].repeat(3, 2).astype(np.float32)
        return self.cache[n]


def test_flickers_shake_pass_on_the_card_is_the_cpus():
    """`flicker`'s camera-shake pass (`scene_shift`, 2026-11-13): every frame registered against the stretch's mean
    frame, or against the frame before where the scene pans, by least squares on the gradient with three Fourier warps
    (`lk_shift`), and again with a small shift planted at the beat. On a card the same in this process, the frames read
    ahead: the same way of registering, each number of the reading within a ten-thousandth of a pixel."""
    print("\nflicker's camera-shake pass")
    from mcdonald import flicker
    for what, clip in (("a picture shaken 0.3 px at the beat", _Shaken(0.3)), ("the same, sliding 1.2 px a frame", _Shaken(0.3, pan=1.2))):
        ns = list(range(1, 151))
        tracks = {"object": {n: clip.at(n) for n in ns}}

        def run(card):
            with on(card):
                return flicker.scene_shift(clip, ns, tracks, {"object": 6.0}, procs=0)
        cpu = run(None)
        check(cpu["scene"]["power"] and cpu["scene"]["registered"] == ("frame to frame" if clip.pan else "against the mean frame")
              and 0.2 <= cpu["object"]["at_beat_px"] <= 0.4,
              f"on the CPU, {what}: registered {cpu['scene']['registered']}, and the shake read at about its size",
              f"{cpu['object']['at_beat_px']:.3f} px at the beat, a planted {flicker.SHIFT_PLANT} px recovered {cpu['object']['recovered']:.2f}")
        for c in the_cards():
            got = run(c)
            a, b, sa, sb = cpu["object"], got["object"], cpu["scene"], got["scene"]
            far = max(abs(a[k] - b[k]) for k in ("at_beat_px", "recovered"))
            check(sa["registered"] == sb["registered"] and sa["power"] == sb["power"] and a["moves"] == b["moves"]
                  and abs(sa["step_px"] - sb["step_px"]) <= 1e-4 and abs(sa["texture"] - sb["texture"]) <= 1e-4 * sa["texture"]
                  and abs(a["at_beat_px"] - b["at_beat_px"]) <= 1e-4 and abs(a["recovered"] - b["recovered"]) <= 1e-3
                  and abs(a["stands"] - b["stands"]) <= 1e-3 * a["stands"] and abs(a["local"] - b["local"]) <= 1e-3 * a["local"],
                  f"{c.name}, {what}: registered the same way, the shake at the beat within 0.0001 px, the same verdict",
                  f"{b['at_beat_px']:.6f} against {a['at_beat_px']:.6f} px; farthest of the shake and the planted share {far:.1e}")
        check("ahead" not in flicker._S and "ref_on" not in flicker._S, f"{what}: nothing of the card's round is left behind")


def test_the_third_pass_of_layers_on_the_card_is_the_cpus():
    """`layers`' third pass (2026-11-13): where a pattern on the sensor holds the templates at zero, each pixel's mean
    over a block is taken out and the block's pairs are matched again (`layers._mean_out`). On a card the same blocks
    in the stage's own process, the pairs matched on the card and the frames read ahead: the same blocks, the same
    pairs read, the scene's velocity within a hundredth of a pixel a frame."""
    print("\nlayers' third pass, the scene under a sensor's pattern")
    import json
    import shutil
    import subprocess
    if shutil.which("ffmpeg") is None:
        print("  SKIP  ffmpeg is not installed")
        return
    from PIL import Image
    from scipy import ndimage
    from mcdonald import clip as clipmod, layers
    v, frames, h, w = (6.0, 1.5), 70, 480, 640
    with tempfile.TemporaryDirectory() as td:
        rng = np.random.default_rng(113)         # test_measurement's breathing clip: a scene behind a pattern four times as strong
        src = Path(td) / "src"
        src.mkdir()
        big = ndimage.gaussian_filter(rng.normal(0, 1, (h + 80, w + 700)), 3.0)
        big = 5.0 * big / big.std()
        pattern = ndimage.gaussian_filter(rng.normal(0, 1, (h, w)), 1.5)
        pattern = 20.0 * pattern / pattern.std()
        for n in range(1, frames + 1):
            scene = ndimage.shift(big, (v[1] * n, v[0] * n), order=1, mode="wrap")[40:40 + h, 350:350 + w]
            g = 110.0 + scene + (1.0 + 0.25 * np.sin(2 * np.pi * n / 23.0)) * pattern + rng.normal(0, 1.0, (h, w))
            Image.fromarray(np.clip(g, 0, 255).astype(np.uint8)).save(src / f"f{n:05d}.png")
        video = Path(td) / "breathes.mkv"
        subprocess.run(["ffmpeg", "-v", "error", "-framerate", "30", "-i", str(src / "f%05d.png"), "-c:v", "ffv1", "-pix_fmt", "gray", str(video)], check=True)
        clip = clipmod.Clip(video, src)
        none = np.zeros((clip.H, clip.W), bool)
        masks = dict(blocks=none, graphics=none, colour=True, tinted=False)

        def run(card):
            with on(card):
                layers.measure(clip, masks, k=5, procs=0, fresh=True, say=lambda *a: None, scene=True)
                cache = max(clip.dir.glob("bg_scene_k5_*.npz"), key=lambda p: p.stat().st_mtime_ns)
                z = np.load(cache)
                return json.loads(str(z["blocks"])), z["tpl"]
        b0, t0 = run(None)
        read0 = [(b["start"], b["tpl_pairs_read"], b["tpl_pairs_tried"]) for b in b0]
        check(len(t0) > 20 and any(r for _, r, _ in read0)
              and all(np.hypot(b["tpl_vx"] - v[0], b["tpl_vy"] - v[1]) < 0.3 for b in b0 if b["tpl_vx"] is not None),
              "on the CPU the third pass reads the drawn scene under the pattern", f"{len(t0)} rows; blocks (start, read, tried) {read0}")
        for c in the_cards():
            b1, t1 = run(c)
            read1 = [(b["start"], b["tpl_pairs_read"], b["tpl_pairs_tried"]) for b in b1]
            same = t0.shape == t1.shape and np.array_equal(t0[:, [0, 1, 2, -2, -1]], t1[:, [0, 1, 2, -2, -1]])
            d = float(np.abs(t0[:, 3:5] - t1[:, 3:5]).max()) if same and len(t0) else np.inf
            dv = max((np.hypot(x["tpl_vx"] - y["tpl_vx"], x["tpl_vy"] - y["tpl_vy"]) for x, y in zip(b0, b1) if x["tpl_vx"] is not None and y["tpl_vx"] is not None),
                     default=np.inf)
            check(read0 == read1 and same and d <= SHIFT_PX and dv <= 0.01,
                  f"{c.name}, the third pass: the same blocks and pairs read, the same templates, the scene's velocity within 0.01 px a frame",
                  f"{len(t1)} rows, worst shift difference {d:.1e} px, velocity {dv:.1e} px/frame")
        check("ahead" not in layers._G, "and no reading threads are left behind")


def test_a_case_says_what_computed_it_and_is_measured_again_that_way():
    """A card's numbers agree with the CPU's to about a part in a million, and `mcdonald share rerun` holds a case file
    to one in a billion. So a case keeps what computed it (`computed_on`), its report says so, a case the CPU measured
    is measured again on the CPU (also on a computer with a card: every reference case from before 2026-11-12 reruns
    as it did), and a case a card took part in is held to the card's agreement, said in the comparison."""
    print("\na case says what computed it")
    import json
    from mcdonald import report, rerun
    case = report.Case("drawn", "drawn.mp4")
    plain = json.loads(case.json())
    case.computed_on = "NVIDIA GeForce RTX 5070 Ti (CuPy 14.2.0, CUDA 13.2)"
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "drawn_case.json"
        path.write_text(case.json(), encoding="utf-8")
        back = report.Case.load(path)
    check(plain["computed_on"] is None and back.computed_on == case.computed_on,
          "a case keeps the card that took part in it, and None where the CPU measured alone; it is read back with the case")
    line = case.computed_on_said()
    check("graphics card" in line and "RTX 5070 Ti" in line and "--gpu none" in line and "part in a million" in line,
          "its report says so under the heading: which card, how far a card agrees with the CPU, and how to measure on the CPU",
          line[:120])
    check("computed_on" in rerun.VOLATILE, "what computed a case is the case's own, not a measurement to compare")
    gpu.begin()
    plain_env = report.envelope("layers", {})
    gpu.took_part(gpu.stand_in())
    card_env = report.envelope("layers", {})
    gpu.begin()
    check(plain_env["notes"] == [] and len(card_env["notes"]) == 1 and "stand-in" in card_env["notes"][0]
          and "--gpu none" in card_env["notes"][0] and set(plain_env) == set(card_env),
          "a command's own --json says so too, among its notes, where a card took part; the envelope's fields are the "
          "same either way", str(card_env["notes"])[:120])
    cpu, card = dict(computed_on=None), dict(computed_on="NVIDIA GeForce RTX 5070 Ti (CuPy 14.2.0, CUDA 13.2)")
    check(rerun.held_to(cpu, cpu) == (rerun.REL, 0.0, None) and rerun.held_to({}, {}) == (rerun.REL, 0.0, None)
          and rerun.held_to(cpu, card)[:2] == (rerun.CARD_REL, rerun.CARD_ABS) and rerun.held_to(card, cpu)[2] == card["computed_on"],
          "two cases the CPU measured are held to one part in a billion, as ever (a case from before this had no such "
          "line); where a card took part in either, to the card's agreement", f"{rerun.REL:g}, {rerun.CARD_REL:g}")
    old = dict(median=0.002164694845058817, rate=2.5843046420297098, pairs=265, said="median 103 px/s (16-84 %: 90-110)", tiny=3.1e-9)
    new = dict(median=0.002164666917630358, rate=2.584304664447357, pairs=265, said="median 103 px/s (16-84 %: 90-110)", tiny=2.2e-9)
    strict, loose, other = [], [], []
    rerun._same(old, new, "fields", strict)
    rerun._same(old, new, "fields", loose, rerun.CARD_REL, rerun.CARD_ABS)
    rerun._same(dict(old, pairs=266, said="median 104 px/s (16-84 %: 90-110)", rate=2.59), new, "fields", other, rerun.CARD_REL, rerun.CARD_ABS)
    check(sorted(w for w, _, _ in strict) == ["fields.median", "fields.rate", "fields.tiny"] and loose == [],
          "PR135's own differences between the CPU and the card (1.3 parts in 100,000 at the most) fail one part in a "
          "billion and pass the card's agreement", str([w for w, _, _ in strict]))
    check(sorted(w for w, _, _ in other) == ["fields.pairs", "fields.rate", "fields.said"],
          "a count, a sentence or a rate that moved by more is a difference still", str([w for w, _, _ in other]))
    seen = {}

    def fake_run(cmd, **kw):
        seen["env"] = (kw.get("env") or {}).get(gpu.GPU_VAR, "<unset>")
        raise RuntimeError("stop here: only the environment is wanted")
    keep = subprocess.run
    with tempfile.TemporaryDirectory() as td, environment(MCDONALD_GPU=None):
        folder = Path(td) / "object-1"
        folder.mkdir()
        for name, on_card, want in (("the CPU", None, gpu.NONE), ("a card", case.computed_on, "<unset>")):
            c = report.Case("drawn", "drawn.mp4")
            c.commands, c.computed_on = ["mcdonald run drawn.mp4 --track drawn_track.csv"], on_card
            (folder / "drawn_case.json").write_text(c.json(), encoding="utf-8")
            subprocess.run = fake_run
            try:
                rerun.rerun_object(folder, "drawn.mp4", Path(td) / "out", say=lambda *a: None)
            except RuntimeError:
                pass
            finally:
                subprocess.run = keep
            check(seen.get("env") == want, f"a case that {name} measured is measured again "
                  + ("on the CPU, whatever card this computer has" if on_card is None else "by this computer's own choice of card"),
                  f"MCDONALD_GPU for the run: {seen.get('env')}")


def main():
    print("mcDonald UAP Toolkit — computing on a graphics card")
    for name in sorted(name for name, fn in globals().items() if name.startswith("test_") and callable(fn)):
        globals()[name]()
    gpu.forget()
    print(f"\n{'ALL PASS' if not FAIL else str(len(FAIL)) + ' FAILED: ' + ', '.join(FAIL)}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    for _s in (sys.stdout, sys.stderr):           # a pipe or a log file on Windows is cp1252
        _s.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
