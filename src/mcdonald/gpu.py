"""The graphics cards (GPUs) this computer has, the choice of one, and the computing done on it.

Two halves. The first finds the cards, for Preferences' choice of one (Jacob, 2026-10-19: "add a GPU selection option;
this should be greyed out if no GPU is available; we will add actual GPU features later"). The second is those
features (2026-11-12, the day the development machine had a card): `card()` is the card this process computes on, or
None, and the stages that have a card version of their arithmetic ask it.

**Finding the cards**, with nothing installed for it:
- Linux: the PCI display controllers (class 03) in /sys/bus/pci/devices, named from the PCI ID list the system keeps
  (pci.ids, the one lspci reads): 1002:68f2 there is "Cedar GL [FirePro 2270]", said here as "AMD FirePro 2270";
- macOS: system_profiler SPDisplaysDataType ("Apple M2", "AMD Radeon Pro 5500M");
- Windows: Win32_VideoController, through PowerShell.
A display controller that is not a graphics processor is left out: a server's management chip (ASPEED, Matrox: merlin
has a Matrox G200 beside its FirePro), a virtual machine's screen (VMware, VirtualBox, QEMU, Hyper-V, Parallels,
Apple's paravirtual one), and a card Windows drives with its basic driver only.

Each card says whether it can compute at all (`compute`: Vulkan lists it as a GPU, or it is NVIDIA's with CUDA's
library, or on a Mac Metal runs on it) and whether mcdonald can compute on it (`cuda`). Only the second kind is
offered (Jacob, 2026-10-19: "the GPU drop-down should only show devices with real GPU features"), and since
2026-11-12 a real feature is one mcdonald has: its arithmetic on a card is CuPy's, which runs on NVIDIA cards through
CUDA, on Linux and Windows. A Mac's card, an AMD or an Intel one is found, named, and said not to be used yet.
merlin's FirePro 2270 (TeraScale 2, on the old radeon driver) cannot compute at all: the only Vulkan device there is
llvmpipe, which is the CPU. No toolkit is imported to find the cards.

**Computing on one.** The rules, each with its reason:
- *Never required.* With no card, no CuPy (the add-on: `mcdonald.addon` installs it), or a card that fails part-way, every stage
  computes on the CPU as it always has. The CPU's arithmetic is the reference, and its code is not touched by any
  of this: the card's version of a routine stands beside it and is held to it (tests/test_gpu.py; the goldens run
  on both).
- *The choice.* MCDONALD_GPU in the environment, which `mcdonald --gpu X` and Preferences set: unset or "auto" is the
  first card, "none" the CPU only, otherwise a card's name (or part of it) or its number.
- *A batch job's allocation, not the machine*, as `progress.cpus` has it for CPUs: inside a Slurm job a card is used
  only where the job was given one (`--gres=gpu:1` sets CUDA_VISIBLE_DEVICES). A job that did not ask must not find
  itself sharing the card with one that did.
- *One process computes on it.* A pool's workers never do (`card()` is None in them): each would hold its own copy
  of the driver's state on the card, a few hundred MB, and they would take turns. A stage with a card version runs
  in this process, the frames read ahead by threads (`progress.Ahead`), and the card does the arithmetic.
- *A stage says so.* A routine with a card version (`forensics.bandpass`, `shift_field`, `spot_response`) runs on the
  card only inside `with gpu.on(card):`, which a stage enters for the whole of a pass (`forensics.pooled_or_on_card`).
  Anywhere else it is the CPU's arithmetic, card or no card. So a stage's numbers never depend on whether a caller
  happened to run it in this process or on a pool: the package's tests hold many stages to "the same on a pool as in
  one process, to the bit", and a card used wherever one was to hand broke that on the first day (2026-11-12:
  `groups`' spots in this process came from the card, its pool's from the CPU).
- *A failure is not a crash.* Out of memory first halves what is sent at once (`Card.fewer`); anything else the card
  refuses is said once on stderr, the card is given up for the rest of the process (`gave_up`), and the CPU does
  the work.
- *One thread talks to the card, and it never ends* (`Card.run`, the thread "mcdonald-card"). CuPy keeps its FFT
  plans in a cache of each thread's own, and that cache runs Python's cycle collector when it is cleared and when
  its thread ends (cupy/fft/_cache.pyx, `_clear_LinkedList`). The window runs the collector in its own thread and
  nowhere else (`mark_qt.Collector`: a widget freed in Measure's thread is a crash), and the window's suite caught
  the card's first version collecting in Measure's thread, 19 times. So no stage's thread ever touches CuPy: every
  routine on a card is handed to the one thread, which is never joined, and `tidy` takes the plans out of the cache
  one by one, which collects nothing. What is left: a card truly out of memory makes CuPy's allocator run the
  collector once, in that thread, before it gives up (cupy/cuda/memory.pyx, `_try_malloc`); batches are planned on
  half the memory free so that it does not come to that.
"""
import contextlib
import ctypes.util
import gzip
import importlib.util
import json
import multiprocessing
import os
import queue
import re
import subprocess
import sys
import threading
from pathlib import Path

import numpy as np

# PCI vendors whose display controllers are not graphics processors: management chips, and virtual machines' screens
NOT_GPUS = {"1a03": "ASPEED", "102b": "Matrox", "15ad": "VMware", "80ee": "VirtualBox", "1234": "QEMU", "1b36": "QEMU",
            "1af4": "virtio", "1414": "Hyper-V", "1ab8": "Parallels", "1013": "Cirrus Logic"}
VENDORS = {"10de": "NVIDIA", "1002": "AMD", "1022": "AMD", "106b": "Apple", "8086": "Intel", "5143": "Qualcomm"}
ORDER = ("10de", "1002", "1022", "106b", "8086")          # the dedicated cards first: what a choice would usually be
PCI_IDS = ("/usr/share/hwdata/pci.ids", "/usr/share/misc/pci.ids", "/usr/share/pci.ids", "/usr/share/hwdata/pci.ids.gz",
           "/usr/share/misc/pci.ids.gz")
COMPUTING_DRIVERS = ("amdgpu", "i915", "xe")              # Linux drivers whose cards compute, when there is no Vulkan to ask
NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0


def found():
    """[{"name", "vendor", "compute", "cuda"}]: the graphics cards here, dedicated ones first, named as the person
    would know them (the second of two the same is "name (2)"), each saying whether it can compute at all and whether
    mcdonald can compute on it (`cuda`); [] where there are none, or they cannot be asked about. Preferences offers
    those mcdonald can use (`usable`)."""
    try:
        cards = _windows() if sys.platform == "win32" else _mac() if sys.platform == "darwin" else linux()
    except Exception:                                 # a system that answers in a way not foreseen: none found, nothing broken
        cards = []
    cards.sort(key=lambda c: ORDER.index(c["vendor"]) if c["vendor"] in ORDER else len(ORDER))
    seen = {}
    for c in cards:
        seen[c["name"]] = seen.get(c["name"], 0) + 1
        if seen[c["name"]] > 1:
            c["name"] = f"{c['name']} ({seen[c['name']]})"
    return cards


def usable(cards):
    """The cards mcdonald can compute on: what Preferences offers. An NVIDIA card with CUDA's library (see the module's
    docstring); whether CuPy is installed to drive it is `installed`, which Preferences says beside the choice."""
    return [c for c in cards if c.get("cuda")]


def installed():
    """Whether CuPy is here to compute with, found without importing it (a tenth of a second, and the driver's
    libraries with it)."""
    try:
        return importlib.util.find_spec("cupy") is not None
    except (ImportError, ValueError):
        return False


def linux(root="/sys/bus/pci/devices", ids=PCI_IDS, ask=None, cuda=None):
    """The PCI display controllers, named, each with whether it can compute: listed by Vulkan as a GPU (`ask`, which is
    `vulkan`), or on NVIDIA's own driver with CUDA's library (`cuda`, which is `has_cuda`). A GPU Vulkan lists that is
    not on PCI (a phone-class chip's, an Apple chip's under Linux) is added by Vulkan's own name."""
    gpus = (ask or vulkan)()
    listed = {(g["vendor"], g["device"]) for g in gpus or ()}
    cards = []
    for dev in sorted(Path(root).glob("*")):
        try:
            if not (dev / "class").read_text().strip().startswith("0x03"):
                continue
            vendor, device = ((dev / f).read_text().strip().lower().removeprefix("0x") for f in ("vendor", "device"))
        except OSError:
            continue
        if vendor in NOT_GPUS:
            continue
        driver = kernel_driver(dev)
        with_cuda = driver == "nvidia" and bool((cuda or has_cuda)())
        compute = ((vendor, device) in listed if gpus is not None else driver in COMPUTING_DRIVERS) or with_cuda
        cards.append(dict(name=named(vendor, device, *pci_names(vendor, device, ids)), vendor=vendor, device=device,
                          compute=compute, cuda=with_cuda, slot=dev.name))
    return cards + _beyond(cards, gpus, cuda or has_cuda)


def kernel_driver(dev):
    """The Linux driver a PCI device is bound to, from its uevent ("DRIVER=amdgpu"); "" for none."""
    try:
        for line in (Path(dev) / "uevent").read_text().splitlines():
            if line.startswith("DRIVER="):
                return line[7:].strip()
    except OSError:
        pass
    return ""


def _beyond(cards, gpus, cuda):
    """The GPUs Vulkan lists that no display controller is: by Vulkan's own name, and able to compute -- for mcdonald
    too where it is NVIDIA's and CUDA's library is here (`cuda`: a compute card that drives no screen)."""
    have = {(c["vendor"], c.get("device")) for c in cards}
    return [dict(name=g["name"], vendor=g["vendor"], device=g["device"], compute=True, cuda=g["vendor"] == "10de" and bool(cuda()))
            for g in gpus or () if (g["vendor"], g["device"]) not in have]


def has_cuda():
    """Whether NVIDIA's driver put CUDA's library here: libcuda on Linux, nvcuda.dll on Windows."""
    if sys.platform == "win32":
        return (Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "nvcuda.dll").exists()
    return ctypes.util.find_library("cuda") is not None


_VULKAN = r"""
import ctypes, json, struct, sys
lib = None
for name in sys.argv[1:]:
    try:
        lib = ctypes.CDLL(name)
        break
    except OSError:
        pass
if lib is None:
    print("null")
    sys.exit()
class App(ctypes.Structure):
    _fields_ = [("sType", ctypes.c_int), ("pNext", ctypes.c_void_p), ("pApplicationName", ctypes.c_char_p),
                ("applicationVersion", ctypes.c_uint32), ("pEngineName", ctypes.c_char_p),
                ("engineVersion", ctypes.c_uint32), ("apiVersion", ctypes.c_uint32)]
class Info(ctypes.Structure):
    _fields_ = [("sType", ctypes.c_int), ("pNext", ctypes.c_void_p), ("flags", ctypes.c_uint32),
                ("pApplicationInfo", ctypes.POINTER(App)), ("enabledLayerCount", ctypes.c_uint32),
                ("ppEnabledLayerNames", ctypes.c_void_p), ("enabledExtensionCount", ctypes.c_uint32),
                ("ppEnabledExtensionNames", ctypes.c_void_p)]
lib.vkCreateInstance.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
lib.vkEnumeratePhysicalDevices.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32), ctypes.c_void_p]
lib.vkGetPhysicalDeviceProperties.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
lib.vkDestroyInstance.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
app = App(0, None, b"mcdonald", 1, b"mcdonald", 1, (1 << 22) | (1 << 12))       # Vulkan 1.1
inst = ctypes.c_void_p()
if lib.vkCreateInstance(ctypes.byref(Info(1, None, 0, ctypes.pointer(app), 0, None, 0, None)), None, ctypes.byref(inst)):
    print("[]")
    sys.exit()
n = ctypes.c_uint32(0)
lib.vkEnumeratePhysicalDevices(inst, ctypes.byref(n), None)
devices = (ctypes.c_void_p * n.value)()
lib.vkEnumeratePhysicalDevices(inst, ctypes.byref(n), devices)
out = []
for d in devices[:n.value]:
    props = ctypes.create_string_buffer(4096)           # VkPhysicalDeviceProperties is 824 bytes
    lib.vkGetPhysicalDeviceProperties(d, props)
    api, driver, vendor, device, kind = struct.unpack_from("<5I", props.raw, 0)
    out.append(dict(vendor="%04x" % vendor, device="%04x" % device, kind=kind,
                    name=props.raw[20:276].split(b"\0")[0].decode("utf-8", "replace")))
lib.vkDestroyInstance(inst, None)
print(json.dumps(out))
"""
GPU_KINDS = (1, 2)              # VkPhysicalDeviceType: an integrated GPU, a discrete one (not 3 virtual, 4 CPU, 0 other)


def vulkan():
    """[{"vendor", "device", "name"}]: the GPUs Vulkan lists here -- not llvmpipe, which is the CPU -- asked in a Python
    of its own (a driver that hangs or crashes takes only that with it); None where there is no Vulkan to ask."""
    names = ["vulkan-1.dll"] if sys.platform == "win32" else ["libvulkan.so.1", "libvulkan.so"]
    try:
        r = subprocess.run([sys.executable, "-I", "-c", _VULKAN, *names], capture_output=True, encoding="utf-8",
                           errors="replace", timeout=30, creationflags=NO_WINDOW)
        got = json.loads(r.stdout.strip().splitlines()[-1]) if r.returncode == 0 and r.stdout.strip() else None
    except (OSError, subprocess.SubprocessError, ValueError, IndexError):
        return None
    if not isinstance(got, list):
        return None
    return [dict(vendor=g["vendor"], device=g["device"], name=g["name"]) for g in got
            if isinstance(g, dict) and g.get("kind") in GPU_KINDS]


_CUDA = r"""
import ctypes, json, sys
lib = None
for name in sys.argv[1:]:
    try:
        lib = ctypes.CDLL(name)
        break
    except OSError:
        pass
if lib is None:
    print("null")
    sys.exit()
v, out = ctypes.c_int(0), {"driver": None, "cards": []}
if lib.cuDriverGetVersion(ctypes.byref(v)) == 0:        # needs no cuInit: the newest CUDA this driver runs, 13050 for 13.5
    out["driver"] = v.value
if lib.cuInit(0) == 0:
    n = ctypes.c_int(0)
    lib.cuDeviceGetCount(ctypes.byref(n))
    for i in range(n.value):
        dev, major, minor = ctypes.c_int(0), ctypes.c_int(0), ctypes.c_int(0)
        ok = [lib.cuDeviceGet(ctypes.byref(dev), i), lib.cuDeviceGetAttribute(ctypes.byref(major), 75, dev),
              lib.cuDeviceGetAttribute(ctypes.byref(minor), 76, dev)]     # CU_DEVICE_ATTRIBUTE_COMPUTE_CAPABILITY_MAJOR, _MINOR
        if not any(ok):
            out["cards"].append([major.value, minor.value])
print(json.dumps(out))
"""


def cuda(ask=None):
    """{"driver": (13, 5), "cards": [(12, 0)]}: the newest CUDA that NVIDIA's driver here runs, and each card's compute
    capability (its generation as CUDA counts it: 6.1 a GTX 1080, 7.5 an RTX 2080, 12.0 an RTX 5070 Ti), read from the
    driver's own library with nothing installed for it; "driver" is None where it did not say. None where CUDA's
    library is not here or does not answer. It is what says which build of CuPy this computer takes (`addon.which`).
    Asked in a Python of its own, as `vulkan` is: a driver that hangs or crashes takes only that with it, and no card
    is opened in this process. `ask` stands in for the asking (a test's)."""
    if ask is not None:
        got = ask()
    else:
        names = ["nvcuda.dll"] if sys.platform == "win32" else ["libcuda.so.1", "libcuda.so"]
        try:
            r = subprocess.run([sys.executable, "-I", "-c", _CUDA, *names], capture_output=True, encoding="utf-8",
                               errors="replace", timeout=30, creationflags=NO_WINDOW)
            got = json.loads(r.stdout.strip().splitlines()[-1]) if r.returncode == 0 and r.stdout.strip() else None
        except (OSError, subprocess.SubprocessError, ValueError, IndexError):
            return None
    if not isinstance(got, dict):
        return None
    v = got.get("driver")
    try:
        return dict(driver=(int(v) // 1000, int(v) % 1000 // 10) if v else None,
                    cards=[(int(a), int(b)) for a, b in got.get("cards") or ()])
    except (TypeError, ValueError):
        return None


def pci_names(vendor, device, ids=PCI_IDS):
    """(the vendor's name, the device's) in the PCI ID list, or Nones where it is not there."""
    for path in ids:
        if not Path(path).exists():
            continue
        try:
            with (gzip.open(path, "rt", encoding="utf-8", errors="replace") if path.endswith(".gz")
                  else open(path, encoding="utf-8", errors="replace")) as f:
                who = None
                for line in f:
                    if who is None:
                        if line[:4].lower() == vendor and line[4:6] == "  ":
                            who = line[6:].strip()
                    elif line.startswith("\t") and not line.startswith("\t\t"):
                        if line[1:5].lower() == device:
                            return who, line[7:].strip()
                    elif line[:1] not in ("\t", "#", "\n"):
                        return who, None                      # the next vendor: no such device under this one
                if who is not None:
                    return who, None
        except OSError:
            continue
    return None, None


def named(vendor, device, vendor_name=None, device_name=None):
    """A card's name as it is sold: the maker, and the model in pci.ids' brackets -- "Cedar GL [FirePro 2270]" from AMD
    is "AMD FirePro 2270", "AD102 [GeForce RTX 4090]" "NVIDIA GeForce RTX 4090"; "graphics card 10de:2684" where the
    list does not have it."""
    maker = VENDORS.get(vendor) or (re.split(r",| \[", vendor_name)[0].strip() if vendor_name else "")
    if not device_name:
        return f"{maker} graphics card {vendor}:{device}".strip()
    models = re.findall(r"\[([^\]]+)\]", device_name)
    model = models[-1] if models else device_name
    return model if not maker or model.lower().startswith(maker.lower()) else f"{maker} {model}"


def _mac():
    r = subprocess.run(["system_profiler", "SPDisplaysDataType", "-json"], capture_output=True, encoding="utf-8",
                       errors="replace", timeout=30)
    return mac(json.loads(r.stdout or "{}"))


def mac(report):
    """The cards in system_profiler's report of SPDisplaysDataType, each computing where Metal runs on it."""
    cards = []
    for d in report.get("SPDisplaysDataType") or []:
        name = str(d.get("sppci_model") or d.get("_name") or "").strip()
        said = str(d.get("spdisplays_vendor") or d.get("spdisplays_vendor-id") or "")
        m = re.search(r"0x([0-9a-fA-F]{4})", said)
        vendor = m.group(1).lower() if m else "106b" if "apple" in (said + name).lower() else ""
        if name and "paravirtual" not in name.lower() and vendor not in NOT_GPUS:
            cards.append(dict(name=name, vendor=vendor, compute=metal(d), cuda=False))
    return cards


def metal(entry):
    """Whether Metal runs on a card, by its entry in system_profiler's report ("spdisplays_mtlgpufamilysupport":
    "spdisplays_metal3"). Every Mac that macOS 13 runs on has Metal, so only an entry that says it has not is a no."""
    said = [str(v).lower() for k, v in entry.items() if "metal" in k.lower() or "mtl" in k.lower()]
    return not any("not" in v or "unsupported" in v for v in said)


def _windows():
    r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                        "Get-CimInstance Win32_VideoController | Select-Object Name, PNPDeviceID | ConvertTo-Json -Compress"],
                       capture_output=True, encoding="utf-8", errors="replace", timeout=60, creationflags=NO_WINDOW)
    got = json.loads(r.stdout or "[]")
    return windows(got if isinstance(got, list) else [got])     # one card comes back as an object, not a list of one


def windows(controllers, ask=None, cuda=None):
    """The cards among Win32_VideoController's rows: real PCI devices with their own driver -- not a virtual machine's
    screen (VMBUS\\, ROOT\\), not a card Windows drives with its basic driver -- each computing where Vulkan (`ask`)
    lists it, or where it is NVIDIA's and CUDA's library is here (`cuda`). A GPU Vulkan lists that is no display
    adapter (a compute card in NVIDIA's TCC mode) is added by Vulkan's own name."""
    gpus = (ask or vulkan)()
    listed = {(g["vendor"], g["device"]) for g in gpus or ()}
    cards = []
    for d in controllers:
        name, pnp = str(d.get("Name") or "").strip(), str(d.get("PNPDeviceID") or "").upper()
        m = re.search(r"VEN_([0-9A-F]{4})(?:&DEV_([0-9A-F]{4}))?", pnp)
        vendor, device = (m.group(1).lower(), (m.group(2) or "").lower()) if m else ("", "")
        if name and pnp.startswith("PCI\\") and vendor not in NOT_GPUS and not name.lower().startswith("microsoft basic"):
            with_cuda = vendor == "10de" and bool((cuda or has_cuda)())
            cards.append(dict(name=name, vendor=vendor, device=device, compute=(vendor, device) in listed or with_cuda,
                              cuda=with_cuda))
    return cards + _beyond(cards, gpus, cuda or has_cuda)


# ---- computing on a card ------------------------------------------------------------------------------------------
GPU_VAR = "MCDONALD_GPU"
NONE = "none"                   # the choice that says the CPU only (Preferences' "None: the CPU only", `--gpu none`)
STAND_IN = "stand-in"           # the choice that puts NumPy in the card's place: the card's code, run on the CPU (tests)
_OFF = (NONE, "off", "no", "cpu")
_FIRST = ("", "auto", "first", "yes", "on")
SHARE = 0.5                     # of the card's free memory, the share one batch may take: the desktop draws on it too
PLANS = 8                       # FFT plans kept on the card (CuPy's cache): a stage uses two or three sizes


def choose(value):
    """Compute on this card from now on, in this process and every one it starts: a card's name or part of it, its
    number, "none" for the CPU only; None or "" leaves the choice to `card` (the first that computes). What `mcdonald
    --gpu X` and Preferences do. The card in use is let go, and asked for again at the next `card()`."""
    value = str(value or "").strip()
    if value:
        os.environ[GPU_VAR] = value
    else:
        os.environ.pop(GPU_VAR, None)
    forget()


def asked():
    """The choice as the environment has it, in lower case: "" for the first card, NONE, STAND_IN, or a card's name
    or number."""
    value = os.environ.get(GPU_VAR, "").strip().lower()
    return NONE if value in _OFF else "" if value in _FIRST else value


def given():
    """Whether this process may use a card where there is one: always, but inside a batch job only where the job was
    given one. Slurm sets CUDA_VISIBLE_DEVICES for a job that asked (`--gres=gpu:1`) and leaves it unset for one that
    did not, which on a machine that does not fence its cards off could compute on one anyway -- beside the job it
    was given to."""
    if not os.environ.get("SLURM_JOB_ID", "").strip():
        return True
    seen = os.environ.get("CUDA_VISIBLE_DEVICES", "").strip()
    return bool(seen) and seen.lower() != "nodevfiles"


class _OneThread:
    """The one thread that talks to a card (see the module's docstring: CuPy's FFT plans are each thread's own, and
    letting them go runs the cycle collector there). `run(fn, ...)` is fn's result, computed in that thread while the
    caller waits; what fn raises is raised in the caller. A daemon, never joined: it ends with the process."""

    def __init__(self):
        self.jobs = queue.SimpleQueue()
        self.thread = threading.Thread(target=self._loop, name="mcdonald-card", daemon=True)
        self.thread.start()

    def _loop(self):
        while True:
            fn, args, kw, done = self.jobs.get()
            try:
                done.append((True, fn(*args, **kw)))
            except BaseException as e:                # handed to the caller, whatever it is
                done.append((False, e))
            done.ready.set()

    def run(self, fn, *args, **kw):
        if threading.current_thread() is self.thread:
            return fn(*args, **kw)
        done = _Answer()
        self.jobs.put((fn, args, kw, done))
        done.ready.wait()
        ok, value = done[0]
        if ok:
            return value
        raise value


class _Answer(list):
    def __init__(self):
        super().__init__()
        self.ready = threading.Event()


_one_thread = None


def _the_thread():
    global _one_thread
    if _one_thread is None:
        _one_thread = _OneThread()
    return _one_thread


class Card:
    """A card to compute on: `xp` is its array module, `fft` and `ndimage` its transforms and filters -- CuPy's, which
    answer to NumPy's and SciPy's names, so that a routine written against these three runs on the card or, with the
    stand-in (`stand_in`), on the CPU. `run(fn, ...)` computes fn on the card: in the one thread that talks to it,
    with this card the current one. `up` puts an array on the card and `down` brings one back, inside such an fn."""

    def __init__(self, name, xp, fft, ndimage, index=None, library="", errors=()):
        self.name, self.xp, self.fft, self.ndimage, self.index, self.library = name, xp, fft, ndimage, index, library
        self.errors = errors              # what the card raises when it cannot go on: `gave_up` takes these
        self.real = index is not None
        self.less = 1.0                   # `fewer` halves it: the share of `room` a batch is planned on
        self.stopped = ""                 # what `gave_up` was told: from then on it is no card to compute on

    def __enter__(self):
        global _computed
        _computed = self                  # arithmetic on this card from here on: a case says so (`computed_on`)
        if self.real:
            self._local().append(self.xp.cuda.Device(self.index))
            self._local()[-1].__enter__()
        return self

    def __exit__(self, *exc):
        if self.real:
            self._local().pop().__exit__(*exc)
        return False

    def _local(self):
        if not hasattr(_THREAD, "devices"):
            _THREAD.devices = []
        return _THREAD.devices

    def run(self, fn, *args, **kw):
        """fn(*args, **kw), computed where this card's arithmetic is done: for a real card in the one thread that
        talks to it, this card the current one; for the stand-in, here. Every routine on a card goes through this."""
        if not self.real:
            with self:
                return fn(*args, **kw)
        return _the_thread().run(self._here, fn, args, kw)

    def _here(self, fn, args, kw):
        with self:
            return fn(*args, **kw)

    def up(self, a, dtype=None):
        return self.xp.asarray(a, dtype=dtype)

    def down(self, a):
        return self.xp.asnumpy(a) if self.real else np.asarray(a)

    def holds(self, a):
        """Whether an array is this card's already (a caller may hand over what an earlier step left there)."""
        return self.real and isinstance(a, self.xp.ndarray)

    def room(self):
        """Bytes a batch may take: SHARE of what is free on the card now, counting what this process holds ready to
        use again, and less after an out-of-memory (`fewer`). The stand-in has 1 GB, so that its batches are split
        as a card's are."""
        if not self.real:
            return int(self.less * 2 ** 30)
        return int(self.less * SHARE * self.run(self._free))

    def _free(self):
        return self.xp.cuda.Device(self.index).mem_info[0] + self.xp.get_default_memory_pool().free_bytes()

    def batch(self, each, most):
        """How many items of `each` bytes go to the card at once: as many as `room` has place for, at least one, at
        most `most`."""
        return int(max(1, min(int(most), self.room() // max(int(each), 1))))

    @staticmethod
    def full(error):
        """Whether what the card raised says it is out of memory: CuPy's own pool (a MemoryError), the driver, or the
        FFT library asking for its work area."""
        said = str(error).upper()
        return isinstance(error, MemoryError) or "OUT_OF_MEMORY" in said or "ALLOC_FAILED" in said

    def fewer(self):
        """After an out-of-memory: what the card holds ready is given back, and batches are planned on half the room
        from now on. False when halving has been tried four times: the card is too small for one item."""
        self.tidy()
        self.less /= 2
        return self.less >= 1 / 16

    def tidy(self):
        """Give back what this process holds on the card and does not use: its pool's free blocks and its FFT plans.
        A stage calls this when it is done, so that the memory is the desktop's again."""
        if not self.real:
            return
        try:
            self.run(self._tidy)
        except Exception:                             # a card that has stopped may refuse this too
            pass

    def _tidy(self):
        cache = self.xp.fft.config.get_plan_cache()
        cache.set_size(0)                             # each plan taken out in turn; `clear()` would run the cycle
        cache.set_size(PLANS)                         # collector, in this thread (the module's docstring)
        self.xp.get_default_memory_pool().free_all_blocks()

    def __repr__(self):
        return f"Card({self.name!r})"


_THREAD = threading.local()
_UNSET = object()
_computed = None                # the card that has done arithmetic since `begin`, for `computed_on`
_stopped = ""                   # what `gave_up` was told, since `begin`
_card = _UNSET
_why = ""                       # why no card is in use, in words, once `card()` has answered None
_lock = threading.Lock()


def stand_in():
    """NumPy and SciPy in the card's place: every routine written for a card runs, on the CPU. It is how the card's
    code is tested where there is no card (GitHub's runners), and it is asked for by name (MCDONALD_GPU=stand-in)."""
    from scipy import fft, ndimage
    return Card("stand-in (NumPy on the CPU)", np, fft, ndimage, library=f"NumPy {np.__version__}")


@contextlib.contextmanager
def on(c):
    """Inside the block, in this thread, the routines that have a card version compute on the card `c` (`active`); with
    None, on the CPU. A stage enters it for the whole of a pass, so that all of the pass is one arithmetic."""
    before = getattr(_THREAD, "active", None)
    _THREAD.active = c
    try:
        yield c
    finally:
        _THREAD.active = before


def active():
    """The card this thread's arithmetic is on now: the innermost `on`'s, unless it has stopped (`gave_up`); None for
    the CPU, which it is everywhere outside `on`."""
    c = getattr(_THREAD, "active", None)
    return c if c is not None and not c.stopped else None


def card():
    """The card this process may compute on, or None for the CPU: the choice (`asked`), where a card is allowed
    (`given`), never in a pool's worker, and only a card that answers. Asked once a process; `why()` says why not.
    Having one computes nothing by itself: a stage that has a card version of its pass enters `on(card())` for it."""
    global _card, _why
    if _card is not _UNSET:
        return _card
    with _lock:
        if _card is _UNSET:
            _card, _why = _open()
    return _card


def why():
    """Why `card()` is None, in a sentence's words; "" where a card is in use or has not been asked for."""
    return _why if _card is None else ""


def forget():
    """Ask again at the next `card()`: the choice changed, or a test wants another."""
    global _card, _why
    with _lock:
        if _card is not _UNSET and _card is not None:
            _card.tidy()
        _card, _why = _UNSET, ""


def use(c, why_not=""):
    """Compute on `c` from now on (a `Card`, or None for the CPU), whatever the environment says: for a test."""
    global _card, _why
    with _lock:
        _card, _why = c, why_not


def _open():
    """(the card, "") or (None, why not)."""
    choice = asked()
    if choice == NONE:
        return None, "the CPU only was chosen"
    if multiprocessing.parent_process() is not None:
        return None, "a pool's worker computes on the CPU"
    if choice == STAND_IN:
        return stand_in(), ""
    if not given():
        return None, "this batch job was not given a graphics card (for Slurm: --gres=gpu:1)"
    if not installed():
        return None, "CuPy is not installed (`mcdonald setup --install-gpu` installs it)"
    return _the_thread().run(_open_cupy, choice)          # CuPy is loaded and asked in the thread that will use it


def _open_cupy(choice):
    """`_open` for a real card, in the one thread that talks to it: (the card, "") or (None, why not)."""
    try:
        import cupy
        import cupyx.scipy.fft as cfft
        import cupyx.scipy.ndimage as cndimage
        from cupy.cuda.compiler import CompileException
        errors = (MemoryError, RuntimeError, CompileException)
    except Exception as e:                            # a CuPy built for another CUDA, a library it cannot load
        return None, f"CuPy could not be loaded ({type(e).__name__}: {str(e)[:200]})"
    try:
        names = [_text(cupy.cuda.runtime.getDeviceProperties(i).get("name")) or f"card {i}"
                 for i in range(cupy.cuda.runtime.getDeviceCount())]
    except Exception as e:                            # no driver, or one too old for this CuPy
        return None, f"CUDA found no card ({type(e).__name__}: {str(e)[:200]})"
    i = pick(choice, names)
    if i is None and names:                           # the name as `found` gives it, where CUDA spells it otherwise:
        slots = [str(c.get("slot") or "").lower() for c in found() if c["name"].lower() == choice]     # by its PCI slot
        try:
            at = [str(cupy.cuda.Device(j).pci_bus_id).lower() for j in range(len(names))]
            i = next((at.index(s) for s in slots if s in at), None)
        except Exception:
            i = None
    if i is None:
        return None, (f"no card here is called {choice!r} (there {'is' if len(names) == 1 else 'are'}: {', '.join(names)})"
                      if names else "CUDA found no card")
    c = Card(names[i], cupy, cfft, cndimage, index=i, errors=errors,
             library=f"CuPy {cupy.__version__}, CUDA {_cuda_version(cupy)}")
    try:
        cupy.cuda.Device(i).use()                     # this thread's card from now on
        cupy.fft.config.get_plan_cache().set_size(PLANS)
        if float(cupy.arange(4, dtype=cupy.float32).sum()) != 6.0:      # it answers: one sum, brought back
            return None, f"{names[i]} gave a wrong sum"
    except Exception as e:
        return None, f"{names[i]} did not answer ({type(e).__name__}: {str(e)[:200]})"
    return c, ""


def _text(b):
    return b.decode("utf-8", "replace").strip() if isinstance(b, bytes) else str(b or "").strip()


def _cuda_version(cupy):
    try:
        v = cupy.cuda.runtime.runtimeGetVersion()
        return f"{v // 1000}.{v % 1000 // 10}"
    except Exception:
        return "?"


def pick(choice, names):
    """Which of the cards CUDA lists (`names`, in its order) a choice means: "" the first; a number that one (from
    0, as CUDA counts; one or two digits are always a number); a name that card, "name (2)" the second so named, as
    `found` names them; part of a name the first card it is part of. None where it means none of them."""
    choice = choice.strip().lower()
    if not names:
        return None
    if choice == "":
        return 0
    if choice.isdigit() and (int(choice) < len(names) or len(choice) < 3):
        return int(choice) if int(choice) < len(names) else None    # a number; "5070" is part of a name, not the 5,071st card
    low = [n.lower() for n in names]
    m = re.fullmatch(r"(.*\S)\s*\((\d+)\)", choice)
    want, nth = (m.group(1), int(m.group(2))) if m else (choice, 1)
    same = [i for i, n in enumerate(low) if n == want]
    if len(same) >= nth:
        return same[nth - 1]
    part = [i for i, n in enumerate(low) if choice in n or n in choice]
    return part[0] if part else None


_told = False


def gave_up(error, what=""):
    """The card this thread was computing on (`active`) refused (`error`) while computing `what`: said once on stderr,
    and from now on it is no card to compute on -- here, and for the rest of the process if it is the process's own.
    Every caller computes on the CPU next. The numbers are the CPU's, which are the reference."""
    global _card, _why, _told, _stopped
    reason = f"{type(error).__name__}: {str(error).strip()[:300]}"
    c = getattr(_THREAD, "active", None)
    with _lock:
        _stopped = reason
        if c is not None:
            c.stopped = reason
        if c is None or c is _card:
            c, _card, _why = (c if c is not None else _card), None, f"the card stopped ({reason})"
    if c is not None and c is not _UNSET:
        c.tidy()
    if not _told:
        _told = True
        print(f"mcdonald: the graphics card stopped{' while ' + what if what else ''} ({reason}). "
              "The CPU does the rest: the same measurement, more slowly.", file=sys.stderr, flush=True)


def begin():
    """A measurement starts here: `computed_on` says from now on whether a card took part in it."""
    global _computed, _stopped
    _computed, _stopped = None, ""


def took_part(c):
    """The card `c` took part in what is being measured, though it does no arithmetic now: its numbers were read
    back from where an earlier run on it kept them (`layers`' templates beside the frames)."""
    global _computed
    if c is not None:
        _computed = c


def computed_on():
    """The card that did arithmetic since `begin`, named with its library ("NVIDIA GeForce RTX 5070 Ti (CuPy 14.2.0,
    CUDA 13.2)"), with a word more if it stopped part-way and the CPU did the rest; None where the CPU did it all.
    A case keeps this (`report.Case.computed_on`): a card's numbers agree with the CPU's to about a part in a million
    and not to the last digit, so whoever measures the case again has to know which it was (`rerun`)."""
    if _computed is None:
        return None
    return f"{_computed.name} ({_computed.library})" + ("; it stopped part-way, and the CPU did the rest" if _stopped else "")


def said():
    """One line for a log or `mcdonald setup`: what computes, and if it is not a card, why."""
    c = card()
    if c is not None:
        return f"graphics card: {c.name} ({c.library})"
    return f"graphics card: none in use ({why()})"
