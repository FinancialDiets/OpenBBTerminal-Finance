# Gamestonk Jupter Kernel

This python module installs a gamestonk kernel into a local python environment.
The kerlen can be then used to work with Notebooks and Consoles in Jupyter Lab.

## Installation

0. Navigate to this folder

    ```bash
    cd jupyterlab/kernel
    ```

1. Install the kernel module with pip:

    ```bash
    pip install --upgrade .
    ```

2. Install the kernel into jupyter

    ```bash
    jupyter-kernelspec install gamestonk
    ```

## Usage

Open Jupyter Lab and click the G button in the Notebook or the Console launcher.

### Development notes

1. You can install the kernel in development mode by using the `-e` flag

    ```bash
    pip install -e .
    ```

2. Nice tutorial on building simple python wrapper extension [here](https://github.com/ipython-books/cookbook-2nd-code/blob/master/chapter01_basic/06_kernel.ipynb)
