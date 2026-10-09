# Contributing to mcdonald

Thank you for helping. **mcdonald** is maintained by Jacob Haqq Misra, who reviews every change
and makes the release decisions.

## Reporting a problem or asking a question

Open an issue at <https://github.com/haqqmisra/mcdonald/issues>. Please include:

- the output of `mcdonald --version` and your operating system;
- the command you ran, or the steps in the window, and what it printed;
- the video, if it is public (a PURSUE record id such as `PR144` is enough).

A result you think is wrong is a bug report too. Say which number, what you expected, and why.

## Suggesting a change

1. Open an issue first for anything larger than a small fix, so we can agree on the approach.
2. Fork the repository, make the change on a branch, and open a pull request.
3. Run the suites that need no video data before you send it:

   ```bash
   pip install -e ".[gui,dev]"
   python tests/test_reduction.py
   python tests/test_published.py
   python tests/test_tether.py
   python tests/test_cli.py
   python tests/test_measurement.py
   python tests/test_gui.py
   ```

   [README-technical.md](README-technical.md) says what each suite checks.
   `tests/test_golden.py` needs the PURSUE videos and is run by the maintainer.

Ground rules for changes:

- **No number may change silently.** If a change moves a published or golden number, say so in
  the pull request and explain why the new number is right.
- **NO POWER is an answer.** A test that cannot decide a question must say so, never return a
  number the footage cannot support.
- Use the plain words the window already uses for people outside the field.

## Releases

The version is written once, in `src/mcdonald/__init__.py`. A release adds an entry to
[CHANGELOG.md](CHANGELOG.md), sets the version and date in [CITATION.cff](CITATION.cff) and the
status lines of both READMEs (`tests/test_reduction.py` fails until all four agree), and pushes a
tag `vX.Y.Z` matching that version, which publishes it to PyPI.

## Use of AI tools

mcdonald is developed with an AI coding agent (Claude Code). Commits made with its help say so
in a `Co-Authored-By` line. The maintainer reviews every change and makes the design decisions.
AI-assisted contributions are welcome on the same terms: say so in the pull request, and make
sure you have read and tested what you send.

## Conduct

Be courteous and keep to the evidence. This subject draws strong views; disagreements about a
clip are settled by measurements anyone can repeat.
