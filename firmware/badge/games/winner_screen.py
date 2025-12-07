import asyncio

from badge.msg import BadgeAdr, null_badge_adr
from badge.msg.connection import NowListener, Beacon
from gui.core.colors import GREEN, BLACK, RED, D_PINK, WHITE, D_GREEN
from gui.core.ugui import Screen, ssd
from gui.core.writer import CWriter
from gui.fonts import arial35, freesans20, font10 as font10
from gui.primitives import launch
from gui.widgets.buttons import CloseButton
from gui.widgets.label import Label

class WinScr(Screen):
    def __init__(self, winner, message1, message2):

        super().__init__()
        wri = CWriter(ssd, font10, WHITE, BLACK, verbose=False)
        wrib = CWriter(ssd, arial35, D_PINK, BLACK, verbose=False)

        # Display the winner
        self.lbl_i = Label(wri, 170 // 3 - 30, 2, 316, bdcolor=False, justify=1, fgcolor=D_GREEN)
        self.lbl_w = Label(wrib, 170 // 3 + 5, 2, 316, bdcolor=False, justify=1)
        self.lbl_m = Label(wri, 170 // 3 + 60, 2, 316, bdcolor=False, justify=1, fgcolor=D_GREEN)
        self.lbl_m2 = Label(wri, 170 // 3 + 80, 2, 316, bdcolor=False, justify=1, fgcolor=D_GREEN)
        self.lbl_i.value("Winner is")
        self.lbl_w.value(f"{winner}")
        self.lbl_m.value(f"{message1}")
        self.lbl_m2.value(f"{message2}")

        # Close button
        CloseButton(wri)