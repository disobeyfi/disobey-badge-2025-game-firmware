import asyncio
import os
from gui.fonts import font10, font14
from gui.core.colors import *
from gui.core.ugui import Screen, ssd
from gui.core.writer import CWriter
from gui.widgets import Label, LED, Button, Textbox
from bdg.widgets.hidden_active_widget import HiddenActiveWidget
from bdg.buttons import ButtonEvents, ButAct
from gui.core.ugui import Screen
from gui.widgets import LED, Checkbox, CloseButton
from bdg.version import Version
from bdg.bleds import clear_leds, dimm_gamma, L_PINK
from neopixel import NeoPixel
from machine import Pin


class BtnTestLed(LED):
    def __init__(self, wri, x, y, height=20, fgcolor=D_PINK, color=D_PINK):
        super().__init__(wri, x, y, height=height, fgcolor=fgcolor, color=color)
        self.value(False)


class LedTestCheck(Checkbox):
    def __init__(self, wri, x, y, np_pos, height=20, fgcolor=D_PINK, fillcolor=D_PINK):
        super().__init__(
            wri, x, y, height=height, fgcolor=fgcolor, fillcolor=fillcolor, active=False
        )
        self.value(False)
        self.np_pos = np_pos


class HwTestDoneScr(Screen):

    def __init__(self, nxt_scr=None, scr_kwargs={}, test_skipped=False):
        super().__init__()
        self.nxt_scr = nxt_scr
        self.scr_kwargs = scr_kwargs

        wri_title = CWriter(ssd, font14, GREEN, BLACK, verbose=False)
        lbl_title = Label(wri_title, 20, 0, 320, justify=Label.CENTRE)
        lbl_title.value(text="HARDWARE TEST DONE")

        wri_font10 = CWriter(ssd, font10, GREEN, BLACK, verbose=False)

        lbl_subtitle = Label(wri_font10, 50, 0, 320, justify=Label.CENTRE)
        lbl_subtitle.value(text=f"Hardware test done for build {Version().build}")

        lbl_continue = Label(wri_font10, 70, 0, 320, justify=Label.CENTRE)
        if test_skipped:
            lbl_continue.value(text=f"Continue to OTA")
        else:
            lbl_continue.value(text=f"If all looks good, continue to OTA")

        wri = CWriter(ssd, font10, D_PINK, BLACK, verbose=False)

        Button(
            wri,
            120,
            100,
            width=100,
            height=30,
            text="Continue to OTA",
            callback=self.cont,
        )

        HiddenActiveWidget(wri)

    def cont(self, *args):
        Screen.change(self.nxt_scr, kwargs=self.scr_kwargs)


class HwTestScr(Screen):
    # Button task
    bt = None
    # Led task
    lt = None

    HW_TEST_FILE = "/.hw_tested_in_build"

    def __init__(self, force_run=False, nxt_scr=None, scr_kwargs={}):
        super().__init__()
        self.nxt_scr = nxt_scr
        self.scr_kwargs = scr_kwargs
        self.force_run = force_run

        hw_test_done = self._check_test_done()

        if not self.force_run and hw_test_done:
            # Test already passed for this firmware version, skip
            print("Hardware test already done for this firmware version, skipping.")

            # Dummy widgets, after_open will handle continuation
            wri = CWriter(ssd, font10, D_GREEN, BLACK, verbose=False)
            HiddenActiveWidget(wri)

        else:
            self._create_test_screen()

    def _get_current_build_id(self):
        """Get the current build ID from the Version module"""
        try:
            return Version().build
        except:
            return "unknown"

    def _check_test_done(self):
        """Check if hardware test has been done for current firmware version"""
        try:
            with open(self.HW_TEST_FILE, "r") as f:
                saved_build_id = f.read().strip()
                current_build_id = self._get_current_build_id()
                return saved_build_id == current_build_id
        except:
            return False

    def _mark_test_done(self):
        """Mark hardware test as done for current firmware version"""
        try:
            current_build_id = self._get_current_build_id()
            with open(self.HW_TEST_FILE, "w") as f:
                f.write(current_build_id)
            print(f"Hardware test marked as done for build {current_build_id}")
            self._continue()
        except Exception as e:
            print(f"Failed to mark test as done: {e}")

    def _continue(self, test_skipped=False):
        """Continue to next screen"""
        Screen.change(
            HwTestDoneScr,
            kwargs={
                "scr_kwargs": self.scr_kwargs,
                "nxt_scr": self.nxt_scr,
                "test_skipped": test_skipped,
            },
        )

    def _create_test_screen(self):
        """Create the actual hardware test screen"""
        self.wri = CWriter(ssd, font10, D_GREEN, BLACK, verbose=False)
        self.wri_title = CWriter(ssd, font14, D_GREEN, BLACK, verbose=False)

        HiddenActiveWidget(self.wri)

        lbl_t = Label(self.wri_title, 5, 30, 260, justify=Label.CENTRE)
        lbl_t.value(text="Hardware Test")

        self.lbl_h = Label(self.wri, 150, 30, 260, justify=Label.CENTRE)
        self.lbl_h.value(text="Press each button to proceed")
        self.btn_pressed = set()
        self.btn_test_done = False
        self.led_test_done = False

        led_height = 20
        led_spacing = 10 + led_height
        joystick_x = 70
        joystick_y = 80

        btns_x = 70
        btns_y = 220

        self.btn_leds = {
            "btn_stick": BtnTestLed(self.wri, joystick_x, joystick_y),
            "btn_u": BtnTestLed(self.wri, joystick_x - led_spacing, joystick_y),
            "btn_l": BtnTestLed(self.wri, joystick_x, joystick_y - led_spacing),
            "btn_r": BtnTestLed(self.wri, joystick_x, joystick_y + led_spacing),
            "btn_d": BtnTestLed(self.wri, joystick_x + led_spacing, joystick_y),
            "btn_start": BtnTestLed(self.wri, btns_x, btns_y - led_spacing),
            "btn_select": BtnTestLed(self.wri, btns_x - led_spacing, btns_y),
            "btn_b": BtnTestLed(self.wri, btns_x, btns_y + led_spacing),
            "btn_a": BtnTestLed(self.wri, btns_x + led_spacing, btns_y),
        }

        self.d_leds = [
            LedTestCheck(self.wri, 15, 10, np_pos=5),
            LedTestCheck(self.wri, 45, 10, np_pos=6),
            LedTestCheck(self.wri, 75, 10, np_pos=7),
            LedTestCheck(self.wri, 105, 10, np_pos=8),
            LedTestCheck(self.wri, 135, 10, np_pos=9),
        ]
        self.o_leds = [
            LedTestCheck(self.wri, 15, 295, np_pos=4),
            LedTestCheck(self.wri, 45, 295, np_pos=3),
            LedTestCheck(self.wri, 75, 295, np_pos=2),
            LedTestCheck(self.wri, 105, 295, np_pos=1),
            LedTestCheck(self.wri, 135, 295, np_pos=0),
        ]

        ev_subset = ButtonEvents.get_event_subset(
            [
                ("btn_a", ButAct.ACT_PRESS),
                ("btn_b", ButAct.ACT_PRESS),
                ("btn_select", ButAct.ACT_PRESS),
                ("btn_start", ButAct.ACT_PRESS),
                ("btn_stick", ButAct.ACT_PRESS),
                ("btn_l", ButAct.ACT_PRESS),
                ("btn_r", ButAct.ACT_PRESS),
                ("btn_u", ButAct.ACT_PRESS),
                ("btn_d", ButAct.ACT_PRESS),
            ]
        )
        self.be = ButtonEvents(ev_subset)

    def after_open(self):
        hw_test_done = self._check_test_done()

        if not self.force_run and hw_test_done:
            self._continue(test_skipped=True)
        else:
            # Only start button handler if we're actually running the test and not skipping
            if hasattr(self, "be") and (not self.bt or self.bt.done()):
                self.bt = self.reg_task(self.btn_handler(), True)

    async def btn_handler(self):
        async for btn, ev in self.be.get_btn_events():
            print(f"btn: {btn}, ev: {ev}")
            self.btn_leds[btn].value(True)
            self.btn_pressed.add(btn)
            if len(self.btn_pressed) == 9 and not self.btn_test_done:
                self.lbl_h.value(text="All buttons functional")
                await asyncio.sleep(2)
                self.btn_test_done = True
                self.reg_task(self.test_leds(), True)

    async def test_leds(self):
        if self.btn_test_done and not self.led_test_done:
            # TODO: integrate with bleds properly
            led_activation_pin = Pin(17, Pin.OUT)
            led_activation_pin.value(1)  # Enable power to LEDs
            np = NeoPixel(Pin(18), 10)
            color = dimm_gamma([L_PINK], 0.5)[0]

            self.lbl_h.value(text="Testing LEDs")

            for led in self.d_leds:
                led.value(True)

                np[led.np_pos] = color
                np.write()

                await asyncio.sleep(0.2)

            for led in self.o_leds:
                led.value(True)

                np[led.np_pos] = color
                np.write()

                await asyncio.sleep(0.2)

            self.led_test_done = True
            self.lbl_h.value(text=f"Test DONE for build {self._get_current_build_id()}")
            await asyncio.sleep(1)
            clear_leds(np)
            led_activation_pin.value(0)  # Disable power to LEDs
            # Mark test as completed for this firmware version
            self._mark_test_done()
