import asyncio

from badge.msg import BadgeAdr, null_badge_adr
from badge.msg.connection import NowListener, Beacon
from gui.core.colors import GREEN, BLACK, RED
from gui.core.ugui import Screen, ssd
from gui.core.writer import CWriter
from gui.fonts import font10
from gui.primitives import launch
from gui.widgets.buttons import CloseButton
from gui.widgets.dropdown import Dropdown
from gui.widgets.label import Label
from gui.widgets.listbox import Listbox, dolittle


class BadgeScreen(Screen):
    def __init__(self, badge_addr: BadgeAdr = null_badge_adr, ):
        self.baddr = badge_addr

        super().__init__()
        self.wri = CWriter(ssd, font10, GREEN, BLACK, verbose=False)

        self.b_lbl = Label(self.wri, 5, 5, f"{badge_addr}")

        self.b_lbl = Label(self.wri, 20, 5, f"Badge is ACTIVE", bdcolor=RED, fgcolor=GREEN, bgcolor=RED)

        self.s_lbl = Label(self.wri, 35, 160, 100, bdcolor=RED, fgcolor=GREEN, bgcolor=RED)

        self.els_friendly = [
            "TicTacToe", # APP_ID 1
            "React", # APP_ID 2
            "RPSLS", # APP_ID 3
        ]
        self.els_competitive = [
            "blink",  # blink opponent badge to locate 0p
            "dagger",  # close proximity action  5p
            "TicTactToe",  # challenge to TicTacToe 10p
            "BreachProtocol",  # Guess what is the opponent defend key
            "buzz",  # buzz opponents buzzer if fails to counter 10p
        ]

        self.lb = Listbox(
            self.wri,
            50,
            50,
            elements=self.els_friendly,
            dlines=3,
            bdcolor=RED,
            value=1,
            callback=self.lbcb,
            also=Listbox.NOCB,
        )

    async def launch_app(self, app_id):
        # This function is needed to decouple sync / async with launch()
        if not await NowListener.conn_req(self.baddr.mac, app_id):
            self.s_lbl.value("Con failed!")

    def lbcb(self, lb):  # Listbox callback
        if lb.textvalue() == "TicTacToe":
            print("TicTacToe")
            self.s_lbl.value("Connecting...")
            launch(self.launch_app, (1,))
        elif lb.textvalue() == "React":
            self.s_lbl.value("Connecting...")
            launch(self.launch_app, (2,))
        elif lb.textvalue() == "RPSLS":
            self.s_lbl.value("Connecting...")
            launch(self.launch_app, (3,))
        
        print("lbcb!!!")


class ScannerScreen(Screen):
    """Simple scanner draft that start EspNowScanner and display results in a listbox"""

    def __init__(self):
        super().__init__()
        self.update_task = None
        self.sort = 'last_seen'
        self.wri = wri = CWriter(ssd, font10, GREEN, BLACK, verbose=False)
        self.sorters = {
            'last_seen': lambda a: a[2][0].last_seen,
            'rssi': lambda a: a[2][0].rssi,
            'mac': lambda a: a[2][0].mac,
        }

        els = ('last_seen', 'rssi', 'mac',)
        self.s_dropb = Dropdown(wri, 40, 220,
                                elements=els,
                                dlines=5,  # Show 5 lines
                                bdcolor=GREEN,
                                callback=self.set_sort_cb)
        self.s_dropb.textvalue(els[0])

        self.elements = list()
        self.append_list(null_badge_adr)
        self.listbox = Listbox(
            self.wri,
            2,
            2,
            elements=self.elements,
            dlines=7,
            bdcolor=RED,
            value=1,
            also=Listbox.ON_LEAVE,
            width=200,
        )

        CloseButton(self.wri)  # Quit the application

    def set_sort_cb(self, label):
        self.sort = label.textvalue()
        # print(f"set_sort_cb: {self.sort=}")
        try:
            self.elements.sort(key=self.sorters[self.sort], reverse=True)
        except Exception as e:
            print(f"set_sort_cb: {e}")

        self.listbox.update()

    def cb(self, *args):
        # print(f"callback: {args}")
        Screen.change(BadgeScreen, args=(args[1],))

    def on_open(self):
        # TODO: README This is the only way to add workers to task!!
        # if reg_task() is called in init task will not be restarted when coming
        # back from dialog of dropdown
        if not self.update_task or self.update_task.done():
            self.update_task = self.reg_task(self.update_resuls_task(), True)

    def append_list(self, badge_addr: BadgeAdr):

        def is_competitive(badge_addr):
            # TODO: if badge is competitive
            # badge
            return True

        comp = "C"

        # todo: where to import dict_view? fix this to isinstance
        if type(badge_addr).__name__ in ('dict_view', 'list',):
            #   print("got list")
            for b in badge_addr:
                self.append_list(b)
            return

        ##                  ([str, callback, args], [...)
        if len(self.elements) > 20:
            self.elements.pop(0)

        for ui, el in enumerate(self.elements):
            if el[2][0].mac == badge_addr.mac:
                break
        else:
            if badge_addr is null_badge_adr:
                self.elements.append(('-----', dolittle, (badge_addr,)))
            else:
                self.elements.append(
                    (f"[{comp}] {badge_addr.nick} [{badge_addr.rssi}dBm]", self.cb, (badge_addr,)))
            ui = -1

        if ui >= 0:
            self.elements[ui] = (f"[{comp}]{badge_addr.nick} [{badge_addr.rssi}dBm]", self.cb, (badge_addr,))

        # sort based on user selection
        self.elements.sort(key=self.sorters[self.sort], reverse=True)
        # print(f'Badges: {self.elements=}')
        if hasattr(self, "listbox"):
            self.listbox.update()

    async def update_resuls_task(self):
        try:
            print("update_resuls_task: start")
            NowListener.start(None)  # ensure scanner is running
            Beacon.suspend(False)  # ensure that we have beacon on

            # initial update
            self.append_list(NowListener.last_seen.values())

            # wait for changes
            async for latest_key in NowListener.updates():
                self.append_list(NowListener.last_seen[latest_key])
                await asyncio.sleep(0)
            print("update_resuls_task: no more updates")
        except Exception as e:
            print(f"update_resuls_task: {e}")
        finally:
            print("update_resuls_task: end")
