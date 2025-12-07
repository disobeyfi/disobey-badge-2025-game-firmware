import framebuf

from bdg.utils import blit_to_buf, blit
from gui.core import writer
from gui.core.colors import BLACK, GREEN, WHITE
from gui.core.ugui import Widget, Screen
from gui.core.writer import AlphaColor
from hardware_setup import ssd


class SpriteBuffer(framebuf.FrameBuffer):
    def __init__(self, width, height):
        buf = bytearray(height * width * 2)
        self.mvb = memoryview(buf)
        self.height = height  # Required by Writer class
        self.width = width
        self.mode = framebuf.RGB565
        super().__init__(buf, width, height, framebuf.RGB565)

    def from_image(self, image):
        self.mvb[:] = image.data
        return self


class Sprite(Widget):

    def __init__(
        self,
        writer,
        row,
        col,
        image,
        fgcolor=None,
        bgcolor=AlphaColor(BLACK),
        bdcolor=False,
    ):
        # Determine width of sprite
        height = image.rows
        width = image.cols
        super().__init__(writer, row, col, height, width, fgcolor, bgcolor, bdcolor)

        self._sprite = SpriteBuffer(width, height).from_image(image)
        self._bg_store = SpriteBuffer(width, height)

        self._old_row = row
        self._old_col = col
        self.capture_bg()

    def capture_bg(self):
        blit_to_buf(
            ssd, self._bg_store.mvb, self.height, self.width, self.row, self.col
        )  # store background

    def update(self, row: int, col: int, visible: bool):
        self.row = row
        self.col = col
        self.visible = visible
        self.draw = True

    def show(self):  # Passive: no need to test show return value.
        if self.screen != Screen.current_screen:
            # Can occur if a control's action is to change screen.
            print("Sprite did not draw")
            return False  # Subclass abandons
        self.draw = False
        ssd.blit(self._bg_store, self._old_col, self._old_row)  # restore old background
        blit_to_buf(  # store background in new pos
            ssd, self._bg_store.mvb, self.height, self.width, self.row, self.col
        )
        if self.visible:
            # ssd.palette.fg(WHITE)  # prepare for blitting
            # ssd.palette.bg(self.bgcolor)
            # blit with transparency if self.bgcolor matches the _sprite palette
            ssd.blit(self._sprite, self.col, self.row, self.bgcolor)
        self._old_row = self.row
        self._old_col = self.col
