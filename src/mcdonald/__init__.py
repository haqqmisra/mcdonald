"""McDonald UAP Toolkit — measurement tools for single-sensor video of
unidentified objects.

What the package is for: taking a clip of something unidentified and
establishing, frame by frame, what its motion in the image actually permits —
and, just as often, what it does not. Most of the discipline in here is about
the second part.

Three rules the tools are built to keep, because each one was broken once and
produced a wrong number:

1. A rate is meaningless without naming what it is a rate *against*. Layers at
   different ranges do not move together when the platform moves.
2. Pixels per second become metres per second only through an angular scale k
   and a range R. Neither is usually recoverable from a clip, and a speed
   quoted without both sourced is not a measurement.
3. A test that cannot decide has not passed. NO POWER is a verdict and is
   reported, never dropped.

Named for James E. McDonald, who argued that the subject deserved ordinary
scientific instruments rather than either credulity or dismissal.
"""
# The one place the version is written (pyproject reads it). It goes up every time changes go to
# main for others to install: pip --upgrade from GitHub does nothing while it stays the same.
__version__ = "0.2.1"

from . import catalog  # noqa: F401
from .clip import Clip, case_dir, out_prefix, probe, require_ffmpeg, resolve  # noqa: F401

__all__ = ["catalog", "Clip", "case_dir", "out_prefix", "probe", "require_ffmpeg", "resolve",
           "__version__"]
