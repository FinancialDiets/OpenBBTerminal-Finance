"""Gamestonk Jupyter Kernel."""
import io
from contextlib import redirect_stdout
import matplotlib
from ipykernel.kernelbase import Kernel
from terminal import TerminalController, bootup


def _to_svg(fig):
    """Return a svg image from a matplotlib figure."""
    imgdata = io.BytesIO()
    fig.savefig(imgdata, format="svg")
    imgdata.seek(0)
    return imgdata.getvalue().decode("utf-8")


class GamestonkKernel(Kernel):
    """The Gamestonk Kernel."""

    implementation = "Gamestonk"
    implementation_version = "0.1"
    language = "gamestonk"  # will be used for
    # syntax highlighting
    language_version = "1.0"
    language_info = {"name": "gamestonk", "mimetype": "text/plain", "extension": ".gst"}
    banner = "..."

    def __init__(self, **kwargs) -> None:
        """
        Override the Kernel init function.

        During initialization we instantiate the Terminal Controller and do some boot up
        procesdures.

        :param      kwargs:  Keywords arguments
        :type       kwargs:  dict
        """
        super().__init__(**kwargs)
        bootup()
        self.t_controller = TerminalController()

        f = io.StringIO()
        with redirect_stdout(f):
            self.t_controller.print_help()
        self.banner = f.getvalue()

        matplotlib.use("svg")

    def do_execute(
        self,
        code: str,
        silent: bool = False,
        store_history: bool = True,
        user_expressions: dict = None,
        allow_stdin: bool = False,
    ):
        """Execute code in the kernel."""
        if not silent:
            f = io.StringIO()
            with redirect_stdout(f):
                # Process list of commands selected by user
                try:
                    process_input = self.t_controller.switch(code)
                    # None - Keep loop
                    # True - Quit or Reset based on flag
                    # False - Keep loop and show help menu

                    if process_input is not None and isinstance(process_input, tuple):
                        # We expect to receive a matplotlib figure in `process_input`
                        fig, _ = process_input
                        svg_fig = _to_svg(fig)

                        content = {
                            "data": {"image/svg+xml": svg_fig},
                            "metadata": {
                                "image/html": {"width": 600, "height": 400},
                                "isolated": True,
                            },
                        }
                        self.send_response(self.iopub_socket, "display_data", content)
                    if process_input is not None and not isinstance(
                        process_input, bool
                    ):
                        # We expect to receive a controller in `process_input`
                        self.t_controller = process_input
                    if process_input is True and isinstance(process_input, bool):
                        # We expect to receive a True boolean in `process_input`
                        self.t_controller = TerminalController()
                        self.t_controller.print_help()

                except Exception as e:
                    self.send_response(
                        self.iopub_socket,
                        "stream",
                        {"name": "stdout", "text": f"{e}\n"},
                    )
            self.send_response(
                self.iopub_socket,
                "stream",
                {"name": "stdout", "text": f"{f.getvalue()}\n"},
            )

        # We return the execution results.
        return {
            "status": "ok",
            "execution_count": self.execution_count,
            "payload": [],
            "user_expressions": {},
        }
