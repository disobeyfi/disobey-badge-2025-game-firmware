from badge.msg.connection import Connection
from gui.core.colors import GREEN, BLACK
from gui.fonts import font6, font10, font14, arial35
from gui.core.ugui import Screen, ssd, display, Widget
from gui.core.writer import CWriter
from gui.widgets import Label, Button, RadioButtons, LED
import asyncio
from gui.core.colors import *
from bdg.widgets.hidden_active_widget import HiddenActiveWidget
import random
from badge.asyncbutton import ButtonEvents, ButAct

DARKYELLOW = create_color(12, 104, 114, 45)
DIS_RED = create_color(13, 210, 0, 0)
DIS_PINK = create_color(14, 240, 0, 240)
# c: color, hc: highlight color
GAME_BTN_COLORS = [
    {"hc": GREEN, "c": LIGHTGREEN, "btn": "btn_select"},
    {"hc": BLUE, "c": DARKBLUE, "btn": "btn_start"},
    {"hc": YELLOW, "c": DARKYELLOW, "btn": "btn_a"},
    {"hc": RED, "c": LIGHTRED, "btn": "btn_b"},
]


class ReactionButton(Widget):
    def __init__(self, writer, row, col, radius, color, hl_color):
        #  Retract 2 pixels to count borders
        radius -= 2
        super().__init__(
            writer, row, col, radius * 2, radius * 2, color, color, False, False
        )
        self.radius = radius
        self.active = False
        self.hl = False
        self.hl_color = hl_color

    def show(self):
        if super().show():
            c = self.hl_color if self.hl else self.fgcolor

            display.fillcircle(
                self.col + self.radius, self.row + self.radius, self.radius, c
            )
            if self.active:
                self.draw_bd(WHITE)
            else:
                self.draw_bd(c)

    def set_act(self, v: bool):
        self.active = v
        self.draw = True  # trigger redraw

    def set_hl(self, v: bool):
        self.hl = v
        self.draw = True

    def draw_bd(self, color):
        display.circle(
            self.col + self.radius, self.row + self.radius, self.radius + 1, color
        )
        display.circle(
            self.col + self.radius, self.row + self.radius, self.radius + 2, color
        )


class GameOver(Exception):
    def __init__(self, points, reason=""):
        super().__init__()
        self.points = points
        self.reason = reason


class GameWin(Exception):
    def __init__(self, points):
        super().__init__()
        self.points = points


class ReactionGameCasualEndScr(Screen):
    color_map[FOCUS] = DIS_PINK

    def __init__(self, points: int, conn: Connection):
        super().__init__()
        self.conn = conn

        wri_points = CWriter(ssd, arial35, WHITE, BLACK, verbose=False)
        lbl_points = Label(wri_points, 20, 0, 320, justify=Label.CENTRE)
        lbl_points.value(text=f"{points}")

        wri_points = CWriter(ssd, arial35, DIS_RED, BLACK, verbose=False)
        lbl_points = Label(wri_points, 70, 0, 320, justify=Label.CENTRE)
        lbl_points.value(text=f"Game Over!")

        wri = CWriter(ssd, font10, DIS_PINK, BLACK, verbose=False)

        Button(wri, 120, 40, width=100, height=24, text="Menu", callback=self.go_back)
        Button(
            wri, 120, 180, width=100, height=24, text="Restart", callback=self.restart
        )

    def go_back(self, *args):
        Screen.back()

    def restart(self, *args):
        Screen.change(
            ReactionGameScr,
            mode=Screen.REPLACE,
            kwargs={"conn": self.conn, "casual": True},
        )


class ReactionGameScr(Screen):

    STATE_GAME_PAUSED = 0
    STATE_GAME_ONGOING = 1
    STATE_GAME_OVER = 2

    # Game's state
    game = None
    # Game task
    gt = None
    # Button task
    bt = None
    # Game UI state
    gs = STATE_GAME_PAUSED

    def __init__(self, conn: Connection, casual: bool = False):
        self.conn: Connection = conn
        self.casual = casual
        super().__init__()
        self.wri = CWriter(ssd, font10, GREEN, BLACK, verbose=False)

        HiddenActiveWidget(self.wri)

        self.btns = []
        self.higlight_tasks = {}

        height = 42
        spacing = 15
        btn_cnt = len(GAME_BTN_COLORS)
        btns_width = btn_cnt * height + (btn_cnt - 1) * spacing
        pos_y = int((320 - btns_width) / 2)

        self.btn_idx = {}
        for i, btn in enumerate(GAME_BTN_COLORS):
            self.btns.append(
                ReactionButton(self.wri, 100, pos_y, 20, btn["c"], btn["hc"])
            )
            self.btn_idx[btn["btn"]] = i
            pos_y += height + spacing

        self.wri_points = CWriter(ssd, arial35, WHITE, BLACK, verbose=False)
        self.lbl_points = Label(self.wri_points, 20, 0, 320, justify=Label.CENTRE)

        ev_subset = ButtonEvents.get_event_subset(
            [
                ("btn_a", ButAct.ACT_PRESS),
                ("btn_b", ButAct.ACT_PRESS),
                ("btn_b", ButAct.ACT_LONG),
                ("btn_l", ButAct.ACT_PRESS),
                ("btn_r", ButAct.ACT_PRESS),
            ]
        )
        self.be = ButtonEvents(ev_subset)

    async def btn_handler(self):
        async for btn, ev in self.be.get_btn_events():
            if ev == ButAct.ACT_LONG and btn == "btn_b":
                self.go_back()
            elif self.gs == self.STATE_GAME_ONGOING:
                print(f"btn: {btn}, ev: {ev}")
                if ev == ButAct.ACT_PRESS:
                    await self.btn_cb(self.btn_idx[btn])

    def go_back(self):
        # TODO: Should we show popup to confirm leaving game?
        if self.gs == self.STATE_GAME_ONGOING:
            print("game ongoing, can't exit!")
        elif self.gs == self.STATE_GAME_OVER:
            Screen.back()

    def after_open(self):
        if self.casual:
            seed = random.randint(10_000, 100_000)
        else:
            # TODO: Exchange seed with other badge#
            # self.seed = random.randint(10_000, 100_000) + other_badge_seed
            seed = 1

        if not self.game:
            self.game = RGame(seed, 20)

        if not self.gt or self.gt.done():
            self.gt = self.reg_task(self.cont_sqnc(), True)

        if not self.bt or self.bt.done():
            self.bt = self.reg_task(self.btn_handler(), True)

    def on_hide(self):
        self.gs = self.STATE_GAME_PAUSED
        print("screen hidden")

    async def cont_sqnc(self):
        await asyncio.sleep(1.5)
        self.gs = self.STATE_GAME_ONGOING
        print("cont_sqnc")
        try:
            while self.game.has_next_step():
                print("cont_sqnc: has next step")
                if self.gs == self.STATE_GAME_OVER:
                    print("state is game over")
                    break

                btn_idx = self.game.next_step()
                print(f"Button index: {btn_idx}")
                await self.hl_button(btn_idx, self.game.cur_idx)
        except GameOver as go:
            print("game over")
            self.gs = self.STATE_GAME_OVER
            # self.lbl_result.value(text=f"{go.reason} p:{go.points}")

    async def btn_cb(self, btn_idx):
        print(f"game state: {self.gs} {btn_idx=}")
        if self.gs == self.STATE_GAME_ONGOING:
            self.higlight_btn(btn_idx)
            try:
                self.game.btn_press(btn_idx)
                self.lbl_points.value(text=str(self.game.points()))
            except GameOver as go:
                # self.lbl_result.value(text=f"Wrong! Your points: {go.points}")
                await self.stop_game()
            except GameWin as go:
                # self.lbl_result.value(
                #    text=f"You won! Your points: {go.points}")
                await self.stop_game()

    async def _highlight_off(self, btn_idx):
        await asyncio.sleep(0.5)
        self.btns[btn_idx].set_act(False)

    def higlight_btn(self, btn_idx):
        # highlight button with separate task and reschedule highlight
        # if button pressed again during wait time
        self.btns[btn_idx].set_act(True)
        if btn_idx in self.higlight_tasks and not self.higlight_tasks[btn_idx].done():
            self.higlight_tasks[btn_idx].cancel()
        self.higlight_tasks[btn_idx] = asyncio.create_task(self._highlight_off(btn_idx))

    async def hl_button(self, btn_idx, step):
        self.btns[btn_idx].set_hl(True)
        hl_time = 0.2 * (0.99**step)
        await asyncio.sleep(hl_time)
        print(f"hl_time {hl_time}")
        self.btns[btn_idx].set_hl(False)

        base_sleep_time = max(0.2, 1.0 * (0.9**step))
        random_factor = 1  # random.uniform(0.8, 1.2)
        sleep_time = base_sleep_time * random_factor
        print(f"sleep_time {sleep_time}")
        await asyncio.sleep(sleep_time)

    async def stop_game(self):
        self.gs = self.STATE_GAME_OVER

        if self.casual:
            # Littel wait so that btn_b doesn't trigger anything on next screen
            await asyncio.sleep_ms(200)
            Screen.change(
                ReactionGameCasualEndScr,
                mode=Screen.REPLACE,
                kwargs={"points": self.game.points(), "conn": self.conn},
            )


class RGame:
    def __init__(self, seed: int, size: int = 200):
        random.seed(seed)

        self.sqnc = [random.randint(0, 3) for _ in range(size)]
        self.size = size
        self.cur_idx = 0
        self.btn_seq_idx = 0

    def has_next_step(self) -> bool:
        if self.cur_idx - self.btn_seq_idx > 5:
            print("Too much behind {self.cur_idx - self.btn_seq_idx=}")
            raise GameOver(points=self.points(), reason="You are too far behind!")

        return self.cur_idx <= self.size

    def next_step(self) -> int:
        step = self.sqnc[self.cur_idx]
        self.cur_idx += 1
        return step

    def btn_press(self, btn_idx: int):
        print(
            f"btn_press - {btn_idx=} - { self.sqnc[self.btn_seq_idx]=}"
            f" - {self.btn_seq_idx=}"
        )
        if btn_idx != self.sqnc[self.btn_seq_idx]:
            raise GameOver(points=self.points())

        if self.btn_seq_idx == self.size - 1:
            # +1 because index starts at 0
            raise GameWin(points=self.points() + 1)

        self.btn_seq_idx += 1

    def points(self):
        return self.btn_seq_idx
