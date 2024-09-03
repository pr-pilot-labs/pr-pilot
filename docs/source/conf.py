# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "PR Pilot"
copyright = "2024, Arcane Engineering"
author = "Marco Lamina"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "myst_parser",
]

templates_path = ["_templates"]
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_material"
html_static_path = ["_static"]
html_theme_options = {
    "base_url": "https://docs.pr-pilot.ai",
    "repo_url": "https://github.com/PR-Pilot-AI/pr-pilot",
    "repo_name": "PR Pilot",
    "color_primary": "white",
    "color_accent": "blue",
    "html_minify": True,
    "css_minify": True,
    "nav_title": "PR Pilot",
    "google_analytics_account": "G-86FJ02W45S",
    "logo_icon": "✈️",
    "globaltoc_depth": 1,
    "master_doc": False,
    "nav_links": [
        {
            "href": "https://www.pr-pilot.ai/",
            "internal": False,
            "title": "Official Website",
        },
        {
            "href": "https://app.pr-pilot.ai/dashboard/tasks/",
            "internal": False,
            "title": "Dashboard",
        },
        {
            "href": "https://www.pr-pilot.ai/blog/",
            "internal": False,
            "title": "Blog",
        },
        {
            "href": "https://arcane.engineer",
            "internal": False,
            "title": "About Us",
        },
    ],
    "heroes": {
        "index": "Transform your Development Workflow",
    },

}
html_sidebars = {
    "**": ["logo-text.html", "globaltoc.html", "localtoc.html", "searchbox.html"]
}
