"""Sphinx configuration for Shrinkr documentation."""

import os
import sys

# -- Path setup ---------------------------------------------------------------
# Add project root so autodoc2 can import src.*
sys.path.insert(0, os.path.abspath(".."))

# -- Project information ------------------------------------------------------
project = "Shrinkr"
author = "Andrii Borychevskyi"
release = "0.1.0"
copyright = "2026, Andrii Borychevskyi"  # noqa: A001

# -- General configuration ----------------------------------------------------
extensions = [
    "autodoc2",
    "myst_parser",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinxcontrib.mermaid",
]

# MyST (Markdown) settings
myst_enable_extensions = [
    "colon_fence",
    "fieldlist",
    "deflist",
]

# autodoc2 settings — point at the src package
autodoc2_packages = [
    {
        "path": "../src",
        "module": "src",
        "exclude_dirs": ["__pycache__"],
    },
]
autodoc2_render_plugin = "myst"
autodoc2_hidden_objects = ["private", "dunder"]

# Intersphinx: link to external docs
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "fastapi": ("https://fastapi.tiangolo.com", None),
    "sqlalchemy": ("https://docs.sqlalchemy.org/en/20/", None),
    "pydantic": ("https://docs.pydantic.dev/latest/", None),
    "redis": ("https://redis-py.readthedocs.io/en/stable/", None),
}

# -- Options for HTML output --------------------------------------------------
html_theme = "furo"
html_title = "Shrinkr Docs"
html_static_path = ["_static"]

# Furo theme options
html_theme_options = {
    "source_repository": "https://github.com/a-borychevskyi/url-shortener",
    "source_branch": "main",
    "source_directory": "docs/",
}

# -- Source settings ----------------------------------------------------------
source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}
exclude_patterns = ["_build", "superpowers"]
