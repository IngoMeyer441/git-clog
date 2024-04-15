import os
import runpy
import subprocess
from setuptools import setup, find_packages


def get_version_from_pyfile(version_file="git_clog.py"):
    file_globals = runpy.run_path(version_file)
    return file_globals["__version__"]


def get_long_description_from_readme(readme_filename="README.md"):
    long_description = None
    if os.path.isfile(readme_filename):
        with open(readme_filename, "r", encoding="utf-8") as readme_file:
            long_description = readme_file.read()
    return long_description


version = get_version_from_pyfile()
long_description = get_long_description_from_readme()

setup(
    name="git-clog",
    version=version,
    py_modules=["git_clog"],
    python_requires="~=3.3",
    entry_points={"console_scripts": ["git-clog = git_clog:main"]},
    author="Ingo Meyer",
    author_email="IJ_M@gmx.de",
    description=(
        "git-clog outputs the commit graph of the current Git repository and colorizes commit symbols by "
        "interpreting the first six commit hash digits as an RGB color value."
    ),
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="MIT",
    url="https://github.com/IngoMeyer441/git-clog",
    keywords=["git"],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3 :: Only",
        "Topic :: Software Development :: Version Control",
        "Topic :: Software Development :: Version Control :: Git",
        "Topic :: Terminals",
        "Topic :: Utilities",
    ],
)
