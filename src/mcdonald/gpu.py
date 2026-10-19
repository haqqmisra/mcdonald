"""The graphics cards (GPUs) this computer has, for Preferences' choice of one (Jacob, 2026-10-19: "add a GPU selection
option; this should be greyed out if no GPU is available; we will add actual GPU features later").

Nothing in mcdonald computes on a graphics card yet: the window remembers the choice for when something does, and
Preferences says so. The cards are found with nothing installed for it:
- Linux: the PCI display controllers (class 03) in /sys/bus/pci/devices, named from the PCI ID list the system keeps
  (pci.ids, the one lspci reads): 1002:68f2 there is "Cedar GL [FirePro 2270]", said here as "AMD FirePro 2270";
- macOS: system_profiler SPDisplaysDataType ("Apple M2", "AMD Radeon Pro 5500M");
- Windows: Win32_VideoController, through PowerShell.
A display controller that is not a graphics processor is left out: a server's management chip (ASPEED, Matrox: merlin
has a Matrox G200 beside its FirePro), a virtual machine's screen (VMware, VirtualBox, QEMU, Hyper-V, Parallels,
Apple's paravirtual one), and a card Windows drives with its basic driver only.

Only a card that can compute is offered (Jacob, later that day: "the GPU drop-down should only show devices with real
GPU features"). `compute` says whether it can:
- Linux and Windows: Vulkan lists it as a GPU (`vulkan`: the loader comes with every current graphics driver, and
  asking it is how any compute on the card would start), or it is an NVIDIA card with CUDA's library. Where there is
  no Vulkan to ask at all, a Linux card on a driver that computes (amdgpu, i915, xe) is taken at its word.
- macOS: Metal runs on it, which since macOS 13 is every Mac's.
merlin's FirePro 2270 (TeraScale 2, on the old radeon driver) is found and not offered: the only Vulkan device there
is llvmpipe, which is the CPU. No toolkit is imported here.
"""
import ctypes.util
import gzip
import json
import os
import re
import subprocess
import sys
from pathlib import Path

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
    """[{"name", "vendor", "compute"}]: the graphics cards here, dedicated ones first, named as the person would know
    them (the second of two the same is "name (2)"), each saying whether it can compute; [] where there are none, or
    they cannot be asked about. Preferences offers those that can (`usable`)."""
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
    """The cards that can compute: what Preferences offers."""
    return [c for c in cards if c.get("compute")]


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
        compute = ((vendor, device) in listed if gpus is not None else driver in COMPUTING_DRIVERS) or (
            driver == "nvidia" and (cuda or has_cuda)())
        cards.append(dict(name=named(vendor, device, *pci_names(vendor, device, ids)), vendor=vendor, device=device,
                          compute=compute))
    return cards + _beyond(cards, gpus)


def kernel_driver(dev):
    """The Linux driver a PCI device is bound to, from its uevent ("DRIVER=amdgpu"); "" for none."""
    try:
        for line in (Path(dev) / "uevent").read_text().splitlines():
            if line.startswith("DRIVER="):
                return line[7:].strip()
    except OSError:
        pass
    return ""


def _beyond(cards, gpus):
    """The GPUs Vulkan lists that no display controller is: by Vulkan's own name, and able to compute."""
    have = {(c["vendor"], c.get("device")) for c in cards}
    return [dict(name=g["name"], vendor=g["vendor"], device=g["device"], compute=True)
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
            cards.append(dict(name=name, vendor=vendor, compute=metal(d)))
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
            compute = (vendor, device) in listed or (vendor == "10de" and (cuda or has_cuda)())
            cards.append(dict(name=name, vendor=vendor, device=device, compute=compute))
    return cards + _beyond(cards, gpus)
