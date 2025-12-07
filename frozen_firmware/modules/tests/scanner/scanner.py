from collections import deque

from gui.core.colors import GREEN, BLACK, RED
from gui.core.ugui import Screen, ssd
from gui.core.writer import CWriter
from gui.fonts import font10
from gui.widgets.buttons import CloseButton
from gui.widgets.listbox import Listbox
from tests.scanner.now_net import EspNowScanner


class ScannerScreen(Screen):
    """Simple scanner draft that start EspNowScanner and display results in a listbox"""

    def __init__(self):
        super().__init__()
        self.wri = CWriter(ssd, font10, GREEN, BLACK, verbose=False)
        self.elements = deque(list(), 10)
        self.append_list(("NoNE", -200, "test"))
        self.listbox = Listbox(
            self.wri,
            2,
            2,
            elements=list(self.elements),
            dlines=7,
            bdcolor=RED,
            value=1,
            also=Listbox.ON_LEAVE,
            width=200,
        )

        CloseButton(self.wri)  # Quit the application

        self.reg_task(update_resuls_task(self))

    def cb(self, *args):
        print(f"{args}")

    def append_list(self, scanner_result: tuple[str, int, str]):
        # print(f'{scanner_result=}')
        mac, rssi, _ = scanner_result
        self.elements.append((f"{mac} [{rssi}dBm]", self.cb, (mac,)))
        if hasattr(self, "listbox"):
            self.listbox.set_elements(list(self.elements))


async def update_resuls_task(scanner_screen: ScannerScreen):
    try:
        scanner = EspNowScanner()
        scanner.start(task=True)
        async for scan_result in scanner.get_updates():
            scanner_screen.append_list(scan_result)
        print("update_resuls_task: end")
    finally:
        # when task is canceled this makes sure that scanner is stopped
        scanner.stop()
