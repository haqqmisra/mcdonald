---
title: Submit a video
description: Send a UAP video to the developer for analysis with mcDonald, along with additional metadata needed for the analysis.
---

# Submit a video

Have a video of something you could not identify? You can send it to the developer for analysis with
mcDonald. We can constrain the motion and size of an object in a single-camera video with additional information about the camera and observation, listed in the form below. 

We only accept submissions that include values for all items marked **required**. The **optional** items are not needed, but they make the analysis stronger.

!!! warning "Only the original file"
    Please send the original file exactly as the camera or phone saved it. A screen recording, a clip that
    was trimmed, cropped, zoomed, stabilized, or edited, or a copy downloaded from social media or a messaging
    app (which re-compress what they carry) has lost the detail a frame-by-frame measurement depends on.

<noscript>
<div class="admonition failure">
<p class="admonition-title">This form needs JavaScript</p>
<p>Please turn on JavaScript to use the form, or email the developer at
<a href="mailto:jacob@bmsis.org">jacob@bmsis.org</a> with an answer to each required item on this page.</p>
</div>
</noscript>

<form id="submit-form" class="submit-form" data-to="jacob@bmsis.org" novalidate autocomplete="on">

<fieldset data-criterion="contact">
<legend>You</legend>
<div class="sf-row">
<label>Name <span class="sf-req">required</span>
<input type="text" name="name" autocomplete="name" required></label>
<label>Email <span class="sf-req">required</span>
<input type="email" name="email" autocomplete="email" required></label>
</div>
<label class="sf-check"><input type="checkbox" name="permission" required>
I give the developer permission to analyze this video and to contact me.
<span class="sf-req">required</span></label>
</fieldset>

<fieldset data-criterion="1">
<legend>1. The original, unaltered video</legend>
<label>File name <span class="sf-req">required</span>
<input type="text" name="filename" placeholder="IMG_4821.MOV" required></label>
<p class="sf-q">How will you send it? <span class="sf-req">required</span></p>
<label class="sf-check"><input type="radio" name="delivery" value="link" required> A download link
(Google Drive, Dropbox, WeTransfer, or similar)</label>
<label class="sf-check"><input type="radio" name="delivery" value="attach"> I will attach it to the email
(small files only, up to about 20 MB)</label>
<label data-when="delivery=link">Link to the file <span class="sf-req">required</span>
<input type="url" name="link" placeholder="https://"></label>
<label>Who recorded it?
<select name="recorder">
<option value="">(choose)</option>
<option>I did</option>
<option>Someone I know</option>
<option>Another source</option>
</select></label>
<label class="sf-check"><input type="checkbox" name="original" required>
This is the original file from the device that recorded it: not a screen recording, not re-encoded, and not
trimmed, cropped, zoomed, stabilized, edited, or downloaded from social media or a messaging app.
<span class="sf-req">required</span></label>
</fieldset>

<fieldset data-criterion="2">
<legend>2. The field of view</legend>
<p class="sf-hint">Provide either (1) the camera's horizontal field of view or its angular scale, or (2) the specifications of the camera or device.</p>
<div class="sf-row">
<label>Horizontal field of view (degrees)
<input type="number" name="hfov" min="0" max="360" step="any" data-group="fov"></label>
<label>Angular scale
<span class="sf-unit"><input type="number" name="scale" min="0" step="any" data-group="fov">
<select name="scale_unit"><option>deg/pixel</option><option>mrad/pixel</option><option>µrad/pixel</option></select></span></label>
</div>
<div class="sf-row">
<label>Device or camera <input type="text" name="device" placeholder="iPhone 15 Pro; FLIR Star SAFIRE 380-HD"></label>
<label>Lens <input type="text" name="lens" placeholder="main 24 mm; telephoto 120 mm"></label>
</div>
<div class="sf-row">
<label>Zoom setting <input type="text" name="zoom" placeholder="3x; NAR; 2x digital"></label>
<label>Observation mode
<select name="mode">
<option value="">(choose)</option>
<option>Visible</option>
<option>Infrared</option>
<option>Other</option>
<option>Not known</option>
</select></label>
</div>
</fieldset>

<fieldset data-criterion="3">
<legend>3. The range to the object</legend>
<p class="sf-hint">How far the object was from the camera. A best estimate is fine; say how you know it in
the notes at the end.</p>
<div class="sf-row">
<label>Range <span class="sf-req">required</span>
<span class="sf-unit"><input type="number" name="range" min="0" step="any" required>
<select name="range_unit"><option>km</option><option>m</option><option>nmi</option><option>mi</option><option>ft</option></select></span></label>
<label>Range rate (even better)
<span class="sf-unit"><input type="number" name="range_rate" step="any">
<select name="range_rate_unit"><option>m/s</option><option>km/h</option><option>kt</option><option>mph</option></select></span>
<span class="sf-hint">How fast the range changed: positive if the object moved away, negative if it came closer.</span></label>
</div>
</fieldset>

<fieldset data-criterion="4">
<legend>4. The motion of the camera</legend>
<p class="sf-q">Was the camera moving? <span class="sf-req">required</span></p>
<label class="sf-check"><input type="radio" name="platform" value="stationary" required> No: it was standing
still (handheld or on the ground counts as still)</label>
<label class="sf-check"><input type="radio" name="platform" value="moving"> Yes: it was on an aircraft,
a boat, a car, or another moving platform</label>
<div data-when="platform=moving">
<div class="sf-row">
<label>Platform <input type="text" name="platform_type" placeholder="F/A-18F; airliner; sailboat"></label>
<label>Speed <span class="sf-req">required</span>
<span class="sf-unit"><input type="number" name="speed" min="0" step="any">
<select name="speed_unit"><option>kt</option><option>km/h</option><option>mph</option><option>m/s</option></select></span></label>
</div>
<div class="sf-row">
<label>Heading, degrees from true north <span class="sf-req">required</span>
<input type="number" name="heading" min="0" max="360" step="any" placeholder="0 north, 90 east"></label>
<label>Climb or descent rate
<span class="sf-unit"><input type="number" name="climb" step="any" placeholder="negative descending">
<select name="climb_unit"><option>ft/min</option><option>m/s</option></select></span></label>
</div>
<label>Turning or maneuvering during the video?
<input type="text" name="maneuver" placeholder="steady level flight; banking left about 3°/s"></label>
<label>Link to a trajectory log
<input type="url" name="platform_log" placeholder="https://">
<span class="sf-hint">A flight or boat track of the platform during the video, from a flight recorder, ADS-B, AIS, or a GPS app.</span></label>
</div>
</fieldset>

<fieldset data-criterion="5">
<legend>5. The angle to the line of sight</legend>
<p class="sf-hint">The angle between the direction the object moved and the line from the camera to the
object: 90° if it crossed straight across the view, 0° if it moved straight away, 180° if it came straight
toward the camera.</p>
<label>Angle (degrees, 0 to 180) <span class="sf-req">required</span>
<input type="number" name="los_angle" min="0" max="180" step="any" required></label>
</fieldset>

<fieldset data-criterion="6">
<legend>6. The direction the camera faced</legend>
<div class="sf-row">
<label>Compass direction, degrees from true north <span class="sf-req">required</span>
<input type="number" name="azimuth" min="0" max="360" step="any" placeholder="0 north, 90 east" required></label>
<label>Angle above the horizon (degrees)
<input type="number" name="elevation" min="-90" max="90" step="any" placeholder="negative below"></label>
</div>
</fieldset>

<fieldset data-criterion="7">
<legend>7. When and where</legend>
<p class="sf-hint">When the video started, and where the camera was.</p>
<div class="sf-row">
<label>Date <span class="sf-req">required</span> <input type="date" name="date" required></label>
<label>Time <span class="sf-req">required</span> <input type="time" name="time" step="1" required></label>
<label>Time zone <span class="sf-req">required</span>
<select name="tz" required><option value="">(choose)</option></select></label>
</div>
<div class="sf-row">
<label>Latitude (decimal degrees) <span class="sf-req">required</span>
<input type="number" name="lat" min="-90" max="90" step="any" placeholder="32.7157" required></label>
<label>Longitude (decimal degrees) <span class="sf-req">required</span>
<input type="number" name="lon" min="-180" max="180" step="any" placeholder="-117.1611 (west is negative)" required></label>
</div>
</fieldset>

<fieldset data-criterion="8">
<legend>8. The camera's height above sea level</legend>
<p class="sf-hint">For an aircraft, its altitude; on the ground or a boat, the height of the ground or deck.</p>
<label>Height above sea level <span class="sf-req">required</span>
<span class="sf-unit"><input type="number" name="height" step="any" required>
<select name="height_unit"><option>m</option><option>ft</option></select></span></label>
</fieldset>

<fieldset data-criterion="9">
<legend>9. Optional: Weather conditions</legend>
<label>A weather report, or a description of the weather conditions including wind, clouds, visibility, temperature
<textarea name="weather" rows="3" placeholder="a METAR from the nearest airport; clear sky, light wind from the west"></textarea></label>
</fieldset>

<fieldset data-criterion="10">
<legend>10. Optional: A reference object of known size in the video</legend>
<div class="sf-row">
<label>Reference object description and location in the video <input type="text" name="ref_object" placeholder="the ship at the left, at 0:12"></label>
<label>Reference object size <input type="text" name="ref_size" placeholder="length 210 m"></label>
</div>
</fieldset>

<fieldset>
<legend>Anything else</legend>
<label>Is there anything else the developer should know?
<textarea name="notes" rows="4"></textarea></label>
</fieldset>

<div class="sf-status" aria-live="polite">
<p class="sf-q">Required items</p>
<ul id="sf-checklist"></ul>
</div>

<div class="sf-actions">
<button type="submit" class="md-button md-button--primary" id="sf-send" disabled>Send by email</button>
<button type="button" class="md-button" id="sf-copy" disabled>Copy answers</button>
<button type="button" class="md-button" id="sf-download" disabled>Download answers</button>
</div>
<p class="sf-hint" id="sf-after" hidden>If no email opened, or it came out cut short, copy or download your
answers and send them to <span id="sf-address"></span> with the subject <em>mcDonald video submission</em>.</p>

</form>
