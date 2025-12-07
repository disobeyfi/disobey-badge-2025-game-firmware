import asyncio
import random

from badge.asyncbutton import ButtonEvents
from badge.games import fwdbutton
from badge.msg import BadgeAdr, null_badge_adr
from badge.msg.connection import NowListener
from bdg.utils import singleton, Timer
from bdg.config import Config
from bdg.widgets.hidden_active_widget import HiddenActiveWidget
from gui.core.colors import GREEN, BLACK, D_PINK, WHITE, D_GREEN, D_RED
from gui.core.ugui import Screen, ssd
from gui.core.writer import CWriter
from gui.fonts import arial35, freesans20, font10 as font10
from gui.primitives import launch
from gui.widgets.buttons import Button
from gui.widgets.label import Label


class GameScanScr(Screen):
    """Simple scanner draft that start EspNowScanner and display results in a listbox"""

    sync_update = True  # set screen update mode synchronous

    def __init__(self, ready_cb=None):
        super().__init__()
        self.et = None
        self.show_user_error = asyncio.Event()
        self.show_user_error.clear()
        self.bt = None
        self.ready_cb = ready_cb
        self.wrig = CWriter(ssd, arial35, GREEN, BLACK, verbose=False)
        self.wrigs = CWriter(ssd, font10, GREEN, BLACK, verbose=False)
        self.wrip = CWriter(ssd, freesans20, D_PINK, BLACK, verbose=False)

        self.lbl_s = Label(
            self.wrig, int(170 / 2) - 35, 2, 316, bdcolor=False, justify=1
        )
        self.lbl_s2 = Label(self.wrig, int(170 / 2), 2, 316, bdcolor=False, justify=1)

        self.lbl_i = Label(
            self.wrigs, int(170 / 2) + 5, 2, 316, bdcolor=False, justify=1
        )
        self.lbl_b = Label(
            self.wrip, (int(170 / 3) * 2) + 5, 2, 316, bdcolor=False, justify=1
        )

        HiddenActiveWidget(self.wrig)
        self.update_status()

        self.all_events = ButtonEvents()

    async def btn_handler(self):
        async for btn, ev in self.all_events.get_btn_events():
            self.show_user_error.set()

    def after_open(self):
        if not self.bt or self.bt.done():
            self.bt = self.reg_task(self.btn_handler(), True)

        if not self.et or self.et.done():
            self.et = self.reg_task(self.user_error(), True)

        self.reg_task(self.next_scr(), True)

    def update_status(self):
        print(">>> update_status")

        b_found = len(NowListener.last_seen)
        try:
            b_needed = Config.config["espnow"]["b_needed"]
        except KeyError:
            b_needed = 5
        self.lbl_i.visible = True
        self.lbl_b.visible = True
        self.lbl_s.visible = True
        self.lbl_s2.visible = False
        self.lbl_s2.draw = True
        self.lbl_s.value(f"Scanning...")
        self.lbl_i.value(f"please wait...")
        self.lbl_b.value(f"Badges found: {b_found}/{b_needed}")

    async def next_scr(self):
        print(">>> next_scr")
        await asyncio.sleep(10)
        self.lbl_s.value("Ready!")
        self.lbl_i.value("joining the lobby")
        await asyncio.sleep(2)
        launch(self.ready_cb, ())  # notify caller

    async def user_error(self):
        while True:
            await self.show_user_error.wait()
            print(">>> user_error")

            ssd.fill(BLACK)
            Screen.rfsh_start.set()
            await Screen.rfsh_done.wait()
            self.lbl_i.visible = False
            self.lbl_i.draw = True
            self.lbl_b.visible = False
            self.lbl_b.draw = True
            self.lbl_s.visible = True
            self.lbl_s.value("What part don't")
            self.lbl_s2.visible = True
            self.lbl_s2.value("you understand?")
            Screen.show(force=True)
            await asyncio.sleep(3)
            ssd.fill(BLACK)
            self.update_status()
            Screen.show(force=True)
            print(">>> user_error DONE")
            self.show_user_error.clear()


class GameModeScr(Screen):
    sync_update = True  # set screen update mode synchronous

    def __init__(self):
        super().__init__()
        # verbose default indicates if fast rendering is enabled
        wri = CWriter(ssd, font10, WHITE, BLACK, verbose=False)
        self.nick_lbl = Label(wri, 0, 100, 120, bdcolor=False, justify=1)

        row = fwdbutton(wri, 112, 30, ActiveGameScr, text="Competitive")
        row = fwdbutton(wri, 112, 320 // 3 * 2, "CasualPuzzleScr", text="Casual")

    def after_open(self):
        self.update_score()

    def update_score(self):
        self.nick_lbl.value(Config.config["espnow"]["nick"])


class BadgeCooldown(Exception):
    def __init__(self, message="Badge in cooldown"):
        super().__init__(message)


@singleton
class BadgeGame:
    def __init__(self):
        self.opponent_timer = Timer(60, cb=self.clear_opponent)
        self.opponent_cooldown_t = Timer(30)
        self.opponent = None
        self._old_opponent = None
        self.opponent_timer.stop()

    def clear_opponent(self):
        self._old_opponent = self.opponent
        self.opponent = None
        self.opponent_cooldown_t.start()

    def has_opponent(self) -> bool:
        return self.opponent is not None

    def acquire_opponent(self) -> BadgeAdr:
        """
        Attempts to acquire an opponent from the list of last seen entities and starts the
        opponent timer if successful. The method checks two conditions before selecting
        an opponent: whether the opponent timer is still active and whether the cooldown
        timer for the badge is active. If either condition is true, it raises a
        BadgeCooldown exception. If no opponents are available in the list, a null
        badge address is returned.

        :raises BadgeCooldown: If the opponent timer is still active with remaining time
            or if the badge cooldown timer is active.
        :return: The address of the selected opponent if successfully acquired, or
            a null badge address if no opponents are available.
        """
        if self.opponent_timer.is_act():
            raise BadgeCooldown("Opponent still active {opponent_timer.time_left()}s ")
        else:
            if self.opponent_cooldown_t.is_act():
                raise BadgeCooldown("Badge in cooldown {opponent_cooldown_t.time_left()}s ")

        if len(NowListener.last_seen):
            self.opponent = random.choice(NowListener.last_seen.keys())
            self.opponent_timer.start()
            return self.opponent

        return null_badge_adr


class GameLobbyScr(Screen):
    sync_update = True  # set screen update mode synchronous

    def __init__(self):
        super().__init__()
        self.game = BadgeGame()
        # verbose default indicates if fast rendering is enabled
        wri = CWriter(ssd, font10, WHITE, BLACK, verbose=False)
        wrib = CWriter(ssd, arial35, D_PINK, BLACK, verbose=False)
        self.nick_lbl = Label(wri, 0, 100, 120, bdcolor=False, justify=1)

        self.lbl_i = Label(
            wri, 170 // 3, 2, 316, bdcolor=False, justify=1, fgcolor=D_GREEN
        )

        self.lbl_s = Label(wrib, 170 // 3 + 20, 2, 316, bdcolor=False, justify=1)
        self.lbl_i.value("Badge is")
        self.lbl_s.value("ACTIVE")

        fwdbutton(wri, 170 - 30, 135, GameModeScr, text="Play")

    def after_open(self):
        self.update_nickname()

    def update_nickname(self):
        self.nick_lbl.value(Config.config["espnow"]["nick"])


class ActiveGameScr(Screen):
    sync_update = True  # set screen update mode synchronous
    MODE_READY = 0
    MODE_SEARCHING = 1
    MODE_NO_OPPONENT = 2

    def __init__(self):
        super().__init__()
        self.game = None

        self.mode = self.MODE_READY
        # verbose default indicates if fast rendering is enabled
        self.opponent: BadgeAdr = None
        wri = CWriter(ssd, font10, WHITE, BLACK, verbose=False)
        wrib = CWriter(ssd, arial35, D_PINK, BLACK, verbose=False)
        self.nick_lbl = Label(wri, 0, 100, 120, bdcolor=False, justify=1)

        self.lbl_i = Label(
            wri, 170 // 3 - 30, 2, 316, bdcolor=False, justify=1, fgcolor=D_GREEN
        )
        self.lbl_s = Label(wrib, 170 // 3 - 10, 2, 316, bdcolor=False, justify=1)
        self.lbl_i.value("Badge is")
        self.lbl_s.value("ACTIVE")

        self.lbl_t = Label(
            wri, self.lbl_s.mrow, 2, 316, bdcolor=False, justify=1, fgcolor=D_GREEN
        )
        self.lbl_t.value(f"Opponent:")

        self.track_b = Button(
            wri,
            170 - 60,
            105,
            callback=self.track_cb,
            fgcolor=D_PINK,
            bgcolor=BLACK,
            text="Ready to Play",
            textcolor=D_PINK,
        )

        self.lbl_c = Label(
            wri, self.track_b.mrow + 10, 2, 316, bdcolor=False, justify=1, fgcolor=D_RED
        )

    def track_cb(self, button):
        print("track_cb")
        self.mode = self.MODE_SEARCHING
        self.update_ui()

    async def listen_handler(self):
        async for opponent in NowListener.updates(filer_mac=self.opponent.mac):
            print(f"listen_handler: {opponent}")
            self.opponent = opponent
            self.update_ui()

    def after_open(self):
        self.game = BadgeGame()

        if not self.game.has_opponent():
            try:
                self.opponent = self.game.acquire_opponent()
                if self.opponent is null_badge_adr:
                    self.mode = self.MODE_NO_OPPONENT
                else:
                    self.mode = self.MODE_READY
            except BadgeCooldown as e:
                # FIXME: jump to cooldown screen
                Screen.change("CooldownScr", args=[str(e)])
        self.update_ui()

    def update_ui(self):
        self.nick_lbl.value(Config.config["espnow"]["nick"])

        if self.mode == self.MODE_SEARCHING:
            self.track_b.visible = False
            self.lbl_s.value("SEARCHING")
            # TODO: implement changing message from rssi and time
            self.lbl_t.value(f"{self.opponent} signal is too weak!")
        elif self.mode == self.MODE_READY:
            self.track_b.visible = True
            self.lbl_t.value(f"Opponent: {self.opponent}")
            self.lbl_s.value("ACTIVE")
        else:  # mode=self.MODE_NO_OPPONENT
            self.track_b.visible = True
            self.lbl_c.visible = False
            if self.opponent == null_badge_adr:
                self.lbl_t.value(f"No opponents available")
                self.lbl_s.value("CONNECTION LOST")
            else:
                # TODO: contextful message of reason
                self.lbl_t.value(f"{self.opponent} got away!")
                self.lbl_s.value("CONNECTION LOST")

        self.lbl_c.value(f"Time Left:{self.time_left()}")

    def time_left(self):
        self.game.opponent_timer.time_left()
        return "5min 30s"




async def to_game_lobby():
    print("to_game_lobby")
    Screen.change(GameLobbyScr, mode=Screen.REPLACE)


async def start_game():
    print("start_game")
    Screen.change(
        GameScanScr, kwargs={"ready_cb": to_game_lobby}, mode=Screen.REPLACE
    )
