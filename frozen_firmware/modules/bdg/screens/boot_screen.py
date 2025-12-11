"""Boot screen for the badge"""

import asyncio

from bdg.msg import BeaconMsg
from bdg.config import Config
from bdg.version import Version
from bdg.utils import blit
from bdg.widgets.hidden_active_widget import HiddenActiveWidget
from gui.core.colors import GREEN, BLACK
from gui.core.ugui import Screen, ssd
from gui.core.writer import CWriter, AlphaColor
from gui.fonts import font10
from gui.primitives import launch
from gui.widgets.label import Label
from images import boot as screen1


class BootScr(Screen):
    sync_update = True  # set screen update mode synchronous

    def __init__(self, ready_cb=None, espnow=None, sta=None):
        super().__init__()
        self.ready_cb = ready_cb
        self.espnow = espnow
        ver = Version()
        # verbose default indicates if fast rendering is enabled
        self.wri = CWriter(ssd, font10, GREEN, BLACK, verbose=False)
        self.ver_str = f"Ver:{ver.version} b:{ver.build}"
        HiddenActiveWidget(self.wri)

    def after_open(self):
        # Lazy import connection module (saves 3.2s on badge.main import)
        from bdg.msg.connection import NowListener, Beacon

        blit(ssd, screen1, 0, 0)
        self.show(True)
        self.reg_task(self.next_scr(), False)

        # Import global_buttons and new_con_cb from badge.main
        from badge.main import global_buttons, new_con_cb

        self.reg_task(global_buttons(), False)

        nick = Config.config["espnow"]["nick"]
        print(f"BootScr: {nick=}")
        beaconmsg = BeaconMsg(nick)

        Beacon.setup(self.espnow, beaconmsg)
        Beacon.start(task=True)

        NowListener.con_cb = new_con_cb
        NowListener.start(self.espnow)

    async def next_scr(self):
        print(">>> next_scr")
        await asyncio.sleep(3)
        Label(self.wri, 155, 6, self.ver_str, bdcolor=False, bgcolor=AlphaColor(BLACK))
        await asyncio.sleep(1)
        launch(self.ready_cb, ())
