"""Does the object's brightness beat -- and is the beat the object's, or the video's?

"Is it birds?" is asked of most clips of several points, and a bird's wings beat: seen
from afar a flapping bird flickers a few to ten or so times a second. The PR135 agent
(2026-09-22, its items 21, 23 and 24) measured it by hand, and found the two traps that
each fake a result -- both built in here, with a third it asked for:

1. **Pixel phase.** A small aperture re-centred on the rounded position of a point that
   moves a fraction of a pixel a frame takes in more or less of it as the fraction turns:
   planted dots of constant brightness "flickered" 3-6 Hz before any encoding. So the
   aperture is a disc APERTURE px across in radius, its weights the share of each pixel
   inside it (supersampled SUPER times each way), centred on the track smoothed over
   SMOOTH frames, less the median of a ring RING about it (`brightness`).
2. **The codec's rhythm.** A clip's anchor frames (I and P) are coded afresh and the B
   frames between them from them; a point's brightness can follow that. PR135 has a P
   every 4th frame: 30/4 = 7.49 Hz, which is where its points flicker. The rhythm is
   read from the clip itself (`clip.gop`), marked, and a peak within Z_LINE of its own
   frequency error of it is said to be there (item 10).
3. **The same frames, several members.** A rhythm of the video beats every member at
   the same frequency and in step. Members over one common window at frequencies
   further apart than Z_APART of their combined errors (item 10), or at one frequency
   out of step, are not a rhythm of the video (PR135: 7.00 Hz against 7.74-7.82, phases
   84-175 deg apart).
   That is the pass condition where there are members (`common`).

And a control that rides along, which is also the test of whether there is a beat at all:
the same photometry on BACKGROUND apertures about the object, which share the frames, the
codec, the grain and the camera but not the object, measured in the object's brightness.
The object beats only if its strongest beat is ABOVE times theirs (the median of their
strongest): a peak standing over its own band is not enough, because the grain makes
those everywhere. And a beat they share at the object's frequency is not the object's.

Two more, from PR23 (2026-10-09: a look-down clip over a town, called "a bird" at 2.1 Hz),
neither of which the apertures beside the object can catch:

4. **The object lost against what is behind it.** It crossed a hot roof: for seven frames its
   brightness over the ring fell from about 4,800 to nothing and below, and that one dip was
   the whole beat. Where the object's brightness falls under DROP of its own level
   it is lost (`lost`): those frames are filled across before any spectrum (trimmed, at the
   ends), no window that holds one is used, and past LOST_MAX of them no beat is looked for --
   unless they are the troughs of the object's own beat (PR097's dark dots, 2026-10-15: a point
   beating at 25-60 % goes under its ring at every trough), which come in many short runs, one per
   cycle, in the lower half of the cycle (`lost_at_beat`, LOST_RUNS and LOST_TROUGH), and whose beat
   the stage then finds at the troughs' own frequency (`at_the_troughs`, 2026-10-16): those are kept
   and measured as they are, and the finding says so.
5. **Its own slow change.** Taking a curve against its running mean is a filter that passes
   little under 1/DETREND_S, so a brightness that only wanders slowly comes out peaked just
   above that (2 Hz: 64% of random walks through these steps peak at 1.5-2.5 Hz). So the
   strongest beat is held against the slow wander and frame-to-frame jitter that best account
   for the curve's own spectrum (`drift`): it is a beat only where it stands further over
   them than 99 in 100 curves made of that wander and jitter, read the same way, do at their
   strongest. And a strongest that is only the band's edge, the spectrum still rising below
   LOW, is the flank of something slower and no beat (`peak`: WA9ONY-5's balloon, at 1.53 Hz).

Each curve is taken relative to its own running mean over DETREND_S (so a slow change is
not a beat: the paper's 0.5 s, 15 frames at 30 fps and 30 at 60 -- until 2026-10-09 it was 15
frames at any rate, which at 60 fps put the drift's peak at 4 Hz, on Galileo's birds),
windowed (Hann), and zero-padded 16 times; what is reported is
the strongest peak between LOW Hz and just under Nyquist, its amplitude as a share of the
brightness, how far it stands over the median of the band, and the resolution, 1/T.

The beat is looked for in windows of WINDOW_S seconds along the track as well as over
the whole of it (Jacob, 2026-09-29, a Galileo Project bird, "flyer 5": one spectrum over its
5.9 s -- a faint approach and then two seconds of bright flapping at a rate that changes --
peaked at 5.11 Hz, between the paper's 3.90 and 7.80; over the flapping alone the same
curve gives 7.88 and 3.94). Each window is held to the same tests; the clearest that passes
(the highest peak over its band) gives the frequency where it is clearer than the whole
track's. And a peak with another at half its frequency at least HALF as strong is the
double of a beat: a wingbeat's brightness changes twice a stroke, so its second harmonic
is often the stronger. The fundamental is what is reported, with its double named. The
other peak must be one of its own -- clear of the strongest's lobe, in the band, and over
the curve's drift there -- or every 2-s window with a beat under 2.5 Hz finds its "half" on
the flank of the beat itself (PR23's windows all did, and named fundamentals under 1.5 Hz).

And one from the bird sweep (2026-10-10):

6. **An aperture smaller than the thing.** A fixed 4-px aperture with its ring at 7-10 px put the ring on objects
   15-100 px across, their brightness over it came out near nothing, and trap 4 called them lost (PR056, PR086,
   PR116, PR052, PR47). The object's extent is read off its own frames (`extent`, `sizes`): a point no wider than
   APERTURE keeps APERTURE, RING and BACKGROUND exactly; a wider thing gets an aperture APERTURE_OVER times its
   extent, a ring and background apertures beyond it, and the aperture re-centred each frame on its own centroid
   (`sized`, `centred`). Where the frames do not agree on the size -- most give none, or those that do are scattered
   (PR089's bird C after a sensor blank, 2026-10-23: a faint dot 5-9 px across over a sea in column bands, read at 43-66
   px on a few frames and so given a 58-px aperture) -- it is read once off the median of the object's stamps along the
   track, turned to its travel so a trailing smear does not count, against the level just outside it (`stacked_extent`).

And the astronomer's tests (2026-10-15, from `analysis/astronomy_methods_survey.md`, its items 1-4), each
reported beside the stage's own in `fields["astro"]`, `controls`, `false_alarm`, `injection` and `fold`:

7. **Named statistics with known nulls.** The strongest beat again by the Lomb-Scargle periodogram
   (VanderPlas 2018) over the frames that are samples -- a held picture or a frame the object was lost on is
   a missing sample, not a sample -- with Baluev's (2008) false-alarm probability and the sampling's own
   rhythms read off its spectral window (`ls_peak`); the curve's strongest held against copies of itself
   scrambled in chunks, which keep the grain and destroy every rhythm (`scrambled`; Thompson et al. 2018's
   scrambled runs); the background apertures' common mode regressed out of the object's curve (`common_mode`;
   SysRem, Tamuz et al. 2005) and the pixel phase likewise (`pixel_phase`); every background aperture put
   through the object's own tests, so that what passes is a false alarm by construction (`controls_judged`);
   beats planted in them and recovered, for completeness (`injected`; Christiansen et al. 2013); and the frames
   folded on the beat into a bright half and a dim half whose difference shows where the brightness that beats
   is (`fold`; epoch folding, and Kepler's difference image, Bryson et al. 2013). They report; GATE_ASTRO, which
   would make the first two decide, stays off by decision (2026-10-17: the gate study found it cost known birds and
   no false alarm).

And the seismologist's tests (2026-10-15, from `analysis/seismology_methods_survey.md`, its ranked ports 1, 3, 4, 6,
8 and 11), each reported beside the stage's own in `fields["seis"]`, `in_step` and `short_record`:

8. **One sensor's continuous record.** The multitaper spectrum with Thomson's (1982) harmonic F-test -- the chance
   of a line at the beat against a continuum smooth over the tapers' bandwidth, grain and drift alike, in closed
   form (`line_test`) -- and the coherence of the object's curve with each background aperture's at the beat, with
   the level chance clears and the phase's jackknife error (`coherence_at`; Thomson & Chave 1991); the lines read
   as a comb, a fundamental whose multiples hold them (`comb`; harmonic tremor, Hotovec et al. 2013), and the
   fundamental followed along the stretch with its double (`glide`); the noise as a distribution -- every
   background window's spectrum, and the centile the object's windows sit at (`noise_pdf`; McNamara & Buland
   2004); the record as a linear system's output, whose roots that hold still across model orders are its lines,
   a frequency and a decay from a few cycles (`sompi`; Hori et al. 1989), which also reads a track too short for
   the stage (`short_reading`, SHORT_MIN frames and up); members' phases held together, the mean unit phasor's
   modulus against time-slid copies and the array F-statistic (`in_step`; Schimmel & Paulssen 1997; Blandford
   1974), and the same phase coherence pixel by pixel beside the fold (`phase_map`); and the curve's strongest with
   every sample its sign alone (`onebit`; Bensen et al. 2007). They report; GATE_SEIS, which would make the line
   test decide, stays off by decision (2026-10-17: the gate study found it cost known birds for no measurable gain).

And the look-alikes (2026-10-16, from the SETI methods survey, its first port, for ROADMAP.md 0.3):

9. **Where a supply's line would sit.** A lamp on 50-Hz mains flickers at 100 Hz, an aircraft's lights on
   its 400-Hz power at 400 or 800 Hz, and a video at 30 frames a second folds every one of them to 10 Hz
   (`alias`): at 29.97 to 9.19-10.39 Hz, in the band where small birds beat. The table of them for the
   clip's own frame rate, with the rhythms locked to every third, fourth, fifth or sixth frame and the held
   pictures' cadence (`lookalikes`), is in `fields["lookalikes"]`; a beat within its own resolution of one is
   marked with it (`beat[..]["lookalike"]`) -- of a rhythm locked to the frames, which has no width, within its
   frequency error (item 10), as a beat at the codec's line is -- and the finding and the notes say so. It flags,
   it does not reject: a bird can beat at 10 Hz. What tells the two apart is said beside it -- a supply's line
   holds its frequency, a wingbeat's wanders across the windows (`hz_range`) and the seismologist's line test
   finds no stationary line over a whole track of it (item 8).

And the frequencies with their errors (2026-10-17, from the information-theory survey's D1 and D6, for ROADMAP.md 0.3's
objective 2):

10. **How well a frequency is known.** Every peak's frequency has its error -- a block bootstrap in the curve's own
    residual, never under the Cramer-Rao bound (`hz_error`) -- and the codec's mark and the members' independence are
    tests against it (`at_line`, Z_LINE; `common`, Z_APART), not against the resolution 1/T. The resolution says when
    two sinusoids in one curve can be told apart; the error, how well one is known; and on 2-s windows the resolution
    blinded 7.0-8.0 Hz, the middle of the bird band, on the 93 of 112 sensor videos whose codec puts its line at 7.5 Hz.
    Beats are planted beside the line in windows of the background apertures, to measure what the slice now recovers
    and what the old mark did (`sliced`), and every planting has its completeness in closed form beside it, from the
    error exponent of the test (`analytic`).

And two readings for the look-alikes (2026-10-20, from the bird paper's chain-rate table and the Svanström labelled
infrared run, for ROADMAP.md 0.3's objective 4):

11. **Look-alikes that are bands, not lines** (`LOOKALIKE_BANDS`). The 400-Hz power an aircraft's sound actually
    records sits at 398.4-401.3 Hz, not 400.000 (folded at 30 frames a second, 8.4-11.3 Hz), and a lamp on it twice
    that; a bundle of candles flickers near 10 Hz and a sky lantern's flame puffs at 4.7-8.7 Hz, each with its own
    phase; a rotor's, a propeller's and a multirotor's blade-pass and a cryocooler's drive are bands that fold over
    the whole band at video rates. Each is in the table with where it lands (`fold_band`); a beat inside one is
    marked with it, as with a line, except that a band covering WHOLE_BAND of the band or more marks nothing -- the
    notes say once that frequency cannot exclude it.
12. **Steady as a clock, or not** (`steadiness`; the information-theory survey's D2). The whole stretch the object was
    followed over is cut in halves (pieces of STEADY_SEG_S where it is longer than STEADY_PLAIN_S), each fitted by least
    squares, and the pieces' frequencies compared in units of their Cramer-Rao bounds. The same is done to
    STEADY_RUNS steady beats planted at the beat's frequency, with each piece's own amplitude, in the pieces' own
    residuals: the share that wander as much is p. A rhythm locked to the frames, a supply's line and a cooler's drive
    do not wander; a wingbeat does. A reading beside the look-alike marks, not a gate; where the pieces would be
    shorter than MIN_FRAMES it is not read (NO POWER), and it cannot tell a governed rotor from a bird.

And the lights (2026-10-20, a UAPSAC council member's question, from the uap repository's analysis/methods/helicopter_lights.md
and the SETI methods survey's port 14):

13. **A light that flashes in a train** (`lights`, `flashes`, `blinks`, `blink_reading`). An aircraft's anti-collision
    light flashes 40-100 times a minute (14 CFR 25.1401(c), 27.1401(c), 29.1401(c); to 180 where two lights' beams
    overlap). A train of short flashes is a comb in the spectrum, at its rate and every multiple of it, so its fundamental
    sits under the band a beat is looked for in and its harmonics fill it. On every frame each aperture's brightest and
    reddest pixels are read beside its sum (`lights`: on a thing wider than a light, the sum is the thing's and the light
    is only in its brightest pixels -- Svanstrom V_HELICOPTER_054's white light, which its dark body hides from the sum); in
    each of the three curves the flashes are found (`flashes`), their times folded at every rate in BLINK_BAND by Z^2 and
    held against as many times at random (`blinks`); the background apertures, read the same way, are the control. A beat
    that keeps under BLINK_KEEP of its amplitude with the flashes taken out (`deflash`) is the flashes' and is marked
    with them as a look-alike. The disc a light is looked for in reaches the thing's whole silhouette (`reach`, not
    `extent`: a tail light is far outside a helicopter's core), and the controls beside it are twice that far out.
    Known answers (2026-10-20, every labelled track of Svanstrom et al. 2021, 837 of them, visible and infrared, birds,
    drones, airplanes and helicopters): two flash in trains, both helicopters in daylight colour video -- V_HELICOPTER_054's
    white light, 1.00 Hz, p 0.003, which its dark body hides from the sum, and V_HELICOPTER_030's red light, 0.75 Hz,
    p 0.0005 -- and none of the other 835, none of 251 birds among them. No thermal track flashes: an LED gives off
    almost no heat, and a lamp's light leaves through a cover opaque to thermal infrared. It reports; it changes no call.
    A light is hot, and a hot thing is bright on a white-hot display and on a visible picture, but dark on a black-hot
    one, as many pods show it (AARO's Atmospheric Wakes airliner, 2026-10-21): `black_hot` (--black-hot) reads a light
    there as the darkest pixels, the hottest, and turns the sum's sign to match.
    A glint off something that turns flashes too, at its turning rate.

And a rotor's look (2026-10-25, from the uap repository's analysis/sweeps/svanstrom/README.md):

14. **A beat that reaches past the body** (`rotor_said`, `beat[..]["rotor"]`). Of the Svanstrom set's tracks that would be
    named birds, the helicopters' beats reached a background aperture beside them in step (the multitaper coherence at the
    beat, item 8, ROTOR_COHERENCE or more) or sat off the object's middle (the fold's offset, item 7, ROTOR_OFFSET_PX or
    more) on 6 of 8 calls; 0 of 7 airplanes, 0 of 30 of its birds and 1 of 20 known-beat birds (Galileo flyer 2, coherence
    0.77) did. A rotor disc, or the air it drives, reaches past the body; a bird's wings do not. It is said beside the
    headline, as the flame's look-alike is, and changes no call: the thresholds were chosen on those calls.

What it cannot do: say that a beat is a wingbeat. A tumbling or rotating body beats too,
and so does a light that blinks. A beat that survives the controls is the object's own;
what makes it is the rest of the case.
"""
import contextvars
import csv
from functools import lru_cache

import numpy as np
from scipy import ndimage

from . import forensics as vf
from .clip import gop as read_gop
from .progress import PROCS_HELP, pooled, to_stderr
from .report import Found, emit, inputs_of, said_to_stderr

APERTURE = 4.0       # px, radius
SUPER = 8            # each pixel's share of the aperture, from SUPER x SUPER points in it
RING = (7.0, 10.0)   # px, the background ring
SMOOTH = 5           # frames the track is smoothed over, so the aperture does not chase centroid noise
DETREND_S = 0.5      # s of running mean each curve is taken against (`trend_frames`)
LOW = 1.5            # Hz: slower than this is a trend, not a beat
PAD = 16
ABOVE = 3.0          # a beat is the object's only at this many times the background apertures' own (their median
                     # strongest, in the object's brightness): planted dots of constant brightness, encoded as
                     # PR135 is, beat 5-7 % at 2-4 Hz and stand 46-123 times their band -- the grain does that
MIN_FRAMES = 60      # two seconds at 30 fps: fewer, and no frequency is worth quoting
BACKGROUND = [(0, 25), (25, 0), (0, -25), (-25, 0)]     # px, the background apertures about the object
AVOID_MARGIN = 6.0   # px: another tracked thing keeps this far beyond a background aperture's ring and its own (`clear_offsets`)
APART_DEG = 45.0     # members at one frequency but this far out of step are not in step
# Frequencies with their errors (2026-10-17; the information-theory survey's D1 and D6, ROADMAP.md 0.3 objective 2; item 10
# below). Until then a peak was at the codec's line within the resolution 1/T of it, and two members apart past it: 0.5 Hz on
# a 2-s window, so that no window passed from 7.0 to 8.0 Hz on the 93 of 112 sensor videos with an anchor every 4th frame --
# the middle of the bird band (PR085's bird was refused there, and found again by hand).
Z_LINE = 3.0         # a peak is at a codec line where it lies within this many of its own frequency errors of it (`hz_error`)
Z_APART = 3.0        # two members' frequencies are apart where they differ by this many of their combined errors -- over all the
                     # pairs judged at once (`z_apart`, Sidak): a rhythm of the video read in fifteen pairs seems apart no oftener than in one
BOOT = 200           # resamplings of a curve's residual for its frequency's error (`hz_error`) ...
BOOT_BLOCK_S = 0.5   # ... in blocks of this many seconds (15 frames at 30 fps), which keep the residual's colour
ERR_REACH = 4.0      # resolutions: a peak further than this from every codec line is not at one, and its error is not read for it
SLICE_HZ = (0.1, 0.25, 0.4, 1.0)   # Hz either side of a codec line where beats are planted in windows (`sliced`); the last, outside
                                   # the half-hertz the resolution blinded, is the control the slice's recovery is read against
SLICE_AMPL = (0.1, 0.2)            # the planted beats' amplitudes there, shares of the object's brightness
COMPLETE = 0.75      # the completeness the closed-form amplitude is for (`analytic`), as the planted beats' `complete_from` is
HEADLINE_NEAR = 0.5  # Hz: passing windows that do not overlap and agree this closely are one beat come back (`apart_windows`)
SHARED = 0.5         # a background aperture that beats this strongly at the object's frequency shares its beat
WINDOW_S = 2.0       # s: the windows a beat is looked for in along the track, an eighth of a window apart, the last one always
HALF = 0.5           # a peak at half the strongest's frequency, this share of it or more, makes the strongest a double
LOBE = 2.0           # resolutions either side of a peak that are its own lobe (Hann): another peak is further away than that
DROP = 0.25          # the object is lost against what is behind it where its brightness over the ring is under this share of its
                     # own level (`lost`; PR23's roof: 4,800 to -1,054..345 -- a 25 % beat dips to 0.75, a 60 % one to 0.4)
LOST_MAX = 0.1       # lost on more than this share of its frames, and no beat is looked for ...
LOST_RUN = 3         # ... unless the runs of lost frames are short (their median this long or shorter), there are LOST_RUNS or
LOST_RUNS = 6        #     more of them, and they fall at the troughs of the curve's own strongest beat (`lost_at_beat`): a dark
LOST_TROUGH = 0.65   #     object beating hard dips under DROP at every trough (PR097's dots, 2026-10-15: lost on 14-22 % of their
LOST_BAND = 1.0      #     frames in 20-24 runs, median run 1-2 frames, a few of 5-10), and the troughs are the beat, not a crossing
                     #     (PR23's roof and the WA9ONY-5 balloon: 3 runs each, so LOST_RUNS is 6, 2026-10-16) -- and, the second
                     #     half of the rule, the beat the stage then finds is theirs: within LOST_BAND of the troughs' own frequency
                     #     or its double (`at_the_troughs`); else the frames are lost as before
LOOKALIKES = [       # a frequency the world makes, and what makes it: folded through the frame rate, each is where a beat's
    (50.0, "a 50-Hz mains supply"),                              # look-alike sits (`lookalikes`, item 9)
    (100.0, "a lamp on 50-Hz mains, which flickers at twice the mains"),
    (60.0, "a 60-Hz mains supply"),
    (120.0, "a lamp on 60-Hz mains"),
    (400.0, "an aircraft's 400-Hz power"),
    (800.0, "a lamp on 400-Hz aircraft power, which flickers at twice it"),
]
LOOKALIKE_BANDS = [  # rhythms that are bands, not lines (item 11; 2026-10-20): (lo, hi) Hz as made, what makes them, a short
    # name. The bus as heard: PURSUE's PR106/107/111 at 399.60 and 399.82, AARO's FLIR at 399.10 (and 401.27, a second
    # supply), a CBP aircraft at 398.41 (the uap repository's audio census, 2026-10-17). The flames: a bundle of candles
    # near 10 Hz (Kitahata et al. 2009; Chen et al. 2019, 9.9 Hz), a pool fire's puffing at 1.5 D^-1/2 Hz, 4.7-8.7 Hz for
    # a sky lantern's 3-10-cm fuel cell (Cetegen & Ahmed 1993). The mechanical bands are nominal (the infrared methods
    # survey, sections 3.2 and 4.3, from patents and recollection, not measured): they fold over the whole band at video
    # rates, so they are listed and mark nothing there.
    (398.41, 401.27, "an aircraft's 400-Hz power as recorded aircraft sound has it (398.4-401.3 Hz, not 400.000)", "400-Hz bus, as heard"),
    (796.82, 802.54, "a lamp on that power, flickering at twice it", "lamp on the bus, as heard"),
    (9.5, 10.5, "a bundle of candles' flame, which flickers near 10 Hz", "candle flames"),
    (4.7, 8.7, "a sky lantern's flame, which puffs at 4.7-8.7 Hz with its own phase", "sky lantern"),
    (10.0, 30.0, "a helicopter rotor's blade-pass (10-30 Hz)", "rotor"),
    (20.0, 60.0, "a rotor's blade-pass doubled, for an odd number of blades", "rotor, odd blades"),
    (50.0, 150.0, "a turboprop's blade-pass (50-150 Hz)", "propeller"),
    (150.0, 300.0, "a multirotor drone's blade-pass (150-300 Hz)", "multirotor"),
    (40.0, 80.0, "a cooled sensor's cryocooler drive (40-80 Hz), whose jitter moves the whole picture", "cryocooler"),
]
WHOLE_BAND = 0.9     # a band folded over this share of LOW .. top or more marks no beat: frequency cannot exclude it
LIGHT_K = 3          # a light is read as the mean of this many brightest (and reddest) pixels inside the ring, over its median (`lights`)
LIGHT_SIGMA = 4.0    # the thing's whole silhouette, for where its lights can be: pixels this many robust sigmas off the sky (`reach`)
BLINK_MED_S = 2.0    # s: a curve is taken against its running median over this long for its flashes (`blinks`; a flash lasts 0.1-0.3 s)
BLINK_Z = 5.0        # a flash stands this many robust sigmas over that median at its peak ...
BLINK_Z_LO = 2.5     # ... and lasts while it stands over this many; its time is the centroid of that run
BLINK_MERGE_S = 0.15 # s: runs closer than this are one flash (a double flash, a held picture); under the gap between
                     #    flashes of the fastest train looked for (3 Hz, 0.1-s flashes: 0.23 s)
BLINK_EDGE_S = 0.4   # s: no flash this near either end of a curve, where the running median is one-sided
BLINK_MIN = 4        # flashes a train needs
BLINK_BAND = (0.6, 3.0)            # Hz: where a train's rate is looked for -- an anti-collision light flashes 40-100 times a
BLINK_RULE = (40 / 60, 100 / 60)   # minute (14 CFR 25.1401(c), 27.1401(c), 29.1401(c)), to 180 where two lights' beams
BLINK_OVERLAP = 3.0                # overlap
BLINK_TOL = 0.05     # a rate this share outside the rule's edges is still said to be at them (a rate is measured, the rule is not)
BLINK_HARM = 4       # harmonics in the fold's Z^2 statistic: a train of narrow flashes has many
BLINK_FUND = 0.8     # the train's rate is the lowest that folds within this share of the strongest: flashes at period P are in
                     #    step at every multiple of 1/P as well, as strongly (a 1.00-Hz train read as 3.00 without it, 2026-10-20)
BLINK_RUNS = 2000    # sets of as many flash times, at random over the curve, the fold is held against
BLINK_P = 0.01       # a train is a train where under this share of them fold as tightly at any rate in BLINK_BAND
BLINK_SAME = 0.05    # a background aperture flashing within this share of the object's rate shares its train
BLINK_KEEP = 0.5     # a beat that keeps under this share of its amplitude once the flashes are taken out is the flashes'
LIGHT_FLOOR = 1.0    # grey levels: the least scatter a light's curve is held to have (a red excess is exactly 0 between flashes
                     #    where a frame's colour channels are equal, and a robust scatter of 0 would make every flash infinite)
LOOKALIKE_EVERY = (3, 4, 5, 6)   # a rhythm locked to every k-th frame (a codec's anchors, a pulldown, a display's refresh)
STEADY_RUNS = 200    # steady beats planted per beat (`steadiness`, item 12) ...
STEADY_P = 0.01      # ... and the share of them under which it wanders more than a clock does
STEADY_PLAIN_S = 8.0 # s: a stretch up to this long is split in two halves; a longer one in pieces of STEADY_SEG_S
STEADY_SEG_S = 4.0
STEADY_REACH = (0.6, 0.1)   # Hz, share of the beat: each piece's frequency is looked for within the larger of these of it
RUNS = 1000         # the curves that only wander and jitter which the strongest beat is held against ...
BEYOND = 0.99        # ... and the share of them it must stand further over their mean than they do, each at its own strongest
TOP = 0.8            # a beat is heard only up to this share of the Nyquist frequency -- of the frame rate, or of the
                     # picture rate where pictures are held (PR27, 2026-10-11: six windows "beat" at 13.5 Hz on frame-to-frame
                     # noise, 0.9 of the 15-Hz Nyquist; PR34: a clip of 10 pictures a second shown at 30 fps "beat" at 5.02 Hz,
                     # its hold cadence's half, and at 10.03, the cadence itself)
HELD = 0.2           # a frame is a held picture where it differs from the one before by under this share of the typical
                     # change between pictures -- the 80th percentile of the changes, not their median, as a held picture's
                     # difference is the encoder's noise (0.01-0.05 grey levels on PR34) and can be most of them
HELD_MIN = 0.1       # under this share of frames held, the pictures are taken to change on every frame
THUMB = 4            # frames are compared on THUMB x THUMB block means (`_apertures`)
ALSO = 6.0           # a half or a double stands this many times over the drift fitted without it, where it is, to be a peak
CLIP = 10.0          # a frequency standing this many times over the drift fitted to a spectrum is a peak's, and is left out of the fit
# The aperture follows the object's size (the bird sweep, 2026-10-10): a fixed 4-px aperture with its ring at 7-10 px
# put the ring ON an object 15-100 px across (PR056, PR086, PR116, PR052, PR47), its brightness over the ring came out
# near nothing, and the stage called a thing anyone could see "lost". The object's extent is read off its own frames
# (`extent`); a point no wider than APERTURE keeps APERTURE, RING and BACKGROUND exactly; a wider thing gets an
# aperture APERTURE_OVER times its extent, a ring beyond it, background apertures beyond that, and the aperture
# re-centred each frame on the thing's own centroid (a wide thing's centroid is steady; a point's is not, which is
# why a point keeps the smoothed track: trap 1).
EXTENT_FRAMES = 20   # frames the extent is read on, spread over the track
EXTENT_DROP = 0.1    # the extent: where the object's radial profile falls to this share of its centre's height
EXTENT_SIGMA = 3.0   # the centre must stand this far over the far ring's own scatter to have an extent
EXTENT_MAX = 80.0    # px: no extent is read past this
# Where the frames do not agree on the size (PURSUE PR089's bird C after a sensor blank, 2026-10-23: a dot 5-9 px across,
# faint over a sea in column bands; on 7 of 11-12 frames nothing stood out of the far ring and on others the profile never
# fell before the bands did, 43-66 px, so the median of the few gave a 48-px radius and a 58-px aperture, and nothing was
# measured), the size is read once off the median of the object's stamps along the track (`stacked_extent`).
EXTENT_AGREE = 0.5   # the frames agree where at least this share of them give a size ...
EXTENT_SPREAD = 0.5  # ... and the sizes' interquartile range is at most this share of their median
SMEAR_MIN = 1.0      # px a frame: an object this fast is stacked along its travel, and its size read on the half ahead
APERTURE_OVER = 1.2  # a wider thing's aperture, as a multiple of its extent
# ... but for a point-like thing the disc is capped, the ring and the background apertures kept where APERTURE_OVER puts
# them (the aperture study, 2026-10-24, uap analysis/sweeps/svanstrom/README.md: it is the ring that must clear the thing,
# not the disc that must cover it; on 38 birds with known beats -- the bird paper's PURSUE cases, PR089's bird C, Galileo
# flyers 1-5 -- the capped disc found 26 beats against 21, losing none, and a 4-px disc with its ring at 7-10 px lost
# PR135's members 5-6 to refusals; on the Svanstrom set it added four false calls, close helicopters at 1.6-7.8 %, which
# report.BIRD_FLOOR keeps from being named birds). Only under 10 px (Jacob, 2026-10-24): PR41's bird, 10 px, beats 11.6 %
# in the disc that follows it and 7.6 % in a 6-px one, which leaves out part of the wing, under the floor.
POINT_DISC = 6.0     # px: the capped disc's radius ...
POINT_EXTENT = 10.0  # px: ... for a thing whose extent is under this
# The astronomer's tests (2026-10-15; item 7 above). Each is reported beside the stage's own; GATE_ASTRO would make the
# first two decide as well. Off, by decision (Jacob, 2026-10-17, on the gate study of 760 saved curve sets, the held-out
# third left out): it lost 4 of 27 known birds' beats (PR077 1b, PR097 3 and 7, Galileo flyer 4) and none of the 3 false
# alarms of 2,887 background apertures judged as the object; alone its tests pass 58 % of those apertures (Baluev's
# probability assumes white noise; these backgrounds are red). They stay readings.
GATE_ASTRO = False
FAP_MAX = 0.01       # a Lomb-Scargle peak is a beat only with a false-alarm probability (Baluev 2008) under this ...
P_MAX = 0.01         # ... and only where under this share of the curve's own chunk-scrambled copies stand as high
SCRAMBLE_S = 0.25    # s: the chunks a curve is scrambled in; the scramble says nothing of frequencies under 1/SCRAMBLE_S
SCRAMBLES = 200      # scrambled copies
COMMON_K = 2         # components of the background apertures' common mode the object's curve is held against
INJECT_AMPL = (0.02, 0.05, 0.1, 0.2)   # beats planted in the background apertures, as shares of the object's brightness ...
INJECT_N = 4         # ... at this many frequencies spread over the band ...
INJECT_MAX = 300     # ... on at most this many frames of each (the middle of its stretch)
STAMP = 16           # px: the half-size of the stamp of the object kept from every frame, for the fold
FOLD_BINS = 8        # the beat's cycle is folded into this many bins
WINDOW_LINE = 0.1    # a rhythm of the sampling (a line of its spectral window) is reported where it stands this high (nought's is 1)
# The seismologist's tests (2026-10-15; item 8 above). Each is reported beside the stage's own; GATE_SEIS would make
# the multitaper line test decide as well. Off, by decision (Jacob, 2026-10-17, the same study): it lost 3 of 27 known
# birds' beats (PR088 1, PR097 3 and 7) to remove 2 of the 3 false alarms, within their noise; alone it passes 58 % of the
# background apertures (a line in any of up to 47 windows of 2 s). It stays a reading.
GATE_SEIS = False
CONTINUUM_RUNS = 2000     # the noise curves the continuum null holds a beat against (`continuum`; the paper's 2,000)
CONTINUUM_EXCLUDE = 0.5   # Hz either side of the peak left out of the power law fitted to the spectrum
CONTINUUM_P = 0.01        # a peak is a line where fewer than this share of the noise curves stand as high anywhere in the band
RULE = "stage"            # how a whole curve's beat is judged (`whole_passes`): "stage" -- ABOVE times the strongest of the
                          # background apertures beside it and the drift test; "paper" -- the paper's continuum null under
                          # CONTINUUM_P and ABOVE times the background apertures at the beat's own frequency, and the
                          # encoding control (2026-10-16). The 2-s windows keep the stage's tests under both. A measurement
                          # may choose (`measure(rule=)`, `--beat-rule`); the stage's is the default, decided by the controls:
                          # on the whole-video pass's background apertures judged as the object, 0.15 % of 4,700 pass by
                          # the stage's rule and 2.0 % by the paper's -- a rule for an object someone has looked at
RULES = ("stage", "paper")
_RULE = contextvars.ContextVar("mcdonald_flicker_rule", default=None)   # one measurement's choice, in its own thread only


def active_rule():
    """The rule this measurement judges by: its own choice (`measure(rule=)`), else RULE."""
    return _RULE.get() or RULE
MT_NW = 2.5          # the multitaper's time-bandwidth product: K = 2 NW - 1 = 4 tapers, a bandwidth of 2 NW / T Hz
MT_P = 0.01          # a line is a line where the harmonic F-test's chance of one is under this (GATE_SEIS)
COH_P = 0.01         # a coherence stands where it is over the level chance clears with this probability
SOMPI_ORDERS = range(4, 13)   # the autoregressive orders tried ...
SOMPI_SHARE = 0.7    # ... and the share of them a root must hold still across to be a line
SOMPI_TOL = 0.04     # as a share of the frequency: how far a root may move between orders and be the same line
SOMPI_OVER = 1.0     # a line's amplitude stands this many times over what the lines leave of the record (its grain)
SHORT_MIN = 20       # frames: a track under MIN_FRAMES but at least this long gets the short-record reading (`short_reading`)
GLIDE_S = 1.0        # s: the window the beat's fundamental is followed in along the stretch, an eighth of it apart
GLIDE_P = 0.05       # a window's line stands where its F-test's chance there -- a frequency given beforehand -- is under this
PPSD_HOP = 0.5       # the background windows the noise's distribution is read from are this share of WINDOW_S apart
ONEBIT_RES = 2.0     # resolutions: a reading agrees with the stage's beat within this of it, its half or its double
# A rotor's look (item 14, 2026-10-25): what told the Svanstrom set's helicopters that beat from its birds that beat
# (uap analysis/sweeps/svanstrom/README.md, "What else tells a helicopter's beat from a bird's?")
ROTOR_COHERENCE = 0.75   # the beat reaches a background aperture beside the object in step at least this coherently ...
ROTOR_OFFSET_PX = 3.5    # ... or the light that beats sits at least this far from the object's middle (the fold's offset)


def brightness(g, x, y, r=APERTURE, ring=RING, dark=False):
    """The aperture's sum over the ring's median, for a thing centred at (x, y) to a fraction of
    a pixel; None where the ring leaves the frame. Dark things are measured as dark: the sum is
    of how much darker they are."""
    H, W = g.shape
    R = int(np.ceil(ring[1])) + 1
    ix, iy = int(np.floor(x)), int(np.floor(y))
    if ix - R < 0 or iy - R < 0 or ix + R + 1 > W or iy + R + 1 > H:
        return None
    s = g[iy - R:iy + R + 1, ix - R:ix + R + 1].astype(float)
    yy, xx = np.mgrid[iy - R:iy + R + 1, ix - R:ix + R + 1].astype(float)
    off = (np.arange(SUPER) + 0.5) / SUPER - 0.5
    w = np.zeros(s.shape)
    for dy in off:
        for dx in off:
            w += np.hypot(xx + dx - x, yy + dy - y) <= r
    w /= SUPER * SUPER
    rr = np.hypot(xx - x, yy - y)
    bg = float(np.median(s[(rr >= ring[0]) & (rr <= ring[1])]))
    v = float(((s - bg) * w).sum())
    return -v if dark else v


def lights(rgb, g, x, y, ring=RING, k=LIGHT_K, black_hot=False):
    """(white, red): a light's reading in an aperture -- the mean of the k brightest pixels of the grey frame `g` within
    the ring's inner radius of (x, y), over the ring's median; and the same of how much redder than green and blue each
    pixel is, R - max(G, B), from the colour frame `rgb` (None for a grey one). None where the ring leaves the frame. A
    light is a few pixels: on a thing wider than it, the aperture's sum is the thing's (a dark helicopter's body), and
    the light is seen only in its brightest pixels (item 13, Svanstrom V_HELICOPTER_054, 2026-10-20). Not negated for a
    dark thing: a light is bright on anything -- on anything but a black-hot thermal display, where a light, being hot,
    is dark: with `black_hot` the first is the k darkest pixels, how far under the ring's median (still "white" in the
    records: the hottest)."""
    H, W = g.shape
    R = int(np.ceil(ring[1])) + 1
    ix, iy = int(np.floor(x)), int(np.floor(y))
    if ix - R < 0 or iy - R < 0 or ix + R + 1 > W or iy + R + 1 > H:
        return None
    yy, xx = np.mgrid[iy - R:iy + R + 1, ix - R:ix + R + 1].astype(float)
    rr = np.hypot(yy - y, xx - x)
    inner, out = rr < ring[0], (rr >= ring[0]) & (rr <= ring[1])
    s = g[iy - R:iy + R + 1, ix - R:ix + R + 1]
    white = (float(np.median(s[out]) - np.sort(s[inner], axis=None)[:k].mean()) if black_hot else
             float(np.sort(s[inner], axis=None)[-k:].mean() - np.median(s[out])))
    red = None
    if rgb is not None and rgb.ndim == 3 and rgb.shape[2] == 3:
        c = rgb[iy - R:iy + R + 1, ix - R:ix + R + 1].astype(np.float32)
        q = c[..., 0] - np.maximum(c[..., 1], c[..., 2])
        red = float(np.sort(q[inner], axis=None)[-k:].mean() - np.median(q[out]))
    return white, red


def reach(g, x, y):
    """How far the thing at (x, y) reaches: the farthest pixel, from (x, y), of the patch standing LIGHT_SIGMA robust
    sigmas off the sky (either way: a dark body and a bright light alike) and joined to its middle -- the whole silhouette,
    tail and rotor included, where its lights can be. `extent` is the core's (where the profile falls to EXTENT_DROP of
    the centre's height), and a light on a tail boom is far outside it: Svanstrom V_HELICOPTER_054's core is 8.5 px across
    in radius, its lights 14-35 px from its middle (2026-10-20). None where nothing stands out at the middle, or the patch
    runs on to the edge of the EXTENT_MAX disc (clutter joined to it, not the thing)."""
    H, W = g.shape
    R = int(EXTENT_MAX) + 6
    ix, iy = int(round(x)), int(round(y))
    y0, y1, x0, x1 = max(0, iy - R), min(H, iy + R + 1), max(0, ix - R), min(W, ix + R + 1)
    if y1 - y0 < 8 or x1 - x0 < 8:
        return None
    s = g[y0:y1, x0:x1].astype(float)
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(float)
    rr = np.hypot(xx - x, yy - y)
    sky = s[(rr > EXTENT_MAX - 10) & (rr <= EXTENT_MAX + 5)]
    if sky.size < 20:
        return None
    med = float(np.median(sky))
    sig = 1.4826 * float(np.median(np.abs(sky - med))) or 1.0
    m = np.abs(s - med) > LIGHT_SIGMA * sig
    lab, _ = ndimage.label(m)
    near = set(np.unique(lab[(rr <= 3) & m])) - {0}
    if not near:
        return None
    r = float(rr[np.isin(lab, list(near))].max())
    return None if r >= EXTENT_MAX - 10 else r


def light_reach(clip, tracks, ns):
    """{name: the median `reach` over EXTENT_FRAMES frames spread over its span, or None}: how far each tracked thing's
    lights can be from its middle (`lights`, item 13)."""
    out = {}
    for name, t in tracks.items():
        x, y = smoothed(t, ns)
        have = [k for k, n in enumerate(ns) if min(t) <= n <= max(t)]
        pick = [have[int(i)] for i in np.linspace(0, len(have) - 1, min(EXTENT_FRAMES, len(have)))] if have else []
        rs = [reach(vf.grey_of(clip.rgb(ns[k])), x[k], y[k]) for k in pick]
        rs = [r for r in rs if r is not None]
        out[name] = float(np.median(rs)) if len(rs) >= max(1, len(pick) // 2) else None
    return out


def extent(g, x, y, dark=False, ahead=None, local=False):
    """The object's radius (px) about (x, y) in grey frame g, off its radial profile: the median contrast on each
    1-px ring about it (a median, so roofs or wave crests on part of a ring do not count -- PR23, PR056), and the
    first radius where that falls to EXTENT_DROP of the centre's height over the far background. For a Gaussian blob
    that is about the radius holding 90 % of its light. None where the stamp leaves the frame or nothing stands out.
    `ahead`, a unit vector (dx, dy), reads the inner rings on the half of each that lies ahead of it only -- the half
    a trailing smear does not reach (`stacked_extent`). Pixels that are NaN (off the frame, in a stack) are left out.
    `local` takes the background level just outside the object -- the rings 3 to 6 times its half-width at half height
    out, no further than the far ring -- in place of the far ring's: about a faint point in a compressed video a pedestal
    a tenth of its height can reach 20 px (PR089's bird C, a stack of its stamps: 4 of 35 grey levels), and the extent
    read against the far ring then ends in it (`stacked_extent`)."""
    H, W = g.shape
    S = int(EXTENT_MAX) + 25
    ix, iy = int(round(x)), int(round(y))
    if ix - S < 0 or iy - S < 0 or ix + S + 1 > W or iy + S + 1 > H:
        return None
    s = g[iy - S:iy + S + 1, ix - S:ix + S + 1].astype(float)
    yy, xx = np.mgrid[-S:S + 1, -S:S + 1]
    rr = np.hypot(xx + ix - x, yy + iy - y)
    q = -s if dark else s
    ring = np.floor(rr).astype(int)
    keep = np.isfinite(q)
    inner = keep if ahead is None else keep & ((xx + ix - x) * ahead[0] + (yy + iy - y) * ahead[1] >= 0)
    med = lambda v: float(np.median(v)) if v.size else np.nan
    prof = np.array([med(q[(ring == k) & (inner if k < EXTENT_MAX else keep)]) for k in range(int(EXTENT_MAX) + 21)])
    if not np.all(np.isfinite(prof)):
        return None
    far = float(np.median(prof[int(EXTENT_MAX):]))
    top = float(prof[:3].max()) - far
    ann = q[(rr >= EXTENT_MAX) & (rr <= EXTENT_MAX + 20) & keep]
    if top <= EXTENT_SIGMA * 1.4826 * float(np.median(np.abs(ann - np.median(ann)))):
        return None                                          # nothing stands out of the far ring's own scatter
    if local:
        half = np.flatnonzero(prof[:int(EXTENT_MAX) + 1] - far < 0.5 * top)
        hw = max(float(half[0]), 1.0) if len(half) else EXTENT_MAX
        lo = int(min(3 * hw, EXTENT_MAX))
        hi = int(min(max(6 * hw, lo + 5), EXTENT_MAX + 20))
        far = float(np.median(prof[lo:hi + 1]))
        top = float(prof[:3].max()) - far
    below = np.flatnonzero(prof[:int(EXTENT_MAX) + 1] - far < EXTENT_DROP * top)
    return float(below[0]) if len(below) else EXTENT_MAX


def sized(r):
    """(aperture radius, ring, background offset, re-centred?) for an object whose contrast lies within r px:
    APERTURE, RING and BACKGROUND's 25 px for a point no wider than APERTURE, larger for a wider thing -- its ring and
    background apertures beyond APERTURE_OVER times its extent, its disc that too but no more than POINT_DISC where the
    extent is under POINT_EXTENT -- and a disc so capped is not re-centred."""
    if r is None or r <= APERTURE:
        return APERTURE, RING, 25, False
    R = APERTURE_OVER * r
    ring = (R + 3.0, R + 6.0 + 0.25 * R)
    capped = r < POINT_EXTENT and R > POINT_DISC
    # a capped disc stays on the smoothed track, as the paper's own apertures did and the study measured it: re-centred each
    # frame on the thing's centroid it chases the brightest part as the wings move and loses the beat (PR097 object 3: 14 %
    # on the track, 5 % re-centred; PR089 C's 10.5-Hz beat on frames 918-1422, 25 %, gone)
    return (POINT_DISC if capped else R), ring, int(np.ceil(2 * ring[1] + 5)), not capped


def fixed(spec):
    """A fixed aperture, in the form `sized` gives one -- (radius, ring, background offset, re-centred?) -- from the
    radius alone or with its ring and the background apertures' offset, as 'R', 'R,R1,R2' or 'R,R1,R2,BG' (text, a
    number or a sequence; pixels). The paper measured each of its Table 1 objects in a disc of its own size, 2.5 to 12
    px, never re-centred, on the smoothed track (2026-10-16, ROADMAP.md 0.3): where a flock's members fly close
    together, the aperture that grows with the object takes in its neighbours, and a fixed one does not. Without a
    ring, R+3 to R+6 for a point-sized disc (the paper's 7-10 for 4) and `sized`'s for a wider one; without an offset,
    `sized`'s rule, 25 px for a point. ValueError, in plain words, for one that cannot be."""
    if isinstance(spec, (int, float)):
        vals = [float(spec)]
    elif isinstance(spec, str):
        try:
            vals = [float(v) for v in spec.replace(" ", "").split(",") if v != ""]
        except ValueError:
            raise ValueError(f"the aperture {spec!r} is not R, R,R1,R2 or R,R1,R2,BG in pixels, such as 8 or 8,11,16")
    else:
        vals = [float(v) for v in spec]
    if len(vals) not in (1, 3, 4):
        raise ValueError(f"the aperture {spec!r} is not R, R,R1,R2 or R,R1,R2,BG in pixels, such as 8 or 8,11,16")
    R = vals[0]
    if len(vals) >= 3:
        ring = (vals[1], vals[2])
    elif R <= APERTURE:
        ring = (R + 3.0, R + 6.0)
    else:
        ring = (R + 3.0, R + 6.0 + 0.25 * R)
    off = int(round(vals[3])) if len(vals) == 4 else max(25, int(np.ceil(2 * ring[1] + 5)))
    if not 0 < R < ring[0] < ring[1]:
        raise ValueError(f"the aperture {spec!r}: its radius must be above nought and under the ring's inner edge, which "
                         "must be under its outer edge")
    if off <= ring[1] + R:
        raise ValueError(f"the aperture {spec!r}: the background apertures, {off} px away, would overlap the object's ring "
                         f"(out to {ring[1]:g} px) -- put them further out, or leave the offset out")
    return float(R), (float(ring[0]), float(ring[1])), off, False


def clear_offsets(first, others, off, ring):
    """Four background offsets about the object -- (dx, dy) in px -- that keep clear of the other tracked things
    `others`, [(x, y, present)] over the frames (`smoothed`, and where each track is): BACKGROUND's four at `off` where
    they are clear on every frame, else four of 16 directions at `off`, 1.5 times it or twice it, at least 60 degrees
    apart, the nearest clear ones first and, if too few are, those furthest from the things. Clear: the aperture's
    centre stays its ring's outer edge twice over, and AVOID_MARGIN more, from every other thing on every frame it is
    there. PR135's six measured one by one (2026-10-16): the apertures 25 px from E and F sat on neighbouring birds,
    which beat at their rate, and the stage said the background shared their beats. (offsets, moved?)"""
    x0, y0 = first
    need = 2 * ring[1] + AVOID_MARGIN

    def clearance(dx, dy):
        c = np.inf
        for x, y, here in others:
            if np.any(here):
                c = min(c, float(np.min(np.hypot(x0[here] + dx - x[here], y0[here] + dy - y[here]))) - need)
        return c
    default = [(dx * off / 25.0, dy * off / 25.0) for dx, dy in BACKGROUND]
    if all(clearance(*c) > 0 for c in default):
        return default, False
    chosen = []

    def spread(c):
        a = np.arctan2(c[1], c[0])
        return all(abs((a - np.arctan2(d[1], d[0]) + np.pi) % (2 * np.pi) - np.pi) >= np.radians(60) - 1e-9 for d in chosen)
    for R in (off, 1.5 * off, 2.0 * off):
        ring_c = [(R * np.sin(2 * np.pi * k / 16), R * np.cos(2 * np.pi * k / 16)) for k in range(16)]
        for c in sorted((c for c in ring_c if clearance(*c) > 0), key=lambda c: -clearance(*c)):
            if len(chosen) < 4 and spread(c):
                chosen.append(c)
    if len(chosen) < 4:
        rest = [(R * np.sin(2 * np.pi * k / 16), R * np.cos(2 * np.pi * k / 16)) for R in (off, 1.5 * off, 2.0 * off) for k in range(16)]
        for c in sorted(rest, key=lambda c: -clearance(*c)):
            if len(chosen) < 4 and spread(c) and c not in chosen:
                chosen.append(c)
    return chosen, True


def centred(g, x, y, r, ring, dark=False):
    """The object's own centroid near (x, y): contrast over the ring's median within r, weighted (twice)."""
    H, W = g.shape
    R = int(np.ceil(ring[1])) + 1
    for _ in range(2):
        ix, iy = int(round(x)), int(round(y))
        if ix - R < 0 or iy - R < 0 or ix + R + 1 > W or iy + R + 1 > H:
            break
        s = g[iy - R:iy + R + 1, ix - R:ix + R + 1].astype(float)
        yy, xx = np.mgrid[iy - R:iy + R + 1, ix - R:ix + R + 1].astype(float)
        rr = np.hypot(xx - x, yy - y)
        b = float(np.median(s[(rr >= ring[0]) & (rr <= ring[1])]))
        w = np.clip((b - s) if dark else (s - b), 0, None) * (rr <= r)
        if w.sum() <= 0:
            break
        x, y = float((w * xx).sum() / w.sum()), float((w * yy).sum() / w.sum())
    return x, y


def smoothed(track, ns):
    """The track at every frame of `ns`, filled in where it has gaps and smoothed over SMOOTH frames."""
    have = sorted(track)
    x = np.interp(ns, have, [track[n][0] for n in have])
    y = np.interp(ns, have, [track[n][1] for n in have])
    return ndimage.uniform_filter1d(x, SMOOTH, mode="nearest"), ndimage.uniform_filter1d(y, SMOOTH, mode="nearest")


def trend_frames(fps):
    """The running mean's length in frames: DETREND_S at this frame rate."""
    return max(3, int(DETREND_S * fps + 0.5))


def deviation(f, fps, scale=None):
    """A curve taken against its own running mean over DETREND_S, as a share of that mean -- or of `scale`, for a
    background aperture, whose own mean is near nothing: it is measured in the object's brightness -- about nought.
    Every spectrum here is of this."""
    f = np.asarray(f, float)
    trend = ndimage.uniform_filter1d(f, trend_frames(fps), mode="nearest")
    r = (f - trend) / (scale if scale else trend)
    return r - r.mean()


def _spec(r, fps):
    """(frequencies, complex spectrum, the band's mask, Hann weights' sum, rms) of a deviation curve."""
    r = np.asarray(r, float)
    w = np.hanning(len(r))
    F = np.fft.rfft(r * w, PAD * len(r))
    fr = np.fft.rfftfreq(PAD * len(r), 1 / fps)
    band = (fr >= LOW) & (fr <= 0.95 * fps / 2)
    return fr, F, band, float(w.sum()), float(r.std())


def spectrum(f, fps, scale=None):
    """(frequencies, complex spectrum, the band's mask, Hann weights' sum, rms) of a curve taken
    against its own running mean, as a share of that mean -- or of `scale`, for a background
    aperture, whose own mean is near nothing: it is measured in the object's brightness."""
    return _spec(deviation(f, fps, scale), fps)


def peak(f, fps, lines=(), scale=None, err=None):
    """The strongest beat of a curve: frequency, amplitude (a share of the brightness), how it
    stands over the median of the band, its half-power width, whether it is at one of the codec's
    `lines` -- within Z_LINE of its own frequency error (`hz_error`) -- and whether it is only the band's
    `edge`: the strongest within its lobe of the band's first (or last) frequency, with more beyond it -- the
    flank, or a side lobe, of something slower than LOW Hz: a balloon's payload swinging (WA9ONY-5,
    1.53 Hz), a sea's swell under the object (PR144) -- and no peak at all. `err`: True reads the frequency's
    error (`hz_err`) whatever the peak; None (the default), only where the peak is within ERR_REACH resolutions of
    a codec line, where the mark needs it; False never (and the mark falls back to the resolution)."""
    return _peak(deviation(f, fps, scale), fps, lines, err)


def _peak(r, fps, lines=(), err=None):
    """`peak`, of a deviation curve."""
    fr, F, band, wsum, rms = _spec(r, fps)
    P = np.abs(F) ** 2
    k = int(np.argmax(np.where(band, P, -1)))
    res = fps / len(r)
    half = fr[band][P[band] >= P[k] / 2]
    below, above = (fr > 0) & (fr < LOW), fr > 0.95 * fps / 2
    edge = ((fr[k] - LOW <= LOBE * res and below.any() and P[below].max() >= P[k])
            or (0.95 * fps / 2 - fr[k] <= LOBE * res and above.any() and P[above].max() >= P[k]))
    hz = float(fr[k])
    e = None
    if err or (err is None and any(abs(hz - L) <= ERR_REACH * res for L in lines)):
        e = hz_error(r, fps, hz)
    return dict(hz=hz, amplitude=float(2 * np.sqrt(P[k]) / wsum), stands=float(P[k] / np.median(P[band])),
                half_power_hz=[float(half.min()), float(half.max())], resolution_hz=float(res), rms=rms,
                hz_err=e["hz_err"] if e else None, noise_rms=e["noise_rms"] if e else None,
                at_the_codec_line_hz=at_line(hz, e["hz_err"] if e else None, lines, res), edge=bool(edge))


def at_line(hz, err, lines, res=None):
    """The codec line a peak at `hz` is at -- within Z_LINE of its frequency error `err` (D1, 2026-10-17) -- or None.
    The line has no width of its own: it is locked to the frame count, so a rhythm of the codec's is read there to
    within the reading's own error. With no error read (`peak`'s err=False), within the resolution `res`, as until then."""
    if hz is None:
        return None
    if err is None:
        return next((L for L in lines if res is not None and abs(hz - L) <= res), None)
    return next((L for L in lines if abs(hz - L) <= Z_LINE * err), None)


def hz_error(r, fps, hz, runs=BOOT, seed=0):
    """How well a peak's frequency is known (2026-10-17; the information-theory survey's D1, ROADMAP.md 0.3 objective 2):
    {hz_err, boot, bound, grid, amplitude, noise_rms}. The sinusoid at `hz` and a constant are fitted to the deviation
    curve r by least squares; the residual is resampled in blocks of BOOT_BLOCK_S, end to end around the curve (a circular
    block bootstrap, which keeps its colour: grain, a gain's wander, the codec's noise), added back to the fit `runs`
    times, and each copy's peak read as `peak` reads one, within the peak's own lobe (LOBE resolutions): `boot` is their
    spread. `bound` is the Cramer-Rao bound for one sinusoid of the fitted amplitude in white noise of the residual's
    variance (Rife & Boorstyn 1974; Kay 1993, 3.10), which the error is never let under -- the bootstrap is optimistic on
    a short, coloured record below the threshold SNR -- and `grid` the padded spectrum's step over sqrt(12), since the
    frequency is read off that grid: a rhythm locked to the frames is then never more than 1.7 of its errors from its
    line. `hz_err` is the largest of the three. It is not the resolution 1/T: that says when two sinusoids in one curve
    can be told apart; this, how well one is known -- for PR135's members over 4.5 s, 0.017-0.033 Hz against 0.22 (the
    survey's measurement). The same resamplings every time (one seed)."""
    r = np.asarray(r, float)
    n = len(r)
    t = np.arange(n) / fps
    X = np.c_[np.cos(2 * np.pi * hz * t), np.sin(2 * np.pi * hz * t), np.ones(n)]
    beta, *_ = np.linalg.lstsq(X, r, rcond=None)
    fit = X @ beta
    e = r - fit
    amp, var = float(np.hypot(beta[0], beta[1])), float(e.var())
    grid = fps / (PAD * n) / np.sqrt(12)
    bound = float(fps / (2 * np.pi) * np.sqrt(12 * var / (amp ** 2 * n * (n * n - 1)))) if amp > 0 else float("inf")
    k0 = int(round(hz * PAD * n / fps))                    # the padded spectrum's own frequencies, within the peak's lobe
    ks = np.arange(k0 - int(LOBE * PAD), k0 + int(LOBE * PAD) + 1)
    fk = ks * fps / (PAD * n)
    fk = fk[(fk >= LOW) & (fk <= 0.95 * fps / 2)]
    if len(fk) < 3:
        fk = np.array([hz])
    E = np.exp(-2j * np.pi * np.outer(np.arange(n), fk) / fps) * np.hanning(n)[:, None]
    L = min(n, max(2, int(round(BOOT_BLOCK_S * fps))))
    nb = -(-n // L)
    rng, got = np.random.default_rng(seed), []
    for m in [min(runs - i, max(1, int(2e6 // n))) for i in range(0, runs, max(1, int(2e6 // n)))]:
        idx = ((rng.integers(0, n, (m, nb))[:, :, None] + np.arange(L)[None, None, :]) % n).reshape(m, nb * L)[:, :n]
        Y = fit[None, :] + e[idx]
        Y = Y - Y.mean(axis=1, keepdims=True)
        got.append(fk[np.argmax(np.abs(Y @ E), axis=1)])
    boot = float(np.concatenate(got).std()) if got else 0.0
    return dict(hz_err=float(max(boot, bound, grid)), boot=boot, bound=bound, grid=float(grid), amplitude=amp,
                noise_rms=float(np.sqrt(var)))


def _pm(hz, err):
    """'7.39 ± 0.02 Hz': a frequency with its error, where it has one -- to the error's first figure, and to the hundredth
    at least ('7.370 ± 0.003 Hz' for PR085's bird over 31 s)."""
    if err is None:
        return f"{hz:.2f} Hz"
    d = int(min(4, max(2, -np.floor(np.log10(err))))) if err > 0 else 2
    return f"{hz:.{d}f} ± {err:.{d}f} Hz"


def z_apart(pairs):
    """How many of their combined errors two members' frequencies must differ by to be apart when `pairs` pairs are judged
    at once: Z_APART's two-sided chance shared out over them (Sidak) -- 3.0 for one pair, 3.7 for PR135's fifteen."""
    from scipy.special import ndtr, ndtri
    a0 = 2 * (1 - ndtr(Z_APART))
    return float(ndtri(1 - (1 - (1 - a0) ** (1 / max(1, pairs))) / 2))


def analytic(sigma, n, fps, top, floor=None, alpha=1 - BEYOND, complete=COMPLETE):
    """The amplitude a beat needs, in closed form, to be found `complete` of the time in n frames of white noise of rms
    `sigma` (a share of the brightness) by the strongest peak of the Hann-windowed spectrum over LOW..`top` -- the
    information-theory survey's D6, from the error exponent of the test between noise and noise with one sinusoid in it
    (Stein's lemma; Chernoff 1952; Cover & Thomas 2006, 11.8). Each quadrature of the amplitude read at one frequency
    has variance q = 2 sigma^2 sum(w^2) / sum(w)^2 (3 sigma^2 / n for the Hann window); noise alone reaches A at one of
    M = (top - LOW) n / fps frequencies with chance M exp(-A^2 / 2q), so the strongest of noise passes sqrt(2 q ln(M /
    alpha)) once in 1/alpha (alpha the drift test's 1 in 100), and a beat clears that `complete` of the time from
    z(complete) sqrt(q) beyond it. `floor`, the background apertures' median strongest, adds the stage's other test, ABOVE
    times it. A check beside the planted beats, never in place of them: where the two differ by more than a small factor,
    the noise is far from white and Gaussian (the seismologist's noise distribution says how) or the planting has a fault.
    And how long a clip must be: `seconds_for`, the time a beat of 5, 10 and 20 % of the brightness needs in this noise
    -- with the floor, where one is given, taken as the background's grain, which falls as the root of the frames --
    None past 200 s. {sigma, frames, looks, alpha, complete, amplitude, with_floor, seconds_for}."""
    from scipy.special import ndtri
    n = max(int(n), 3)

    def need(m):
        w = np.hanning(m)
        q = 2 * sigma ** 2 * float((w ** 2).sum()) / float(w.sum()) ** 2
        looks = max(1.0, (top - LOW) * m / fps)
        a = float(np.sqrt(q) * (np.sqrt(2 * np.log(looks / alpha)) + ndtri(complete)))
        return (max(a, ABOVE * floor * np.sqrt(n / m)) if floor is not None else a), a, looks
    with_floor, amp, looks = need(n)
    secs = {}
    for a in (0.05, 0.1, 0.2):
        m = MIN_FRAMES
        while m < 200 * fps and need(m)[0] > a:
            m = int(m * 1.25) + 1
        secs[f"{a:g}"] = round(m / fps, 1) if m < 200 * fps else None
    return dict(sigma=float(sigma), frames=n, looks=round(looks, 1), alpha=float(alpha), complete=float(complete),
                amplitude=amp, with_floor=float(with_floor) if floor is not None else None, seconds_for=secs)


def alias(hz, fps):
    """Where a true frequency `hz` appears once sampled at `fps` frames a second: folded into 0 .. fps/2. A 50-Hz
    lamp's 100-Hz flicker at 30 frames a second is 100 - 3 x 30 = 10 Hz; at 29.97, 10.09."""
    f = abs(hz - round(hz / fps) * fps)
    return float(min(f, fps - f))


def lookalikes(fps, pictures=None, top=None, heard=()):
    """The rhythms a supply, a sensor chain or the sampling itself puts into a brightness curve at this frame rate,
    each where it sits in the band: [{hz, what, source}], sorted by frequency. The mains and aircraft supplies and
    the lamps on them (LOOKALIKES) folded through the frame rate (`alias`); a rhythm locked to every k-th frame
    (LOOKALIKE_EVERY); and, where the video holds pictures (`pictures`: a clip of 10 pictures a second shown at 30),
    the pictures' own cadence and its double; and `heard`, the rhythms the clip's own sound carries, already folded
    (`audio.heard`: a propeller's blade-pass shaking a phone, the supply a lamp is on). Only those between LOW and
    `top` (TOP of the Nyquist frequency if not given). A table, not a verdict: a beat at one of these is marked, not
    refused (item 9)."""
    top = TOP * fps / 2 if top is None else top
    out = []
    for hz, what in LOOKALIKES:
        a = alias(hz, fps)
        if LOW <= a <= top:
            out.append(dict(hz=round(a, 3), what=f"{what}, folded through {fps:.5g} frames a second", source=f"{hz:g} Hz"))
    for k in LOOKALIKE_EVERY:
        if LOW <= fps / k <= top:
            out.append(dict(hz=round(fps / k, 3), what=f"a rhythm locked to every {k}th frame (a codec's anchors, a pulldown, "
                                                     "a display's refresh)", source=f"fps/{k}"))
    rate = (pictures or {}).get("rate")
    if rate and (pictures or {}).get("held", 0) >= HELD_MIN:
        for m, say in ((1, "the held pictures' own cadence"), (2, "twice the held pictures' cadence")):
            a = alias(rate * m, fps)
            if LOW <= a <= top:
                out.append(dict(hz=round(a, 3), what=f"{say} ({rate:.1f} pictures a second)", source="pictures"))
    out += [dict(d) for d in heard if LOW <= d["hz"] <= top]
    for lo_hz, hi_hz, what, name in LOOKALIKE_BANDS:        # item 11: the bands, each where it lands in LOW .. top
        pieces = [(max(a, LOW), min(b, top)) for a, b in fold_band(lo_hz, hi_hz, fps) if b >= LOW and a <= top]
        if not pieces:
            continue
        cover = sum(b - a for a, b in pieces) / max(top - LOW, 1e-9)
        out.append(dict(hz=round((pieces[0][0] + pieces[0][1]) / 2, 3), what=what, source=name,
                        band=[[round(a, 3), round(b, 3)] for a, b in pieces], covers=bool(cover >= WHOLE_BAND)))
    return sorted(out, key=lambda d: d["hz"])


def fold_band(lo, hi, fps):
    """A band of true frequencies lo .. hi Hz as it appears at `fps`: [(a, b)], the folded pieces in 0 .. fps/2, merged
    (`alias` over the band, cut where it turns at each multiple of fps/2). A rotor's 10-30 Hz at 30 frames a second
    covers 0-15 Hz; an aircraft's bus as heard, 398.41-401.27 Hz, lands at 8.41-11.27."""
    half = fps / 2
    edges = [lo] + [k * half for k in range(int(lo // half) + 1, int(hi // half) + 1)] + [hi]
    pieces = sorted((min(alias(a, fps), alias(b, fps)), max(alias(a, fps), alias(b, fps))) for a, b in zip(edges, edges[1:]))
    merged = []
    for a, b in pieces:
        if merged and a <= merged[-1][1] + 1e-9:
            merged[-1] = (merged[-1][0], max(merged[-1][1], b))
        else:
            merged.append((a, b))
    return merged


def at_lookalikes(hz, resolution, table, err=None):
    """The entries of `table` near `hz`: the look-alikes a beat at `hz` is marked with. A rhythm locked to every k-th
    frame (its source "fps/k") has no width, as the codec's line has none, so it is held to the beat's own frequency
    error `err`, within Z_LINE of it (2026-10-17, as the codec's mark is: PR135's member E, 7.90 +- 0.07 Hz, is not at
    the 7.49 Hz of every 4th frame); a supply's line wanders with its supply, and a heard or a held-picture rhythm is
    itself a measurement, so those are held to the `resolution`. A band (item 11) marks a beat inside any of its pieces,
    within the resolution of their edges -- unless it covers the band (`covers`), when it marks nothing."""
    if not hz:
        return []
    def near(d):
        if d.get("band") is not None:
            return not d.get("covers") and any(a - resolution <= hz <= b + resolution for a, b in d["band"])
        return abs(d["hz"] - hz) <= (Z_LINE * err if err is not None and str(d.get("source", "")).startswith("fps/") else resolution)
    return [dict(d) for d in table if near(d)]


def _piece_sse(freqs, tc, Q, y):
    """(residual sum of squares, parameters) of a quadratic Q and a sinusoid at each of `freqs` fitted to y by least
    squares, all at once (the normal equations, one 5 x 5 system a frequency)."""
    w = 2 * np.pi * np.asarray(freqs, float)[:, None] * tc[None, :]
    X = np.concatenate([np.broadcast_to(Q, (len(w),) + Q.shape), np.cos(w)[..., None], np.sin(w)[..., None]], axis=2)
    XtX, Xty = np.einsum("gni,gnj->gij", X, X), np.einsum("gni,n->gi", X, y)
    try:
        beta = np.linalg.solve(XtX, Xty[..., None])[..., 0]
    except np.linalg.LinAlgError:
        beta = np.stack([np.linalg.lstsq(A, v, rcond=None)[0] for A, v in zip(XtX, Xty)])
    return float(y @ y) - np.einsum("gi,gi->g", beta, Xty), beta


def _piece_fit(t, y, fps, f0):
    """One piece of a stretch (item 12): (f, params, residual, bound). The information-theory survey's D2 fit -- a
    sinusoid and a quadratic by least squares, the frequency on a grid of 0.05/T within STEADY_REACH of f0, refined
    within half a resolution of the best of it (bounded: an unbounded peak search in each half lets the planted clocks
    scatter to 0.3-0.6 Hz, and the test has no power) -- and its Cramer-Rao bound in the residual's own level near f."""
    from scipy.optimize import minimize_scalar
    T = float(t.max() - t.min())
    tc = t - t.mean()
    u = tc / (T / 2)
    Q = np.column_stack([np.ones_like(t), u, u * u])
    reach = max(STEADY_REACH[0], STEADY_REACH[1] * f0)
    grid = np.arange(max(LOW, f0 - reach), min(0.95 * fps / 2, f0 + reach), 0.05 / max(T, 1.0))
    if len(grid) < 2:
        grid = np.array([f0])
    sse, _ = _piece_sse(grid, tc, Q, y)
    g = float(grid[int(np.argmin(sse))])
    f = float(minimize_scalar(lambda q: _piece_sse([q], tc, Q, y)[0][0], bounds=(g - 0.5 / T, g + 0.5 / T),
                              method="bounded", options=dict(xatol=1e-6)).x)
    p = _piece_sse([f], tc, Q, y)[1][0]
    X = np.column_stack([Q, np.cos(2 * np.pi * f * tc), np.sin(2 * np.pi * f * tc)])
    resid = y - X @ p
    fr = np.arange(max(0.5, f - 1.5), min(fps / 2, f + 1.5), 0.5 / T)      # the residual's level near f, the beat's own lobe out
    fr = fr[np.abs(fr - f) > 2 / T]
    sigma2 = float(np.mean(np.abs(np.exp(-2j * np.pi * np.outer(fr, t)) @ resid) ** 2 / len(t))) if len(fr) else float(resid.var())
    dfd = 2 * np.pi * tc * (-p[3] * np.sin(2 * np.pi * f * tc) + p[4] * np.cos(2 * np.pi * f * tc))
    J = np.column_stack([X, dfd])
    try:
        bound = float(np.sqrt(np.linalg.inv(J.T @ J / max(sigma2, 1e-300))[-1, -1]))
    except np.linalg.LinAlgError:
        bound = float("inf")
    return f, p, resid, bound


def _split(t, y, fps, f0, pieces):
    """The pieces' frequencies, bounds and how far apart they are in units of them: z = |f1 - f2| / sqrt(c1^2 + c2^2)
    for two halves, the bound-weighted chi-square about their weighted mean for more."""
    fs, cs, fits = [], [], []
    for tt, yy in zip(np.array_split(t, pieces), np.array_split(y, pieces)):
        f, p, resid, c = _piece_fit(tt, yy, fps, f0)
        fs.append(f), cs.append(c), fits.append((p, resid))
    fs, cs = np.array(fs), np.array(cs)
    if not np.all(np.isfinite(cs)) or np.any(cs <= 0):
        return fs, cs, None, fits
    if pieces == 2:
        return fs, cs, float(abs(fs[0] - fs[1]) / np.hypot(*cs)), fits
    w = 1 / cs ** 2
    return fs, cs, float(np.sum(w * (fs - np.sum(w * fs) / np.sum(w)) ** 2)), fits


def steadiness(r, fps, hz, runs=STEADY_RUNS, seed=0):
    """Is the beat at `hz` in the deviation curve r as steady as a clock? (item 12; the information-theory survey's D2.)
    {pieces, hz, bounds, stat, clock_99, p, wanders, wander_share, power, why}. The curve is cut in two halves (pieces of
    STEADY_SEG_S over STEADY_PLAIN_S), each fitted by `_piece_fit`, and the pieces' frequencies compared (`_split`).
    `runs` steady beats -- at `hz`, with each piece's own fitted amplitude (a beat that is weak in one half is planted
    weak there: the survey's trap for this test), a random phase -- are planted in the pieces' own residuals, resampled
    in blocks of BOOT_BLOCK_S end to end round the curve, and read the same way. p is the share of them that come apart
    as far as the beat's pieces did (with the beat counted in, so never under 1/(runs + 1)); `wanders` is p < STEADY_P.
    A rhythm locked to the frames, a supply's line (the buses heard in aircraft sound hold to +-0.01 Hz within a clip)
    and a cooler's drive do not wander; a wingbeat does (2-5 % between halves for the Galileo birds and PR135's six). It
    cannot tell a bird from a governed rotor, whose 1 % is kept, in hertz, by the fold. Where the pieces would be under
    MIN_FRAMES the stretch is too short and nothing is read (power False)."""
    r = np.asarray(r, float)
    n = len(r)
    out = dict(pieces=None, hz=None, bounds=None, stat=None, clock_99=None, p=None, wanders=None, wander_share=None,
               power=False, why=None)
    if not hz or n < 2 * MIN_FRAMES:
        out["why"] = f"too short to split: {n} frames, and each half needs {MIN_FRAMES}"
        return out
    pieces = 2 if n / fps <= STEADY_PLAIN_S else int(n // (STEADY_SEG_S * fps))
    t = np.arange(n) / fps
    fs, cs, stat, fits = _split(t, r, fps, hz, pieces)
    out.update(pieces=pieces, hz=[round(float(f), 4) for f in fs], bounds=[round(float(c), 4) for c in cs],
               wander_share=float(np.ptp(fs) / hz))
    if stat is None:
        out["why"] = "a piece's frequency bound could not be read (no beat in it)"
        return out
    out.update(stat=stat, power=True)
    if not runs:
        out["why"] = "no steady beats planted"
        return out
    split = np.array_split(t, pieces)
    trend = np.concatenate([np.column_stack([np.ones_like(tt), (tt - tt.mean()) / ((tt.max() - tt.min()) / 2),
                                             ((tt - tt.mean()) / ((tt.max() - tt.min()) / 2)) ** 2]) @ p[:3]
                            for tt, (p, _) in zip(split, fits)])
    amp = np.concatenate([np.full(len(tt), np.hypot(p[3], p[4])) for tt, (p, _) in zip(split, fits)])
    e = np.concatenate([resid for _, resid in fits])
    L = min(n, max(2, int(round(BOOT_BLOCK_S * fps))))
    nb = -(-n // L)
    rng = np.random.default_rng(seed)
    clock = []
    for _ in range(runs):
        idx = ((rng.integers(0, n, nb)[:, None] + np.arange(L)[None, :]) % n).ravel()[:n]
        s = _split(t, trend + amp * np.cos(2 * np.pi * hz * t + rng.uniform(0, 2 * np.pi)) + e[idx], fps, hz, pieces)[2]
        clock.append(np.inf if s is None else s)
    clock = np.array(clock)
    p = float((1 + np.sum(clock >= stat)) / (1 + len(clock)))
    out.update(clock_99=float(np.quantile(clock[np.isfinite(clock)], 0.99)) if np.isfinite(clock).any() else None,
               p=p, wanders=bool(p < STEADY_P))
    return out


def _z2(t, freqs, m=BLINK_HARM):
    """Z^2_m of event times `t` (s) at each of `freqs` (Buccheri et al. 1983): 2/n times the summed squared moduli of
    the first m harmonics' phasors. Flashes all at one phase stand at 2 n m; times at random, about 2 m."""
    t = np.asarray(t, float)
    ph = 2 * np.pi * np.asarray(freqs, float)[:, None] * t[..., None, :]          # (..., frequencies, times)
    return 2.0 / t.shape[-1] * sum(np.cos(k * ph).sum(-1) ** 2 + np.sin(k * ph).sum(-1) ** 2 for k in range(1, m + 1))


def flashes(f, fps, floor=0.0):
    """The flashes in a curve, and the curve's scatter: ([(first, last + 1, centroid, height)], sigma), where first and
    last are places in `f`, the centroid (a fractional place) is the run's own brightness-weighted middle, and the height
    is in robust sigmas. The curve is taken against its running median over BLINK_MED_S (a median, not the beat's
    running mean, so a flash of 0.1-0.3 s stands on the level between flashes and not on a mean it has raised); a flash
    is a run standing over BLINK_Z_LO sigma that reaches BLINK_Z, clear of BLINK_EDGE_S at either end; runs closer than
    BLINK_MERGE_S are one (a double flash, or a held picture repeating one). Its time is the run's centroid, not its
    highest frame: a flash with a flat top (a rotating beacon's sweep) puts its highest frame anywhere along the top, and
    the train's timing scatters by as much (V_HELICOPTER_030, 2026-10-20: p 0.026 by the highest frame, 0.001 by the
    centroid). The scatter is held to at least `floor` (LIGHT_FLOOR for a light's curve). (None, 0) for a flat curve -- a
    grey video's reddest pixels, which are all 0."""
    f = np.asarray(f, float)
    ok = np.isfinite(f)
    if ok.sum() < 2 * fps:
        return None, 0.0
    f = np.where(ok, f, np.interp(np.arange(len(f)), np.flatnonzero(ok), f[ok]))
    r = f - ndimage.median_filter(f, int(round(BLINK_MED_S * fps)) | 1, mode="nearest")
    sigma = max(1.4826 * float(np.median(np.abs(r - np.median(r)))), floor)
    if sigma <= 1e-9:
        sigma = float(np.std(r))
    if sigma <= 1e-9:
        return None, 0.0
    z = r / sigma
    e = max(1, int(round(BLINK_EDGE_S * fps)))
    runs, k = [], 0
    while k < len(z):
        if z[k] > BLINK_Z_LO:
            j = k
            while j < len(z) and z[j] > BLINK_Z_LO:
                j += 1
            if z[k:j].max() > BLINK_Z and k >= e and j <= len(z) - e:
                runs.append([k, j])
            k = j
        else:
            k += 1
    merged = []
    for a, b in runs:
        if merged and a - merged[-1][1] < BLINK_MERGE_S * fps:
            merged[-1][1] = b
        else:
            merged.append([a, b])
    out = []
    for a, b in merged:
        w = np.clip(r[a:b], 0, None)
        out.append((a, b, float((np.arange(a, b) * w).sum() / w.sum()), float(z[a:b].max())))
    return out, sigma


def blinks(f, fps, runs=BLINK_RUNS, seed=0, floor=0.0):
    """Does a curve flash in a regular train, as an aircraft's anti-collision light does (item 13)? The flashes
    (`flashes`); their times folded at every rate in BLINK_BAND by Z^2 with BLINK_HARM harmonics; the fold's strongest
    held against `runs` sets of as many times at random over the same span, read the same way (p: the share that fold
    as tightly at any rate there); the rate, the lowest that folds within BLINK_FUND of the strongest (flashes in step at
    1/P are in step at 2/P and 3/P too), refined by a straight line through the flashes' times against their cycle
    numbers (a flash missed counts its cycle), with its error from the line's residuals. A train is BLINK_MIN flashes or
    more at p under BLINK_P. `rule` says where the rate falls: "anti-collision" within BLINK_RULE (40-100 a minute,
    BLINK_TOL either side), "overlap" up to BLINK_OVERLAP (180 a minute, two lights' beams overlapping), else None.
    {read, why, flashes, at (centroids, places in f), runs, height_sigma, width_s, hz, hz_err, per_minute, z2, p,
    train, rule}."""
    f = np.asarray(f, float)
    fl, sigma = flashes(f, fps, floor)
    if fl is None:
        return dict(read=False, why="flat, or under two seconds", flashes=0, train=False)
    out = dict(read=True, why=None, flashes=len(fl), at=[round(c, 2) for _, _, c, _ in fl], runs=[[a, b] for a, b, _, _ in fl],
               height_sigma=round(float(np.median([h for *_, h in fl])), 1) if fl else None,
               width_s=round(float(np.median([(b - a) / fps for a, b, _, _ in fl])), 3) if fl else None,
               hz=None, hz_err=None, per_minute=None, z2=None, p=None, train=False, rule=None)
    if len(fl) < BLINK_MIN:
        out["why"] = f"{len(fl)} flash{'es' if len(fl) != 1 else ''}, under the {BLINK_MIN} a train needs"
        return out
    e = max(1, int(round(BLINK_EDGE_S * fps)))
    T = (len(f) - 2 * e) / fps
    t = (np.array([c for _, _, c, _ in fl]) - e) / fps
    freqs = np.arange(BLINK_BAND[0], BLINK_BAND[1], 0.05 / T)
    zt = _z2(t, freqs)
    j = int(np.argmax(zt))
    tops = [i for i in range(len(zt)) if zt[i] >= BLINK_FUND * zt[j]
            and (i == 0 or zt[i] >= zt[i - 1]) and (i == len(zt) - 1 or zt[i] >= zt[i + 1])]
    f0 = min(tops) if tops else j                        # the fundamental: the lowest rate that folds nearly as tightly
    rng = np.random.default_rng(seed)
    hi, batch = 0, max(1, int(2e6 // (len(freqs) * len(t))))
    for at in range(0, runs, batch):                     # the null, in batches of sets that fit in memory
        R = rng.uniform(0, T, (min(batch, runs - at), len(t)))
        hi += int((_z2(R, freqs).max(-1) >= zt[j]).sum())
    p = (hi + 1) / (runs + 1)
    P = 1 / freqs[f0]
    cyc = np.round((t - t[0]) / P)
    err = None
    if len(np.unique(cyc)) >= 3:
        A = np.vstack([cyc, np.ones_like(cyc)]).T
        sol, *_ = np.linalg.lstsq(A, t, rcond=None)
        res = t - A @ sol
        if sol[0] > 0:
            P = float(sol[0])
            se = np.sqrt((res ** 2).sum() / max(1, len(t) - 2) / ((cyc - cyc.mean()) ** 2).sum())
            err = float(se / P ** 2)
    hz = 1 / P
    lo, top = BLINK_RULE
    rule = ("anti-collision" if lo * (1 - BLINK_TOL) <= hz <= top * (1 + BLINK_TOL) else
            "overlap" if hz <= BLINK_OVERLAP * (1 + BLINK_TOL) else None)
    out.update(hz=round(hz, 4), hz_err=round(err, 4) if err is not None else None, per_minute=round(60 * hz, 1),
               z2=round(float(zt[f0]), 1), p=round(float(p), 4), train=bool(p < BLINK_P), rule=rule if p < BLINK_P else None)
    return out


def deflash(f, runs):
    """The curve with its flashes taken out: each run, a frame either side, filled straight across from the frames
    beyond it -- what a beat keeps without them (`blink_reading`)."""
    f = np.asarray(f, float).copy()
    n = len(f)
    for a, b in runs:
        a, b = max(0, a - 1), min(n, b + 1)
        left, right = (f[a - 1] if a > 0 else f[b] if b < n else f[a]), (f[b] if b < n else f[a - 1] if a > 0 else f[a])
        f[a:b] = np.linspace(left, right, b - a + 2)[1:-1]
    return f


BLINK_CURVES = (("brightness", "brightness"), ("white", "brightest pixels"), ("red", "reddest pixels (a red light)"))


def blink_reading(found, raw, lit, ns, fps, dark=False, black_hot=False):
    """Item 13 on a measurement the stage has judged: does each object flash in a train, in its brightness (`raw`, the
    stage's own curve), its brightest pixels or its reddest (`lit`, `lights`)? The background apertures read the same
    way are the control: one flashing within BLINK_SAME of the object's rate shares its train, which is then the scene's.
    Where the object has its own train and a beat, the beat is read again with the flashes taken out (`deflash`): one that
    keeps under BLINK_KEEP of its amplitude is the flashes' -- a train is a comb in the spectrum, at its rate and every
    multiple -- and is marked with them as a look-alike, as a supply's line is ("marked, not refused"). On a black-hot
    display (`black_hot`) a light is dark: the sum is read the other way up, and `lit` holds the darkest pixels. Writes
    fields["blink"] and the notes; changes no call."""
    F = found.fields
    lit = lit or {}
    tracks = [n for n in (F.get("tracks") or []) if n in raw]
    bgs = [c for c in list(raw) + [c for c in lit if c not in raw] if c.startswith("background")]

    def series(name, which):
        if which == "brightness":
            v = raw.get(name) or []
            measured_dark = dark and not name.startswith("background")             # the sum is of how much darker
            sign = -1.0 if measured_dark != bool(black_hot) else 1.0               # a light is hot: bright, or on a
                                                                                    # black-hot display dark
            return [None if x is None else sign * x for x in v]
        k = 0 if which == "white" else 1
        return [None if q is None or q[k] is None else q[k] for q in lit.get(name) or []]

    def read(name, which):
        v = series(name, which)
        idx = [i for i, x in enumerate(v) if x is not None]
        if len(idx) < 2 * fps:
            return None
        a, b = idx[0], idx[-1] + 1
        r = blinks([np.nan if x is None else x for x in v[a:b]], fps, floor=0.0 if which == "brightness" else LIGHT_FLOOR)
        r["first"], r["last"] = int(ns[a]), int(ns[b - 1])
        if r.get("at"):
            r["frames"] = [round(ns[a] + c, 1) for c in r.pop("at")]
            r["runs"] = [[a + p, a + q] for p, q in r["runs"]]                   # places in ns
        return r

    out = {}
    for name in tracks:
        cur = {which: read(name, which) for which, _ in BLINK_CURVES}
        cur = {k: v for k, v in cur.items() if v is not None}
        trains = [k for k, v in cur.items() if v.get("train")]
        best = min(trains, key=lambda k: (cur[k]["p"], -cur[k]["flashes"])) if trains else None
        rec = dict(curves=cur, best=best, train=bool(best), hz=None, controls=[], controls_read=None, controls_n=len(bgs),
                   shared=False, beat_kept=None, marked=False, black_hot=bool(black_hot))
        if best:
            c = cur[best]
            rec.update(hz=c["hz"], hz_err=c["hz_err"], per_minute=c["per_minute"], p=c["p"], flashes=c["flashes"],
                       frames=c["frames"], rule=c["rule"], width_s=c["width_s"])
            rec["controls_read"] = []                    # the apertures with a curve read, flashing or not: a control off
            for bg in bgs:                               # the frame says nothing (V_030's sit twice its wide disc out)
                for which, _ in BLINK_CURVES:
                    q = read(bg, which)
                    if q is not None and bg not in rec["controls_read"]:
                        rec["controls_read"].append(bg)
                    if q and q.get("train"):
                        rec["controls"].append(dict(aperture=bg, curve=which, hz=q["hz"], p=q["p"], flashes=q["flashes"]))
            rec["shared"] = any(abs(q["hz"] - c["hz"]) <= BLINK_SAME * c["hz"] for q in rec["controls"])
            b = (F.get("beat") or {}).get(name)
            if not rec["shared"] and b and b.get("hz"):
                lo = ns[0]
                a, z = b["first"] - lo, b["last"] - lo + 1
                v = np.array([np.nan if x is None else x for x in (raw.get(name) or [])[a:z]], float)
                ok = np.isfinite(v)
                if ok.sum() >= MIN_FRAMES:
                    v = np.where(ok, v, np.interp(np.arange(len(v)), np.flatnonzero(ok), v[ok]))
                    inside = [[max(0, p - a), min(len(v), q - a)] for p, q in c["runs"] if q > a and p < z]
                    before, after = amp_at(v, fps, b["hz"]), amp_at(deflash(v, inside), fps, b["hz"])
                    rec["beat_kept"] = round(after / before, 3) if before > 0 else None
                    ks = [k for k in range(1, int(2 * fps / c["hz"]) + 2)
                          if abs(alias(k * c["hz"], fps) - b["hz"]) <= max(b.get("resolution_hz") or 0, 0.05) / 2]
                    rec["harmonic"] = ks[0] if ks else None
                    if inside and rec["beat_kept"] is not None and rec["beat_kept"] < BLINK_KEEP:
                        rec["marked"] = True
                        b.setdefault("lookalike", []).append(dict(
                            hz=b["hz"], source="anti-collision light", kept=rec["beat_kept"], harmonic=rec["harmonic"],
                            what=(f"its own flashes, a train at {c['hz']:.2f} Hz ({c['per_minute']:.0f} a minute"
                                  + (", an anti-collision light's rate" if c["rule"] == "anti-collision" else "")
                                  + f"), without which the beat keeps {rec['beat_kept']:.0%} of its amplitude")))
        out[name] = rec
        if best:
            found.notes.append(said_blink(name, rec, len(tracks) > 1, len(bgs)))
    F["blink"] = out
    return out


def said_blink(name, rec, several=False, nbg=0):
    """The note for an object's flash train (item 13)."""
    word = ("hottest pixels (the darkest, on this black-hot display)" if rec.get("black_hot") and rec["best"] == "white"
            else dict(BLINK_CURVES)[rec["best"]])
    who = f" ({name})" if several else ""
    err = f" +- {rec['hz_err']:.2f}" if rec.get("hz_err") is not None else ""
    s = (f"Its {word}{who} {'flashes' if word == 'brightness' else 'flash'} in a regular train: {rec['flashes']} flashes, "
         f"{rec['hz']:.2f}{err} Hz ({rec['per_minute']:.0f} a minute), each about {rec['width_s']:.2f} s; of {BLINK_RUNS} sets of "
         f"as many flashes at random times, {rec['p']:.1%} fold as tightly at any rate from {BLINK_BAND[0]:g} to {BLINK_BAND[1]:g} Hz. ")
    if rec["rule"] == "anti-collision":
        s += ("That is the rate an aircraft's anti-collision light must flash at: 40 to 100 times a minute (14 CFR 25.1401, "
              "27.1401 and 29.1401). ")
    elif rec["rule"] == "overlap":
        s += ("That is faster than one anti-collision light may flash (100 a minute), within the 180 allowed where two "
              "lights' beams overlap. ")
    s += ("A train of short flashes is a comb in the spectrum, at its rate and every multiple of it, so its harmonics reach "
          "through the band a beat is looked for in. ")
    if rec["shared"]:
        s += ("But the background beside it flashes in a train at the same rate ("
              + ", ".join(f"{q['aperture']}, {q['curve']}, {q['hz']:.2f} Hz" for q in rec["controls"]) + "): the train is the scene's, not the object's.")
    elif rec["controls"]:
        s += ("A background aperture flashes too, but at another rate ("
              + ", ".join(f"{q['aperture']}, {q['curve']}, {q['hz']:.2f} Hz" for q in rec["controls"]) + ").")
    elif rec.get("controls_read") is not None and len(rec["controls_read"]) < nbg:
        k = len(rec["controls_read"])
        s += (f"Only {k} of the {nbg} background apertures beside it could be read, and {'it does' if k == 1 else 'none'} not "
              f"flash in a train; the other{'s were' if nbg - k > 1 else ' was'} off the frame, or on it for under 2 s." if k else
              f"None of the {nbg} background apertures beside it could be read (off the frame, or on it for under 2 s), "
              "so nothing here says the train is not the scene's.")
    elif nbg:
        s += f"None of the {nbg} background apertures beside it flashes in a train."
    else:
        s += "No background aperture beside it could be read, so nothing here says the train is not the scene's."
    if rec.get("beat_kept") is not None:
        s += (f" Its beat keeps {rec['beat_kept']:.0%} of its amplitude with the flashes taken out: "
              + ("the beat is the flashes'" + (f" (their {_nth(rec['harmonic'])} multiple, folded through the frame rate)" if rec.get("harmonic") else "")
                 + ", marked as a look-alike, not refused." if rec["marked"] else "the beat is not the flashes'."))
    return s


def lost(f, fps):
    """Where the object is lost against what is behind it -- its brightness over the ring under DROP
    of its own level, or nothing or less: a mask over the curve f. Its level is the running upper
    quartile over WINDOW_S, which a gap of up to three quarters of that does not pull down (a running
    median over a second is pulled down by any gap over half a second, and finds none of it)."""
    f = np.asarray(f, float)
    level = ndimage.percentile_filter(f, 75, size=max(3, int(round(WINDOW_S * fps)) | 1), mode="nearest")
    return (f <= 0) | (f < DROP * level)


def filled(f, mask):
    """The curve f with the frames under `mask` filled across from those either side."""
    f = np.asarray(f, float).copy()
    k = np.arange(len(f))
    if mask.any() and (~mask).sum() >= 2:
        f[mask] = np.interp(k[mask], k[~mask], f[~mask])
    return f


def at_the_troughs(beat, at):
    """The second half of the troughs rule: is the beat the stage found the one whose troughs the lost frames were
    taken for -- within LOST_BAND of the troughs' own frequency (`lost_at_beat`'s `hz`), or its double, where the
    brightness beats twice a stroke? PR097's dots: beats of 6.94, 6.69 and 2.34 Hz at troughs of 7.16, 6.72 and 2.28.
    PR149's objects: 9.16 and 4.84 Hz at troughs of 3.13 and 3.07 -- not theirs, and their frames are lost as before."""
    near = [beat.get("hz"), beat.get("double_hz")]
    return any(v is not None and abs(v - at["hz"]) <= LOST_BAND for v in near)


def runs_of(mask):
    """The runs of True in a mask, as [(first index, one past the last)]: the stretches of frames an object was lost on."""
    mask = np.asarray(mask, bool)
    runs, k = [], 0
    while k < len(mask):
        if mask[k]:
            j = k
            while j < len(mask) and mask[j]:
                j += 1
            runs.append((k, j)); k = j
        else:
            k += 1
    return runs


def lost_at_beat(f, bad, fps, lines=()):
    """Are the frames found lost the troughs of the curve's own beat? PR097's dark dots (2026-10-15): a point that
    beats at 25-60 % of its brightness falls under DROP of its level for a frame or two at every trough, so `lost`
    marked 14-22 % of their frames and the stage refused the clearest beaters in the clip. A crossing (PR23's roof)
    is one run of several frames; a beat's troughs are many short runs, one per cycle, in step with the beat. So:
    LOST_RUNS runs or more whose median length is LOST_RUN frames or shorter (a few longer ones, where two troughs
    merge or the object fades, are allowed), and at least LOST_TROUGH of the lost frames fall in the lower half of
    the curve's own strongest beat. The frequency is read off the curve with the lost frames filled across (the
    curve as it is divides by a level that the troughs pull to nothing); the phase is read off the curve as it is,
    its running mean subtracted and band-passed within LOST_BAND of that frequency so a rate that wanders is
    followed -- filling across the troughs flattens them and loses their phase. Under no relation between the lost
    frames and the beat the share would be 0.5 +- 0.07 for 40-50 frames; PR097's three dark dots read 0.69-0.80.
    This is the first half of the rule, and it suspects rather than decides: on the whole-video pass's 142 refused
    objects it kept 44 whose lost frames came in short runs, of which 39 never beat at all (faint things lost against
    clutter by chance, in short runs). `judge` keeps the frames for good only where the beat it then finds is the one
    the troughs belong to (`at_the_troughs`); PR23's roof crossing and the WA9ONY-5 balloon, 3 runs each, never get
    this far (LOST_RUNS is 6). Returns dict(hz, share, runs, frames) or None."""
    bad = np.asarray(bad, bool)
    if not bad.any():
        return None
    runs = [b - a for a, b in runs_of(bad)]
    if len(runs) < LOST_RUNS or np.median(runs) > LOST_RUN:
        return None
    ff = filled(np.asarray(f, float), bad)
    p = peak(ff, fps, lines)
    if not p or not p.get("hz"):
        return None
    x = np.asarray(f, float)
    x = x - ndimage.uniform_filter1d(x, trend_frames(fps), mode="nearest")   # as it is: the troughs are in it
    X = np.fft.rfft(x - x.mean()); fr = np.fft.rfftfreq(len(x), 1 / fps)
    X[np.abs(fr - p["hz"]) > LOST_BAND] = 0
    bp = np.fft.irfft(X, len(x))                                    # the beat alone, its phase followed along the track
    share = float((bp[bad] < 0).mean())
    if share < LOST_TROUGH:
        return None
    return dict(hz=float(p["hz"]), share=share, runs=len(runs), frames=int(bad.sum()))


def _steps(X, fps):
    """The spectra (complex, padded) of the rows of X -- curves as a share of their level, about 0 -- through
    the steps a curve is taken through (`spectrum`), with the running mean subtracted rather than divided by:
    the same, for a curve that changes by a small share of itself."""
    R = X - ndimage.uniform_filter1d(X, trend_frames(fps), axis=-1, mode="nearest")
    R = R - R.mean(axis=-1, keepdims=True)
    return np.fft.rfft(R * np.hanning(X.shape[-1]), PAD * X.shape[-1], axis=-1)


def _batches(n, runs):
    m = max(1, min(200, int(4e6 // (PAD * n))))            # a long track's padded spectra are big: so many at a time
    return [min(m, runs - i) for i in range(0, runs, m)]


@lru_cache(maxsize=16)
def _units(n, fps):
    """The mean spectra, through those steps, of n frames of a random walk of unit step and of unit white
    grain: what a curve that only wanders, and one that only jitters, give at each frequency."""
    rng, rw, w = np.random.default_rng(1), 0.0, 0.0
    for m in _batches(n, RUNS):
        rw = rw + (np.abs(_steps(np.cumsum(rng.normal(0, 1, (m, n)), axis=1), fps)) ** 2).sum(axis=0)
        w = w + (np.abs(_steps(rng.normal(0, 1, (m, n)), fps)) ** 2).sum(axis=0)
    return rw / RUNS, w / RUNS


def _fit(P, rw, w, nat, rounds=3, iters=12):
    """(a, b) for each row of P: the wander's and the jitter's variance a frame whose spectrum a rw + b w
    is most likely to have given the row's (Whittle's likelihood, by reweighted least squares), at the
    frequencies `nat`, less those that stand CLIP times over the fit -- a peak's, which are not drift."""
    P = P[:, nat]
    X1, X2 = rw[nat][None, :], w[nat][None, :]
    keep = np.ones(P.shape, bool)
    for r in range(rounds + 1):
        E = np.broadcast_to(np.where(keep, P, 0).sum(1, keepdims=True) / np.maximum(keep.sum(1, keepdims=True), 1), P.shape)
        for _ in range(iters):
            W = keep / np.maximum(E, 1e-300) ** 2
            S11, S12, S22 = (W * X1 * X1).sum(1), (W * X1 * X2).sum(1), (W * X2 * X2).sum(1)
            T1, T2 = (W * X1 * P).sum(1), (W * X2 * P).sum(1)
            det = S11 * S22 - S12 ** 2
            a = (S22 * T1 - S12 * T2) / np.where(det > 0, det, np.inf)
            b = (S11 * T2 - S12 * T1) / np.where(det > 0, det, np.inf)
            a, b = (np.where(b < 0, T1 / np.maximum(S11, 1e-300), np.maximum(a, 0)),
                    np.where(a < 0, T2 / np.maximum(S22, 1e-300), np.maximum(b, 0)))
            a, b = np.maximum(a, 0), np.maximum(b, 0)
            E = np.maximum(a[:, None] * X1 + b[:, None] * X2, 1e-300)
        if r < rounds:
            keep = P <= CLIP * E
    return a, b


def drift(f, fps, runs=RUNS, scale=None):
    """The strongest beat of a curve against its own slow change: {over: how far it stands over E, the
    spectrum of the wander and jitter that best account for the curve's (`_fit`), where it is; needed: how
    far BEYOND of `runs` curves made of that wander and jitter stand over theirs, read the same way, each at
    its own strongest; passes; wander, jitter: as shares of the brightness a frame}.

    Fitted to the spectrum rather than read off the curve's frame-to-frame steps, because a beat is in
    those steps too: flyer 5's beat, read as wander, hid its own half. And each of the curves made is read
    as this one was, its own wander and jitter fitted, so that how well 2 s of a curve tell drift from a beat
    is in the answer: read off the steps, or fitted with the strongest left out, 4-10 in 100 curves that only
    wandered passed for one in a hundred. The curves are made the same way every time (one seed), so a curve
    gives one answer. `scale`, as `spectrum`'s: a background aperture is measured in the object's brightness."""
    f = np.asarray(f, float)
    n = len(f)
    fr, F, band, _, _ = spectrum(f, fps, scale)
    P = np.abs(F) ** 2
    rw, w = _units(n, fps)
    nat = np.arange(PAD, int(np.flatnonzero(band)[-1]) + 1, PAD)             # every frequency the curve resolves, past nought
    k = int(np.argmax(np.where(band, P, -1)))
    a, b = (float(v[0]) for v in _fit(P[None, :], rw, w, nat))
    rng, z = np.random.default_rng(0), []
    for m in _batches(n, runs):
        Q = np.abs(np.sqrt(a) * _steps(np.cumsum(rng.normal(0, 1, (m, n)), axis=1), fps)
                   + np.sqrt(b) * _steps(rng.normal(0, 1, (m, n)), fps)) ** 2
        j = np.argmax(np.where(band, Q, -1), axis=1)
        aq, bq = _fit(Q, rw, w, nat)
        z.append(Q[np.arange(m), j] / np.maximum(aq * rw[j] + bq * w[j], np.finfo(float).tiny))
    needed = float(np.quantile(np.concatenate(z), BEYOND))
    over = float(P[k] / max(a * rw[k] + b * w[k], np.finfo(float).tiny))
    return dict(over=over, needed=needed, passes=bool(over >= needed), wander=float(np.sqrt(a)), jitter=float(np.sqrt(b)))


def harmonics(f, fps, scale=None, drift_too=False):
    """The strongest beat of a curve as a fundamental and its double: (fundamental Hz, double Hz or
    None, the share of the strongest that a peak at half its frequency has, the share at double).
    With a peak at half at least HALF of the strongest, the strongest is the double and the
    fundamental the half; else the strongest is the fundamental, and a double is named where a
    peak at twice it has at least HALF of it. Either is a peak of its own: a local maximum in the
    band, further from the strongest than its lobe, and -- with `drift_too` -- standing ALSO times
    over the curve's drift there, fitted (`_fit`) to the rest of the spectrum: the frequencies asked
    about are left out of the fit, or a real half props up the drift it is held against (flyer 5's
    3.9 Hz, 4 times over a fit it was in and 30 over one it was not)."""
    fr, F, band, wsum, _ = spectrum(f, fps, scale)
    P = np.abs(F) ** 2
    k = int(np.argmax(np.where(band, P, -1)))
    n = len(f)
    res = fps / n
    top = np.r_[False, (P[1:-1] >= P[:-2]) & (P[1:-1] >= P[2:]), False]
    if drift_too:
        rw, w = _units(n, fps)
        nat = np.arange(PAD, int(np.flatnonzero(band)[-1]) + 1, PAD)

    def share(hz):
        m = band & top & (np.abs(fr - hz) <= 1.5 * res) & (np.abs(fr - fr[k]) > LOBE * res)
        if m.any() and drift_too:
            a, b = (float(v[0]) for v in _fit(P[None, :], rw, w, nat[np.abs(fr[nat] - hz) > LOBE * res]))
            m &= P >= ALSO * (a * rw + b * w)
        return float(np.sqrt(P[m].max() / P[k])) if m.any() and P[k] > 0 else 0.0
    half, double = share(fr[k] / 2), share(fr[k] * 2)
    if half >= HALF:
        return float(fr[k] / 2), float(fr[k]), half, double
    return float(fr[k]), (float(fr[k] * 2) if double >= HALF else None), half, double


def window_test(f, others, fps, lines, top, scale=None, harmonic=True):
    """One stretch of a curve held to the tests every window is (`windows`), against `others`, the background apertures'
    curves over the same frames: {hz, hz_err, amplitude, stands, resolution_hz, floor, shared, at_the_codec_line_hz,
    codec_by_resolution_hz, over_drift, drift_needed, edge, fundamental_hz, fundamental_err, double_hz, above_top,
    passes, passes_by_resolution}, or None with no background to hold it against. It passes where its strongest is ABOVE
    times the background's (the median of their strongest) and they do not share it, it stands over its own drift, it is
    no band edge, it is under `top`, and it is not at a codec line -- within Z_LINE of its own frequency error (D1,
    2026-10-17). `codec_by_resolution_hz` and `passes_by_resolution` are what the mark within the resolution, the rule
    until then, says of the same window. `harmonic`: name the fundamental (`harmonics`), else the strongest is it."""
    sc = scale if scale else float(np.median(f))
    p = peak(f, fps, lines, scale, err=True)
    floors, shared = [], False
    for g in others:
        floors.append(peak(g, fps, (), sc)["amplitude"])
        fr, F, _, wsum, _ = spectrum(g, fps, sc)
        if 2 * np.abs(F[int(np.argmin(np.abs(fr - p["hz"])))]) / wsum >= SHARED * p["amplitude"]:
            shared = True
    if not floors:
        return None
    floor = float(np.median(floors))
    d = drift(f, fps, scale=scale)
    fund, dbl = harmonics(f, fps, scale, drift_too=True)[:2] if harmonic else (p["hz"], None)
    old = at_line(p["hz"], None, lines, p["resolution_hz"])
    rest = bool(p["amplitude"] >= ABOVE * floor and not shared and d["passes"] and not p["edge"] and p["hz"] <= top)
    return dict(hz=p["hz"], hz_err=p["hz_err"], amplitude=p["amplitude"], stands=p["stands"], resolution_hz=p["resolution_hz"],
                floor=floor, shared=shared, at_the_codec_line_hz=p["at_the_codec_line_hz"], codec_by_resolution_hz=old,
                over_drift=d["over"], drift_needed=d["needed"], edge=p["edge"], fundamental_hz=fund,
                fundamental_err=p["hz_err"] * fund / p["hz"] if p["hz"] else p["hz_err"], double_hz=dbl,
                above_top=bool(p["hz"] > top), passes=bool(rest and p["at_the_codec_line_hz"] is None),
                passes_by_resolution=bool(rest and old is None))


def apart_windows(passing, near=HEADLINE_NEAR):
    """(how many of the passing windows `passing` do not overlap and lie within `near` Hz of one another, the fundamental
    they gather on): the most there are. A beat that comes back along the track, not one stretch read in several
    overlapping windows (the headline rule, 2026-10-17: Jacob's decision 6 of ROADMAP.md, on the gate study's evidence)."""
    best = (0, None)
    for w0 in passing:
        group = sorted((w for w in passing if abs(w["fundamental_hz"] - w0["fundamental_hz"]) <= near), key=lambda w: w["first"])
        n, last = 0, -1
        for w in group:                              # windows are one length: by first frame, the greedy pick is the most
            if w["first"] > last:
                n, last = n + 1, w["last"]
        if n > best[0]:
            best = (n, w0["fundamental_hz"])
    return best


def windows(raw, name, bgs, ns, fps, lines, gone=(), top=None, scale=None):
    """The object's beat in windows of WINDOW_S along the track, each held to the tests the whole
    track is (`window_test`): [{first, last, hz, hz_err, amplitude, stands, resolution_hz, floor, shared,
    at_the_codec_line_hz, codec_by_resolution_hz, over_drift, drift_needed, edge, fundamental_hz, fundamental_err,
    double_hz, above_top, passes, passes_by_resolution}]. Windows where an aperture leaves the
    frame, or that hold a frame where the object was lost (`gone`: indices into the curves), are left out. A window
    passes only below `top` Hz (`pictures`; TOP of the frame rate's Nyquist frequency if not given). With `scale`,
    the curve is a background aperture's, measured in the object's brightness (`controls_judged`)."""
    top = TOP * fps / 2 if top is None else top
    n = len(ns)
    W = max(MIN_FRAMES, int(round(WINDOW_S * fps)))
    step = max(1, W // 8)
    starts = list(range(0, n - W + 1, step))
    if starts and starts[-1] != n - W:
        starts.append(n - W)                                   # the last window too: the flapping may be at the track's end
    out = []
    for s in starts:
        f = raw[name][s:s + W]
        if any(v is None for v in f) or (scale is None and np.median(f) <= 0) or any(s <= k < s + W for k in gone):
            continue
        # the windows keep the stage's own tests under either rule: the bird paper's candidates came from them (the
        # whole-video pass), and its continuum null judged whole tracks; read in 2-s windows, many to a track, the null
        # called 124 more of the pass's 1,157 objects, 97 of them at 1.5-3.5 Hz where the running mean makes bumps
        w = window_test(f, [raw[b][s:s + W] for b in bgs if not any(v is None for v in raw[b][s:s + W])], fps, lines, top, scale)
        if w is not None:
            out.append(dict(first=int(ns[s]), last=int(ns[s + W - 1]), **w))
    return out


_G = {}


def _init(clip, pos, dark, ap=None, thumbs=False, stamps=False, lit=False, litring=None, litpos=None, black_hot=False):
    _G.update(clip=clip, pos=pos, dark=dark, ap=ap or {}, thumbs=thumbs, stamps=stamps, lit=lit, litring=litring or {},
              litpos=litpos or {}, black_hot=black_hot)


def stamp(g, x, y, dark=False, half=STAMP):
    """The frame about (x, y), 2 * half + 1 px square, shifted (bilinear) so that (x, y) is its centre pixel exactly;
    None where it leaves the frame. A dark thing is turned up, so every stamp's contrast is the thing's own. Kept from
    every frame for the fold (`fold`)."""
    H, W = g.shape
    ix, iy = int(np.floor(x)), int(np.floor(y))
    R = half + 2
    if ix - R < 0 or iy - R < 0 or ix + R + 1 > W or iy + R + 1 > H:
        return None
    s = g[iy - R:iy + R + 1, ix - R:ix + R + 1].astype(np.float32)
    s = ndimage.shift(s, (iy - y, ix - x), order=1, mode="nearest")[2:-2, 2:-2]
    return -s if dark else s


def _apertures(job):
    """Frame n's brightness in every aperture, k being its place in the frames the positions are of. An aperture
    sized for a wider thing (`sized`) is re-centred on the thing's own centroid first."""
    k, n = job
    rgb = _G["clip"].rgb(n)
    g = vf.grey_of(rgb)
    out, cut, lit = [], {}, {}
    for name, (x, y) in _G["pos"].items():
        dark = _G["dark"] and not name.startswith("background")
        r, ring, _, recentre = _G["ap"].get(name, (APERTURE, RING, 25, False))
        cx, cy = centred(g, x[k], y[k], r, ring, dark) if recentre else (x[k], y[k])
        out.append(brightness(g, cx, cy, r=r, ring=ring, dark=dark))
        if _G.get("stamps") and not name.startswith("background"):
            cut[name] = stamp(g, cx, cy, dark)
        if _G.get("lit") and not name.startswith("background"):   # its brightest and reddest pixels, for a light (item 13)
            lr = _G["litring"].get(name, ring)
            lit[name] = lights(rgb, g, cx, cy, ring=lr, black_hot=_G.get("black_hot")) if np.isfinite(cx) and np.isfinite(cy) else None
    if _G.get("lit"):                                        # and the same beside it, as far out as its lights reach
        for name, (x, y, lr) in _G["litpos"].items():
            lit[name] = lights(rgb, g, x[k], y[k], ring=lr, black_hot=_G.get("black_hot")) if np.isfinite(x[k]) and np.isfinite(y[k]) else None
    if _G.get("thumbs"):                                     # the picture, small, for `pictures`: is it a new one?
        H, W = (g.shape[0] // THUMB) * THUMB, (g.shape[1] // THUMB) * THUMB
        t = g[:H, :W].reshape(H // THUMB, THUMB, W // THUMB, THUMB).mean((1, 3))
        out.append(np.clip(np.round(t), 0, 255).astype(np.uint8))
        where = {}                                           # and each object's own centroid (`scene_shift`'s own-motion reading)
        for name, (x, y) in _G["pos"].items():
            if name.startswith("background") or not (np.isfinite(x[k]) and np.isfinite(y[k])):
                continue
            r, ring, _, _ = _G["ap"].get(name, (APERTURE, RING, 25, False))
            where[name] = centred(g, x[k], y[k], r, ring, _G["dark"])
        out.append(where)
    if _G.get("stamps"):                                     # the object on this frame, for the fold
        out.append(cut)
    if _G.get("lit"):
        out.append(lit)
    return out


def stacked_extent(greys, x, y, ux=None, uy=None, dark=False):
    """The object's extent (`extent`) read once, off the median of its stamps on the frames `greys` (grey frames),
    centred on (x[i], y[i]) to a fraction of a pixel. Where it moves at SMEAR_MIN px a frame or more (`ux`, `uy`: its
    displacement a frame on each), each stamp is first turned so that its travel points one way, and the size is read
    on the half ahead of it: a trailing smear, or a train of echoes behind a fast point, then does not count, and the
    bands or texture of the scene, which the object crosses, average out in the median. The level it is read against is
    the stack's own just outside the object (`extent`'s `local`). None where nothing stands out of the stack either.
    (radius or None, moving?)"""
    S = int(EXTENT_MAX) + 25
    ax = np.arange(-S, S + 1, dtype=float)
    T, U = np.meshgrid(ax, ax)                       # T along x (the travel, once turned), U across it
    speed = np.hypot(ux, uy) if ux is not None else None
    moving = speed is not None and len(speed) > 0 and float(np.median(speed)) >= SMEAR_MIN
    cuts = []
    for i, g in enumerate(greys):
        if moving and speed[i] > 0:
            c, s_ = ux[i] / speed[i], uy[i] / speed[i]
        else:
            c, s_ = 1.0, 0.0
        X, Y = x[i] + T * c - U * s_, y[i] + T * s_ + U * c
        cuts.append(ndimage.map_coordinates(g.astype(float), [Y, X], order=1, cval=np.nan))
    if not cuts:
        return None, moving
    with np.errstate(all="ignore"):
        stack = np.nanmedian(np.array(cuts), axis=0) if len(cuts) > 1 else cuts[0]
    return extent(stack, float(S), float(S), dark, ahead=(1.0, 0.0) if moving else None, local=True), moving


def _stamp_fits(g, x, y):
    """Whether `extent`'s stamp about (x, y) lies inside the frame g (it reads none where it does not)."""
    H, W = g.shape
    S = int(EXTENT_MAX) + 25
    ix, iy = int(round(x)), int(round(y))
    return ix - S >= 0 and iy - S >= 0 and ix + S + 1 <= W and iy + S + 1 <= H


def sizes(clip, tracks, ns, dark=False, how=None):
    """{name: (extent px or None, sized(extent))}: each track's extent, the median over EXTENT_FRAMES frames spread
    over its span (`extent`), and the aperture that follows from it. Where those frames do not agree -- of the frames
    whose stamp lies inside the picture, fewer than EXTENT_AGREE give a size, or the sizes they give spread wider than
    EXTENT_SPREAD of their median -- the size is read off the stack of those frames instead (`stacked_extent`). Where no
    frame's stamp lies inside the picture (a small frame: the Svanstrom set's 320 x 256), nothing changes: no size, and
    the point's aperture, as before -- on that set reading those off a stack too changed 23 of 432 calls, two bird calls
    lost among them (2026-10-24). With a dict as `how`, what was read is put in it for each track: {frames, fit, read,
    median, spread, used ("frames" or "stack"), stack, along (stacked along its travel?)}."""
    out = {}
    for name, t in tracks.items():
        x, y = smoothed(t, ns)
        have = [k for k, n in enumerate(ns) if min(t) <= n <= max(t)]
        pick = [have[int(i)] for i in np.linspace(0, len(have) - 1, min(EXTENT_FRAMES, len(have)))] if have else []
        greys = [vf.grey_of(clip.rgb(ns[k])) for k in pick]
        each = [extent(g, x[k], y[k], dark) for g, k in zip(greys, pick)]
        fit = [i for i, (g, k) in enumerate(zip(greys, pick)) if _stamp_fits(g, x[k], y[k])]
        rs = [r for r in each if r is not None]
        r = float(np.median(rs)) if rs else None
        spread = float(np.subtract(*np.percentile(rs, [75, 25])) / r) if rs and r else None
        rec = dict(frames=len(pick), fit=len(fit), read=len(rs), median=r, spread=spread, used="frames")
        if fit and (len(rs) < EXTENT_AGREE * len(fit) or (spread is not None and spread > EXTENT_SPREAD)):
            ux, uy = np.gradient(x), np.gradient(y)
            kk = [pick[i] for i in fit]
            r, along = stacked_extent([greys[i] for i in fit], x[kk], y[kk], ux[kk], uy[kk], dark)
            rec.update(used="stack", stack=r, along=along)
        if how is not None:
            how[name] = rec
        out[name] = (r, sized(r))
    return out


def curves(clip, tracks, ns, dark=False, progress=None, stop=None, about=None, procs=None, ap=None, thumbs=None, stamps=None,
           offsets=None, moves=None, lit=None, litring=None, black_hot=False):
    """{name: brightness on each frame of ns} for each track, and for background apertures about
    the track `about` (the first, if not named) -- None where the aperture leaves the frame or a
    mask covers it. `ap` is {track: sized(...)} (`sizes`); without it every aperture is APERTURE, its
    ring RING and the background apertures BACKGROUND, as before. The frames are read on `procs`
    processes (`progress.pooled`; 0: in this one). With a list as `thumbs`, each frame's picture, small, is put in it
    as well (`pictures`), from the same reading of the frame, and with a list as `moves` beside it each track's own
    centroid on the frame, {name: (x, y)} (`centred`; for `scene_shift`); with a dict as `stamps`, each track's stamp of the object
    on each frame (`stamp`), {name: [stamp or None per frame of ns]}, for the fold. `offsets`, [(dx, dy)] in px, puts the
    background apertures there in place of BACKGROUND's (`clear_offsets`), each named by its own offset. With a dict as
    `lit`, each track's light on every frame (`lights`), {name: [(white, red) or None per frame of ns]}, for `blinks`, in
    the disc `litring` gives it ({name: (r, (r, r_out))}; its brightness aperture's ring if not given), and the same at
    four places beside the track `about`, twice as far out as that disc and a little more, named "background light dx,dy".
    `black_hot`: the picture is a black-hot thermal display, where a light is dark (`lights`)."""
    ap = dict(ap or {})
    pos = {name: smoothed(t, ns) for name, t in tracks.items()}
    about = about if about in pos else next(iter(pos))
    first = pos[about]
    r, ring, off, _ = ap.get(about, (APERTURE, RING, 25, False))
    if offsets is None:                                  # named by the default offsets whatever the size, so the CSV keeps its columns
        where = [((dx, dy), (dx * off / 25, dy * off / 25)) for dx, dy in BACKGROUND]
    else:
        where = [((int(round(dx)), int(round(dy))), (dx, dy)) for dx, dy in offsets]
    for (nx, ny), (dx, dy) in where:
        name = f"background {nx:+d},{ny:+d}"
        pos[name] = (first[0] + dx, first[1] + dy)
        ap[name] = (r, ring, off, False)
    litring = dict(litring or {})
    litpos = {}
    if lit is not None:                                  # the light's controls: the object's own disc, far enough out to miss it
        lr = litring.get(about, (ring[0], ring))[1] if about in litring else ring
        far = max(off, 2 * lr[1] + 6)
        for dx, dy in BACKGROUND:
            u, v = int(round(dx * far / 25)), int(round(dy * far / 25))
            litpos[f"background light {u:+d},{v:+d}"] = (first[0] + u, first[1] + v, lr)
        litring = {name: r[1] for name, r in litring.items()}
    out = {name: [] for name in pos}
    for got in pooled(procs, _apertures, list(enumerate(ns)), _init, (clip, pos, dark, ap, thumbs is not None, stamps is not None,
                                                                    lit is not None, litring, litpos, black_hot),
                      8, progress, stop, "Flicker", pixels=clip.W * clip.H):
        for name, v in zip(pos, got[:len(pos)]):
            out[name].append(v)
        extra = list(got[len(pos):])
        if thumbs is not None:
            thumbs.append(extra.pop(0))
            where = extra.pop(0)
            if moves is not None:
                moves.append(where)
        if stamps is not None:
            cut = extra.pop(0)
            for name in tracks:
                stamps.setdefault(name, []).append(cut.get(name))
        if lit is not None:
            got_lit = extra.pop(0)
            for name in list(tracks) + list(litpos):
                lit.setdefault(name, []).append(got_lit.get(name))
    return out


def pictures(thumbs, fps):
    """How many new pictures a second the frames carry: {rate, held (share of frames), top_hz}. A held frame repeats the
    picture before it (HELD of the typical change between pictures); `top_hz` is the highest frequency a beat is
    heard at, TOP of the Nyquist frequency of the frame rate or, where pictures are held, of the picture rate; `held_k`,
    which frames (their places in the frames read) repeat the one before -- missing samples to the Lomb-Scargle
    periodogram (`ls_peak`), however few.

    Known to misread two chains (2026-10-20): an encoder that skips a still sky (IPPP; the Svanström set, a fresh
    picture every frame) makes fresh pictures look held (0.10-0.18 of frames), and one that re-encodes held pictures
    afresh (the Galileo Sphere chain, 0.59 held) makes them look new (0.50). Read instead by the object's own motion, or
    with it, it lost PURSUE's real holds (PR149's 0.22 read as none: a contact at 21 px a frame leaves its centroid's
    reach on a held frame); held frames' spacing does not tell the two apart either (PR149 and the Svanström bird both
    0.58 in their two commonest intervals). On PURSUE the whole frame reads PR149, PR44 and PR135 to their truth."""
    d = np.array([np.mean(np.abs(a.astype(np.int16) - b.astype(np.int16))) for a, b in zip(thumbs[:-1], thumbs[1:])])
    if len(d) < 2:
        return dict(rate=fps, held=0.0, top_hz=TOP * fps / 2, held_k=[])
    typical = float(np.percentile(d, 80))                    # a change between pictures while under 80% of frames are held
    held_k = [int(i) + 1 for i in np.flatnonzero(d < HELD * typical)] if typical > 0 else []
    held = float(np.mean(d < HELD * typical)) if typical > 0 else 0.0
    rate = fps * (1 - held) if held >= HELD_MIN else fps
    return dict(rate=float(rate), held=held, top_hz=float(TOP * rate / 2), held_k=held_k)

def common(raw, seg, members, ns, fps, lines=()):
    """Whether members beat as one, over the frames each pair has in common (a flock's members come and go --
    PR135, 2026-10-08 -- so each pair is taken over its own overlap, MIN_FRAMES or more): pairs, each at its own
    peak there with its frequency's error (`hz_error`), with the phase between them at the cross-spectrum's peak -- and
    `independent`: two whose frequencies differ by more than `z_needed` of their combined errors (`apart_z`; Z_APART over
    all the pairs judged, `z_apart`), or at one frequency more than APART_DEG out of step. Until 2026-10-17 they had to
    differ by more than the resolution, 1/T over their common frames (`resolution_hz`): PR135's members over 4.5 s are
    known to 0.02-0.03 Hz, and three pairs 0.15-0.20 Hz apart were called one frequency."""
    pairs = []
    for a in range(len(members)):
        for b in range(a + 1, len(members)):
            ma, mb = members[a], members[b]
            lo, hi = max(seg[ma][0], seg[mb][0]), min(seg[ma][1], seg[mb][1])
            if hi - lo < MIN_FRAMES:
                continue
            fa, fb = raw[ma][lo:hi], raw[mb][lo:hi]
            if any(v is None for v in fa) or any(v is None for v in fb):
                continue
            pa, pb = peak(fa, fps, lines, err=True), peak(fb, fps, lines, err=True)
            fr, Fa, band, _, _ = spectrum(fa, fps)
            _, Fb, _, _, _ = spectrum(fb, fps)
            X = Fa * np.conj(Fb)
            k = int(np.argmax(np.where(band, np.abs(X), -1)))
            apart = abs(pa["hz"] - pb["hz"])
            phase = float(np.degrees(np.angle(X[k])))
            pairs.append(dict(members=[ma, mb], hz=[pa["hz"], pb["hz"]], hz_err=[pa["hz_err"], pb["hz_err"]],
                              frames=[int(ns[lo]), int(ns[hi - 1])], apart_hz=apart,
                              apart_z=float(apart / np.hypot(pa["hz_err"], pb["hz_err"])), resolution_hz=float(fps / (hi - lo)),
                              cross_hz=float(fr[k]), phase_deg=phase))
    need = z_apart(len(pairs))
    for q in pairs:
        q.update(z_needed=need, independent=bool(q["apart_z"] > need or abs(q["phase_deg"]) > APART_DEG))
    return pairs


# ---- the astronomer's tests (item 7; 2026-10-15) -------------------------------------------------------------
def lombscargle(t, y, freqs):
    """The generalised (floating-mean) Lomb-Scargle periodogram of y sampled at t, at `freqs` (Hz): the share of
    y's variance a sinusoid at each frequency, with its own mean, accounts for -- the "standard" normalisation, 0 to 1
    (Zechmeister & Kuerster 2009; VanderPlas 2018, sec. 6). Built for samples that are not evenly spaced: a frame left
    out is a missing sample, not a sample. Every sample weighs alike."""
    t, y, freqs = np.asarray(t, float), np.asarray(y, float), np.asarray(freqs, float)
    n = len(t)
    out = np.zeros(len(freqs))
    if n < 4:
        return out
    y = y - y.mean()
    yy = float((y * y).sum()) / n
    if yy <= 0:
        return out
    step = max(1, int(2e6 // n))                            # so many frequencies at a time: the cos/sin matrix is step x n
    for a in range(0, len(freqs), step):
        ph = 2 * np.pi * freqs[a:a + step, None] * t[None, :]
        c, s = np.cos(ph), np.sin(ph)
        C, S = c.mean(1), s.mean(1)
        YC, YS = (c * y).mean(1), (s * y).mean(1)
        CC, SS, CS = (c * c).mean(1) - C * C, (s * s).mean(1) - S * S, (c * s).mean(1) - C * S
        D = CC * SS - CS * CS
        ok = D > 1e-9 * np.maximum(CC * SS, np.finfo(float).tiny)
        num = SS * YC ** 2 + CC * YS ** 2 - 2 * CS * YC * YS
        out[a:a + step] = np.where(ok, num / (yy * np.where(ok, D, 1.0)), 0.0)
    return np.clip(out, 0.0, 1.0)


def window(t, freqs):
    """The spectral window of the sampling t: |sum exp(2 pi i f t)|^2 / N^2 -- 1 at nought and at every rhythm of
    the sampling (every third frame kept: 1 at fps/3), small between. A peak of the periodogram at one of its lines is
    the sampling's, as a beat at the codec's line is the codec's."""
    t, freqs = np.asarray(t, float), np.asarray(freqs, float)
    n = len(t)
    out = np.zeros(len(freqs))
    if n == 0:
        return out
    step = max(1, int(2e6 // n))
    for a in range(0, len(freqs), step):
        ph = 2 * np.pi * freqs[a:a + step, None] * t[None, :]
        out[a:a + step] = (np.cos(ph).sum(1) ** 2 + np.sin(ph).sum(1) ** 2) / n ** 2
    return out


def fap_baluev(z, t, fmin, fmax):
    """The false-alarm probability of the strongest Lomb-Scargle peak, of power z (standard normalisation), found between
    fmin and fmax Hz on samples at t: how often noise alone makes one as high somewhere in that band. Baluev 2008's
    alias-free bound (his eq. 6; VanderPlas 2018 sec. 7.4.2), as astropy computes it, with the band's width where
    astropy takes the whole range from nought."""
    from scipy.special import gammaln
    t = np.asarray(t, float)
    N = len(t)
    if N < 5 or z <= 0 or fmax <= fmin:
        return 1.0
    NH, NK = N - 1, N - 3
    W = (fmax - fmin) * np.sqrt(4 * np.pi * np.var(t))
    z = min(float(z), 1 - 1e-12)
    gam = np.sqrt(2 / NH) * np.exp(gammaln(NH / 2) - gammaln((NH - 1) / 2))
    tau = gam * W * (1 - z) ** (0.5 * (NK - 1)) * np.sqrt(0.5 * NH * z)
    cdf = 1 - (1 - z) ** (0.5 * NK)
    return float(np.clip(1 - cdf * np.exp(-tau), 0.0, 1.0))


def ls_peak(r, fps, keep=None, top=None):
    """The strongest beat of a deviation curve by the Lomb-Scargle periodogram over the frames `keep` (a held picture,
    or a frame the object was lost on, is a missing sample, not a sample), between LOW and `top` Hz: {hz, power, fap,
    kept, dropped, resolution_hz, window_lines_hz, window_at_peak, at_a_window_line}. The sampling's own rhythms are
    read off its spectral window (`window`) up to the frame rate's Nyquist frequency, above WINDOW_LINE; a peak within
    the resolution of one is an alias of the sampling. On every frame of an even cadence there are none, and the peak
    sits where the Hann-windowed spectrum's does; the probability is what the spectrum alone cannot give."""
    r = np.asarray(r, float)
    n = len(r)
    keep = np.ones(n, bool) if keep is None else np.asarray(keep, bool)
    t = np.arange(n) / fps
    tk, yk = t[keep], r[keep]
    fmax = min(0.95 * fps / 2, top) if top else 0.95 * fps / 2
    df = fps / (PAD * n)
    nothing = dict(hz=None, power=None, fap=None, kept=int(len(tk)), dropped=int(n - len(tk)), resolution_hz=None,
                   window_lines_hz=[], window_at_peak=None, at_a_window_line=None)
    if len(tk) < 8 or fmax <= LOW + 2 * df:
        return nothing
    freqs = np.arange(LOW, fmax, df)
    P = lombscargle(tk, yk, freqs)
    k = int(np.argmax(P))
    span = float(tk[-1] - tk[0])
    res = 1 / span if span > 0 else fps / n
    wf = np.arange(df, 0.95 * fps / 2, df)
    Wn = window(tk, wf)
    tops = np.r_[False, (Wn[1:-1] >= Wn[:-2]) & (Wn[1:-1] > Wn[2:]), False] & (Wn >= WINDOW_LINE) & (wf > 2 * res)
    lines = [float(v) for v in wf[tops]]
    return dict(hz=float(freqs[k]), power=float(P[k]), fap=fap_baluev(P[k], tk, LOW, fmax), kept=int(len(tk)),
                dropped=int(n - len(tk)), resolution_hz=float(res), window_lines_hz=lines,
                window_at_peak=float(window(tk, [freqs[k]])[0]),
                at_a_window_line=bool(any(abs(freqs[k] - L) <= res for L in lines)))


def _over_powerlaw(fr, A, keep):
    """Each row of the amplitude spectra A over the power law fitted to it on the frequencies `keep`, a straight line in
    log amplitude against log frequency by least squares: a spectrum against its own red continuum."""
    X = np.log(fr[keep])
    xc = X - X.mean()
    Y = np.log(A[:, keep] + 1e-12)
    slope = ((Y - Y.mean(axis=1, keepdims=True)) * xc).sum(axis=1) / float(xc @ xc)
    icpt = Y.mean(axis=1) - slope * X.mean()
    lf = np.log(np.maximum(fr, fr[1] if len(fr) > 1 else 1.0))
    return A / np.exp(icpt[:, None] + slope[:, None] * lf[None, :])


def continuum(r, fps, top=None, runs=CONTINUUM_RUNS, exclude=CONTINUUM_EXCLUDE, seed=0):
    """The paper's continuum null (the bird sweep's review of 2026-10-14/15, `beat_stability.py`, which judged every
    object of its Table 1 by it): the strongest peak of a deviation curve between LOW and `top` Hz, as a ratio to a
    power law fitted to the amplitude spectrum over that band with `exclude` Hz either side of the peak left out,
    held against `runs` curves of Gaussian noise shaped to the same continuum -- a power law fitted to the curve's own
    Fourier amplitudes, the curve's length and spread, and no line -- each read the same way, at its own strongest
    anywhere in the band, so that the look elsewhere is in the answer. {hz, ratio, needed95, needed99, p, runs}: `p`
    is the share of the noise curves whose largest ratio stands as high as the peak's. Known birds stand far over it
    (the review: PR41's 15.1 and PR44's 18.4 against a 99 % level of about 4.4); PR102's 3.4 against 4.5 did not. A
    red continuum -- grain, a gain's wander, the codec's noise -- is what it holds a peak against; what it cannot know
    is a slow change the running mean turns into a bump near 1/DETREND_S (the drift test's trap): the noise curves
    are not taken through the running mean. The same curves every time (one seed)."""
    r = np.asarray(r, float)
    n = len(r)
    hi = min(top or 0.95 * fps / 2, 0.95 * fps / 2)
    nothing = dict(hz=None, ratio=None, needed95=None, needed99=None, p=None, runs=runs)
    if n < 16 or hi <= LOW:
        return nothing
    w = np.hanning(n)
    Z = PAD * n
    fr = np.fft.rfftfreq(Z, 1 / fps)
    band = (fr >= LOW) & (fr <= hi)
    A = 2 * np.abs(np.fft.rfft((r - r.mean()) * w, Z)) / w.sum()
    k = int(np.flatnonzero(band)[np.argmax(A[band])])
    f0 = float(fr[k])
    keep = band & (np.abs(fr - f0) > exclude)
    if keep.sum() < 4:
        return nothing
    r0 = float(_over_powerlaw(fr, A[None, :], keep)[0, k])
    fx = np.fft.rfftfreq(n, 1 / fps)
    Xr = np.abs(np.fft.rfft(r - r.mean()))
    kk = (fx >= LOW) & (fx <= hi) & (np.abs(fx - f0) > exclude)
    if kk.sum() < 3:
        return nothing
    pc = np.polyfit(np.log(fx[kk]), np.log(Xr[kk] + 1e-12), 1)
    shape = np.exp(np.polyval(pc, np.log(np.maximum(fx, fx[1]))))
    rng, mx = np.random.default_rng(seed), []
    sd = float(r.std()) or 1.0
    for m in _batches(n, runs):
        Zs = shape[None, :] * (rng.normal(size=(m, len(fx))) + 1j * rng.normal(size=(m, len(fx))))
        y = np.fft.irfft(Zs, n, axis=1)
        y *= sd / np.maximum(y.std(axis=1, keepdims=True), 1e-12)
        Ay = 2 * np.abs(np.fft.rfft((y - y.mean(axis=1, keepdims=True)) * w[None, :], Z, axis=1)) / w.sum()
        mx.append(_over_powerlaw(fr, Ay, keep)[:, band].max(axis=1))
    mx = np.concatenate(mx)
    return dict(hz=f0, ratio=r0, needed95=float(np.percentile(mx, 95)), needed99=float(np.percentile(mx, 99)),
                p=float(np.mean(mx >= r0)), runs=int(runs))


def amp_at(f, fps, hz, scale=None):
    """A curve's amplitude at `hz` -- a share of its brightness, or of `scale` -- read off its spectrum at the nearest
    frequency: what the background beside an object does at the object's own beat."""
    fr, F, _, wsum, _ = spectrum(f, fps, scale)
    return float(2 * np.abs(F[int(np.argmin(np.abs(fr - hz)))]) / wsum)


def whole_passes(f, p, fps, top, others, floor, scale=None, oscale=None, d=None, bg_at=None):
    """Does a whole curve's strongest beat pass the whole-track tests of RULE, against the curves beside it? `f` is the
    curve (its brightness on each frame, in `scale` if a background aperture's), `p` its `peak`, `others` the background
    apertures' curves over the same frames (in `oscale`), `floor` the median of their strongest, `d` its `drift` if
    already read. (passes, what was read). Under either rule a peak at the band's edge or above `top` does not pass.
    "stage": its amplitude ABOVE times `floor`, and the drift test. "paper" (the bird paper's Table 1, ROADMAP.md 0.3):
    the continuum null under CONTINUUM_P (`continuum`), and its amplitude ABOVE times the background apertures' median
    amplitude at its own frequency -- the background must not beat there, not merely be quiet everywhere: a scene full
    of texture lifts the strongest of every aperture beside a point that beats well clear of it (PR085, 2026-10-16).
    `bg_at(hz)`, where given, is that median read off the background apertures' own spectra, each over its own stretch
    -- an aperture that leaves the frame before the object does has no value on the object's last frames (PR141's
    infrared half, 2026-10-16: its amplitude there came out as nothing, and the beat was refused)."""
    if p["edge"] or p["hz"] > top:
        return False, {}
    if active_rule() == "paper":
        cn = continuum(deviation(f, fps, scale), fps, top=top)
        if cn["p"] is None:
            return False, dict(continuum_p=None)
        if bg_at is not None:
            bg = bg_at(cn["hz"])
        else:
            at0 = [amp_at(o, fps, cn["hz"], oscale) for o in others if not any(v is None for v in o)]
            bg = float(np.median(at0)) if at0 else float("inf")
        return bool(cn["p"] <= CONTINUUM_P and p["amplitude"] >= ABOVE * bg), dict(
            continuum_p=cn["p"], continuum_ratio=cn["ratio"], continuum_needed99=cn["needed99"], background_at_beat=bg)
    d = d or drift(f, fps, scale=scale)
    return bool(p["amplitude"] >= ABOVE * floor and d["passes"]), dict(over_drift=d["over"], drift_needed=d["needed"])


def scrambled(r, fps, top=None, runs=SCRAMBLES, chunk_s=SCRAMBLE_S, seed=0):
    """The curve's strongest beat held against copies of itself scrambled in chunks of `chunk_s` (surrogate data,
    Theiler et al. 1992, in the form Kepler's vetting used, Thompson et al. 2018): a chunk keeps the grain, the codec's
    quantisation and the jitter from one frame to the next, and the chunks' order destroys every rhythm slower than a
    chunk. So the share of copies whose strongest stands as high over the band as the curve's does (`stands`, as
    `peak` reads it) is the chance of a peak that high from the grain alone: {p, stands, needed (the 99th centile of
    theirs), runs, chunk_s, valid_above_hz}. It says nothing of frequencies under 1/chunk_s, where the scrambling also
    destroys the slow wander the drift test is for. The same copies every time (one seed)."""
    r = np.asarray(r, float)
    n = len(r)
    L = max(2, int(round(chunk_s * fps)))
    fr, F, band, _, _ = _spec(r, fps)
    if top:
        band = band & (fr <= top)
    if band.sum() < 2:
        return dict(p=None, stands=None, needed=None, runs=0, chunk_s=L / fps, valid_above_hz=fps / L)
    P = np.abs(F) ** 2
    obs = float(P[band].max() / np.median(P[band]))
    chunks = [np.arange(a, min(a + L, n)) for a in range(0, n, L)]
    rng, w, z = np.random.default_rng(seed), np.hanning(n), []
    for m in _batches(n, runs):
        X = np.stack([r[np.concatenate([chunks[j] for j in rng.permutation(len(chunks))])] for _ in range(m)])
        Q = np.abs(np.fft.rfft(X * w, PAD * n, axis=-1)[:, band]) ** 2
        z.append(Q.max(1) / np.maximum(np.median(Q, axis=1), np.finfo(float).tiny))
    z = np.concatenate(z)
    return dict(p=float((np.sum(z >= obs) + 1) / (len(z) + 1)), stands=obs, needed=float(np.quantile(z, 0.99)),
                runs=int(len(z)), chunk_s=L / fps, valid_above_hz=fps / L)


def common_mode(r, R, k=COMMON_K, scene=None):
    """The object's deviation curve r less what the whole frame does: the scene's level and contrast (`scene`: rows
    over the same frames, each a deviation curve -- the mean and the spread of the frame, small, from `thumbs`), and
    what the background apertures' curves R (rows) share -- their common mode, the first k components of the
    standardised rows (SysRem, Tamuz et al. 2005, and TFA, Kovacs et al. 2005, with every aperture weighted alike,
    which is a principal-component fit) -- regressed out of r with a constant. The gain a camera changes, or a
    display's brightness as a phone films it, scales the whole frame: its contrast follows the gain exactly, where an
    aperture's contrast over its ring follows it by whatever that contrast happens to be, in either sign, as the aperture
    crosses the scene -- which is why the scene's own curves come first. A beat the background does not have loses
    about (k + 2)/n of its variance to chance alignment and no more. Returns (the residual, {components, r2: the share
    of r's variance all of it accounts for, r2_scene: the scene's level and contrast alone, share_of_controls: the share
    of the apertures' variance the components hold, mode: the first component, over the frames})."""
    r, R = np.asarray(r, float), np.asarray(R, float)
    n = len(r)
    k = int(max(0, min(k, R.shape[0] if R.ndim == 2 else 0, n // 10)))
    S = np.asarray(scene, float) if scene is not None and len(scene) else np.zeros((0, n))
    if (k == 0 and not len(S)) or (k and R.shape[1] != n) or (len(S) and S.shape[1] != n):
        return r.copy(), dict(components=0, r2=0.0, r2_scene=0.0, share_of_controls=0.0, mode=None)
    var = float(r.var())

    def fit(X):
        beta, *_ = np.linalg.lstsq(np.c_[np.ones(n), X.T], r, rcond=None)
        return r - np.c_[np.ones(n), X.T] @ beta

    def stand(Z):
        Z = Z - Z.mean(1, keepdims=True)
        sd = Z.std(1, keepdims=True)
        return Z / np.where(sd > 0, sd, 1.0)
    rows = [stand(S)] if len(S) else []
    r2_scene = float(max(0.0, 1 - fit(rows[0]).var() / var)) if rows and var > 0 else 0.0
    s, mode, share = np.zeros(0), None, 0.0
    if k:
        Z = stand(R)
        _, s, Vt = np.linalg.svd(Z, full_matrices=False)
        rows.append(Vt[:k])
        mode, tot = Vt[0], float((s ** 2).sum())
        share = float((s[:k] ** 2).sum() / tot) if tot > 0 else 0.0
    resid = fit(np.vstack(rows))
    return resid, dict(components=k, r2=float(max(0.0, 1 - resid.var() / var)) if var > 0 else 0.0, r2_scene=r2_scene,
                       share_of_controls=share, mode=mode)


def pixel_phase(r, x, y):
    """The share of a deviation curve that follows where within its pixel the object sits -- the pixel phase, dx = x -
    round(x) and dy likewise, to second order (Spitzer's intra-pixel decorrelation, Knutson et al. 2008; Deming et al.
    2015's pixel-level form): (the residual curve, r2). The disc aperture's sub-pixel weights (trap 1) should leave
    nothing here; this measures what they left. For a point: a wider thing's aperture is re-centred on its own
    centroid, which these positions are not."""
    r, x, y = (np.asarray(v, float) for v in (r, x, y))
    dx, dy = x - np.round(x), y - np.round(y)
    X = np.c_[np.ones(len(r)), dx, dy, dx * dx, dy * dy, dx * dy]
    beta, *_ = np.linalg.lstsq(X, r, rcond=None)
    resid = r - X @ beta
    var = float(r.var())
    return resid, (float(max(0.0, 1 - resid.var() / var)) if var > 0 else 0.0)


def passes_astro(A):
    """Whether a track's astronomer's tests allow its beat (GATE_ASTRO): a Lomb-Scargle false-alarm probability under
    FAP_MAX, a peak that is not a line of the sampling, and under P_MAX of its scrambled copies as high -- where the
    scramble can speak (above 1/SCRAMBLE_S)."""
    ls, sc = A.get("lombscargle") or {}, A.get("scramble") or {}
    if ls.get("fap") is not None and ls["fap"] > FAP_MAX:
        return False
    if ls.get("at_a_window_line"):
        return False
    if sc.get("p") is not None and sc["p"] > P_MAX and (ls.get("hz") or 0) >= sc["valid_above_hz"]:
        return False
    return True


def disagreements(strong, astro, far):
    """Where the astronomer's tests disagree with a beat the stage called: sentences for the notes, or none."""
    off = []
    for n in strong:
        A = astro.get(n) or {}
        ls, sc, cm = A.get("lombscargle") or {}, A.get("scramble") or {}, A.get("common_mode")
        if ls.get("fap") is not None and ls["fap"] > FAP_MAX:
            off.append(f"{n}: the Lomb-Scargle false-alarm probability of its peak is {ls['fap']:.2g}")
        if ls.get("at_a_window_line"):
            off.append(f"{n}: its peak, {ls['hz']:.2f} Hz, is at a rhythm of the sampling")
        if sc.get("p") is not None and sc["p"] > P_MAX and (ls.get("hz") or 0) >= sc["valid_above_hz"]:
            off.append(f"{n}: {sc['p']:.2f} of its chunk-scrambled copies stand as high")
        if cm and cm.get("r2", 0) >= 0.5 and cm.get("after_amplitude", 0) < 0.5 * (cm.get("before_amplitude") or 0):
            off.append(f"{n}: the scene's own change and the background apertures' common mode account for {cm['r2']:.0%} of its "
                       "curve and halve its beat")
    if far and far["whole"][0]:
        off.append(f"{far['whole'][0]} of {far['whole'][1]} background apertures pass the object's own tests themselves")
    return off


def controls_judged(use, seg, bgs, ns, fps, lines, scale, top, gone=(), windows_too=False):
    """Each background aperture put through the object's own tests, as if it were the object -- held against the others
    -- so that what passes is a false alarm by construction (the Robovetter's inverted and scrambled runs, Thompson et
    al. 2018: data known to hold no signal, through the whole pipeline): ({name: {passes, hz, amplitude, over_drift,
    drift_needed, windows_passing, windows}}, {whole: [passing, judged], windows: [passing, all]}). The windows take
    as long again as the object's did, and are run only with `windows_too`."""
    out, whole, wins = {}, [0, 0], [0, 0]
    gone = list(gone)
    for b in bgs:
        others = [c for c in bgs if c != b and c in seg]
        if not others or b not in seg:
            continue
        s0, s1 = seg[b]
        f = use[b][s0:s1]
        if any(v is None for v in f) or s1 - s0 < MIN_FRAMES:
            continue
        amps = [peak(use[c][s0:s1], fps, (), scale)["amplitude"] for c in others if not any(v is None for v in use[c][s0:s1])]
        if not amps:
            continue
        floor = float(np.median(amps))
        p = peak(f, fps, lines, scale)
        d = drift(f, fps, scale=scale)
        ok, read = whole_passes(f, p, fps, top, [use[c][s0:s1] for c in others if not any(v is None for v in use[c][s0:s1])],
                                floor, scale, scale, d)
        ok = bool(ok and p["at_the_codec_line_hz"] is None)
        row = dict(passes=ok, hz=p["hz"], amplitude=p["amplitude"], over_drift=d["over"], drift_needed=d["needed"],
                   windows_passing=None, windows=None, **{k: v for k, v in read.items() if k not in ("over_drift", "drift_needed")})
        if windows_too:
            own = {m: use[m][s0:s1] for m in [b] + others}
            W = windows(own, b, others, ns[s0:s1], fps, lines, gone=[k - s0 for k in gone if s0 <= k < s1], top=top, scale=scale)
            kw = sum(1 for w in W if w["passes"])
            row.update(windows_passing=kw, windows=len(W))
            wins[0] += kw
            wins[1] += len(W)
        out[b] = row
        whole[0] += int(ok)
        whole[1] += 1
    return out, dict(whole=whole, windows=wins)


def injected(use, seg, bgs, fps, lines, scale, top, amplitudes=INJECT_AMPL, n_hz=INJECT_N, seed=0):
    """Beats planted in the background apertures' curves -- which have the frames, the grain, the codec and the camera,
    and no object -- at `amplitudes` (shares of the object's brightness) and n_hz frequencies across the band, each put
    through the whole track's tests as the object is (injection and recovery: Christiansen et al. 2013, for Kepler):
    {amplitudes, hz, recovered: [[the share of trials, by amplitude then frequency]], trials, frames, complete_from: the
    smallest amplitude recovered in three trials of four or more at every frequency, or None; analytic: the same in
    closed form from the apertures' own noise (`analytic`), the check on it}. A beat is recovered where the curve passes,
    its strongest is within two resolutions of the frequency planted and not at a codec line. On at most INJECT_MAX
    frames of each aperture, the middle of its stretch. Until 2026-10-17 a frequency within two resolutions of a codec
    line was moved three away from it, so the slice beside the line was never measured; `sliced` plants there now."""
    fmax = min(top, 0.95 * fps / 2)
    hzs = [float(v) for v in np.linspace(LOW + 1.0, fmax - 1.0, n_hz)] if fmax - LOW > 3.0 else []
    rng = np.random.default_rng(seed)
    rec = np.zeros((len(amplitudes), len(hzs)))
    trials, frames, noise, floors = 0, None, [], []
    for b in bgs:
        others = [c for c in bgs if c != b and c in seg]
        if not others or b not in seg or not hzs:
            continue
        s0, s1 = seg[b]
        if s1 - s0 > INJECT_MAX:
            mid = (s0 + s1) // 2
            s0, s1 = mid - INJECT_MAX // 2, mid - INJECT_MAX // 2 + INJECT_MAX
        if s1 - s0 < MIN_FRAMES or any(v is None for v in use[b][s0:s1]):
            continue
        amps = [peak(use[c][s0:s1], fps, (), scale)["amplitude"] for c in others if not any(v is None for v in use[c][s0:s1])]
        if not amps:
            continue
        floor = float(np.median(amps))
        f = np.asarray(use[b][s0:s1], float)
        frames = len(f)
        t = np.arange(len(f)) / fps
        res = fps / len(f)
        noise.append(float(deviation(f, fps, scale).std()))
        floors.append(floor)
        trials += 1
        for i, a in enumerate(amplitudes):
            for j, hz in enumerate(hzs):
                g = f + a * scale * np.sin(2 * np.pi * hz * t + rng.uniform(0, 2 * np.pi))
                p = peak(g, fps, lines, scale)
                if p["at_the_codec_line_hz"] is not None or abs(p["hz"] - hz) > 2 * res:
                    continue
                if active_rule() == "stage" and p["amplitude"] < ABOVE * floor:
                    continue                                 # the cheap test first: the drift's bootstrap is the slow one
                if whole_passes(g, p, fps, top, [use[c][s0:s1] for c in others if not any(v is None for v in use[c][s0:s1])],
                                floor, scale, scale)[0]:
                    rec[i, j] += 1
    if trials:
        rec /= trials
    complete = next((float(a) for i, a in enumerate(amplitudes) if (rec[i] >= COMPLETE).all()), None) if trials and hzs else None
    return dict(amplitudes=[float(a) for a in amplitudes], hz=[round(h, 3) for h in hzs], recovered=rec.round(3).tolist(),
                trials=trials, frames=frames, complete_from=complete,
                analytic=analytic(float(np.median(noise)), frames, fps, top, floor=float(np.median(floors))) if trials else None)


def sliced(use, seg, bgs, fps, lines, scale, top, offsets=SLICE_HZ, amplitudes=SLICE_AMPL, seed=0):
    """Beats planted where the codec's rhythm is (2026-10-17; the information-theory survey's D1 and D6, ROADMAP.md 0.3
    objective 2): in one window of WINDOW_S of each background aperture -- the middle of its stretch, which has the
    frames, the grain, the codec and the camera and no object -- `offsets` Hz either side of each codec line between
    LOW and `top`, at `amplitudes` (shares of the object's brightness), each put through a window's tests as the object's
    windows are (`window_test`). Until then a window's peak within the resolution of a line, 0.5 Hz on 2 s, never
    passed, and the planted beats were moved off the line, so this slice's completeness was never measured:
    `by_resolution` is what that rule recovers of the same beats. The last offset, 1 Hz, lies outside the slice it
    blinded: the control the slice's recovery is read against. A beat is recovered where the window passes with its
    strongest within a resolution of the frequency planted. {lines_hz, offsets_hz, amplitudes, recovered,
    by_resolution: [[the share of plantings, by amplitude then offset]], trials, frames, analytic: in closed form from
    the windows' own noise (`analytic`)}, or None with no codec line in the band."""
    W = max(MIN_FRAMES, int(round(WINDOW_S * fps)))
    Ls = [float(L) for L in lines if LOW + max(offsets) <= L <= min(top, 0.95 * fps / 2) - max(offsets)]
    if not Ls:
        return None
    rng = np.random.default_rng(seed)
    rec, old, tried = (np.zeros((len(amplitudes), len(offsets))) for _ in range(3))
    trials, noise, floors = 0, [], []
    t, res = np.arange(W) / fps, fps / W
    for b in bgs:
        others = [c for c in bgs if c != b and c in seg]
        if not others or b not in seg or seg[b][1] - seg[b][0] < W:
            continue
        a0 = (seg[b][0] + seg[b][1]) // 2 - W // 2
        f = use[b][a0:a0 + W]
        oth = [use[c][a0:a0 + W] for c in others if not any(v is None for v in use[c][a0:a0 + W])]
        if any(v is None for v in f) or not oth:
            continue
        f = np.asarray(f, float)
        noise.append(float(deviation(f, fps, scale).std()))
        floors.append(float(np.median([peak(g, fps, (), scale)["amplitude"] for g in oth])))
        trials += 1
        for i, a in enumerate(amplitudes):
            for j, o in enumerate(offsets):
                for L in Ls:
                    for hz in (L - o, L + o):
                        w = window_test(f + a * scale * np.sin(2 * np.pi * hz * t + rng.uniform(0, 2 * np.pi)), oth, fps, lines,
                                        top, scale, harmonic=False)
                        if w is None:
                            continue
                        found = abs(w["hz"] - hz) <= res
                        tried[i, j] += 1
                        rec[i, j] += bool(w["passes"] and found)
                        old[i, j] += bool(w["passes_by_resolution"] and found)
    if not trials:
        return None
    share = lambda x: (x / np.maximum(tried, 1)).round(3).tolist()
    return dict(lines_hz=Ls, offsets_hz=[float(o) for o in offsets], amplitudes=[float(a) for a in amplitudes],
                recovered=share(rec), by_resolution=share(old), trials=trials, frames=W,
                analytic=analytic(float(np.median(noise)), W, fps, top, floor=float(np.median(floors))))


def scene_curves(thumbs, positions, lo, hi, fps, ap=APERTURE):
    """The frame's level and contrast -- the mean and the spread of each frame, small (`thumbs`, THUMB px to one), with
    every tracked thing masked out of it (a box about each `positions` entry, the aperture and 8 px about, so that a
    bright point's own beat is not read as the scene's) -- over the places lo..hi of the frames, each as a deviation
    curve (`deviation`): rows for `common_mode`'s `scene`. None where the thumbs do not cover the stretch."""
    if not thumbs or len(thumbs) < hi or any(thumbs[k] is None for k in range(lo, hi)):
        return None
    level, spread = [], []
    for k in range(lo, hi):
        t = np.asarray(thumbs[k], float)
        m = np.ones(t.shape, bool)
        for x, y in (positions or {}).values():
            if k < len(x):
                cx, cy, h = x[k] / THUMB, y[k] / THUMB, (ap + 8) / THUMB + 1
                y0, y1 = int(max(0, np.floor(cy - h))), int(min(t.shape[0], np.ceil(cy + h) + 1))
                x0, x1 = int(max(0, np.floor(cx - h))), int(min(t.shape[1], np.ceil(cx + h) + 1))
                m[y0:y1, x0:x1] = False
        if m.sum() < 16:
            return None
        level.append(float(t[m].mean()))
        spread.append(float(t[m].std()))
    return np.stack([deviation(level, fps), deviation(spread, fps)])


SHIFT_PLANT = 0.05   # px: a sinusoidal shift of the whole picture planted at each beat, the scene-shift reading's own test
SHIFT_TEXTURE = 0.5  # band-passed gradient energy a pixel (grey levels squared) under which the scene has nothing to register
SHIFT_PAN = 0.3      # px a frame: a scene that moves more than this is registered frame to frame, else against its mean
SHIFT_MASK = 30      # px round every tracked thing, kept out of the scene
SHIFT_STANDS = 10.0  # the scene moves at a beat where its shift there stands this many times over the band's median
_S = {}


def _bandpass(g):
    return ndimage.gaussian_filter(g, 1.0) - ndimage.gaussian_filter(g, 6.0)


def _fshift(g, dy, dx):
    """g moved by (dy, dx) px, sub-pixel, by the Fourier shift theorem: the planted test's warp, and the iteration's."""
    H, W = g.shape
    ky, kx = np.fft.fftfreq(H)[:, None], np.fft.rfftfreq(W)[None, :]
    return np.fft.irfft2(np.fft.rfft2(g) * np.exp(-2j * np.pi * (ky * dy + kx * dx)), s=g.shape).astype(np.float32)


def lk_shift(a, b, mask, iters=3):
    """(dy, dx, texture) taking band-passed frame a onto band-passed frame b: one translation of the whole picture, by
    least squares on a's gradient over `mask` (Lucas-Kanade), iterated with a Fourier warp of b. No correlation peak,
    so no pull toward whole pixels and no lock onto an infrared sensor's fixed pattern (phase correlation did both, on
    PR135, 2026-10-19). `texture`: the masked gradient energy a pixel."""
    gy, gx = np.gradient(a)
    m = mask > 0
    Ayy, Axx, Axy = float((gy[m] ** 2).sum()), float((gx[m] ** 2).sum()), float((gx[m] * gy[m]).sum())
    det = Ayy * Axx - Axy ** 2
    if not m.any() or det <= 0:
        return float("nan"), float("nan"), 0.0
    d = np.zeros(2)
    for _ in range(iters):
        it = ((_fshift(b, -d[0], -d[1]) if d.any() else b) - a)[m]
        by, bx = -float((gy[m] * it).sum()), -float((gx[m] * it).sum())
        d += np.array([(Axx * by - Axy * bx) / det, (Ayy * bx - Axy * by) / det])
    return float(d[0]), float(d[1]), float((Ayy + Axx) / m.sum())


def _shift_mask(k):
    """The scene's mask on the k-th frame of the stretch: not the burned-in graphics, not within SHIFT_MASK of any track."""
    m = _S["scene"].copy()
    for x, y in _S["pos"]:
        if np.isfinite(x[k]) and np.isfinite(y[k]):
            ix, iy = int(x[k]), int(y[k])
            m[max(0, iy - SHIFT_MASK):iy + SHIFT_MASK, max(0, ix - SHIFT_MASK):ix + SHIFT_MASK] = 0
    return m


def _shift_sums(job):
    """The sum and the sum of squares of a run of frames' grey: for the stretch's mean frame and the still pixels."""
    s = s2 = None
    for n in job:
        g = vf.grey_of(_S["clip"].rgb(n)).astype(np.float64)
        s, s2 = (g, g * g) if s is None else (s + g, s2 + g * g)
    return s, s2, len(job)


def _shift_job(k):
    """Frame k of the stretch registered -- against the mean frame, or against the frame before where the scene pans --
    as it is and with SHIFT_PLANT planted at each beat: [(dy, dx), texture, [(dy, dx) planted, a beat]]."""
    ns, fps, hz = _S["ns"], _S["fps"], _S["hz"]
    grey = lambda n: vf.grey_of(_S["clip"].rgb(n)).astype(np.float32)
    g = grey(ns[k])
    m = _shift_mask(k)
    if _S["pan"]:
        if k == 0:
            return None
        g0 = grey(ns[k - 1])
        ref = _bandpass(g0)
        plant0 = [_bandpass(_fshift(g0, SHIFT_PLANT * np.sin(2 * np.pi * h * (k - 1) / fps), 0.0)) for h in hz]
    else:
        ref, plant0 = _S["ref"], [_S["ref"]] * len(hz)
    dy, dx, tex = lk_shift(ref, _bandpass(g), m)
    planted = [lk_shift(r0, _bandpass(_fshift(g, SHIFT_PLANT * np.sin(2 * np.pi * h * k / fps), 0.0)), m)[:2]
               for h, r0 in zip(hz, plant0)]
    return (dy, dx), tex, planted


def _shift_init(clip, ns, pos, fps, hz, scene, ref, pan):
    _S.update(clip=clip, ns=ns, pos=pos, fps=fps, hz=hz, scene=scene, ref=ref, pan=pan)


def _at_beat(series, hz, fps):
    """(amplitude, stands): a series about its 0.5-s running mean, at hz (within one resolution), over the band's median."""
    s = np.asarray(series, float)
    ok = np.isfinite(s)
    if ok.sum() < MIN_FRAMES:
        return None, None
    s = np.interp(np.arange(len(s)), np.flatnonzero(ok), s[ok])
    d = s - ndimage.uniform_filter1d(s, trend_frames(fps), mode="nearest")
    fr, F, band, wsum, _ = _spec(d - d.mean(), fps)
    P = np.abs(F) ** 2
    near = band & (np.abs(fr - hz) <= fps / len(d))
    if not near.any():
        return None, None
    k = np.flatnonzero(near)[int(np.argmax(P[near]))]
    return float(2 * np.abs(F[k]) / wsum), float(P[k] / np.median(P[band]))


def scene_shift(clip, ns, tracks, beats, moves=None, procs=None, progress=None, stop=None):
    """Does the sensor's own motion -- a cryocooler's drive, a gimbal's servo -- sit at a beat? (`--scene-shift`,
    2026-10-20; the bird paper's chain-rate table.) A jitter moves the whole picture, the object with it, and turns into
    brightness through the aperture and the pixel grid; the Svanström set's airplanes that "beat like a bird" at 2-3.5 Hz
    were tracked by a pan-and-tilt platform. Over the frames ns: the burned-in graphics (pixels that do not change) and
    every track (SHIFT_MASK) are masked; each band-passed frame is registered against the stretch's mean frame (which
    takes out an infrared sensor's fixed pattern) or, where the scene pans (over SHIFT_PAN a frame), against the frame
    before, the shifts summed (`lk_shift`); the shift's amplitude at each beat and how it stands are read, and the same
    with SHIFT_PLANT px planted at that beat in every frame -- its recovery is the reading's sensitivity, the scene and
    its fixed pattern moved together, so an upper bound on it. Beside it, each object's own centroid at its beat
    (`moves`, as `curves` collects them). `beats` is {name: hz}. {name: {...}}, and {"scene": {...}} for the frames."""
    pos = [smoothed(t, ns) for t in tracks.values()]
    n = len(ns)
    hz = [float(h) for h in beats.values()]
    runs = [ns[i:i + 25] for i in range(0, n, 25)]
    _shift_init(clip, ns, pos, clip.fps, hz, None, None, False)
    got = pooled(procs, _shift_sums, runs, _shift_init, (clip, ns, pos, clip.fps, hz, None, None, False), 1, progress, stop,
                 "Scene shift: the mean frame", pixels=clip.W * clip.H)
    s = sum(g[0] for g in got)
    s2 = sum(g[1] for g in got)
    k = sum(g[2] for g in got)
    mean = (s / k).astype(np.float32)
    scene = (np.sqrt(np.maximum(s2 / k - (s / k) ** 2, 0)) >= 1.0).astype(np.float32)   # the graphics hold still: out
    ref = _bandpass(mean)
    probe = list(range(1, n, max(1, n // 20)))[:20]          # pan or hold? a few pairs, frame to frame
    _shift_init(clip, ns, pos, clip.fps, [], scene, ref, True)
    steps = [np.hypot(*_shift_job(i)[0]) for i in probe]
    pan = bool(np.nanmedian(steps) > SHIFT_PAN) if steps else False
    init = (clip, ns, pos, clip.fps, hz, scene, ref, pan)
    rows = pooled(procs, _shift_job, list(range(n)), _shift_init, init, 4, progress, stop, "Scene shift", pixels=clip.W * clip.H)
    rows = [r for r in rows if r is not None]
    d = np.array([r[0] for r in rows], float)
    tex = float(np.nanmedian([r[1] for r in rows])) if rows else 0.0
    path = np.nancumsum(d, axis=0) if pan else d
    out = {"scene": dict(frames=[int(ns[0]), int(ns[-1])], registered="frame to frame" if pan else "against the mean frame",
                         step_px=float(np.nanmedian(steps)) if steps else None, texture=tex, power=bool(tex >= SHIFT_TEXTURE),
                         why=None if tex >= SHIFT_TEXTURE else f"no texture to register (gradient energy {tex:.2f})")}
    for j, (name, h) in enumerate(beats.items()):
        a = [_at_beat(path[:, c], h, clip.fps) for c in (0, 1)]
        amp, stands = max(a, key=lambda q: q[1] or 0)
        p = np.array([r[2][j] for r in rows], float)
        pp = np.nancumsum(p, axis=0) if pan else p
        rec = max((_at_beat(pp[:, c], h, clip.fps)[0] or 0) for c in (0, 1)) / SHIFT_PLANT
        wob = None
        if moves:
            xy = np.array([m.get(name, (np.nan, np.nan)) for m in moves], float)
            wob = max((_at_beat(xy[:, c], h, clip.fps)[0] or 0) for c in (0, 1)) if len(xy) >= MIN_FRAMES else None
        out[name] = dict(hz=h, at_beat_px=amp, stands=stands, planted_px=SHIFT_PLANT, recovered=rec, own_px=wob,
                         moves=bool(out["scene"]["power"] and stands is not None and stands >= SHIFT_STANDS))
    return out


def shift_said(sh):
    """The note for `scene_shift`'s reading: does the sensor's own motion sit at the beat?"""
    sc = sh.get("scene") or {}
    if not sc.get("power"):
        return (f"The scene's own motion at the beat was not read: {sc.get('why')}. A cooler's or a gimbal's jitter is "
                "neither seen nor excluded.")
    parts = []
    for name, r in sh.items():
        if name == "scene" or r.get("at_beat_px") is None:
            continue
        own = f"; its own centroid moves {r['own_px']:.3f} px there" if r.get("own_px") is not None else ""
        parts.append(f"{name} at {r['hz']:.2f} Hz: the scene moves {r['at_beat_px']:.4f} px (standing {r['stands']:.0f} times "
                     f"over its band), a planted {r['planted_px']:g} px came back at {r['recovered']:.2f} of itself{own} -- "
                     + ("the sensor moves at the beat: a jitter may make it" if r["moves"] else "no jitter of the sensor there"))
    return (f"The scene's own motion at the beat (registered {sc['registered']}, frames {sc['frames'][0]}-{sc['frames'][1]}): "
            + "; ".join(parts) + ". The sensor's fixed pattern does not move with a jitter and pulls the reading toward "
            "nothing by its share of the picture's detail, which is not measured.")


def ap_of(fields, name):
    """The aperture radius a track was measured with (fields["aperture_px"]: one number before 2026-10-10, since then one a track)."""
    a = fields.get("aperture_px")
    return float(a.get(name, APERTURE)) if isinstance(a, dict) else float(a or APERTURE)


def rotor_said(rot):
    """The words for a rotor's look (item 14): which of the two the beat shows, with its number."""
    bits = []
    if "background" in rot.get("marked", ()):
        bits.append(f"its beat reaches the background beside it in step (coherence {rot['coherence']:.2f} with {rot['background']})")
    if "off its middle" in rot.get("marked", ()):
        bits.append(f"the light that beats sits {rot['offset_px']:.1f} px off its middle")
    return " and ".join(bits) + ", as a helicopter's rotor does"


def fold(r, hz, fps, stamps, thumbs=None, ap=APERTURE, at=None, controls=()):
    """The frames folded on the beat (epoch folding, as pulsar data is read; and Kepler's difference image, Bryson et
    al. 2013): the deviation curve r in FOLD_BINS bins of the beat's cycle, the brightest bin's half of the cycle
    against the other half, and the mean picture of the object over the bright half less that over the dim half --
    where in the picture the brightness that beats is. A beat of the object's folds into the object's pixels; the
    codec's rhythm into blocks over the frame; a change of gain into the whole scene; a neighbour's beat beside it.
    `stamps` are the object's stamps (`stamp`) for the frames of r, `thumbs` the frames small (`_apertures`; THUMB px
    to one), `at` the object's place and reach in a thumb (x, y, half-width, half-height), `controls` the background
    apertures' deviation curves over the same frames. Returns ({hz, bins, bright_frames, dim_frames, amplitude,
    controls_amplitude, in_aperture_share, area_share, concentration, offset_px, object_peak, scene_rms, at}, (the
    bright stamp, the dim stamp, their difference, the whole frame's difference)) -- the pictures None where there
    were too few stamps."""
    r = np.asarray(r, float)
    n = len(r)
    ph = (np.arange(n) / fps * hz) % 1.0
    b = np.minimum((ph * FOLD_BINS).astype(int), FOLD_BINS - 1)
    bins = [float(r[b == i].mean()) if (b == i).any() else 0.0 for i in range(FOLD_BINS)]
    ph0 = (int(np.argmax(bins)) + 0.5) / FOLD_BINS
    dist = np.abs(((ph - ph0 + 0.5) % 1.0) - 0.5)
    bright, dim = dist < 0.25, dist >= 0.25
    out = dict(hz=float(hz), bins=bins, bright_frames=int(bright.sum()), dim_frames=int(dim.sum()), amplitude=None,
               controls_amplitude=None, in_aperture_share=None, area_share=None, concentration=None, offset_px=None,
               object_peak=None, scene_rms=None, at=[float(v) for v in at] if at else None)
    pics = (None, None, None, None)
    if bright.sum() < 2 or dim.sum() < 2:
        return out, pics
    out["amplitude"] = float(0.5 * (r[bright].mean() - r[dim].mean()))
    cs = [np.asarray(c, float) for c in controls if len(c) == n]
    if cs:
        out["controls_amplitude"] = float(np.median([0.5 * (c[bright].mean() - c[dim].mean()) for c in cs]))
    ok = np.array([s is not None for s in stamps]) if stamps is not None and len(stamps) == n else np.zeros(n, bool)
    if (ok & bright).sum() >= 2 and (ok & dim).sum() >= 2:
        A = np.stack([np.asarray(stamps[k], float) for k in range(n) if ok[k]])
        S = A.shape[-1] // 2
        yy, xx = np.mgrid[-S:S + 1, -S:S + 1]
        rr = np.hypot(xx, yy)
        ring = (rr >= min(ap + 3, S - 2)) & (rr <= S)
        A = A - np.median(A[:, ring], axis=1)[:, None, None]      # each stamp's contrast over its own ring
        mb, md = A[bright[ok]].mean(0), A[dim[ok]].mean(0)
        diff = mb - md
        inside = rr <= ap
        tot = float(np.abs(diff).sum())
        share = float(np.abs(diff)[inside].sum() / tot) if tot > 0 else 0.0
        area = float(inside.mean())
        sm = ndimage.gaussian_filter(diff, 1.0)
        near = np.abs(sm) * (rr <= 2 * ap)                       # the change's centroid within twice the aperture: a clipped
        cx, cy = (float((near * xx).sum() / near.sum()), float((near * yy).sum() / near.sum())) if near.sum() > 0 else (0.0, 0.0)
        out.update(in_aperture_share=share, area_share=area, concentration=float(share / area) if area > 0 else None,
                   offset_px=float(np.hypot(cx, cy)), object_peak=float(sm[S, S]))   # core beats as a ring about the object
        pics = (mb, md, diff, None)
    if thumbs is not None and len(thumbs) == n and all(t is not None for t in thumbs):
        T = np.stack([np.asarray(t, float) for t in thumbs])
        scene = T[bright].mean(0) - T[dim].mean(0)
        mask = np.ones(scene.shape, bool)
        if at:
            x0, y0, hw, hh = at
            ys, xs = np.mgrid[0:scene.shape[0], 0:scene.shape[1]]
            mask &= ~((np.abs(xs - x0) <= hw) & (np.abs(ys - y0) <= hh))
        if mask.sum() > 16:
            out["scene_rms"] = float(np.sqrt(np.mean(scene[mask] ** 2)))
        pics = (pics[0], pics[1], pics[2], scene)
    return out, pics


def said_astro(fields):
    """What `mcdonald flicker` prints of the astronomer's tests, from the fields."""
    L = []
    for name, A in (fields.get("astro") or {}).items():
        ls, sc, cm, pp = A.get("lombscargle") or {}, A.get("scramble") or {}, A.get("common_mode"), A.get("pixel_phase")
        if ls.get("hz") is not None:
            L.append(f"  {name}, over frames {A['frames'][0]}-{A['frames'][1]}, Lomb-Scargle on {ls['kept']} frames" + (f" ({ls['dropped']} held or lost, left out)" if ls["dropped"] else "")
                     + f": {ls['hz']:.2f} Hz, power {ls['power']:.2f}, false-alarm probability {ls['fap']:.1e}"
                     + (f"; the sampling's own rhythm at {', '.join(f'{v:.1f}' for v in ls['window_lines_hz'])} Hz" if ls["window_lines_hz"] else "")
                     + (" -- the peak is at it" if ls.get("at_a_window_line") else ""))
        if sc.get("p") is not None:
            L.append(f"  {name}, scrambled in {sc['chunk_s']:.2f}-s chunks: {sc['p']:.3f} of {sc['runs']} copies stand as high "
                     f"({sc['stands']:.0f}x the band; {sc['needed']:.0f}x would be 1 in 100), said above {sc['valid_above_hz']:.1f} Hz")
        if cm:
            L.append(f"  {name}, the scene's level and contrast and the background's common mode ({cm['components']} components) account "
                     f"for {cm['r2']:.0%} of its curve (the scene alone {cm.get('r2_scene', 0):.0%}); "
                     f"without them {cm['after_hz']:.2f} Hz, {cm['after_amplitude']:.1%} (before {cm['before_amplitude']:.1%})"
                     + (f"; the mode itself peaks at {cm['mode_hz']:.2f} Hz" + (" -- the codec's" if cm.get("mode_at_the_codec_line_hz") else "")
                        if cm.get("mode_hz") is not None else ""))
        if pp:
            L.append(f"  {name}, the pixel phase accounts for {pp['r2']:.0%} of its curve; without it {pp['after_hz']:.2f} Hz, {pp['after_amplitude']:.1%}")
    far = fields.get("false_alarm")
    if far and far["whole"][1]:
        L.append(f"  the background apertures through the object's own tests: {far['whole'][0]} of {far['whole'][1]} beat over the whole track"
                 + (f", {far['windows'][0]} of {far['windows'][1]} of their windows" if far["windows"][1] else ""))
    inj = fields.get("injection")
    if inj and inj.get("trials"):
        an = inj.get("analytic") or {}
        L.append(f"  beats planted in the background apertures ({inj['trials']} apertures, {inj['frames']} frames, at "
                 + ", ".join(f"{h:.1f}" for h in inj["hz"]) + " Hz), recovered: "
                 + "; ".join(f"{a:.0%} of the brightness in {np.mean(row):.0%} of trials" for a, row in zip(inj["amplitudes"], inj["recovered"]))
                 + (f" -- complete from {inj['complete_from']:.0%}" if inj.get("complete_from") is not None else " -- none at every frequency")
                 + (f"; in closed form, from their noise, {an['with_floor']:.1%}" if an.get("with_floor") is not None else ""))
    sl = fields.get("slice")
    if sl and sl.get("trials"):
        an = sl.get("analytic") or {}
        L.append(f"  beats planted beside the codec's {', '.join(f'{v:g}' for v in sl['lines_hz'])} Hz in a {WINDOW_S:g}-s window of each "
                 f"background aperture ({sl['trials']}), recovered at "
                 + ", ".join(f"{o:g}" for o in sl["offsets_hz"]) + " Hz either side: "
                 + "; ".join(f"{a:.0%} of the brightness " + "/".join(f"{v:.0%}" for v in row)
                             + " (by the mark at the resolution " + "/".join(f"{v:.0%}" for v in old) + ")"
                             for a, row, old in zip(sl["amplitudes"], sl["recovered"], sl["by_resolution"]))
                 + (f"; in closed form, from their noise, {an['with_floor']:.1%}" if an.get("with_floor") is not None else ""))
    for name, fo in (fields.get("fold") or {}).items():
        if fo.get("amplitude") is None:
            continue
        L.append(f"  {name}, folded on {fo['hz']:.2f} Hz: bright half over dim {fo['amplitude']:.1%}"
                 + (f" (the background beside it {fo['controls_amplitude']:.1%})" if fo.get("controls_amplitude") is not None else "")
                 + (f"; the difference picture holds {fo['in_aperture_share']:.0%} of its change within the aperture, "
                    f"{fo['concentration']:.1f}x the aperture's share of it, peaking {fo['offset_px']:.1f} px off the object"
                    if fo.get("concentration") is not None else "")
                 + (f"; the rest of the frame changes {fo['scene_rms']:.2f} levels rms" if fo.get("scene_rms") is not None else ""))
    return L


# ---- the seismologist's tests (item 8; 2026-10-15) -----------------------------------------------------------
def tapers(n, nw=MT_NW):
    """Slepian tapers for n samples at time-bandwidth nw (Thomson 1982): (K x n, their eigenvalues), K = 2 nw - 1."""
    from scipy.signal.windows import dpss
    K = max(2, int(round(2 * nw - 1)))
    v, lam = dpss(n, nw, Kmax=K, return_ratios=True)
    return np.asarray(v, float), np.asarray(lam, float)


def multitaper(r, fps, nw=MT_NW):
    """The multitaper spectrum of a deviation curve (Thomson 1982; brought to seismograms by Park, Lindberg & Vernon
    1987): K Slepian tapers, each an independent look at the record, their spectra averaged by eigenvalue -- and the
    **harmonic F-test** at every frequency: how much of the K tapered spectra one sinusoid there accounts for, against
    what is left, F with 2 and 2K-2 degrees of freedom under a continuum smooth over the tapers' bandwidth, grain and
    drift alike (the null the drift test builds by a thousand curves, had in closed form). {fr, S, F, p, amplitude (the
    sinusoid's, as a share of the brightness), Y (the eigencoefficients, K x frequencies), K, bandwidth_hz}, on the
    PAD-fold grid the rest of the stage uses."""
    from scipy.stats import f as fdist
    r = np.asarray(r, float)
    n = len(r)
    v, lam = tapers(n, nw)
    K = v.shape[0]
    Y = np.fft.rfft(v * r[None, :], PAD * n, axis=-1)
    fr = np.fft.rfftfreq(PAD * n, 1 / fps)
    S = (lam[:, None] * np.abs(Y) ** 2).sum(0) / lam.sum()
    U = v.sum(1)                                            # each taper's weight at nought: nought itself for the odd ones
    UU = float((U ** 2).sum())
    mu = (U[:, None] * Y).sum(0) / UU                       # half the sinusoid's complex amplitude at each frequency
    resid = (np.abs(Y - U[:, None] * mu[None, :]) ** 2).sum(0)
    F = (K - 1) * np.abs(mu) ** 2 * UU / np.maximum(resid, np.finfo(float).tiny)
    return dict(fr=fr, S=S, F=F, p=fdist.sf(F, 2, 2 * K - 2), amplitude=2 * np.abs(mu), Y=Y, K=K, bandwidth_hz=2 * nw * fps / n)


def line_test(r, fps, hz, top=None, lines=()):
    """`multitaper` read: the harmonic F-test at the stage's beat `hz` -- the strongest F within half a bandwidth of it
    -- and the lines in the band, local maxima of F under MT_P a bandwidth apart, strongest first: {hz, F, p, p_band (the
    chance of one as strong anywhere in the band: one look a resolution), amplitude, strongest {hz, F, p, amplitude},
    lines [{hz, F, p, amplitude, at_the_codec_line_hz}], K, bandwidth_hz, resolution_hz}. In a window of 2 s the
    bandwidth is 2.5 Hz, so there it says whether a line is there at all; over the whole track it tells the fundamental
    from the double."""
    r = np.asarray(r, float)
    n = len(r)
    M = multitaper(r, fps)
    fr, F, p, A, bw = M["fr"], M["F"], M["p"], M["amplitude"], M["bandwidth_hz"]
    hi = min(top or fps, 0.95 * fps / 2)
    band = (fr >= LOW) & (fr <= hi)
    res = fps / n
    out = dict(hz=None, F=None, p=None, p_band=None, amplitude=None, strongest=None, lines=[], K=M["K"], bandwidth_hz=bw, resolution_hz=res)
    if band.sum() < 3 or not hz:
        return out
    looks = max(1.0, (hi - LOW) / res)
    near = band & (np.abs(fr - hz) <= bw / 2)
    if near.any():
        k = int(np.flatnonzero(near)[np.argmax(F[near])])
        out.update(hz=float(fr[k]), F=float(F[k]), p=float(p[k]), p_band=float(1 - (1 - p[k]) ** looks), amplitude=float(A[k]))
    Fb = np.where(band, F, -1.0)
    tops = np.flatnonzero(np.r_[False, (Fb[1:-1] >= Fb[:-2]) & (Fb[1:-1] > Fb[2:]), False] & (p < MT_P))
    kept = []
    for k in sorted(tops, key=lambda k: -F[k]):
        if all(abs(fr[k] - fr[j]) > bw for j in kept):
            kept.append(k)
    def codec(k):                                       # within Z_LINE of the line's own frequency error, read where it matters
        near = any(abs(fr[k] - L) <= ERR_REACH * res for L in lines)
        return at_line(float(fr[k]), hz_error(r, fps, float(fr[k]))["hz_err"] if near else None, lines, res)
    out["lines"] = [dict(hz=float(fr[k]), F=float(F[k]), p=float(p[k]), p_band=float(1 - (1 - p[k]) ** looks), amplitude=float(A[k]),
                         at_the_codec_line_hz=codec(k)) for k in kept[:8]]
    k = int(np.argmax(Fb))
    out["strongest"] = dict(hz=float(fr[k]), F=float(F[k]), p=float(p[k]), amplitude=float(A[k]))
    return out


def line_windows(r, fps, hz, top=None, window_s=WINDOW_S):
    """`line_test` at the beat in windows of `window_s` along the stretch, a quarter of a window apart: a wingbeat's
    rate wanders, so over a whole track its energy spreads across the tapers' bandwidth and the F-test, which asks for
    one stationary sinusoid, says no line; within 2 s it is one. The frequency is given beforehand, so each window's
    chance is the F-test's own, not the band's. {windows, passing (under MT_P), share, best_p, best_frames (as places
    in r), amplitudes (each window's, where it passes)}."""
    r = np.asarray(r, float)
    n = len(r)
    W = min(n, max(MIN_FRAMES, int(round(window_s * fps))))
    out = dict(windows=0, passing=0, share=None, best_p=None, best_frames=None, amplitudes=[])
    if n < 16 or not hz:
        return out
    step = max(1, W // 4)
    starts = list(range(0, n - W + 1, step)) or [0]
    if starts[-1] != n - W:
        starts.append(n - W)
    best = None
    for a in starts:
        L = line_test(r[a:a + W], fps, hz, top=top)
        if L["p"] is None:
            continue
        out["windows"] += 1
        if L["p"] < MT_P:
            out["passing"] += 1
            out["amplitudes"].append(round(L["amplitude"], 4))
        if best is None or L["p"] < best[0]:
            best = (L["p"], a, a + W - 1)
    if out["windows"]:
        out.update(share=out["passing"] / out["windows"], best_p=float(best[0]), best_frames=[int(best[1]), int(best[2])])
    return out


def coherence_at(ra, rb, fps, hz, nw=MT_NW, window_s=WINDOW_S):
    """The magnitude-squared coherence of two deviation curves at `hz`, by multitaper eigencoefficients in windows of
    `window_s` along them (Thomson & Chave 1991): K tapers in each of M windows are K M independent looks, so with no
    coherence at all the estimate clears `level` with probability COH_P (level = 1 - COH_P^(1/(KM-1))); and the phase
    of b behind a there, with its jackknife error over the looks: {gamma2, level, above, phase_deg, phase_err_deg,
    looks}. `shared` asks the same with an amplitude rule; this answers with a chance."""
    ra, rb = np.asarray(ra, float), np.asarray(rb, float)
    n = len(ra)
    nothing = dict(gamma2=None, level=None, above=None, phase_deg=None, phase_err_deg=None, looks=0)
    if n < 16 or len(rb) != n or not hz:
        return nothing
    W = min(n, max(MIN_FRAMES // 2, int(round(window_s * fps))))
    starts = list(range(0, n - W + 1, W)) or [0]
    v, lam = tapers(W, nw)
    e = np.exp(-2j * np.pi * hz * np.arange(W) / fps)
    A = np.concatenate([(v * (ra[s:s + W] * e)[None, :]).sum(1) for s in starts])
    B = np.concatenate([(v * (rb[s:s + W] * e)[None, :]).sum(1) for s in starts])
    L = len(A)
    if L < 3:
        return dict(nothing, looks=L)
    X = A * np.conj(B)
    den = float((np.abs(A) ** 2).sum() * (np.abs(B) ** 2).sum())
    if den <= 0:
        return dict(nothing, looks=L)
    g2 = float(np.abs(X.sum()) ** 2 / den)
    level = 1 - COH_P ** (1 / (L - 1))
    ph0 = np.angle(X.sum())
    d = np.array([np.angle(np.exp(1j * (np.angle(X[np.arange(L) != i].sum()) - ph0))) for i in range(L)])
    err = float(np.degrees(np.sqrt((L - 1) / L * (d ** 2).sum())))
    return dict(gamma2=g2, level=float(level), above=bool(g2 > level), phase_deg=float(np.degrees(ph0)), phase_err_deg=err, looks=L)


def noise_pdf(R, fps, hz, obj=None, hop=PPSD_HOP):
    """The noise as a distribution (McNamara & Buland 2004's probabilistic power spectral density, which every
    seismic station's noise is drawn as): the amplitude spectrum of every window of WINDOW_S along every background
    aperture's curve (`R`: rows, deviation curves in the object's brightness), the windows `hop` of a window apart,
    and at each frequency the 50th, 90th and 99th centiles of them -- and the object's own windows (`obj`: its
    deviation curve, the same windows) at `hz` against them: the centile its median window's amplitude sits at, and
    the share of its windows over their 99th. Every amplitude as `peak` reads it. Returns ({hz, windows, object_windows,
    object_amplitude, centile, share_over_99, level50, level90, level99}, {fr, p50, p90, p99, obj: the object's median
    window spectrum} for the figure); the second None where there are too few windows."""
    R = np.atleast_2d(np.asarray(R, float))
    n = R.shape[1]
    W = min(n, max(MIN_FRAMES, int(round(WINDOW_S * fps))))   # a stretch shorter than a window is one window
    out = dict(hz=float(hz) if hz else None, windows=0, object_windows=0, object_amplitude=None, centile=None, share_over_99=None,
               level50=None, level90=None, level99=None)
    if n < MIN_FRAMES // 2 or not hz:
        return out, None
    step = max(1, int(round(hop * W)))
    starts = list(range(0, n - W + 1, step))
    w = np.hanning(W)
    fr = np.fft.rfftfreq(PAD * W, 1 / fps)

    def amps(x, s):
        return 2 * np.abs(np.fft.rfft((x[s:s + W] - x[s:s + W].mean()) * w, PAD * W)) / w.sum()
    S = np.stack([amps(x, s) for x in R for s in starts])
    p50, p90, p99 = np.percentile(S, 50, axis=0), np.percentile(S, 90, axis=0), np.percentile(S, 99, axis=0)
    k = int(np.argmin(np.abs(fr - hz)))
    out.update(windows=int(S.shape[0]), level50=float(p50[k]), level90=float(p90[k]), level99=float(p99[k]))
    arrays = dict(fr=fr, p50=p50, p90=p90, p99=p99, obj=None)
    if obj is not None and len(obj) == n:
        o = np.asarray(obj, float)
        O = np.stack([amps(o, s) for s in starts])
        med = float(np.median(O[:, k]))
        out.update(object_windows=int(O.shape[0]), object_amplitude=med, centile=float(100 * np.mean(S[:, k] < med)),
                   share_over_99=float(np.mean(O[:, k] > p99[k])))
        arrays["obj"] = np.median(O, axis=0)
    return out, arrays


def sompi(r, fps, orders=SOMPI_ORDERS, top=None, tol=SOMPI_TOL, share=SOMPI_SHARE, over=SOMPI_OVER, backward=False):
    """The record as the output of a linear system -- the Sompi method (Hori et al. 1989; Kumazawa et al. 1990), written
    for the Earth's free oscillations and used since to read a volcano's long-period events from a few cycles (Nakano
    et al. 1998): an autoregressive model fitted at every order in `orders` (least squares, forwards -- a decaying
    line run backwards grows, so the backward prediction a stationary fit adds, `backward`, cancels the decay),
    whose roots are complex frequencies, a frequency and a growth or decay rate each. The signal's roots hold still
    across the orders and the noise's scatter, so a line is a cluster of roots within `tol` of one frequency at `share`
    of the orders or more, and whose amplitude, fitted to the record with the other lines' (a growing or decaying
    sinusoid each), stands `over` times what the lines leave -- grain makes roots that hold still too, small ones; the
    strongest of those that hold still but do not stand is `weak`. The strongest is reported: {hz, growth_per_s, q (for a decaying line, pi f over its decay rate),
    amplitude (as a share of the brightness), stability (the share of orders it held at), orders (tried), lines (all
    of them, strongest first), n}. hz None where no root holds still. A frequency from a few cycles, in exchange for
    the model: for a record too short for the stage's spectrum (SHORT_MIN to MIN_FRAMES frames), and for a swing."""
    r = np.asarray(r, float)
    r = r - r.mean()
    n, dt = len(r), 1 / fps
    hi = min(top or fps, 0.95 * fps / 2)
    tried, roots = [], []
    for p in orders:
        if n < 3 * p + 2:
            continue
        X = np.stack([r[p - j - 1:n - j - 1] for j in range(p)], 1)
        if backward:
            Xb = np.stack([r[j + 1:n - p + j + 1] for j in range(p)], 1)
            a, *_ = np.linalg.lstsq(np.vstack([X, Xb]), np.r_[r[p:], r[:n - p]], rcond=None)
        else:
            a, *_ = np.linalg.lstsq(X, r[p:], rcond=None)
        tried.append(int(p))
        for z in np.roots(np.r_[1.0, -a]):
            if z.imag > 0:
                f = float(np.angle(z) / (2 * np.pi * dt))
                if LOW <= f <= hi:
                    roots.append((int(p), f, float(np.log(max(abs(z), 1e-12)) / dt)))
    out = dict(hz=None, growth_per_s=None, q=None, amplitude=None, over=None, stability=None, orders=tried, lines=[], weak=None, n=int(n))
    if len(tried) < 3 or not roots:
        return out
    need = share * len(tried)
    cands = []
    for i, (p, f, g) in enumerate(roots):
        members = [j for j, (_, f2, _) in enumerate(roots) if abs(f2 - f) <= tol * f]
        cands.append((len({roots[j][0] for j in members}), i, members))
    cands.sort(key=lambda c: (-c[0], c[1]))
    used, clusters = [False] * len(roots), []
    for n_ord, i, members in cands:
        if used[i] or n_ord < need:
            continue
        free = [j for j in members if not used[j]]
        held = {roots[j][0] for j in free}
        if len(held) < need:
            continue
        for j in free:
            used[j] = True
        clusters.append(dict(hz=float(np.median([roots[j][1] for j in free])), growth_per_s=float(np.median([roots[j][2] for j in free])),
                             stability=len(held) / len(tried)))
    if not clusters:
        return out
    t = np.arange(n) * dt
    cols = []
    for c in clusters:
        e = np.exp(c["growth_per_s"] * t)
        e = e / max(float(e.max()), 1e-12)
        cols += [e * np.cos(2 * np.pi * c["hz"] * t), e * np.sin(2 * np.pi * c["hz"] * t)]
    A = np.stack(cols, 1)
    beta, *_ = np.linalg.lstsq(A, r, rcond=None)
    left = float((r - A @ beta).std())                       # what the lines leave: the grain
    for k, c in enumerate(clusters):
        comp = A[:, 2 * k:2 * k + 2] @ beta[2 * k:2 * k + 2]
        c["amplitude"] = float(np.sqrt(2) * comp.std())
        c["over"] = float(c["amplitude"] / max(left, np.finfo(float).tiny))
        g = c["growth_per_s"]
        c["q"] = float(np.pi * c["hz"] / -g) if g < 0 else None
    clusters.sort(key=lambda c: -c["amplitude"])
    out["weak"] = next(({k: c[k] for k in ("hz", "amplitude", "over", "stability")} for c in clusters if c["over"] < over), None)
    clusters = [c for c in clusters if c["over"] >= over]
    out["lines"] = clusters
    if not clusters:
        return out
    best = clusters[0]
    out.update(hz=best["hz"], growth_per_s=best["growth_per_s"], q=best["q"], amplitude=best["amplitude"], over=best["over"], stability=best["stability"])
    return out


def comb(lines, hz, res, bw=None):
    """The beat's lines read as a comb -- harmonic tremor: a fundamental and overtones at its exact multiples, which move
    together (Hotovec et al. 2013), and the cepstrum (Bogert, Healy & Tukey 1963, invented to time echoes in
    seismograms), which reads a comb's spacing from the log spectrum as one peak; here the comb is read from the
    multitaper's `lines` whose chance anywhere in the band is under MT_P -- of the window the beat is clearest in,
    where a wingbeat is one line (`line_windows`); a 2-s window has a grain line under MT_P itself once in five.
    The fundamental whose multiples hold the most of them (each within a resolution of a multiple) with the fewest
    multiples missing below the
    highest, among the candidates every line's frequency over 1, 2 and 3 offers, the higher fundamental where two
    tie (a line's half is never preferred to the line): {fundamental_hz, n_lines, missing, lines_hz, agrees (within
    ONEBIT_RES resolutions of the stage's hz, its half or its double)}. None with fewer than two lines on the comb:
    one line is not a comb."""
    fs = [L["hz"] for L in lines if L.get("p_band", L.get("p", 1.0)) <= MT_P]
    tol = res
    if len(fs) < 2:
        return None
    best = None
    for f in fs:
        for k in (1, 2, 3):
            f0 = f / k
            if f0 < LOW:
                continue
            on = [g for g in fs if round(g / f0) >= 1 and abs(g - round(g / f0) * f0) <= tol]
            if len(on) < 2:
                continue
            ks = {int(round(g / f0)) for g in on}
            missing = max(ks) - len(ks)
            score = (len(on) - missing, f0)
            if best is None or score > best[0]:
                best = (score, on, missing)
    if best is None:
        return None
    _, on, missing = best
    f0 = best[0][1]
    f0 = float(np.mean([g / round(g / f0) for g in on]))
    return dict(fundamental_hz=f0, n_lines=len(on), missing=int(missing), lines_hz=sorted(float(g) for g in on),
                agrees=bool(min(abs(f0 - hz), abs(f0 - hz / 2), abs(f0 - 2 * hz)) <= ONEBIT_RES * res))


def glide(r, fps, hz, double_hz=None, top=None, window_s=GLIDE_S, nw=2.0):
    """The beat's fundamental followed along the stretch in windows of `window_s`, an eighth of a window apart -- the
    ridge a volcano observatory draws through a spectrogram of gliding tremor (Hotovec et al. 2013), and the frequency
    drift search of a pulsar's (Ransom et al. 2002) -- about the stage's fundamental, and its double about the stage's
    double, each the strongest local maximum within reach (a window's resolution and half a hertz) that stands -- the
    window's own harmonic F-test there under GLIDE_P (the frequency is given beforehand, so the chance is not for the
    whole band), with `nw` tapers' worth of bandwidth; where the fundamental's line
    does not stand and the double's does, the fundamental is the double's half, and says so. Followed over the whole
    track, not the stretch the beat is reported from: flyer 5's rate settles over its approach. {t, hz, double_hz, stands, from_double: per window; windows; slope_hz_per_s,
    range_hz, r2, start_hz, end_hz: a line through the fundamental where it stands; together: the share of windows
    with both lines in which the double sits at twice the fundamental, within a resolution -- a comb's overtones move
    with it; windows_with_both; resolution_hz}. A glide under the window's resolution is not one."""
    r = np.asarray(r, float)
    n = len(r)
    W = max(16, int(round(window_s * fps)))
    out = dict(t=[], hz=[], double_hz=[], stands=[], from_double=[], windows=0, slope_hz_per_s=None, range_hz=None, r2=None,
               start_hz=None, end_hz=None, together=None, windows_with_both=0, resolution_hz=fps / W)
    if n < W + 4 or not hz:
        return out
    hi = min(top or fps, 0.95 * fps / 2)
    reach = fps / W + 0.5
    step = max(1, W // 8)
    starts = list(range(0, n - W + 1, step))
    d0 = double_hz if double_hz else 2 * hz
    fr = np.fft.rfftfreq(PAD * W, 1 / fps)
    band = (fr >= LOW) & (fr <= hi)
    if not band.any():
        return out
    for s in starts:
        M = multitaper(r[s:s + W] - r[s:s + W].mean(), fps, nw=nw)
        P, pv = M["S"], M["p"]

        def ridge(f):
            m = band & (np.abs(fr - f) <= reach)
            if not m.any():
                return None, 1.0
            k = int(np.flatnonzero(m)[np.argmax(P[m])])
            local = 0 < k < len(P) - 1 and P[k] >= P[k - 1] and P[k] >= P[k + 1]
            return (float(fr[k]) if local else None), float(pv[k])
        f1, p1 = ridge(hz)
        f2, p2 = ridge(d0)
        st1, st2 = f1 is not None and p1 < GLIDE_P, f2 is not None and p2 < GLIDE_P
        out["t"].append(float((s + W / 2) / fps))
        out["hz"].append(f1 if st1 else (f2 / 2 if st2 else None))
        out["double_hz"].append(f2 if st2 else None)
        out["stands"].append(bool(st1 or st2))
        out["from_double"].append(bool(not st1 and st2))
    out["windows"] = len(starts)
    ts = np.array([t for t, f in zip(out["t"], out["hz"]) if f is not None])
    fs = np.array([f for f in out["hz"] if f is not None])
    if len(fs) >= 5:
        A = np.c_[np.ones(len(ts)), ts - ts.mean()]
        beta, *_ = np.linalg.lstsq(A, fs, rcond=None)
        ss = float(((fs - fs.mean()) ** 2).sum())
        out.update(slope_hz_per_s=float(beta[1]), range_hz=float(fs.max() - fs.min()), start_hz=float(fs[0]), end_hz=float(fs[-1]),
                   r2=float(1 - ((fs - A @ beta) ** 2).sum() / ss) if ss > 0 else 0.0)
    both = [(f, d) for f, d, src in zip(out["hz"], out["double_hz"], out["from_double"]) if f is not None and d is not None and not src]
    if both:
        out.update(together=float(np.mean([abs(d - 2 * f) <= fps / W for f, d in both])), windows_with_both=len(both))
    return out


def in_step(curves, hz, fps, slides=200, seed=0, nw=MT_NW):
    """Whether members beat in step at `hz`, by their phases: each deviation curve band-passed about hz (two resolutions
    or half a hertz either side), its instantaneous phase from the analytic signal, and the modulus of the members' mean
    unit phasor averaged over the frames -- the phase coherence a phase-weighted stack weights by (Schimmel & Paulssen
    1997): 1 in step, about 1/sqrt(N) for N at random -- held against `slides` copies in which every member's curve is
    slid round by a random number of frames (the time-slides of gravitational-wave searches): `p_slides`, the share as
    coherent. And the array F-statistic at hz (Melton & Bailey 1957; Blandford 1974): the members' mean curve's power
    there over the mean of their residuals', by multitaper eigencoefficients, F with 2K and 2K(N-1) degrees of freedom
    under no shared component. {members, n, hz, R, p_slides, F, p_F, K, slides}. `common` asks this of pairs by
    their cross-spectrum's phase; this asks it of all of them at once, with a chance."""
    from scipy.stats import f as fdist
    names = list(curves)
    out = dict(members=names, n=len(names), hz=float(hz) if hz else None, R=None, p_slides=None, F=None, p_F=None, K=None, slides=int(slides))
    if len(names) < 2 or not hz:
        return out
    X = np.stack([np.asarray(curves[m], float) for m in names])
    N, n = X.shape
    if n < 16:
        return out
    fr = np.fft.fftfreq(n, 1 / fps)
    mask = (fr > 0) & (np.abs(fr - hz) <= max(2 * fps / n, 0.5))
    Z = np.fft.fft(X - X.mean(1, keepdims=True), axis=-1)
    Z[:, ~mask] = 0
    ph = np.angle(np.fft.ifft(2 * Z, axis=-1))

    def R_of(ph):
        return float(np.abs(np.exp(1j * ph).mean(0)).mean())
    R = R_of(ph)
    rng = np.random.default_rng(seed)
    z = np.array([R_of(np.stack([np.roll(ph[i], int(rng.integers(n))) for i in range(N)])) for _ in range(slides)])
    v, lam = tapers(n, nw)
    K = v.shape[0]
    e = np.exp(-2j * np.pi * hz * np.arange(n) / fps)
    Y = np.stack([(v * (X[i] * e)[None, :]).sum(1) for i in range(N)])
    beam = Y.mean(0)
    den = float((np.abs(Y - beam[None, :]) ** 2).sum())
    F = float((N - 1) * N * (np.abs(beam) ** 2).sum() / max(den, np.finfo(float).tiny))
    out.update(R=R, p_slides=float((np.sum(z >= R) + 1) / (slides + 1)), F=F, p_F=float(fdist.sf(F, 2 * K, 2 * K * (N - 1))), K=int(K))
    return out


def phase_map(stamps, r, hz, fps, ap):
    """Where in the picture the beat is, by phase: each pixel of the stamps' time series band-passed about hz, its
    instantaneous phase against the aperture curve's, and the modulus of the mean unit phasor of their difference over
    the frames -- 1 where the pixel beats with the aperture, about 1/sqrt(frames) where it does not: the phase-weighted
    stack's weight, pixel by pixel (Schimmel & Paulssen 1997), beside the fold's difference picture, which weighs by
    amplitude. A gain the whole frame shares is coherent everywhere; a beat of the object's within the aperture.
    Returns (the map, {phase_inside: its mean within the aperture, phase_outside: beyond twice the aperture,
    phase_frames}); (None, None) without enough stamps."""
    keep = [k for k, s in enumerate(stamps) if s is not None]
    if len(keep) < 16 or len(keep) < 0.8 * len(stamps) or not hz:
        return None, None
    A = np.stack([np.asarray(stamps[k], float) for k in keep])
    rr = np.asarray(r, float)[keep]
    T = len(keep)
    fr = np.fft.fftfreq(T, 1 / fps)
    mask = (fr > 0) & (np.abs(fr - hz) <= max(2 * fps / T, 0.5))

    def analytic(x):
        Z = np.fft.fft(x - x.mean(0, keepdims=True), axis=0)
        Z[~mask] = 0
        return np.fft.ifft(2 * Z, axis=0)
    pa = np.angle(analytic(A))
    pr = np.angle(analytic(rr[:, None, None]))[:, 0, 0]
    coh = np.abs(np.exp(1j * (pa - pr[:, None, None])).mean(0))
    S = coh.shape[0] // 2
    yy, xx = np.mgrid[-S:S + 1, -S:S + 1]
    d = np.hypot(xx, yy)
    inside, outside = d <= ap, d >= 2 * ap
    return coh, dict(phase_inside=float(coh[inside].mean()), phase_outside=float(coh[outside].mean()) if outside.any() else None,
                     phase_frames=int(T))


def onebit(r, fps, hz, lines=(), top=None):
    """The curve's strongest beat again with every sample's size thrown away -- its sign alone (one-bit normalisation,
    Bensen et al. 2007, the ambient-noise standard: it keeps the phase of every rhythm and lets no glint, level step or
    burst of gain outweigh the rest): {hz, stands, amplitude (of the sign curve, 0 to 1), agrees (within ONEBIT_RES
    resolutions of the stage's hz, its half or its double), at_the_codec_line_hz}. A beat in the linear reading and not
    in this one was a few frames that outweighed the rest; one in both is the waveform's."""
    r = np.asarray(r, float)
    s = np.sign(r - np.median(r))
    fr, F, band, wsum, _ = _spec(s, fps)
    if top:
        band = band & (fr <= top)
    out = dict(hz=None, stands=None, amplitude=None, agrees=None, at_the_codec_line_hz=None)
    if band.sum() < 3 or not hz:
        return out
    P = np.abs(F) ** 2
    k = int(np.argmax(np.where(band, P, -1)))
    res = fps / len(r)
    f = float(fr[k])
    e = hz_error(s, fps, f)["hz_err"] if any(abs(f - L) <= ERR_REACH * res for L in lines) else None
    return dict(hz=f, hz_err=e, stands=float(P[k] / np.median(P[band])), amplitude=float(2 * np.sqrt(P[k]) / wsum),
                agrees=bool(min(abs(f - hz), abs(f - hz / 2), abs(f - 2 * hz)) <= ONEBIT_RES * res),
                at_the_codec_line_hz=at_line(f, e, lines, res))


def short_reading(r, fps, lines=(), top=None):
    """A record too short for the stage's spectrum (SHORT_MIN to MIN_FRAMES frames) read anyway: its strongest peak as
    `peak` would, and the Sompi line: {n, peak {hz, amplitude, stands, at_the_codec_line_hz}, sompi}. A reading, not a
    beat: nothing holds it against the background beside it."""
    r = np.asarray(r, float)
    p = _peak(r, fps, lines, err=True)
    return dict(n=int(len(r)), peak=dict(hz=p["hz"], hz_err=p["hz_err"], amplitude=p["amplitude"], stands=p["stands"],
                                         at_the_codec_line_hz=p["at_the_codec_line_hz"]),
                sompi=sompi(r, fps, top=top))


def _nth(x):
    """81 -> 81st."""
    k = int(round(x))
    return f"{k}{'th' if 10 <= k % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(k % 10, 'th')}"


def said_short(name, sr):
    """One line for a short record's reading."""
    so, p = sr["sompi"], sr["peak"]
    head = f"{name}: {sr['n']} frames, under the {MIN_FRAMES} a beat needs; read anyway -- strongest peak {p['hz']:.2f} Hz, {p['amplitude']:.1%}"
    if so.get("hz") is not None:
        how = f"decaying, Q {so['q']:.0f}" if so["q"] else f"growing {so['growth_per_s']:+.2f}/s"
        return head + (f"; by Sompi a line at {so['hz']:.2f} Hz, {so['amplitude']:.1%}, {how}, holding still at {so['stability']:.0%} of the "
                       f"model's orders ({so['orders'][0]}-{so['orders'][-1]}). A reading, not a beat: nothing holds it against the background")
    return head + "; by Sompi no line holds still across the model's orders. A reading, not a beat"


def passes_seis(S):
    """Whether a track's seismologist's tests allow its beat (GATE_SEIS): a line at the beat by the multitaper F-test,
    under MT_P -- over the stretch, anywhere in the band, or in a window of 2 s along it (a wingbeat's rate wanders:
    over a whole track it is no stationary line, within 2 s it is one)."""
    L, W = S.get("line") or {}, S.get("line_windows") or {}
    whole = L.get("p_band") is not None and L["p_band"] <= MT_P
    return whole or bool(W.get("passing")) or L.get("p") is None


def disagreements_seis(strong, seis, step=None, independent=None):
    """Where the seismologist's tests disagree with a beat the stage called: sentences for the notes, or none."""
    off = []
    for n in strong:
        S = seis.get(n) or {}
        L, ob, nz = S.get("line") or {}, S.get("onebit") or {}, S.get("noise") or {}
        W = S.get("line_windows") or {}
        if L.get("p_band") is not None and L["p_band"] > MT_P and W.get("windows") and not W.get("passing"):
            off.append(f"{n}: no line at its beat by the multitaper F-test, over the stretch (chance {L['p_band']:.2g} anywhere in the "
                       f"band) or in any of its {W['windows']} windows of {WINDOW_S:g} s (the best {W['best_p']:.2g})")
        if ob.get("agrees") is False:
            off.append(f"{n}: with every sample its sign alone (one bit) its strongest is at {ob['hz']:.2f} Hz, not its beat")
        if nz.get("centile") is not None and nz["centile"] < 90:
            off.append(f"{n}: its windows' amplitude at the beat sits only at the {_nth(nz['centile'])} centile of the background's own windows")
        coh = [c.replace("background ", "") for c, v in (S.get("coherence") or {}).items() if v.get("above")]
        if coh:
            off.append(f"{n}: coherent at its beat with what is not the object ({', '.join(coh)})")
    if step and step.get("p_slides") is not None and step["p_slides"] <= MT_P and (step.get("p_F") or 1) <= MT_P and independent:
        off.append(f"the members are in step at {step['hz']:.2f} Hz by their phases (coherence {step['R']:.2f}, {step['p_slides']:.3f} of "
                   f"time-slid copies as coherent), which a rhythm of the video would make")
    return off


def said_seis(fields):
    """What `mcdonald flicker` prints of the seismologist's tests, from the fields."""
    L = []
    for name, S in (fields.get("seis") or {}).items():
        ln, cb, gl, so, ob, nz, co = (S.get(k) for k in ("line", "comb", "glide", "sompi", "onebit", "noise", "coherence"))
        if ln and ln.get("p") is not None:
            lw = S.get("line_windows") or {}
            L.append(f"  {name}, over frames {S['frames'][0]}-{S['frames'][1]}, the multitaper F-test ({ln['K']} tapers, bandwidth "
                     f"{ln['bandwidth_hz']:.2f} Hz) at its beat: a line at {ln['hz']:.2f} Hz, {ln['amplitude']:.1%}, F {ln['F']:.1f}, chance "
                     f"{ln['p']:.1e} ({ln['p_band']:.1e} anywhere in the band)"
                     + (" -- a stationary line over the whole stretch" if ln["p_band"] <= MT_P else " -- no stationary line over the whole stretch (a wingbeat's rate wanders)")
                     + (f"; in windows of {WINDOW_S:g} s along it {lw['passing']} of {lw['windows']} have one (the best chance {lw['best_p']:.1e}"
                        + (f", frames {lw['frames'][0]}-{lw['frames'][1]}" if lw.get("frames") else "") + ")" if lw.get("windows") else "")
                     + (f"; stationary lines in the band at " + ", ".join(f"{q['hz']:.2f}" for q in ln["lines"]) + " Hz" if ln["lines"] else ""))
        if cb:
            L.append(f"  {name}, as a comb: fundamental {cb['fundamental_hz']:.2f} Hz, {cb['n_lines']} lines on it"
                     + (f", {cb['missing']} multiples missing" if cb["missing"] else "") + (" -- the stage's beat" if cb["agrees"] else " -- not the stage's beat"))
        if gl and gl.get("slope_hz_per_s") is not None:
            L.append(f"  {name}, its fundamental followed in windows of {GLIDE_S:g} s: {gl['start_hz']:.2f} to {gl['end_hz']:.2f} Hz, "
                     f"{gl['slope_hz_per_s']:+.2f} Hz/s (r2 {gl['r2']:.2f}), a range of {gl['range_hz']:.2f} Hz (the window resolves {gl['resolution_hz']:.1f})"
                     + (f"; the double moves with it in {gl['together']:.0%} of the {gl['windows_with_both']} windows that have both"
                        if gl.get("together") is not None else "")
                     + (f"; taken from the double in {sum(gl['from_double'])} of {gl['windows']} windows" if any(gl["from_double"]) else ""))
        if so and so.get("hz") is not None:
            how = f"decaying, Q {so['q']:.0f}" if so["q"] else f"growing {so['growth_per_s']:+.2f}/s"
            L.append(f"  {name}, by Sompi (orders {so['orders'][0]}-{so['orders'][-1]}): {so['hz']:.2f} Hz, {so['amplitude']:.1%}, {how}, "
                     f"holding still at {so['stability']:.0%} of the orders" + (f"; {len(so['lines'])} lines in all" if len(so["lines"]) > 1 else ""))
        elif so:
            L.append(f"  {name}, by Sompi: no line holds still across the model's orders")
        if ob and ob.get("hz") is not None:
            L.append(f"  {name}, one bit (every sample its sign alone): {ob['hz']:.2f} Hz, {ob['stands']:.0f}x the band"
                     + (" -- the beat" if ob["agrees"] else " -- not the beat"))
        if nz and nz.get("centile") is not None:
            L.append(f"  {name}, against the background's own windows ({nz['windows']} of {WINDOW_S:g} s): its windows' amplitude at the beat, "
                     f"{nz['object_amplitude']:.1%}, sits at their {_nth(nz['centile'])} centile (their 99th is {nz['level99']:.1%}); "
                     f"{nz['share_over_99']:.0%} of its windows are over it")
        cs = [(c, v) for c, v in (co or {}).items() if v.get("gamma2") is not None]
        if cs:
            up = [f"{c.replace('background ', '')} ({v['gamma2']:.2f}, {v['phase_deg']:+.0f} +/- {v['phase_err_deg']:.0f} deg)" for c, v in cs if v["above"]]
            L.append(f"  {name}, coherence at the beat with the background beside it and the frame's level and contrast: "
                     + ", ".join(f"{v['gamma2']:.2f}" for _, v in cs)
                     + f" (chance clears {cs[0][1]['level']:.2f} with {cs[0][1]['looks']} looks)" + ("; coherent: " + ", ".join(up) if up else "; none coherent"))
    st = fields.get("in_step")
    if st and st.get("R") is not None:
        L.append(f"  {', '.join(st['members'])} in step at {st['hz']:.2f} Hz? phase coherence {st['R']:.2f} (1 in step, about "
                 f"{1 / np.sqrt(st['n']):.2f} at random); {st['p_slides']:.3f} of {st['slides']} copies slid round in time are as "
                 f"coherent; array F {st['F']:.1f}, chance {st['p_F']:.1e}")
    for name, sr in (fields.get("short_record") or {}).items():
        L.append("  " + said_short(name, sr))
    return L


def measure(clip, tracks, dark=False, out=None, say=print, progress=None, stop=None, procs=None, nulls=False, aperture=None,
            rule=None, avoid=None, scene=False, black_hot=False):
    """The stage: each track's beat, the background apertures' about the first, the codec's rhythm,
    and -- with two tracks or more -- whether they beat as one. `tracks` is {name: {frame: (x, y)}}:
    the object's track, or the members of a group (groups.members). Writes <out>_flicker.csv. `nulls` runs the slower
    controls as well: the background apertures through every window, and beats planted in them, across the band and
    beside the codec's lines (`mcdonald flicker` does, unless told --no-nulls; `mcdonald run` and a test need not). `aperture`, if given ('R', 'R,R1,R2' or 'R,R1,R2,BG'; `fixed`), is the disc
    every track is measured in, never re-centred, in place of the one that follows each object's size. `rule` ("stage" or
    "paper", RULES) is how this measurement judges a beat; RULE where it is not given. `avoid`, {name: {frame: (x, y)}},
    are other tracked things in the video, not measured, that the background apertures keep clear of (`clear_offsets`).
    `black_hot`: the clip is a black-hot thermal display, where a light (hot) is dark, for item 13 (`lights`)."""
    if rule is not None and str(rule).strip() != "":
        if rule not in RULES:
            raise ValueError(f"the beat rule {rule!r} is not one of {', '.join(RULES)}")
        token = _RULE.set(rule)
        try:
            found = measure(clip, tracks, dark=dark, out=out, say=say, progress=progress, stop=stop, procs=procs, nulls=nulls,
                            aperture=aperture, avoid=avoid, scene=scene, black_hot=black_hot)
        finally:
            _RULE.reset(token)
        found.fields["rule"] = rule
        return found
    fix = fixed(aperture) if aperture is not None and str(aperture).strip() != "" else None
    g = read_gop(clip.video, clip.fps) if getattr(clip, "video", None) else None
    lines = (g or {}).get("lines_hz") or []
    names = list(tracks)
    # Each track over its own frames. A group's members come and go -- PR135's flock, 2026-10-08: one seen from
    # frame 1240, another from 1283 -- and the frames they all share can be none; so the curves are read over
    # the union, and each is measured over its own span, the pairs over what each pair has in common.
    spans = {}
    for name, t in tracks.items():
        fs = [n for n in t if clip.n0 <= n <= clip.n1]
        if fs:
            spans[name] = (min(fs), max(fs))
    fields = dict(frames=0, first=None, last=None, codec=g, aperture_px=APERTURE, tracks=names, spans=spans)
    if black_hot:                                        # said only where given: a case without it reruns to its fields
        fields["black_hot"] = True
    if not spans:
        return Found("flicker", fields=dict(fields, beats=None, finding=None),
                     no_power=[("flicker", "no track on the frames that are open")])
    lo, hi = min(a for a, _ in spans.values()), max(b for _, b in spans.values())
    ns = list(range(lo, hi + 1))
    fields.update(frames=len(ns), first=lo, last=hi)
    longest = max(spans, key=lambda name: spans[name][1] - spans[name][0])
    if spans[longest][1] - spans[longest][0] + 1 < MIN_FRAMES:
        notes = []
        if spans[longest][1] - spans[longest][0] + 1 >= SHORT_MIN:       # read anyway, for the short-record reading (item 8)
            try:
                sz = sizes(clip, {longest: tracks[longest]}, ns, dark)
                raw = curves(clip, {longest: tracks[longest]}, ns, dark, progress, stop, about=longest, procs=procs,
                             ap={name: (fix or s) for name, (_, s) in sz.items()})
                own = [v for v in raw.get(longest, []) if v is not None]
                if len(own) >= SHORT_MIN and np.median(own) > 0:
                    fields["short_record"] = {longest: dict(short_reading(deviation(own, clip.fps), clip.fps, lines, top=TOP * clip.fps / 2),
                                                            frames=[int(spans[longest][0]), int(spans[longest][1])])}
                    notes.append(said_short(longest, fields["short_record"][longest]) + ".")
            except Exception as e:                           # a reading that cannot be made does not undo the stage's answer
                say(f"  ! the short record was not read: {type(e).__name__}: {e}")
        return Found("flicker", fields=dict(fields, beats=None, finding=None),
                     no_power=[("flicker", f"{len(ns)} frames{' in common' if len(names) > 1 else ''}, under the {MIN_FRAMES} a beat needs")],
                     notes=notes)
    # the background apertures go with the track seen longest (a group's first member may be seen briefly:
    # PR135's object 2, 42 frames of its first), and the stretch reported is that track's
    first = max(spans, key=lambda name: spans[name][1] - spans[name][0])
    read = {}
    sz = sizes(clip, tracks, ns, dark, how=read)
    ap = {name: (fix or s) for name, (_, s) in sz.items()}
    fields["extent_read"] = read
    for name, rec in read.items():
        if rec["used"] == "stack":
            each = (f"{rec['read']} of {rec['frames']} frames gave a size"
                    + (f", {rec['median']:.0f} px at the median, spread {100 * rec['spread']:.0f} %" if rec["median"] else ""))
            got = (f"{rec['stack']:.0f} px" if rec["stack"] is not None else "nothing stands out of it either, so the point's")
            say(f"  {name}: the frames do not agree on its size ({each}); read off their stack"
                + (" along its travel, on the half ahead of it" if rec.get("along") else "") + f": {got}")
    if fix:
        fields["aperture_fixed"] = dict(radius_px=fix[0], ring_px=list(fix[1]), background_px=fix[2])
        say(f"  the aperture is fixed, as given: a disc of {fix[0]:g} px, its background the median of the ring "
            f"{fix[1][0]:g}-{fix[1][1]:g} px, the background apertures {fix[2]} px away; never re-centred")
    fields.update(extent_px={n: e for n, (e, _) in sz.items()}, aperture_px={n: s[0] for n, s in ap.items()},
                  ring_px={n: list(s[1]) for n, s in ap.items()}, background_px=ap[first][2],
                  recentred=[n for n, s in ap.items() if s[3]])
    wide = [n for n, s in ap.items() if s[3]]
    if wide:
        say("  aperture follows the object: " + "; ".join(
            f"{n} {sz[n][0]:.1f} px across in radius -> aperture {ap[n][0]:.1f} px, ring {ap[n][1][0]:.0f}-{ap[n][1][1]:.0f} px,"
            f" re-centred each frame" for n in wide))
    thumbs, stamps, moves, lit = [], {}, [], {}
    reaches = light_reach(clip, tracks, ns)              # item 13: how far each thing's lights can be from its middle
    litring = {}
    for name in tracks:
        r0 = ap[name][1][0]
        r = max(r0, reaches[name] + 2) if reaches.get(name) else r0
        litring[name] = (r, (r, r + 8))
    fields["light_reach_px"] = reaches
    pos = {name: smoothed(t, ns) for name, t in tracks.items()}
    offsets, moved = None, False
    if avoid:
        others = []
        for name, t in avoid.items():
            if not t:
                continue
            x, y = smoothed(t, ns)
            others.append((x, y, np.array([min(t) <= n <= max(t) for n in ns])))
        offsets, moved = clear_offsets(pos[first], others, ap[first][2], ap[first][1])
        fields["background_offsets"] = [[float(dx), float(dy)] for dx, dy in offsets]
        fields["avoided"] = sorted(avoid)
        if moved:
            say(f"  the background apertures are moved clear of {len(others)} other tracked thing{'s' if len(others) != 1 else ''}: "
                + ", ".join(f"{dx:+.0f},{dy:+.0f}" for dx, dy in offsets) + " px")
    raw = curves(clip, tracks, ns, dark, progress, stop, about=first, procs=procs, ap=ap, thumbs=thumbs, stamps=stamps,
                 offsets=offsets if moved else None, moves=moves, lit=lit, litring=litring, black_hot=black_hot)
    fields["pictures"] = pictures(thumbs, clip.fps)
    if fields["pictures"]["held"] >= HELD_MIN:
        say(f"  the video holds pictures: {fields['pictures']['held']:.0%} of frames repeat the one before, so it carries "
            f"{fields['pictures']['rate']:.1f} pictures a second, and a beat is heard only up to {fields['pictures']['top_hz']:.1f} Hz")
    planted_once = {}

    def encoding(hz, amp, top):
        """The planted-dot encoding control at a beat: the dots planted and encoded once, read at any frequency."""
        from . import planted
        if "dots" not in planted_once:
            planted_once["dots"] = planted.dots(clip, tracks[first], dark=dark, ap=ap[first], say=say)
        return planted.at_beat(planted_once["dots"], hz, amp, clip.fps, top=top)
    fields["rule"] = active_rule()
    found = judge(raw, ns, clip.fps, lines, fields, first, out=out, say=say, positions=pos, stamps=stamps, thumbs=thumbs, nulls=nulls,
                  encoding=encoding if getattr(clip, "video", None) else None, lit=lit)
    try:                                                 # item 13: a light that flashes in a train, beside whatever was found
        blink_reading(found, raw, lit, ns, clip.fps, dark, black_hot)
    except Exception as e:                               # a reading that cannot be made does not undo the stage's answer
        say(f"  ! the lights were not read: {type(e).__name__}: {e}")
    if scene and found.fields.get("beats") is True:      # the sensor's own motion at each of the objects' own beats
        own = {n: found.fields["beat"][n]["hz"] for n in (found.fields.get("strong") or []) if n in found.fields.get("beat", {})}
        if own:
            say("  the scene's own motion at the beat" + ("s" if len(own) > 1 else "") + ": registering every frame")
            sh = scene_shift(clip, ns, tracks, own, moves=moves, procs=procs, progress=progress, stop=stop)
            found.fields["scene_shift"] = sh
            found.notes.append(shift_said(sh))
    if moved:
        found.notes.append(f"The background apertures were moved clear of the other tracked thing{'s' if len(avoid) != 1 else ''} "
                           f"in the video ({', '.join(sorted(avoid))}): at " + ", ".join(f"{dx:+.0f},{dy:+.0f}" for dx, dy in offsets)
                           + " px from it, where the usual four would have lain on one of them on some frame.")
    if fix:
        ext = {n: e for n, (e, _) in sz.items() if e is not None}
        found.notes.append(f"The aperture was fixed, as given: a disc of {fix[0]:g} px, its background the median of the ring "
                           f"{fix[1][0]:g}-{fix[1][1]:g} px, the background apertures {fix[2]} px from it, never re-centred"
                           + (" (the object's own extent: " + ", ".join(f"{n} {e:.1f} px" for n, e in ext.items()) + ")" if ext else "")
                           + ". It does not follow the object's size, as it does when none is given.")
    if wide:
        found.notes.append("The object is wider than the point-sized aperture, so the aperture follows it: " + "; ".join(
            f"{n} falls to {EXTENT_DROP:.0%} of its height {sz[n][0]:.1f} px out, so its aperture is {ap[n][0]:.1f} px, "
            f"its ring {ap[n][1][0]:.0f}-{ap[n][1][1]:.0f} px, re-centred each frame on its own centroid" for n in wide)
            + f"; the background apertures are {ap[first][2]} px from it.")
    return found


def judge(raw, ns, fps, lines, fields, first, out=None, say=print, positions=None, stamps=None, thumbs=None, nulls=False,
          encoding=None, lit=None):
    """The stage from the curves on (`measure` reads them): `raw` is {name: brightness on each frame of
    ns, None where it was not measured} for each track in fields["tracks"] and for the background
    apertures, which go with the track `first`; fields has the codec, the tracks' spans and the stretch.
    `positions` is {track: (x, y) over ns} (`smoothed`), `stamps` {track: [stamp per frame]} and `thumbs` the frames
    small (`curves`), for the astronomer's tests (item 7); each is optional, and the test that needs it is left out
    without it. `nulls` runs the slower of them (`controls_judged`'s windows, `injected`). `encoding(hz, amplitude, top)`,
    where given, is the planted-dot encoding control at a beat (`planted.at_beat`, its dots encoded once by `measure`):
    asked wherever one object's beat sits at the codec's rhythm, which only it can tell from the codec's (about 20 s, in
    that case alone), and of a beat of one object's own under the "paper" rule, of which it is a part, or with `nulls`;
    under the "paper" rule a beat the encoded dots make as well is not the object's. `lit`, where given, is each thing's
    light on every frame (`curves(lit=)`, item 13), written beside the brightness as "<name> white" and "<name> red"
    (the red only for a colour video; "<name> hot", the darkest pixels, in place of white on a black-hot display)."""
    names, lo = fields["tracks"], ns[0]
    k0 = {name: (a - lo, b - lo + 1) for name, (a, b) in fields["spans"].items()}
    for name in names:                                     # outside its own span a track's position is its end's held: not measured
        a, b = k0.get(name, (0, 0))
        raw[name] = [None] * a + raw[name][a:b] + [None] * (len(ns) - b)
    for name in list(raw):                                 # the background apertures go with the member seen longest
        if name.startswith("background"):
            a, b = k0.get(first, (0, 0))
            raw[name] = [None] * a + raw[name][a:b] + [None] * (len(ns) - b)
    # ---- the lost frames, the spectra and each object's beat (`beats_pass`): one pass -- or two, where a track's lost
    # frames looked like the troughs of its own beat (`lost_at_beat`, the first half of the rule). They are kept in the
    # first pass, and kept for good only where the beat the stage then finds is theirs (`at_the_troughs`: within
    # LOST_BAND of the troughs' own frequency, or its double); for every other track the second pass handles them as
    # lost, as before 2026-10-15. Set on the whole-video pass's 142 refused objects, measured again (2026-10-16): the
    # first half alone kept 44, the stage then found a beat on 5 -- PR097's three dark dots (beats 6.9, 6.7, 2.3 Hz at
    # troughs of 7.2, 6.7, 2.3) and two objects of PR149 whose beats (9.2, 4.8 Hz) were nowhere near their troughs'
    # 3.1 Hz -- and the other 39 would have said "the troughs of its own beat" of a beat that was never found.
    seg0 = {}
    for name, f in raw.items():
        idx = [k for k, v in enumerate(f) if v is not None]
        if idx:
            seg0[name] = (idx[0], idx[-1] + 1)
    cands = {}                                             # the tracks whose lost frames look like the troughs of a beat
    for name in names:
        if name not in seg0:
            continue
        s0, s1 = seg0[name]
        own = raw[name][s0:s1]
        if any(v is None for v in own) or np.median(own) <= 0:
            continue
        bad = lost(own, fps)
        if bad.any():
            at = lost_at_beat(own, bad, fps, lines)
            if at:
                cands[name] = at
    pic = fields.get("pictures") or dict(rate=fps, held=0.0, top_hz=TOP * fps / 2)
    top = pic["top_hz"]

    def beats_pass(trust):
        """From the lost frames to each object's beat, the troughs of the tracks in `trust` kept: the pass's state,
        or the Found that ends the stage. `F` is what the pass says of the fields, merged in once the pass stands."""
        F = {}
        # each curve's own stretch: the ends where an aperture leaves the frame are trimmed away (a bird flying out at
        # the frame's top, flyer 5's last frames); only a curve with a hole in the middle is refused below
        seg = dict(seg0)
        # where a track is lost against what is behind it (PR23, 2026-10-09: a hot roof), its ends are trimmed as well,
        # and the frames between are filled across in every curve measured with it -- `use`, which the spectra are taken
        # of; `raw` is what was measured, and is what the CSV keeps
        use, gone, too_lost = dict(raw), {}, {}
        for name in names:
            if name not in seg:
                continue
            s0, s1 = seg[name]
            own = raw[name][s0:s1]
            if any(v is None for v in own) or np.median(own) <= 0:
                continue                                   # refused below, as before
            bad = lost(own, fps)
            if not bad.any():
                continue
            a, b = 0, len(own)
            while a < b and bad[a]:
                a += 1
            while b > a and bad[b - 1]:
                b -= 1
            if name in trust:                              # the troughs of its own beat: kept, measured as they are
                F.setdefault("lost_at_beat", {})[name] = dict(cands[name], first=int(ns[s0 + a]), last=int(ns[s0 + b - 1]))
                gone[name] = []
                seg[name] = (s0 + a, s0 + b) if b > a else None
                if seg[name] is None:
                    del seg[name]
                    continue
                if name == first:                          # the apertures beside it go no further than it does
                    for m in [c for c in raw if c.startswith("background") and c in seg]:
                        seg[m] = (max(seg[m][0], seg[name][0]), min(seg[m][1], seg[name][1]))
                continue
            gone[name] = [s0 + k for k in range(a, b) if bad[k]]
            F.setdefault("lost", {})[name] = [int(ns[s0 + k]) for k in np.flatnonzero(bad)]
            if bad.sum() > LOST_MAX * len(own):
                too_lost[name] = (int(bad.sum()), len(own))
            seg[name] = (s0 + a, s0 + b) if b > a else None
            if seg[name] is None:
                del seg[name]
                continue
            for m in [name] + ([c for c in raw if c.startswith("background")] if name == first else []):
                if m not in seg:
                    continue
                f = list(use[m])
                if m != name:                              # the apertures beside it go no further than it does
                    seg[m] = (max(seg[m][0], seg[name][0]), min(seg[m][1], seg[name][1]))
                m0, m1 = seg[m]
                part = f[m0:m1]
                if gone[name] and not any(v is None for v in part):
                    mask = np.isin(np.arange(m0, m1), gone[name])
                    f[m0:m1] = filled(part, mask).tolist()
                use[m] = f
        F.update(frames=fields["frames"], first=fields["first"], last=fields["last"])
        if first in seg:
            s0, s1 = seg[first]
            if (s0, s1) != k0[first]:
                F["trimmed"] = dict(start=s0 - k0[first][0], end=k0[first][1] - s1)
            F.update(frames=s1 - s0, first=ns[s0], last=ns[s1 - 1])         # the stretch reported: the object's (the member seen longest)
        if not seg or max(b - a for a, b in seg.values()) < MIN_FRAMES:
            return Found("flicker", fields=dict(fields, **F, beats=None, finding=None),
                         no_power=[("flicker", f"{F['frames']} frames with the object's aperture inside the frame, under the {MIN_FRAMES} a beat needs")])
        spectra, per = {}, {}
        scale = None
        for name, f in use.items():                        # the object's (or members') first, then the background's
            bg = name.startswith("background")
            s = seg.get(name)
            own = f[s[0]:s[1]] if s else []
            ok = [v for v in own if v is not None]
            if len(ok) < len(own) or len(own) < MIN_FRAMES or (not bg and np.median(ok) <= 0) or (bg and not scale) or name in too_lost:
                per[name] = None
                continue
            if not bg and scale is None:
                scale = float(np.median(ok))               # the background apertures are measured in this
            fr, FF, band, wsum, _ = spectrum(own, fps, scale if bg else None)
            spectra[name] = dict(fr=fr, F=FF, band=band, wsum=wsum, peak=peak(own, fps, lines, scale if bg else None, err=not bg))
            per[name] = spectra[name]["peak"]
        obj = [n for n in names if per.get(n)]
        bgs = [n for n in raw if n.startswith("background") and per.get(n)]
        F["curves"] = per
        F["short"] = [n for n in names if n in seg and seg[n][1] - seg[n][0] < MIN_FRAMES]     # members too brief for a beat
        short_record = {}                                  # ... read anyway, for the short-record reading (item 8)
        for n in F["short"]:
            s0, s1 = seg[n]
            own = use[n][s0:s1]
            if s1 - s0 >= SHORT_MIN and not any(v is None for v in own) and np.median(own) > 0:
                short_record[n] = dict(short_reading(deviation(own, fps), fps, lines, top=top), frames=[int(ns[s0]), int(ns[s1 - 1])])
        if short_record:
            F["short_record"] = short_record
        if not obj:
            if too_lost:
                name, (k, n) = next(iter(too_lost.items()))
                why = (f"the object is lost against what is behind it on {k} of its {n} frames (its brightness over the ring "
                       f"under {DROP:.0%} of its own, or none), more than {LOST_MAX:.0%} of them: no beat is looked for")
            else:
                why = "the object is not brighter than the ring about it on every frame, or its aperture leaves the frame"
            return Found("flicker", fields=dict(fields, **F, beats=None, finding=None), no_power=[("flicker", why)])
        res = fps / max(1, F["frames"])                    # of the stretch reported: the object's (the member seen longest)
        if not bgs:
            return Found("flicker", fields=dict(fields, **F, beats=None, finding=None),
                         no_power=[("flicker", "no background aperture beside the object could be measured, so there is "
                                               "nothing to hold its beat against")])
        floor = float(np.median([per[b]["amplitude"] for b in bgs]))   # the scene's and the codec's own flicker
        F["noise_floor"] = floor
        # the beat in windows along the track, and what is reported for each object: the clearest window that passes
        # where it is clearer than the whole track, or where the whole track does not pass, else the whole track -- as a
        # fundamental with its double named. The whole track passes where its strongest beat is ABOVE the background's
        # and stands over its own drift (`drift`).
        F["windows"], F["beat"] = {}, {}
        F["top_hz"] = top
        whole_ok = {}
        for n in obj:
            s0, s1 = seg[n]
            own = {m: use[m][s0:s1] for m in [n] + bgs}
            d = drift(own[n], fps)
            per[n].update(over_drift=d["over"], drift_needed=d["needed"])
            per[n]["above_top"] = per[n]["hz"] > top
            def bg_at(hz, bgs=bgs, spectra=spectra):
                vals = [float(2 * np.abs(spectra[b]["F"][int(np.argmin(np.abs(spectra[b]["fr"] - hz)))]) / spectra[b]["wsum"]) for b in bgs]
                return float(np.median(vals)) if vals else float("inf")
            ok, read = whole_passes(own[n], per[n], fps, top, [own[b] for b in bgs], floor, None, scale, d, bg_at=bg_at)
            per[n].update(read)
            whole_ok[n] = ok
            wins = windows(own, n, bgs, ns[s0:s1], fps, lines, gone=[k - s0 for k in gone.get(n, [])], top=top)
            F["windows"][n] = wins
            passing = [w for w in wins if w["passes"]]
            best = max(passing, key=lambda w: w["stands"]) if passing else None
            fund, dbl, _, _ = harmonics(own[n], fps, drift_too=True)
            whole = dict(first=ns[s0], last=ns[s1 - 1], hz=fund, hz_err=per[n]["hz_err"] * fund / per[n]["hz"] if per[n]["hz"] else None,
                         double_hz=dbl, amplitude=per[n]["amplitude"], stands=per[n]["stands"],
                         resolution_hz=per[n]["resolution_hz"], source="the whole track")
            # the clearest window where it stands over the whole track, or the whole track fails -- but under the paper's
            # rule a whole track that passes is what is reported, as the paper read whole tracks (PR097's objects 3 and 7,
            # 2026-10-16: 6.86 and 6.63 Hz over the track, 6.50 and 4.84 in their clearest windows)
            if best is not None and (not whole_ok[n] or (best["stands"] > per[n]["stands"] and active_rule() != "paper")):
                pick = dict(first=best["first"], last=best["last"], hz=best["fundamental_hz"], hz_err=best["fundamental_err"],
                            double_hz=best["double_hz"], amplitude=best["amplitude"], stands=best["stands"],
                            resolution_hz=best["resolution_hz"],
                            source=f"the clearest of {len(passing)} windows of {WINDOW_S:g} s that beat, of {len(wins)}")
            else:
                pick = whole
            clear = [w for w in passing if best is not None and w["stands"] >= 0.5 * best["stands"]]     # the clear windows' range
            pick["hz_range"] = [min(w["fundamental_hz"] for w in clear), max(w["fundamental_hz"] for w in clear)] if clear else None
            pick["windows_passing"] = len(passing)
            pick["windows"] = len(wins)
            pick["windows_passing_by_resolution"] = sum(1 for w in wins if w["passes_by_resolution"])
            # does the beat come back (the headline rule, 2026-10-17): the whole track beats, or windows that do not
            # overlap agree -- one stretch is the weakest evidence the stage gives, dozens of windows a track at 1 in 100
            pick["whole_passes"] = bool(whole_ok[n])
            pick["windows_apart"] = apart_windows(passing)[0]
            pick["comes_back"] = bool(whole_ok[n] or pick["windows_apart"] >= 2)
            F["beat"][n] = pick
            # what amplitude a beat would need in this track's own noise, in closed form (D6): how faint a beat it can hear
            F.setdefault("analytic", {})[n] = analytic(per[n]["noise_rms"], s1 - s0, fps, top, floor=floor)
        strong = [n for n in obj if whole_ok[n] or F["beat"][n]["windows_passing"]]
        F["strong"] = strong
        return dict(F=F, seg=seg, use=use, gone=gone, too_lost=too_lost, spectra=spectra, per=per, obj=obj, bgs=bgs,
                    scale=scale, floor=floor, whole_ok=whole_ok, strong=strong, res=res)

    st = beats_pass(set(cands))
    if cands:                                              # kept for good only where the beat found is theirs
        kept = set() if isinstance(st, Found) else {n for n in cands if n in st["strong"] and at_the_troughs(st["F"]["beat"][n], cands[n])}
        if kept != set(cands):
            st = beats_pass(kept)
    if isinstance(st, Found):
        return st
    fields.update(st["F"])
    seg, use, gone, too_lost, spectra, per = st["seg"], st["use"], st["gone"], st["too_lost"], st["spectra"], st["per"]
    obj, bgs, scale, floor, whole_ok, strong, res = st["obj"], st["bgs"], st["scale"], st["floor"], st["whole_ok"], st["strong"], st["res"]
    # ---- the look-alikes (item 9; 2026-10-16): where a supply's or the sampling's own rhythm would sit ----------------
    try:                                                   # the clip's own sound, where it has any (`mcdonald audio`)
        from .audio import heard
        sound = heard(str(clip.video), fps)
    except Exception:                                      # the sound is never worth the stage
        sound = []
    table = lookalikes(fps, pic, top, heard=sound)
    fields["lookalikes"] = table
    for n in obj:
        b = fields["beat"][n]
        e = b.get("hz_err")
        b["lookalike"] = at_lookalikes(b["hz"], b["resolution_hz"], table, e)
        b["double_lookalike"] = (at_lookalikes(b["double_hz"], b["resolution_hz"], table, e * b["double_hz"] / b["hz"] if e is not None and b["hz"] else None)
                                 if b.get("double_hz") else [])
    # ---- the astronomer's tests (item 7; 2026-10-15): each beside the stage's own, in the fields -----------------
    held_k = set(pic.get("held_k") or [])
    astro = {}
    for n in obj:
        b = fields["beat"][n]
        s0, s1 = b["first"] - lo, b["last"] - lo + 1         # the stretch the beat is reported from (a window, or the whole track)
        if not (seg[n][0] <= s0 < s1 <= seg[n][1]):
            s0, s1 = seg[n]
        r = deviation(use[n][seg[n][0]:seg[n][1]], fps)[s0 - seg[n][0]:s1 - seg[n][0]]
        gone_n = set(gone.get(n, []))
        keep = np.array([k not in held_k and k not in gone_n for k in range(s0, s1)])
        A = dict(frames=[int(ns[s0]), int(ns[s1 - 1])], lombscargle=ls_peak(r, fps, keep, top=top), scramble=scrambled(r, fps, top=top),
                 common_mode=None, pixel_phase=None)
        cs = [c for c in bgs if c in seg]
        lo_, hi_ = max([s0] + [seg[c][0] for c in cs]), min([s1] + [seg[c][1] for c in cs])
        if cs and hi_ - lo_ >= MIN_FRAMES and not any(v is None for c in cs for v in use[c][lo_:hi_]):
            rr = deviation(use[n][seg[n][0]:seg[n][1]], fps)[lo_ - seg[n][0]:hi_ - seg[n][0]]
            scene = scene_curves(thumbs, positions, lo_, hi_, fps, ap_of(fields, n)) if thumbs else None
            resid, cm = common_mode(rr, np.stack([deviation(use[c][seg[c][0]:seg[c][1]], fps, scale)[lo_ - seg[c][0]:hi_ - seg[c][0]]
                                                  for c in cs]), scene=scene)
            mode = cm.pop("mode")
            before, after = _peak(rr, fps, lines), _peak(resid, fps, lines)
            own = _peak(mode, fps, lines) if mode is not None else None
            cm.update(frames=[int(ns[lo_]), int(ns[hi_ - 1])], before_hz=before["hz"], before_amplitude=before["amplitude"],
                      after_hz=after["hz"], after_amplitude=after["amplitude"], after_stands=after["stands"],
                      mode_hz=own["hz"] if own else None, mode_at_the_codec_line_hz=own["at_the_codec_line_hz"] if own else None)
            A["common_mode"] = cm
        if positions and n in positions:
            x, y = positions[n]
            resid, r2 = pixel_phase(r, x[s0:s1], y[s0:s1])
            q = _peak(resid, fps, lines)
            A["pixel_phase"] = dict(r2=r2, after_hz=q["hz"], after_amplitude=q["amplitude"])
        astro[n] = A
    fields["astro"] = astro
    # ---- the paper's continuum null (2026-10-16, ROADMAP.md 0.3): over the stretch each beat is reported from ---------
    cont = {}
    for n in obj:
        b = fields["beat"][n]
        s0, s1 = b["first"] - lo, b["last"] - lo + 1
        if not (seg[n][0] <= s0 < s1 <= seg[n][1]):
            s0, s1 = seg[n]
        r = deviation(use[n][seg[n][0]:seg[n][1]], fps)[s0 - seg[n][0]:s1 - seg[n][0]]
        cont[n] = dict(continuum(r, fps, top=top), frames=[int(ns[s0]), int(ns[s1 - 1])])
    fields["continuum"] = cont
    gated = []
    if GATE_ASTRO:                                           # the first two decide as well (off until the goldens are read with it)
        gated = [n for n in strong if not passes_astro(astro[n])]
        strong = [n for n in strong if n not in gated]
        fields["strong"], fields["gated"] = strong, gated
    # ---- the seismologist's tests (item 8; 2026-10-15): each beside the stage's own, in the fields -----------------
    seis, noise_arrays = {}, {}
    for n in obj:
        b = fields["beat"][n]
        s0, s1 = b["first"] - lo, b["last"] - lo + 1         # the stretch the beat is reported from, as the astronomer's tests take it
        if not (seg[n][0] <= s0 < s1 <= seg[n][1]):
            s0, s1 = seg[n]
        r = deviation(use[n][seg[n][0]:seg[n][1]], fps)[s0 - seg[n][0]:s1 - seg[n][0]]
        S = dict(frames=[int(ns[s0]), int(ns[s1 - 1])], line=line_test(r, fps, b["hz"], top=top, lines=lines), comb=None,
                 line_windows=line_windows(r, fps, b["hz"], top=top),
                 glide=dict(glide(deviation(use[n][seg[n][0]:seg[n][1]], fps), fps, b["hz"], b["double_hz"], top=top),
                            frames=[int(ns[seg[n][0]]), int(ns[seg[n][1] - 1])]),
                 sompi=sompi(r, fps, top=top),
                 onebit=onebit(r, fps, b["hz"], lines, top), coherence={}, noise=None)
        if S["line_windows"]["best_frames"]:                 # the comb from the lines of the window where the beat is clearest
            a0, a1 = S["line_windows"]["best_frames"]
            S["line_windows"]["frames"] = [int(ns[s0 + a0]), int(ns[s0 + a1])]
            B = line_test(r[a0:a1 + 1], fps, b["hz"], top=top, lines=lines)
            S["comb"] = comb(B["lines"], b["hz"], B["resolution_hz"])
            S["line_windows"]["best_lines"] = [dict(hz=q["hz"], p=q["p"], amplitude=q["amplitude"]) for q in B["lines"]]
        else:
            S["comb"] = comb(S["line"]["lines"], b["hz"], S["line"]["resolution_hz"])
        cs = [c for c in bgs if c in seg]
        lo_, hi_ = max([s0] + [seg[c][0] for c in cs]), min([s1] + [seg[c][1] for c in cs])
        if cs and hi_ - lo_ >= MIN_FRAMES and not any(v is None for c in cs for v in use[c][lo_:hi_]):
            rr = deviation(use[n][seg[n][0]:seg[n][1]], fps)[lo_ - seg[n][0]:hi_ - seg[n][0]]
            R = {c: deviation(use[c][seg[c][0]:seg[c][1]], fps, scale)[lo_ - seg[c][0]:hi_ - seg[c][0]] for c in cs}
            S["coherence"] = {c: coherence_at(rr, R[c], fps, b["hz"]) for c in cs}
            sc = scene_curves(thumbs, positions, lo_, hi_, fps, ap_of(fields, n)) if thumbs else None
            if sc is not None:                               # the frame's own level and contrast: the camera's channels
                S["coherence"]["scene level"] = coherence_at(rr, sc[0], fps, b["hz"])
                S["coherence"]["scene contrast"] = coherence_at(rr, sc[1], fps, b["hz"])
            S["noise"], noise_arrays[n] = noise_pdf(np.stack(list(R.values())), fps, b["hz"], obj=rr)
        seis[n] = S
    fields["seis"] = seis
    # ---- steady as a clock, or not (item 12; 2026-10-20): over the whole stretch each object was followed over, each
    # piece's frequency looked for about the beat's -- not over the beat's own stretch, which is a single 2-s window
    # where that is clearer than the whole track (PR135's C-F), too short to split
    steady = {}
    for n in obj:
        s0, s1 = seg[n]
        steady[n] = dict(steadiness(deviation(use[n][s0:s1], fps), fps, fields["beat"][n]["hz"]),
                         frames=[int(ns[s0]), int(ns[s1 - 1])])
    fields["steadiness"] = steady
    fields["in_step"] = None
    if len(strong) > 1:
        lo_, hi_ = max(seg[m][0] for m in strong), min(seg[m][1] for m in strong)
        if hi_ - lo_ >= MIN_FRAMES:
            hz_ = float(np.median([fields["beat"][m]["hz"] for m in strong]))
            together = {m: deviation(use[m][seg[m][0]:seg[m][1]], fps)[lo_ - seg[m][0]:hi_ - seg[m][0]] for m in strong}
            fields["in_step"] = dict(in_step(together, hz_, fps), frames=[int(ns[lo_]), int(ns[hi_ - 1])])
    gated_s = []
    if GATE_SEIS:                                            # the line test decides as well (off until the goldens are read with it)
        gated_s = [n for n in strong if not passes_seis(seis[n])]
        strong = [n for n in strong if n not in gated_s]
        fields["strong"], fields["gated_seis"] = strong, gated_s
    ctrl, far = controls_judged(use, seg, bgs, ns, fps, lines, scale, top, gone=gone.get(first, ()), windows_too=nulls)
    fields["controls"], fields["false_alarm"] = ctrl, far
    if nulls:
        fields["injection"] = injected(use, seg, bgs, fps, lines, scale, top)
        fields["slice"] = sliced(use, seg, bgs, fps, lines, scale, top)
    folds, drawn = {}, []
    if stamps:
        for n in obj:
            b = fields["beat"][n]
            a, c = b["first"] - lo, b["last"] - lo + 1       # the stretch the beat is reported from, as places in ns
            s0, s1 = seg[n]
            if not (s0 <= a < c <= s1) or n not in stamps:
                continue
            r = deviation(use[n][s0:s1], fps)[a - s0:c - s0]
            ctrls = [deviation(use[cc][a:c], fps, scale) for cc in bgs
                     if cc in seg and seg[cc][0] <= a and seg[cc][1] >= c and not any(v is None for v in use[cc][a:c])]
            at = None
            if positions and n in positions:
                x, y = positions[n]
                at = (float(np.median(x[a:c])) / THUMB, float(np.median(y[a:c])) / THUMB,
                      (float(np.ptp(x[a:c])) / 2 + ap_of(fields, n) + 8) / THUMB, (float(np.ptp(y[a:c])) / 2 + ap_of(fields, n) + 8) / THUMB)
            numbers, pics = fold(r, b["hz"], fps, stamps[n][a:c], thumbs[a:c] if thumbs else None, ap=ap_of(fields, n), at=at, controls=ctrls)
            cmap, pm = phase_map(stamps[n][a:c], r, b["hz"], fps, ap_of(fields, n))      # item 8: the same, by phase
            if pm:
                numbers.update(pm)
            pics = tuple(pics) + (cmap,)
            folds[n] = numbers
            if n in strong:
                drawn.append((n, numbers, pics))
    fields["fold"] = folds
    # ---- a rotor's look (item 14, 2026-10-25): the beat reaching the background beside the object in step, or the light
    # that beats sitting off the object's middle -- a rotor disc, or the air it drives, reaches past the body; a bird's wings
    # do not. A reading beside the headline, as the flame's is: chosen on eight helicopter calls, not yet held to others
    for n in obj:
        coh = {c: v["gamma2"] for c, v in ((seis.get(n) or {}).get("coherence") or {}).items()
               if c.startswith("background") and v and v.get("gamma2") is not None}
        best = max(coh, key=coh.get) if coh else None
        off = (folds.get(n) or {}).get("offset_px")
        marked = (["background"] if best is not None and coh[best] >= ROTOR_COHERENCE else []) + \
                 (["off its middle"] if off is not None and off >= ROTOR_OFFSET_PX else [])
        fields["beat"][n]["rotor"] = dict(coherence=coh.get(best) if best else None, background=best, offset_px=off, marked=marked)
        if marked and n in strong:
            say(f"  {n}: " + rotor_said(fields["beat"][n]["rotor"]) + " (a reading, not a test)")
    # the background shares the beat if, at the object's own frequency over the whole track, it beats half as strongly
    # or more -- asked of every object with a beat, wherever the beat reported comes from, as is the codec's rhythm
    def at(name, hz):
        S = spectra[name]
        k = int(np.argmin(np.abs(S["fr"] - hz)))
        return float(2 * np.abs(S["F"][k]) / S["wsum"])
    shared = [b for b in bgs if any(at(b, per[n]["hz"]) >= SHARED * per[n]["amplitude"] for n in strong)]
    pairs = common(use, seg, obj, ns, fps, lines) if len(obj) > 1 else []
    fields["pairs"] = pairs
    at_line = [n for n in strong if per[n]["at_the_codec_line_hz"] is not None]
    npw, notes = [], []
    if not strong:
        over = [n for n in obj if per[n]["amplitude"] >= ABOVE * floor]
        if gated:
            b = fields["beat"][gated[0]]
            beats, why = False, (f"what beats at {b['hz']:.2f} Hz, {b['amplitude']:.0%} of its brightness, does not pass the "
                                 f"astronomer's tests: " + "; ".join(disagreements(gated, astro, None)) + ": no beat of its own")
        elif gated_s:
            b = fields["beat"][gated_s[0]]
            beats, why = False, (f"what beats at {b['hz']:.2f} Hz, {b['amplitude']:.0%} of its brightness, does not pass the "
                                 f"seismologist's line test: " + "; ".join(disagreements_seis(gated_s, seis)) + ": no beat of its own")
        elif over and per[over[0]]["above_top"]:
            p = per[over[0]]
            held = (f"it holds pictures ({pic['held']:.0%} of frames repeat the one before) and carries {pic['rate']:.1f} "
                    "a second, so " if pic["held"] >= HELD_MIN else "")
            beats, why = False, (f"its strongest, at {p['hz']:.2f} Hz, is above the highest frequency this video can carry as "
                                 f"a beat: {held}a beat is heard only up to {top:.1f} Hz ({TOP:g} of the Nyquist frequency), "
                                 f"and nothing below that beats: no beat of its own in {fields['frames']} frames")
        elif over and per[over[0]]["edge"]:
            p = per[over[0]]
            beats, why = False, (f"its strongest, at {p['hz']:.2f} Hz, is only the edge of the band a beat is looked for in: "
                                 f"its brightness changes more slowly than {LOW:g} Hz, which is not a beat, and no window of "
                                 f"{WINDOW_S:g} s along the track beats: no beat of its own in {fields['frames']} frames")
        elif over:
            p = per[over[0]]
            beats, why = False, (f"what peaks at {p['hz']:.2f} Hz, {p['amplitude']:.0%} of its brightness, is no more than "
                                 f"a brightness that only wanders slowly makes there once its running mean is taken out "
                                 f"(it stands {p['over_drift']:.1f} times over that, where {p['drift_needed']:.1f} would be a "
                                 f"beat), and no window of {WINDOW_S:g} s along the track beats: no beat of its own in "
                                 f"{fields['frames']} frames")
        else:
            beats, why = False, (f"no beat reaches {ABOVE:g} times what the background beside it does ({floor:.1%} of the "
                                 f"object's brightness, the median of their strongest) in {len(ns)} frames "
                                 f"({len(ns) / fps:.1f} s, resolution {res:.2f} Hz)")
    elif shared:
        beats, why = None, (f"the background beside it beats at the same frequency ({', '.join(shared)}): "
                            "not the object's own")
        npw.append(("flicker", why))
    elif len(obj) > 1:
        if any(p["independent"] for p in pairs if set(p["members"]) <= set(strong)):
            beats, why = True, ("members over the same frames beat at different frequencies or out of step, which a "
                                "rhythm of the video cannot do: the beat is theirs")
        elif not pairs:
            beats, why = None, (f"no two members share the {MIN_FRAMES} frames it takes to hear whether they beat as one")
            npw.append(("flicker", why))
        else:
            beats, why = None, ("the members beat as one, at one frequency and in step: a rhythm of the video would do "
                                "that" + (f", and it is at the codec's {at_line and per[at_line[0]]['at_the_codec_line_hz']:g} Hz"
                                          if at_line else ""))
            npw.append(("flicker", why))
    elif at_line:
        n_ = at_line[0]
        e = encoding(per[n_]["hz"], per[n_]["amplitude"], top) if encoding is not None else None
        if e is not None:
            fields.setdefault("encoding", {})[n_] = e
        if e and e.get("clears"):
            b = fields["beat"][n_]
            beats, why = True, (f"it beats at {_pm(b['hz'], b.get('hz_err'))}" + (f" (and at {b['double_hz']:.2f}, its double)" if b["double_hz"] else "")
                                + f", {b['amplitude']:.0%} of its brightness, over frames {b['first']}–{b['last']}"
                                + (f" ({b['source']})" if b["source"] != "the whole track" else "")
                                + f", within {Z_LINE:g} of its errors of the codec's {per[n_]['at_the_codec_line_hz']:g} Hz -- but constant dots "
                                f"planted in the clip's own frames and encoded like it reach at most {e['at_beat_max']:.1%} there, "
                                f"{e['ratio']:.0f} times less" + (" (the encoder's own faint line there)" if e.get("line_at_beat") else "")
                                + ": the encoder does not make it, and the background beside it does not share it")
        else:
            beats, why = None, (f"it beats at {_pm(per[n_]['hz'], per[n_].get('hz_err'))}, within {Z_LINE:g} of its errors of the codec's "
                                f"{per[n_]['at_the_codec_line_hz']:g} Hz, and there is one thing, so nothing tells the "
                                "two apart" + (f" (the encoding control: {e['skipped']})" if e and e.get("skipped") else
                                               (f" -- constant dots encoded like the clip reach {e['at_beat_max']:.1%} there, "
                                                f"against its {e['amplitude']:.1%}" + (", with a line at it" if e.get("line_at_beat") else "")
                                                if e else "")))
            npw.append(("flicker", why))
    else:
        b = fields["beat"][strong[0]]
        beats, why = True, (f"it beats at {_pm(b['hz'], b.get('hz_err'))}" + (f" (and at {b['double_hz']:.2f}, its double)" if b["double_hz"] else "")
                            + f", {b['amplitude']:.0%} of its brightness, over frames {b['first']}–{b['last']}"
                            + (f" ({b['source']})" if b["source"] != "the whole track" else "")
                            + ", clear of the codec's rhythm and not shared by the background beside it"
                            + ("" if b.get("comes_back", True) else
                               "; that is one stretch: the whole track does not beat, and no window apart from it does"))
    if fields.get("lost_at_beat"):
        for n, d in fields["lost_at_beat"].items():
            why += (f"; on {d['frames']} frames{' (' + n + ')' if len(names) > 1 else ''} its brightness over the ring fell under "
                    f"{DROP:.0%} of its level, but in {d['runs']} runs, mostly short, at the troughs of its own {d['hz']:.2f}-Hz beat "
                    f"({d['share']:.0%} of them in the lower half of the cycle): they are its beat, kept")
        notes.append("Frames where the object fell under the ring's level came in short runs, one per cycle, at the troughs of "
                     "its own strongest beat, so they were kept and measured as they are (a dark object beating hard goes under "
                     "its ring at every trough). A crossing (one run of several frames) is still left out as before.")
    for n in (strong if beats is True else []):            # a beat of the object's own that sits where a look-alike would
        b = fields["beat"][n]
        la = b.get("lookalike") or []
        if not la:
            continue
        who = f" ({n})" if len(names) > 1 else ""
        at_lines = [d for d in la if d.get("band") is None]
        at_bands = [d for d in la if d.get("band") is not None]
        where = " and ".join(([f"where {', or '.join(d['what'] for d in at_lines)} would appear through this frame rate"] if at_lines else [])
                             + ([f"inside the band of {', or of '.join(d['what'] for d in at_bands)}"] if at_bands else []))
        why += f"; its {b['hz']:.2f} Hz{who} is also {where}: a look-alike, marked, not refused"
        rng = b.get("hz_range")
        line = ((fields.get("seis") or {}).get(n) or {}).get("line") or {}
        steady = (f"this one ranges {rng[0]:.2f}-{rng[1]:.2f} Hz across the windows that beat" if rng and rng[1] - rng[0] > 0 else
                  f"this one holds one frequency across the windows that beat") if rng else "this one was read over one stretch"
        held = ""
        if line.get("p") is not None:
            held = (" and the seismologist's line test finds a stationary line over the whole stretch" if line["p"] <= MT_P else
                    " and the seismologist's line test finds no stationary line over the whole stretch, as a wingbeat's wander gives")
        st = (fields.get("steadiness") or {}).get(n) or {}
        if st.get("p") is not None:
            parts = "halves" if st["pieces"] == 2 else f"{st['pieces']} pieces"
            clock = (f"; and of {STEADY_RUNS} steady beats planted at its frequency in its own noise, only {st['p']:.1%} come "
                     f"apart between its {parts} as far as it does (p {st['p']:.3f}): it wanders more than a clock can" if st["wanders"] else
                     f"; and of {STEADY_RUNS} steady beats planted at its frequency in its own noise, {st['p']:.0%} come apart "
                     f"between its {parts} as far as it does (p {st['p']:.2f}), so steadiness cannot tell it from a supply's "
                     "line or a rhythm of the frames")
        elif st.get("why"):
            clock = f"; its steadiness against a clock was not read ({st['why']})"
        else:
            clock = ""
        notes.append(f"The beat at {b['hz']:.2f} Hz{who} sits {where} (fields.lookalikes has the whole table for it). A look-alike "
                     "is marked, not refused: a bird can beat there too. What tells a supply's line from a wingbeat: a supply holds "
                     f"its frequency, a wingbeat's wanders -- {steady}{held}{clock}.")
    cover = [d for d in fields.get("lookalikes") or [] if d.get("covers")]
    if beats is True and cover:                            # item 11: the bands that fold over everything, said once
        notes.append("Folded through this frame rate, " + ", ".join(d["what"] for d in cover) + " could each land anywhere in "
                     "the band a beat is looked for in, so a beat's frequency alone excludes none of them (fields.lookalikes, "
                     "`covers`). Not a frequency but the rest of the case tells them from a wingbeat.")
    if beats is True and encoding is not None and len(obj) == 1 and (nulls or active_rule() == "paper"):   # one object's own beat
        for n_ in strong[:1]:
            if n_ not in (fields.get("encoding") or {}):
                b = fields["beat"][n_]
                fields.setdefault("encoding", {})[n_] = encoding(b["hz"], b["amplitude"], top)
            e = fields["encoding"][n_]
            if e and not e.get("skipped") and not e.get("clears"):
                said_e = (f"constant dots planted in the clip's own frames and encoded like it reach {e['at_beat_max']:.1%} within "
                          f"0.5 Hz of its beat, against its {e['amplitude']:.1%}" + (", and one has a line there" if e.get("line_at_beat") else ""))
                if active_rule() == "paper":
                    beats, why = None, f"the encoder may make it: {said_e}"
                    npw.append(("flicker", why))
                else:
                    notes.append(f"The encoding control does not clear the beat: {said_e}. Under the paper's rule it would not be the object's own.")
    if beats is True:                                      # where the astronomer's tests disagree with the stage, the notes say so
        off = disagreements(strong, astro, far)
        if off:
            notes.append("The astronomer's checks disagree with the beat: " + "; ".join(off) + ". They are reported with the "
                         "measurement and do not yet decide it.")
        off = disagreements_seis(strong, seis, fields.get("in_step"), independent=len(obj) > 1)
        if off:
            notes.append("The seismologist's checks disagree with the beat: " + "; ".join(off) + ". They are reported with the "
                         "measurement and do not yet decide it.")
    if fields.get("lost"):
        where = "; ".join(_frames(v) + (f" ({n})" if len(names) > 1 else "") for n, v in fields["lost"].items())
        why += f"; frames {where}, where it was lost against what is behind it, are left out"
        notes.append(f"Lost against what is behind it (its brightness over the ring under {DROP:.0%} of its own level, "
                     f"or none) on frames {where}: left out of the spectra -- filled across from the frames either side, or "
                     "trimmed at the ends -- and no window holding one is used. What a crossing does to the contrast is "
                     "the background's, not the object's.")
    fields.update(beats=beats, finding=why, resolution_hz=res)
    notes.append("A beat that is the object's own says it varies; it does not say it is a wingbeat. A tumbling or "
                 "rotating body beats too, and so does a light that blinks.")
    result = {n: ("" if n in strong else "strongest peak ")
              + _pm(fields['beat'][n]['hz'], fields['beat'][n].get('hz_err'))
              + (f" (and {fields['beat'][n]['double_hz']:.2f}, its double)" if fields["beat"][n]["double_hz"] else "")
              + f", {fields['beat'][n]['amplitude']:.1%}, {fields['beat'][n]['stands']:.0f}x the band, frames "
              f"{fields['beat'][n]['first']}–{fields['beat'][n]['last']}"
              + (f" (at the codec's {per[n]['at_the_codec_line_hz']:g} Hz)" if per[n]["at_the_codec_line_hz"] else "")
              + ("" if n in strong else "; no beat of its own")
              for n in obj}
    result["finding"] = why
    files = []
    if out:
        with open(f"{out}_flicker.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            hot = "hot" if fields.get("black_hot") else "white"
            lit_cols = [(c, j, f"{c} {hot if j == 0 else 'red'}") for c in (lit or {}) for j in (0, 1)
                        if len(lit[c]) == len(ns) and any(q is not None and q[j] is not None for q in lit[c])]
            w.writerow(["frame", "t_s"] + list(raw) + [h for *_, h in lit_cols])
            for k, n in enumerate(ns):
                w.writerow([n, round((n - 1) / fps, 4)] + ["" if raw[c][k] is None else round(raw[c][k], 2) for c in raw]
                           + ["" if lit[c][k] is None or lit[c][k][j] is None else round(lit[c][k][j], 2) for c, j, _ in lit_cols])
        files.append(f"{out}_flicker.csv")
        say(f"wrote {out}_flicker.csv")
        if beats is True:                    # a beat the stage calls the object's own is drawn with its controls (PR41, 2026-10-10)
            try:
                from . import figures
                files.append(figures.beat(f"{out}_beat.png", fps, ns, use, seg, scale, fields["beat"], strong, bgs,
                                          lines, trend=trend_frames(fps)))
                say(f"wrote {out}_beat.png")
            except Exception as e:           # a figure that cannot be drawn does not undo the measurement
                say(f"  ! the beat figure was not drawn: {type(e).__name__}: {e}")
            if drawn:
                try:
                    from . import figures
                    files.append(figures.fold(f"{out}_fold.png", drawn, fps))
                    say(f"wrote {out}_fold.png")
                except Exception as e:
                    say(f"  ! the fold figure was not drawn: {type(e).__name__}: {e}")
            rows = [(n, noise_arrays[n], fields["beat"][n]["hz"], lines, seis[n]["noise"]) for n in strong if noise_arrays.get(n) is not None]
            if rows:
                try:
                    from . import figures
                    files.append(figures.noise(f"{out}_noise.png", rows, fps))
                    say(f"wrote {out}_noise.png")
                except Exception as e:
                    say(f"  ! the noise figure was not drawn: {type(e).__name__}: {e}")
    return Found("flicker", result, fields, files=files, no_power=npw, notes=notes)


def _frames(ks):
    """Frame numbers as runs: [131, 132, 133, 138] -> "131–133 and 138"."""
    runs = []
    for k in sorted(ks):
        if runs and k == runs[-1][1] + 1:
            runs[-1][1] = k
        else:
            runs.append([k, k])
    said = [f"{a}–{b}" if b > a else f"{a}" for a, b in runs]
    return ", ".join(said[:-1]) + " and " + said[-1] if len(said) > 1 else said[0]


def of_member(group, name, folder, track=None):
    """A member of a group followed on its own (`several.split_group`): its flicker stage, read from
    the group's (`group`: that stage's fields), where it was measured over its own frames beside its
    fellows. The beat is its own where it is out of step with another member's, or at another frequency
    -- the test a flock allows that one thing alone does not (PR135, 2026-10-08: alone, three of the
    paper's six birds are vetoed by the codec's line or the bird beside them). Nothing is read from the
    video here."""
    beat = (group.get("beat") or {}).get(name)
    pairs = [q for q in group.get("pairs") or [] if name in q["members"]]
    span = (group.get("spans") or {}).get(name)
    frames = len(track) if track else (span[1] - span[0] + 1 if span else 0)
    fields = dict(codec=group.get("codec"), frames=frames, first=span[0] if span else None, last=span[1] if span else None,
                  tracks=["object"], curves={"object": (group.get("curves") or {}).get(name)}, pairs=pairs,
                  resolution_hz=(beat or {}).get("resolution_hz"),
                  aperture_px=(lambda a: a.get(name) if isinstance(a, dict) else a)(group.get("aperture_px")),
                  of_group=dict(folder=folder, member=name, members=len(group.get("beat") or {}), beats=group.get("beats")))
    npw, notes = [], [f"Measured with the other members of its group ({folder}), each over its own frames, in the group's "
                      "flicker stage: a beat is its own where it is at another frequency, or out of step, from a fellow's, "
                      "which a rhythm of the video cannot do."]
    with_ = lambda q: q["members"][1] if q["members"][0] == name else q["members"][0]
    strong = group.get("strong")                           # a case from before 2026-10-09 has none: its beats passed then
    if not beat or (strong is not None and name not in strong):
        if name in (group.get("short") or []):
            why = f"seen on {frames} frames, under the {MIN_FRAMES} a beat needs"
        else:
            why = ("no beat in the group's flicker stage: not brighter than the ring about it on every frame, or nothing past "
                   "the background beside it and its own slow change")
        npw.append(("flicker", why))
        return Found("flicker", dict(finding=why), dict(fields, beat={}, beats=None, finding=why), no_power=npw, notes=notes)
    apart = [q for q in pairs if q["independent"]]
    shown = f"{beat['hz']:.2f} Hz" + (f" (and at {beat['double_hz']:.2f}, its double)" if beat.get("double_hz") else "")
    if apart:
        beats = True
        why = (f"it beats at {shown}, {beat['amplitude']:.0%} of its brightness, over frames {beat['first']}–{beat['last']}; "
               f"out of step with, or at another frequency from, {', '.join(with_(q) for q in apart)} of its group: the beat is its own")
    elif pairs:
        beats = None
        why = (f"it beats at {shown}, as one with {', '.join(with_(q) for q in pairs)} of its group, at one frequency and in step: "
               "a rhythm of the video would do that")
        npw.append(("flicker", why))
    else:
        beats = None
        why = f"it beats at {shown}, and no other member shares the {MIN_FRAMES} frames it takes to hear whether the beat is its own"
        npw.append(("flicker", why))
    result = {"object": f"{shown}, {beat['amplitude']:.1%}, {beat['stands']:.0f}x the band, frames {beat['first']}–{beat['last']}",
              "finding": why}
    return Found("flicker", result, dict(fields, beat={"object": beat}, beats=beats, finding=why), no_power=npw, notes=notes)


def said(fields):
    """What `mcdonald flicker` prints, from the fields."""
    L = []
    g = fields.get("codec")
    if g:
        L.append(f"the codec: an I frame every {g['i_period']:g}, an anchor every {g['anchor_period']:g}"
                 + (f"; its rhythm at {', '.join(f'{v:g}' for v in g['lines_hz'])} Hz" if g["lines_hz"] else
                    "; no rhythm of its anchors under Nyquist"))
    if fields.get("frames"):
        L.append(f"frames {fields['first']}-{fields['last']}: {fields['frames']}, resolution "
                 f"{fields.get('resolution_hz') or 0:.2f} Hz")
    for name, p in (fields.get("curves") or {}).items():
        if p:
            L.append(f"  {name}: {_pm(p['hz'], p.get('hz_err'))}, {p['amplitude']:.1%} of {'the object' if name.startswith('background') else 'its'}"
                     f" brightness, {p['stands']:.0f} times the "
                     f"band's median" + (f", {p['over_drift']:.1f} times what its drift makes there ({p['drift_needed']:.1f} needed)"
                                         if p.get("over_drift") is not None else "")
                     + (f"  -- at the codec's {p['at_the_codec_line_hz']:g} Hz" if p["at_the_codec_line_hz"] else ""))
        else:
            L.append(f"  {name}: not measured (not brighter than its ring on every frame, lost against what is behind it too "
                     "often, or off the frame)")
    for name, ks in (fields.get("lost") or {}).items():
        L.append(f"  {name}: lost against what is behind it on frames {_frames(ks)}, left out")
    for name, d in (fields.get("lost_at_beat") or {}).items():
        L.append(f"  {name}: under its ring on {d['frames']} frames in {d['runs']} runs, mostly short, at the troughs of its own "
                 f"{d['hz']:.2f}-Hz beat ({d['share']:.0%} in the lower half of the cycle): kept, not left out")
    if fields.get("lookalikes"):
        las = fields["lookalikes"]
        L.append("  look-alikes at this frame rate: " + ", ".join(f"{d['hz']:.2f} Hz ({d['source']})" for d in las if d.get("band") is None))
        bands = [d for d in las if d.get("band") is not None]
        if bands:
            L.append("  look-alike bands at this frame rate: " + "; ".join(
                f"{', '.join(f'{a:.2f}-{z:.2f}' for a, z in d['band'])} Hz ({d['source']}{', the whole band: marks nothing' if d.get('covers') else ''})"
                for d in bands))
    for name, b in (fields.get("beat") or {}).items():
        if b.get("lookalike"):
            L.append(f"  {name}: its {b['hz']:.2f} Hz is at a look-alike (within its resolution, or its errors for a rhythm locked to the frames) -- "
                     + "; ".join(d["what"] for d in b["lookalike"]) + " -- marked, not refused")
        st = (fields.get("steadiness") or {}).get(name) or {}
        if st.get("p") is not None:
            L.append(f"  {name}: steadiness over frames {st['frames'][0]}-{st['frames'][1]}, in {st['pieces']} pieces at "
                     + ", ".join(f"{h:.3f}" for h in st["hz"]) + f" Hz: {st['stat']:.2f} apart in their bounds against "
                     + (f"{st['clock_99']:.2f} for 99 in 100 steady clocks, " if st.get("clock_99") is not None else "")
                     + f"p {st['p']:.3f} -- " + ("wanders more than a clock can" if st["wanders"] else "no more than a clock's"))
        elif st.get("why"):
            L.append(f"  {name}: steadiness not read -- {st['why']}")
        sh = (fields.get("scene_shift") or {}).get(name) or {}
        if sh.get("at_beat_px") is not None:
            L.append(f"  {name}: the scene moves {sh['at_beat_px']:.4f} px at its {sh['hz']:.2f} Hz (stands {sh['stands']:.0f}; a "
                     f"planted {sh['planted_px']:g} px read {sh['recovered']:.2f} of itself)"
                     + (f", its own centroid {sh['own_px']:.3f} px" if sh.get("own_px") is not None else "")
                     + (" -- the sensor moves at the beat" if sh.get("moves") else ""))
        L.append(f"  {name}, in windows of {WINDOW_S:g} s along the track: {b['windows_passing']} of {b['windows']} beat"
                 + (f" ({b['windows_passing_by_resolution']} by the codec's mark at the resolution, the rule until 2026-10-17)"
                    if b.get("windows_passing_by_resolution") is not None and b["windows_passing_by_resolution"] != b["windows_passing"] else "")
                 + (f", at {b['hz_range'][0]:.2f}-{b['hz_range'][1]:.2f} Hz" if b.get("hz_range") else "")
                 + ("; reported: " if name in fields.get("strong", [name]) else "; no beat of its own, the strongest: ")
                 + _pm(b["hz"], b.get("hz_err")) + (f" and its double {b['double_hz']:.2f}" if b["double_hz"] else "")
                 + f", {b['amplitude']:.1%}, {b['stands']:.0f}x, frames {b['first']}-{b['last']} ({b['source']})")
    for name, a in (fields.get("analytic") or {}).items():
        secs = (a.get("seconds_for") or {}).get("0.1")
        L.append(f"  {name}, in closed form: a beat needs {a['amplitude']:.1%} of its brightness to be heard {a['complete']:.0%} of the "
                 f"time over its {a['frames']} frames of noise ({a['sigma']:.1%} a frame)"
                 + (f", {a['with_floor']:.1%} with the background's own flicker" if a.get("with_floor") is not None else "")
                 + (f"; one of 10 % needs {secs:g} s" if secs is not None else "; one of 10 % is not heard in 200 s"))
    for q in fields.get("pairs") or []:
        L.append(f"  {q['members'][0]} x {q['members'][1]}: {_pm(q['hz'][0], (q.get('hz_err') or [None, None])[0])} and "
                 f"{_pm(q['hz'][1], (q.get('hz_err') or [None, None])[1])}"
                 + (f", {q['apart_z']:.1f} of their errors apart ({q['z_needed']:.1f} needed)" if q.get("apart_z") is not None else "")
                 + f", {q['phase_deg']:+.0f} deg apart at {q['cross_hz']:.2f}"
                 + (f" over frames {q['frames'][0]}-{q['frames'][1]}" if q.get("frames") else "")
                 + ("  (independent)" if q["independent"] else ""))
    if fields.get("short"):
        L.append(f"  too brief for a beat (under {MIN_FRAMES} frames): " + ", ".join(fields["short"]))
    for name, e in (fields.get("encoding") or {}).items():
        if e and e.get("skipped"):
            L.append(f"  {name}, the encoding control: {e['skipped']}")
        elif e:
            L.append(f"  {name}, the encoding control: {e['clean']} constant dots encoded like the clip reach at most "
                     f"{e['at_beat_max']:.1%} within 0.5 Hz of its {e['hz']:.2f} Hz, against its {e['amplitude']:.1%} "
                     f"({e['ratio']:.1f} times)" + ("; one has a line there" if e.get("line_at_beat") else "")
                     + (": the encoder does not make it" if e.get("clears") else ": not cleared"))
    for name, c in (fields.get("continuum") or {}).items():
        if c.get("p") is not None:
            L.append(f"  {name}, the paper's continuum null over frames {c['frames'][0]}-{c['frames'][1]}: its strongest, "
                     f"{c['hz']:.2f} Hz, stands {c['ratio']:.1f} times over the power law of its own spectrum; {c['p']:.3f} of "
                     f"{c['runs']} noise curves of that continuum stand as high anywhere in the band ({c['needed99']:.1f} would be "
                     f"1 in 100)")
    for name, k in (fields.get("blink") or {}).items():
        cur = k.get("curves") or {}
        bits = []
        for which, word in BLINK_CURVES:
            c = cur.get(which)
            if not c:
                continue
            bits.append(f"{word} {c['flashes']} flash{'es' if c['flashes'] != 1 else ''}"
                        + (f", {c['hz']:.2f} Hz p {c['p']:.4f}" if c.get("p") is not None else ""))
        if bits:
            L.append(f"  {name}, flashes (item 13): " + "; ".join(bits)
                     + (f" -- a train at {k['hz']:.2f} Hz, {k['per_minute']:.0f} a minute"
                        + (" (an anti-collision light's rate)" if k.get("rule") == "anti-collision" else
                           " (two anti-collision lights overlapping)" if k.get("rule") == "overlap" else "")
                        + ("; the background shares it" if k.get("shared") else "")
                        + (f"; the beat keeps {k['beat_kept']:.0%} without the flashes" if k.get("beat_kept") is not None else "")
                        if k.get("train") else " -- no train"))
    L += said_astro(fields)
    L += said_seis(fields)
    if fields.get("finding"):
        L.append(fields["finding"])
    return L


# ---- CLI ----------------------------------------------------------------------------
def main():
    import argparse

    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--track", help="CSV with frame and x/y columns: the object")
    ap.add_argument("--members", help="a groups _members.csv (frame, member, x_px, y_px): each member's beat, and "
                                      "whether they beat as one")
    ap.add_argument("--workdir")
    ap.add_argument("--n0", type=int)
    ap.add_argument("--n1", type=int)
    ap.add_argument("--dark", action="store_true", help="the object is darker than what is round it")
    ap.add_argument("--black-hot", action="store_true",
                    help="the clip is a black-hot thermal display (hot is dark): a light, which is hot, is looked for in the "
                         "darkest pixels (item 13)")
    ap.add_argument("--aperture", metavar="R[,R1,R2[,BG]]",
                    help="measure in a fixed disc of R px, its background the median of the ring R1-R2 px, the background "
                         "apertures BG px away, never re-centred (default: an aperture that follows the object's size)")
    ap.add_argument("--avoid", metavar="TRACK.csv[,TRACK.csv...]",
                    help="other tracked things in the video, not measured: the background apertures keep clear of them")
    ap.add_argument("--beat-rule", choices=RULES, default=None,
                    help=f"how a beat is judged: stage (the default) -- {ABOVE:g} times the background beside it and the drift "
                         "test; paper -- the bird paper's continuum null, the background at the beat's own frequency, and the "
                         "planted-dot encoding control")
    ap.add_argument("--out", metavar="DIR", help="case directory for results (default: ./<tag>, or $MCDONALD_CASES/<tag>)")
    ap.add_argument("--procs", type=int, default=None, help=PROCS_HELP)
    ap.add_argument("--no-nulls", action="store_true", help="skip the slower controls: the background apertures through "
                                                            "every window as if each were the object, and beats planted in them")
    ap.add_argument("--scene-shift", action="store_true",
                    help="also read the scene's own motion at each beat -- a cooler's or a gimbal's jitter -- by registering "
                         "every frame, with a shift planted at the beat as its test (reads the stretch again: slower)")
    ap.add_argument("--json", action="store_true",
                    help="print the measurement as JSON on stdout, its numbers as fields (the envelope every command "
                         "prints); everything else goes to stderr")
    args = ap.parse_args()
    if not args.track and not args.members:
        ap.error("give --track, or --members")
    if args.aperture:
        try:
            fixed(args.aperture)
        except ValueError as e:
            ap.error(str(e))
    with said_to_stderr(args.json) as lines:
        found, clip = _main(args)
    code = 0 if found.fields.get("finding") is not None else vf.EXIT_NOTHING
    if args.json:
        emit(found.envelope("flicker", inputs_of(args), clip, said=lines, exit_code=code,
                            error=None if not code else found.no_power[0][1]))
    return code


def read_avoid(text):
    """{name: track} from 'A.csv,B.csv', or None: the other tracked things `--avoid` names, each named by its folder and
    file -- a queue's objects keep their tracks under one name in folders of their own (object-2/pr135_track.csv ...),
    and named by the file alone, five of PR135's six collapsed into one (2026-10-16)."""
    if not text:
        return None
    from pathlib import Path
    out = {}
    for p in (q.strip() for q in str(text).split(",")):
        if p:
            name = f"{Path(p).parent.name}/{Path(p).stem}" if Path(p).parent.name else Path(p).stem
            k, j = name, 2
            while k in out:
                k, j = f"{name} ({j})", j + 1
            out[k] = vf.read_track(p)
    return out


def read_members(path, n0=None, n1=None):
    """{member: {frame: (x, y)}} from a groups _members.csv."""
    out = {}
    for r in csv.DictReader(open(path, newline="", encoding="utf-8")):
        n = int(r["frame"])
        if (n0 is None or n >= n0) and (n1 is None or n <= n1):
            out.setdefault(f"member {r['member']}", {})[n] = (float(r["x_px"]), float(r["y_px"]))
    return out


def _main(args):
    video, tag, _ = vf.resolve(args.video)
    tracks = read_members(args.members, args.n0, args.n1) if args.members else {"object": vf.read_track(args.track)}
    frames = [n for t in tracks.values() for n in t]
    clip = vf.Clip(video, args.workdir, args.n0 if args.n0 is not None else min(frames),
                   args.n1 if args.n1 is not None else max(frames))
    out = vf.out_prefix(args.out, tag)
    print(f"{video.name}: {clip.W}x{clip.H}, {clip.fps:.3f} fps, frames {clip.n0}-{clip.n1}")
    found = measure(clip, tracks, dark=args.dark, out=out, progress=to_stderr(), procs=args.procs, nulls=not args.no_nulls,
                    aperture=args.aperture, rule=args.beat_rule, avoid=read_avoid(args.avoid), scene=args.scene_shift,
                    black_hot=args.black_hot)
    print("\n".join(said(found.fields)))
    return found, clip


if __name__ == "__main__":
    raise SystemExit(main())
