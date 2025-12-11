"""
Profile import time for badge.main to identify bottlenecks
"""

import time


def profile_imports():
    """Profile each major import and initialization step"""

    start = time.ticks_ms()
    last = start

    def checkpoint(label):
        nonlocal last
        now = time.ticks_ms()
        elapsed = time.ticks_diff(now, last)
        total = time.ticks_diff(now, start)
        print(f"[{total:6d}ms] {label:40s} (+{elapsed:5d}ms)")
        last = now

    checkpoint("START")

    import asyncio

    checkpoint("import asyncio")

    from math import sin, cos

    checkpoint("import math")

    import aioespnow

    checkpoint("import aioespnow")

    import network

    checkpoint("import network")

    import gui.fonts.freesans20 as font

    checkpoint("import gui.fonts.freesans20")

    import gui.fonts.font10 as font10

    checkpoint("import gui.fonts.font10")

    import hardware_setup

    checkpoint("import hardware_setup")

    from bdg.screens.loading_screen import LoadingScreen

    checkpoint("import LoadingScreen")

    from badge.msg import BeaconMsg

    checkpoint("import BeaconMsg")

    from badge.msg.connection import Connection, NowListener, Beacon

    checkpoint("import Connection, NowListener, Beacon")

    import frozen_fs

    checkpoint("import frozen_fs")

    from bdg.config import Config

    checkpoint("import Config")

    from bdg.version import Version

    checkpoint("import Version")

    import gui.core.colors

    checkpoint("import gui.core.colors")

    from gui.core.ugui import Screen, ssd, quiet

    checkpoint("import gui.core.ugui")

    from gui.core.writer import CWriter, AlphaColor

    checkpoint("import CWriter, AlphaColor")

    from gui.primitives import launch

    checkpoint("import launch")

    from gui.widgets import Label, Button, CloseButton, Listbox

    checkpoint("import gui.widgets")

    from gui.widgets.dialog import DialogBox

    checkpoint("import DialogBox")

    from hardware_setup import BtnConfig, LED_PIN, LED_AMOUNT, LED_ACTIVATE_PIN

    checkpoint("import BtnConfig (from hardware_setup)")

    from badge.asyncbutton import ButtonEvents, ButAct

    checkpoint("import ButtonEvents, ButAct")

    from badge.games import change_app

    checkpoint("import badge.games.change_app")

    from badge.games.reaction_game import ReactionGameScr

    checkpoint("import ReactionGameScr")

    from badge.games.rps import RpsScreen

    checkpoint("import RpsScreen")

    from badge.games.badge_game import GameLobbyScr, start_game

    checkpoint("import GameLobbyScr, start_game")

    from badge.scan_screen import ScannerScreen

    checkpoint("import ScannerScreen")

    from badge.games.tictac import TicTacToe

    checkpoint("import TicTacToe")

    from bdg.utils import blit

    checkpoint("import blit")

    from badge.bleds import ScoreLeds

    checkpoint("import ScoreLeds")

    from images import boot as screen1

    checkpoint("import images.boot")

    from bdg.widgets.hidden_active_widget import HiddenActiveWidget

    checkpoint("import HiddenActiveWidget")

    from bdg.screens.ota import OTAScreen

    checkpoint("import OTAScreen")

    # Note: ScoreLeds initialization moved to start_badge() function
    # so it no longer runs at import time

    print(f"\n{'='*60}")
    print(f"TOTAL TIME: {time.ticks_diff(time.ticks_ms(), start)}ms")
    print(f"{'='*60}")


# Run the profiling
profile_imports()
