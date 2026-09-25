"""Only for what pyproject.toml cannot say: the documents `mcdonald readme` prints are copied
into the package when it is built, so that an install carries them and needs no repository.
They stay where they are in the repository (README-technical.md at the top, the rest in docs/),
one copy each; an editable install reads them there (mcdonald.readme_cli)."""
import shutil
from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py

DOCS = ["README-technical.md", "docs/method.md", "docs/agents.md", "docs/install.md"]


class build_py_with_docs(build_py):
    def run(self):
        super().run()
        out = Path(self.build_lib) / "mcdonald" / "docs"
        out.mkdir(parents=True, exist_ok=True)
        for d in DOCS:
            shutil.copyfile(d, out / Path(d).name)


setup(cmdclass={"build_py": build_py_with_docs})
