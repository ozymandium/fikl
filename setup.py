from distutils.core import setup

setup(name="fikl",
    version="0.1",
    description="A Python tool for decision making using weighted scores.",
    packages=["fikl"],
    entry_points = {
        "console_scripts": [
            "fikl = fikl.cli:main",
        ],
    },
)
