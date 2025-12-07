from gui.core.ugui import Widget
from gui.core.colors import *

# Set focus border to black to match our background
color_map[FOCUS] = BLACK


class HiddenActiveWidget(Widget):

    def __init__(
        self,
        writer,
        callback=None,
        args=[],
    ):
        super().__init__(writer, 0, 0, 0, 0, None, None, False, "", True)
        super()._set_callbacks(callback, args)
