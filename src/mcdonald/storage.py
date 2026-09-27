"""Where mcdonald keeps what is large: the videos it downloads, and their frames as pictures.

One folder, the storage folder, holds both:

    <storage>/videos/   videos fetched from a catalog (PR113 is 67 MB, the largest PURSUE one 3.2 GB)
    <storage>/frames/   each video's frames, saved losslessly to be measured (PR113 whole: 2.1 GB)

It is $MCDONALD_HOME if that is set, else Documents/mcdonald. The window lets someone with
no terminal choose it, remembers the choice, and puts it in $MCDONALD_HOME for the process
(`mark_qt.use_remembered_storage`), so that everything it starts sees the same folder; it
also makes a video's results there, in <storage>/<tag>, when nobody said where. From a
command line, results go in the working directory as they always have (`clip.case_dir`).

Frames were in the temporary directory until 2026-09-24. On Fedora that is memory, and a
whole clip is gigabytes of it; a person at a window could not move them anywhere else.
"""
import http.client
import os
import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path


def home():
    env = os.environ.get("MCDONALD_HOME", "").strip()
    if env:
        return Path(env).expanduser()
    docs = Path.home() / "Documents"
    return (docs if docs.is_dir() else Path.home()) / "mcdonald"


def videos():
    return home() / "videos"


def frames():
    return home() / "frames"


class Incomplete(OSError):
    """A download that stopped short, or was stopped: nothing is left of it."""


class Unreachable(OSError):
    """A download that could not start: no network, an address that does not answer, or a
    certificate Python cannot check. Its message says which, and what to do."""


def certificate_fix():
    """What to do when Python cannot check a website's certificate. Python from python.org on a
    Mac has no certificates until its own "Install Certificates.command" has been run once, and
    every download then fails with CERTIFICATE_VERIFY_FAILED; `mcdonald setup` says the same."""
    if sys.platform == "darwin":
        return ("Python cannot check the website's certificate. With Python from python.org on a Mac, run "
                "\"Install Certificates.command\" once (in Applications → Python 3.x), then try again")
    return "Python cannot check the website's certificate: run `pip install --upgrade certifi`, then try again"


def is_certificate_error(err):
    why = getattr(err, "reason", err)
    return isinstance(why, ssl.SSLCertVerificationError) or "CERTIFICATE_VERIFY_FAILED" in str(why)


def why_unreachable(err, where="DVIDS"):
    """One sentence for a download that could not start, from what urlopen raised."""
    if is_certificate_error(err):
        return certificate_fix()
    if isinstance(err, urllib.error.HTTPError):
        return f"{where} answered {err.code} ({err.reason}) for that address"
    why = getattr(err, "reason", err)
    return f"could not reach {where} ({why}): check the internet connection"


def download(url, dest, size=None, progress=None, stop=None, chunk=1 << 20):
    """Fetch `url` to `dest`, by way of `dest.part`, so that a file under the real name is
    always whole. `size` is what the catalog says it is, and the file must come to that;
    `progress(done, total)` is called as it comes, and `stop()` returning true ends it.
    Returns dest; raises Unreachable if it could not start (the message says why, and what to
    do about a certificate), Incomplete (and removes the part) if it did not all arrive."""
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    done = 0
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "mcdonald"}), timeout=60)
    except OSError as e:                          # URLError, an SSL error and a timeout are all OSErrors
        raise Unreachable(why_unreachable(e)) from e
    try:
        with r, open(part, "wb") as f:
            total = size or int(r.headers.get("Content-Length") or 0) or None
            while True:
                if stop and stop():
                    raise Incomplete(f"the download of {dest.name} was stopped")
                try:
                    block = r.read(chunk)
                except (OSError, http.client.HTTPException) as e:           # the connection lost part way (IncompleteRead is no OSError)
                    raise Incomplete(f"{dest.name}: the connection was lost after {done} of {total or '?'} bytes ({e})") from e
                if not block:
                    break
                f.write(block)
                done += len(block)
                if progress:
                    progress(done, total)
        if total and done != total:
            raise Incomplete(f"{dest.name}: {done} of {total} bytes arrived")
        part.replace(dest)
        return dest
    finally:
        part.unlink(missing_ok=True)


def download_on_terminal(rec, dest):
    """For the command line: say what is being fetched and how far along it is, on stderr,
    so that stdout stays what the command prints."""
    import sys
    size = int(rec.get("bytes") or 0) or None
    print(f"{rec.get('id') or dest.stem} is not on this computer: downloading it"
          + (f" ({size / 1e6:.0f} MB)" if size else "") + f" from {rec['url']}\n  to {dest}", file=sys.stderr)
    step = [0]

    def progress(done, total):
        if total and done * 10 // total > step[0]:
            step[0] = done * 10 // total
            print(f"  {step[0] * 10}%", file=sys.stderr)
    return download(rec["url"], dest, size, progress)
