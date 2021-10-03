"""Setup script for the Gamestonk Jupyter Kernel."""
from setuptools import setup

setup(
    name="gamestonk_kernel",
    version="0.0.1",
    description="Gamestonk Jupyter Kernel",
    url="https://github.com/GamestonkTerminal/GamestonkTerminal",
    author="piiq",
    author_email="",
    license="MIT",
    packages=["gamestonk_kernel"],
    install_requires=[
        "matplotlib",
        "numpy",
    ],
    classifiers=["Development Status :: 1 - Planning"],
)
