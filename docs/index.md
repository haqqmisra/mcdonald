---
title: Home
hide:
  - navigation
  - toc
---

<div class="hero" markdown>

<h1 class="hero-logo">
  <img alt="mcDonald UAP Toolkit" src="logo-light.svg#only-light" width="460">
  <img alt="mcDonald UAP Toolkit" src="logo-dark.svg#only-dark" width="460">
</h1>

**mcdonald** is a frame-by-frame analysis toolkit for measuring the kinematics of an unknown object in a
single-camera video.

<!-- README: quote -->

[Install](#install){ .md-button .md-button--primary }
[Try an exercise](exercises/README.md){ .md-button }
[Read the papers](publications.md){ .md-button }

</div>

<!-- README: status -->

## How it goes

Open a video and press **Begin**. mcdonald does the three steps below without asking anything, and the report
opens at the end. To take the steps one at a time, and to mark the object by hand, use **Advanced Mode**.

<div class="grid cards" markdown>

-   :material-magnify:{ .lg } **1. Find the object**

    ---

    The computer looks for things that move against the background. You choose which one is the object.

-   :material-motion-play-outline:{ .lg } **2. Follow it**

    ---

    The computer follows the object through every frame, and shows you the track to check.

-   :material-ruler:{ .lg } **3. Measure**

    ---

    Works out how the object moved, and writes a report that starts with what it found.

</div>

The video can be one of your own, or one of the public PURSUE videos by its name: mcdonald downloads it for you.

## Two ways to use it

<div class="grid cards" markdown>

-   :material-application-outline:{ .lg } **The window**

    ---

    For people. It takes you through each step, and nothing needs typing once it is installed.

    ```bash
    mcdonald-gui
    ```

-   :material-console:{ .lg } **The command line**

    ---

    For developers, advanced users and AI agents. Every step in the window has a command.

    ```bash
    mcdonald
    ```

    [The command line](../README-technical.md) · [For an AI agent](agents.md)

</div>

## Install

<!-- README: Install -->

## Support

<!-- README: Support -->
