# primitives.py micro-gui demo of use of graphics primitives

# Released under the MIT License (MIT). See LICENSE.
# Copyright (c) 2021 Peter Hinch

# hardware_setup must be imported before other modules because of RAM use.
import hardware_setup  # Create a display instance
from gui.core.ugui import Screen, Window, ssd, display

from gui.widgets import Label, CloseButton
from gui.core.writer import CWriter

# Font for CWriter
import gui.fonts.font10 as font10
import gui.fonts.freesans20 as font20
from gui.core.colors import *
from gui.widgets.menu import Menu
from tests.scanner.scanner import ScannerScreen


def cb(button, n):
    print("Help callback", n)


def cb_sm(lb, n):
    print("Submenu callback", lb.value(), lb.textvalue(), n)


def cb_start_scanner(lb, n):
    Screen.change(ScannerScreen)


class MainScreen(Screen):

    def __init__(self):
        super().__init__()
        wri = CWriter(ssd, font20, GREEN, BLACK, verbose=False)
        col = 100
        row = 100
        Label(wri, row, col, "Disobey 2025")

        metals2 = (
            ("Gold", cb_sm, (6,)),
            ("Silver", cb_sm, (7,)),
            ("Iron", cb_sm, (8,)),
            ("Zinc", cb_sm, (9,)),
            ("Copper", cb_sm, (10,)),
        )

        esp_funcs = (
            ("Scanner", cb_start_scanner, (0,)),
            ("", cb_sm, (1,)),
            ("Argon", cb_sm, (2,)),
            ("Krypton", cb_sm, (3,)),
            ("Xenon", cb_sm, (4,)),
            ("Radon", cb_sm, (5,)),
        )

        metals = (
            ("Lithium", cb_sm, (6,)),
            ("Sodium", cb_sm, (7,)),
            ("Potassium", cb_sm, (8,)),
            ("Rubidium", cb_sm, (9,)),
            ("More", metals2),
        )

        mnu = (("ESP-NOW!", esp_funcs), ("Metal", metals), ("Help", cb, (2,)))

        wri = CWriter(ssd, font10, GREEN, BLACK, verbose=False)
        Menu(wri, bgcolor=BLUE, textcolor=WHITE, fgcolor=RED, args=mnu)

        CloseButton(wri)  # Quit the application

    def after_open(self):
        display.usegrey(False)
        # Coordinates are x, y as per framebuf
        # circle method is in Display class only
        display.circle(70, 70, 30, RED)
        # These methods exist in framebuf, so also in SSD and Display
        ssd.hline(0, 127, 128, BLUE)
        ssd.vline(127, 0, 128, BLUE)


def run():
    print("Primitives demo.")
    Screen.change(MainScreen)


run()
