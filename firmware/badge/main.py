import asyncio
from math import sin, cos

import aioespnow
import network

import gui.fonts.freesans20 as font
import gui.fonts.font10 as font10  # noqa Create a display instance
import hardware_setup
from bdg.screens.loading_screen import LoadingScreen
from bdg.screens.boot_screen import BootScr
from badge.msg import BeaconMsg
from badge.msg.connection import Connection, NowListener, Beacon

# import frozen_fs mounts `frozen_fs` as `/readonly_fs`
import frozen_fs
from bdg.config import Config
from bdg.version import Version
from gui.core.colors import *
from gui.core.ugui import Screen, ssd, quiet
from gui.core.writer import CWriter, AlphaColor  # noqa
from gui.primitives import launch

from gui.widgets import Label, Button, CloseButton, Listbox
from gui.widgets.dialog import DialogBox
from hardware_setup import BtnConfig, LED_PIN, LED_AMOUNT, LED_ACTIVATE_PIN
from .asyncbutton import ButtonEvents, ButAct
from .games import change_app
from .games.reaction_game import ReactionGameScr
from .games.rps import RpsScreen
from badge.games.badge_game import GameLobbyScr, start_game
from .scan_screen import ScannerScreen

# from .sprite import Sprite
# import sprite
from badge.games.tictac import TicTacToe
from bdg.utils import blit
from .bleds import ScoreLeds
from images import boot as screen1
from bdg.widgets.hidden_active_widget import HiddenActiveWidget
from bdg.screens.ota import OTAScreen


ScoreLeds(
    LED_PIN,
    LED_AMOUNT,
    LED_ACTIVATE_PIN,
)


class ShowBdgs(Screen):
    sync_update = True  # set screen update mode synchronous

    def __init__(self):
        super().__init__()

        def fwd(button, my_kwargs):
            Screen.change(DialogBox, kwargs=my_kwargs)

        # verbose default indicates if fast rendering is enabled
        wri = CWriter(ssd, font, GREEN, BLACK, verbose=False)
        print("I dont want to show badges")
        Label(wri, 35, 100, "Show Badges", bdcolor=None)
        kwargs = {
            "writer": wri,
            "row": 20,
            "col": 2,
            "elements": (("Yes", GREEN), ("No", RED), ("Foo", YELLOW)),
            "label": "Test dialog",
        }
        row = 60
        col = 200
        Button(
            wri,
            row,
            col,
            text="Dialog",
            bgcolor=RED,
            textcolor=WHITE,
            callback=fwd,
            args=(kwargs,),
        )

        CloseButton(wri)  # Quit the application

    def after_open(self):
        # copy_img_to_mvb('screen1.bin', ssd)
        blit(ssd, screen1, 0, 0)
        self.show(True)


class OptionScreen(Screen):
    sync_update = True  # set screen update mode synchronous

    def __init__(self):
        super().__init__()
        # verbose default indicates if fast rendering is enabled
        wri = CWriter(ssd, font, GREEN, BLACK, verbose=False)
        self.els = [
            "Home",
            "Scan",
            "TicTacToe",
            "Reaction",
            "Firmware update",
        ]
        self.lb = Listbox(
            wri,
            50,
            50,
            elements=self.els,
            dlines=3,
            bdcolor=RED,
            value=1,
            callback=self.lbcb,
            also=Listbox.ON_LEAVE,
        )

        # Test of movable sprite object with disobey (:
        # self.sprite = Sprite(wri, 40, 150, sprite)
        # self.sprite.visible = False  # update_sprite task will take over.

        CloseButton(wri)  # Quit the application

    def on_open(self):
        # register callback that will make new connection dialog to pop up
        pass

    def on_hide(self):
        # executed when any other window is opened on top
        pass

    def after_open(self):
        # copy_img_to_mvb('screen1.bin', ssd)
        blit(ssd, screen1, 0, 0)  # show background
        self.show(True)  #
        # self.sprite.capture_bg()  #  capture new background for sprite
        # task will set sprite visible
        # self.reg_task(self.update_sprite(), True)

    async def update_sprite(self):
        # example of using sprite
        print(">>>> new update_sprite task")
        x = self.sprite.col
        y = self.sprite.row
        t = 0.0
        await asyncio.sleep(1)
        self.sprite.visible = True
        try:
            while True:
                self.sprite.update(
                    y + int(cos(t) * 10.0),
                    x + int(sin(t) * 20.0),
                    True,
                )
                await asyncio.sleep_ms(50)
                t += 0.3
        except asyncio.CancelledError:
            self.sprite.visible = False

    def lbcb(self, lb):  # Listbox callback
        if lb.textvalue() == "Home":
            Screen.change(GameLobbyScr)
        elif lb.textvalue() == "Reaction":
            # Casual mode: on
            Screen.change(ReactionGameScr, mode=Screen.STACK, args=(None, True))
        elif lb.textvalue() == "Scan":
            Screen.change(ScannerScreen, mode=Screen.STACK)
        elif lb.textvalue() == "TicTacToe":
            Screen.change(TicTacToe, mode=Screen.STACK, args=(None,))
        elif lb.textvalue() == "Firmware update":
            Screen.change(
                OTAScreen,
                mode=Screen.STACK,
                kwargs={
                    "espnow": self.espnow,
                    "sta": self.sta,
                    "fw_version": Version().version,
                    "ota_config": Config.config["ota"],
                },
            )


async def new_con_cb(conn: Connection, req=False):
    """
    Handles an incoming connection request by presenting the user with a
    dialog box to accept or decline the connection.

    Handles self initiated connection if req=True
    """
    accept = False
    if not req:
        w_reply = asyncio.Event()

        def resp(window):
            nonlocal accept
            # convert response to True
            print(f"con accept: {window.value()=}")
            accept = window.value() == "Yes"
            w_reply.set()

        wri = CWriter(ssd, font, GREEN, BLACK, verbose=False)

        kwargs = {
            "writer": wri,
            "row": 20,
            "col": 20,
            "elements": (("Yes", GREEN), ("No", RED)),
            "label": "Incoming connection",
            "callback": resp,
            "closebutton": False,
        }

        # show the dialog box
        Screen.change(DialogBox, kwargs=kwargs)

        try:
            # this will block until dialog callback resp() is called or timeout
            await asyncio.wait_for(w_reply.wait(), 15)
        except asyncio.TimeoutError:
            DialogBox.close()  # close dialog

    if accept or req:
        # TODO: change the app that conn was opened
        # Simulate start of App
        if isinstance(Screen.current_screen, OptionScreen):
            # If at home screen add app on top
            mode = Screen.STACK
        else:
            # if we have other app on, replace it
            print(f"Con: Screen.REPLACE {Screen.current_screen=}")
            mode = Screen.REPLACE

        if conn.con_id == 1:  # tictactoe
            Screen.change(
                LoadingScreen,
                mode=mode,
                kwargs={
                    "title": "TicTacToe",
                    "wait": 10,
                    "nxt_scr": TicTacToe,
                    "scr_args": (conn,),
                },
            )
        elif conn.con_id == 2:  # reaction
            Screen.change(
                LoadingScreen,
                mode=mode,
                kwargs={
                    "title": "Reaction Game",
                    "wait": 10,
                    "nxt_scr": ReactionGameScr,
                    # Casual mode: off
                    "scr_args": (conn, False),
                },
            )

        elif conn.con_id == 3:  # RPS
            Screen.change(
                LoadingScreen,
                mode=mode,
                kwargs={
                    "title": "RPSLS",
                    "wait": 10,
                    "nxt_scr": RpsScreen,
                    # Casual mode: off
                    "scr_args": (conn,),
                },
            )

    return accept


async def global_buttons():
    print("global_buttons")
    ev_subset = ButtonEvents.get_event_subset(
        [
            ("btn_select", ButAct.ACT_DOUBLE),
            ("btn_b", ButAct.ACT_LONG),
            ("btn_start", ButAct.ACT_LONG),
        ],
    )

    be = ButtonEvents(events=ev_subset)

    handlers = {
        "btn_select": lambda ev: print(f"btn_select {ev}") or change_app(OptionScreen),
        "btn_b": lambda ev: print(f"[__Back]") or Screen.back(),
        "btn_start": lambda ev: print(f"btn_start {ev}") or change_app(ScannerScreen),
    }

    async for btn, ev in be.get_btn_events():
        handlers.get(btn, lambda e: print(f"Unknown {btn} {e}"))(ev)


def start_badge():
    print("->Badge<-")

    # init button even machine
    ButtonEvents.init(BtnConfig)

    Config.load()
    channel = int(Config.config["espnow"]["ch"])

    sta = network.WLAN(network.STA_IF)
    # set configured wifi channels
    sta.active(True)
    sta.config(channel=channel)
    sta.config(txpower=10)
    e = aioespnow.AIOESPNow()
    e.active(True)

    # TODO: WE need to define channel
    own_mac = sta.config("mac")
    print(f"MAC: \nmac={own_mac} ")

    quiet()

    # Startup boot screen...
    Screen.change(BootScr, kwargs={"ready_cb": start_game, "espnow": e, "sta": sta})

    # Screen.change(RpsScreen, args=(None,))


start_badge()
