from gui.core.colors import GREEN, BLACK
from gui.fonts import font6, font10, font14
from gui.core.ugui import Screen, ssd
from gui.core.writer import CWriter
from gui.widgets import Label
import uasyncio as asyncio
from bdg.widgets.hidden_active_widget import HiddenActiveWidget


class LoadingScreen(Screen):

    def __init__(
        self,
        title: str,
        wait: int,
        nxt_scr: Screen,
        scr_args: tuple = None,
        scr_kwargs: dict = None,
    ):
        super().__init__()

        wri_title = CWriter(ssd, font14, GREEN, BLACK, verbose=False)

        lbl_t = Label(wri_title, 30, 0, 320, justify=Label.CENTRE)
        lbl_t.value(text=title)

        self.wri = CWriter(ssd, font10, GREEN, BLACK, verbose=False)
        self.lbl_wait = Label(self.wri, 100, 0, 320, justify=Label.CENTRE)

        self.set_lbl_wait(wait)

        HiddenActiveWidget(self.wri)

        self.reg_task(self.wait(wait, nxt_scr, scr_args, scr_kwargs))

    async def wait(self, wait: int, nxt_scr: Screen, scr_args: tuple, scr_kwargs: dict):
        for i in range(wait):
            self.set_lbl_wait(wait - i)
            await asyncio.sleep(1)

        if scr_args is not None:
            Screen.change(nxt_scr, mode=Screen.REPLACE, args=scr_args)
        elif scr_kwargs is not None:
            Screen.change(nxt_scr, mode=Screen.REPLACE, kwargs=scr_kwargs)
        else:
            Screen.change(nxt_scr, mode=Screen.REPLACE)

    def set_lbl_wait(self, sec: int):
        self.lbl_wait.value(text=f"Starts in {sec}..")
