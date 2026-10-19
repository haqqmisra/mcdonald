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
Apple's paravirtual one), and a card Windows drives with its basic driver only. No toolkit is imported here.
"""
import gzip
import json
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
NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0


def found():
    """[{"name", "vendor"}]: the graphics cards here, dedicated ones first, named as the person would know them (the
    second of two the same is "name (2)"); [] where there are none, or they cannot be asked about."""
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


def linux(root="/sys/bus/pci/devices", ids=PCI_IDS):
    cards = []
    for dev in sorted(Path(root).glob("*")):
        try:
            if not (dev / "class").read_text().strip().startswith("0x03"):
                continue
            vendor, device = ((dev / f).read_text().strip().lower().removeprefix("0x") for f in ("vendor", "device"))
        except OSError:
            continue
        if vendor not in NOT_GPUS:
            cards.append(dict(name=named(vendor, device, *pci_names(vendor, device, ids)), vendor=vendor))
    return cards


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
    """The cards in system_profiler's report of SPDisplaysDataType."""
    cards = []
    for d in report.get("SPDisplaysDataType") or []:
        name = str(d.get("sppci_model") or d.get("_name") or "").strip()
        said = str(d.get("spdisplays_vendor") or d.get("spdisplays_vendor-id") or "")
        m = re.search(r"0x([0-9a-fA-F]{4})", said)
        vendor = m.group(1).lower() if m else "106b" if "apple" in (said + name).lower() else ""
        if name and "paravirtual" not in name.lower() and vendor not in NOT_GPUS:
            cards.append(dict(name=name, vendor=vendor))
    return cards


def _windows():
    r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                        "Get-CimInstance Win32_VideoController | Select-Object Name, PNPDeviceID | ConvertTo-Json -Compress"],
                       capture_output=True, encoding="utf-8", errors="replace", timeout=60, creationflags=NO_WINDOW)
    got = json.loads(r.stdout or "[]")
    return windows(got if isinstance(got, list) else [got])     # one card comes back as an object, not a list of one


def windows(controllers):
    """The cards among Win32_VideoController's rows: real PCI devices with their own driver -- not a virtual machine's
    screen (VMBUS\\, ROOT\\), not a card Windows drives with its basic driver, which nothing could compute on."""
    cards = []
    for d in controllers:
        name, pnp = str(d.get("Name") or "").strip(), str(d.get("PNPDeviceID") or "").upper()
        m = re.search(r"VEN_([0-9A-F]{4})", pnp)
        vendor = m.group(1).lower() if m else ""
        if name and pnp.startswith("PCI\\") and vendor not in NOT_GPUS and not name.lower().startswith("microsoft basic"):
            cards.append(dict(name=name, vendor=vendor))
    return cards
