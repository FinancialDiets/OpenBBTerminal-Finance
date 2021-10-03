"""Gamestonk Kernel Module Main magics file."""

if __name__ == "__main__":
    from ipykernel.kernelapp import IPKernelApp
    from .gamestonk_kernel import GamestonkKernel

    IPKernelApp.launch_instance(kernel_class=GamestonkKernel)
