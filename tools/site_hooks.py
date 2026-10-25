"""MkDocs hooks for the website (mkdocs.yml): the root's own files as pages, their links, the README's words.

The site is built from the Markdown already in the repository, written for GitHub. Three things make that
work without copying a file into docs/:

  * the root's own file on how to contribute is made a page here (ROOT_PAGES), and the window's icon is the
    site's logo;
  * every link is pointed where it leads on the site: a page the site carries goes to that page, and anything
    else -- a page left off the site (the methods, the technical README, the changelog), LICENSE, the code --
    goes to GitHub. A link written relative to the root, to docs/install.md, or as GitHub's own URL for it, all
    arrive at install.md. README.md is the front page;
  * the front page and About say what the README says: `<!-- README: Install -->` is the README's section of that name,
    and `<!-- README: status -->` / `<!-- README: quote -->` its status line and its quote, so the two never
    disagree (tests/test_reduction.py already holds the README to the version), less any line that points at
    the roadmap: the site does not mention it (Jacob, 2026-10-24). On the publications page,
    `<!-- CITATION -->` is the toolkit's own citation from CITATION.cff, which the same test holds.
"""
import posixpath
import re
from pathlib import Path

import yaml
from mkdocs.structure.files import File

REPO = Path(__file__).resolve().parents[1]
GITHUB = "https://github.com/haqqmisra/mcdonald/"

# a page on the site <- the file at the repository's root it is made from
ROOT_PAGES = {"contributing.md": "CONTRIBUTING.md"}
# a file on the site <- a file elsewhere in the repository
COPIED = {"assets/mcdonald.svg": "src/mcdonald/icons/mcdonald-small.svg"}
# where a link to a repository file arrives on the site, when it is not under docs/
ARRIVES = {src: page for page, src in ROOT_PAGES.items()} | {"README.md": "index.md"}
ON_SITE = set()                                       # the files the site carries (on_files)

LINK = re.compile(r"(\]\()([^)\s]+)((?:\s+\"[^\"]*\")?\))")
FENCE = re.compile(r"^\s*(```|~~~)", re.M)
NAMED = re.compile(r"(?<!!)\[(`?[\w./-]+\.md`?)\]\(([^)\s]+)\)")


def on_config(config):
    # the cases page and one page a case file, once it is back in the nav (1.0) and tools/site_cases.py made them
    pages = Path(config["docs_dir"]) / "cases" / "pages.txt"
    if pages.exists():
        cases = [p for p in pages.read_text(encoding="utf-8").split() if p]
        config["nav"] = [{"Cases": ["cases/index.md", *cases]} if entry == {"Cases": "cases/index.md"} else entry
                         for entry in config["nav"]]
    return config


def on_files(files, config):
    for page, src in ROOT_PAGES.items():
        files.append(File.generated(config, page, content=(REPO / src).read_text(encoding="utf-8")))
    for to, src in COPIED.items():
        files.append(File.generated(config, to, abs_src_path=str(REPO / src)))
    ON_SITE.clear()
    ON_SITE.update(f.src_uri for f in files if not f.inclusion.is_excluded())
    return files


def on_page_markdown(markdown, page, config, files):
    src = page.file.src_uri
    if "<!-- README:" in markdown:
        markdown = readme_words(markdown, src)
    markdown = markdown.replace("<!-- CITATION -->", citation())
    at = ROOT_PAGES.get(src, "docs/" + src)          # where the page's text lives in the repository
    # links outside fenced code only: a fence's text is shown as it is
    parts = FENCE.split(markdown)
    out, inside = [], False
    for i, part in enumerate(parts):
        if i % 2 == 1:                                # the fence marker itself
            out.append(part)
            inside = not inside
            continue
        out.append(part if inside else LINK.sub(lambda m: m[1] + arrive(m[2], at, src) + m[3], titled(part, at)))
    return "".join(out)


def in_repo(target, at):
    """The repository path a link written in the file `at` leads to, and its #anchor; None for the outside world."""
    if target.startswith(GITHUB + "blob/main/") or target.startswith(GITHUB + "tree/main/"):
        path, at = target[len(GITHUB + "blob/main/"):], ""
    elif re.match(r"^[a-z]+:|^#|^/", target):
        return None
    else:
        path = target
    path, hash_, anchor = path.partition("#")
    return posixpath.normpath(posixpath.join(posixpath.dirname(at), path)), hash_ + anchor


def titled(markdown, at):
    """A link whose words are only the file's name ([docs/install.md](...)) says the page's title instead."""
    def title(m):
        found = in_repo(m[2], at)
        if found and found[0].endswith(m[1].strip("`")) and (REPO / found[0]).is_file():
            h1 = re.search(r"^# (.+)$", (REPO / found[0]).read_text(encoding="utf-8"), re.M)
            if h1:
                return f"[{h1[1].strip()}]({m[2]})"
        return m[0]
    return NAMED.sub(title, markdown)


def arrive(target, at, page):
    """A link written in the repository file `at`, made right for the site's page `page`."""
    found = in_repo(target, at)
    if found is None:
        return target
    repo, anchor = found
    site = ARRIVES.get(repo, repo[len("docs/"):] if repo.startswith("docs/") else None)
    if site and not posixpath.splitext(site)[1] and (REPO / repo / "README.md").exists():
        site += "/README.md"
    if site not in ON_SITE:
        return GITHUB + ("tree" if (REPO / repo).is_dir() else "blob") + "/main/" + repo + anchor
    return posixpath.relpath(site, posixpath.dirname(page) or ".") + anchor


def readme_words(markdown, page):
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    status = re.search(r"^\*\*Status:\*\*.*$", readme, re.M)[0]
    quote = re.search(r"^> \".*?(?=\n\n)", readme, re.M | re.S)[0]
    markdown = markdown.replace("<!-- README: status -->", status).replace("<!-- README: quote -->", quote)

    def section(m):
        name = m[1]
        found = re.search(rf"^## {re.escape(name)}\n(.*?)(?=^## |\Z)", readme, re.M | re.S)
        if not found:
            raise ValueError(f"README.md has no section '## {name}' for the front page")
        words = re.sub(r"^.*ROADMAP\.md.*\n?", "", found[1], flags=re.M).strip()
        # its links are the README's, written relative to the root
        return LINK.sub(lambda l: l[1] + arrive(l[2], "README.md", page) + l[3], titled(words, "README.md"))
    return re.sub(r"<!-- README: (?!status|quote)(.+?) -->", section, markdown)


def citation():
    cff = yaml.safe_load((REPO / "CITATION.cff").read_text(encoding="utf-8"))
    names = ", ".join(f"{a['family-names']}, {a['given-names'][0]}." for a in cff["authors"])
    return (f"{names} ({cff['date-released'].year}). *{cff['title']}* (version {cff['version']}). "
            f"[{cff['repository-code']}]({cff['repository-code']})")
