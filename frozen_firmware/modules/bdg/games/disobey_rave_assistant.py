import asyncio
import ujson
from machine import Pin
from neopixel import NeoPixel

from gui.core.ugui import Screen, ssd, color_map, FOCUS
from gui.core.writer import CWriter
from gui.widgets import Label, RadioButtons
import gui.fonts.arial10 as arial10
from gui.core.colors import *
from bdg.config import Config
from bdg.widgets.hidden_active_widget import HiddenActiveWidget
from bdg.bleds import clear_leds, dimm_gamma, L_PINK

# Config section key for rave assistant settings
RAVE_CONFIG_KEY = "disobey-rave-assistant"


class LedCountLabel(Label):
    def __init__(self, writer, row, col, width, on_adjust):
        super().__init__(
            writer,
            row,
            col,
            width,
            bdcolor=False,
            justify=Label.CENTRE,
        )
        self._on_adjust = on_adjust
        self.active = True
        self.adjustable = True

        cs = Screen.current_screen
        if cs is not None and self not in cs.lstactive:
            cs.lstactive.append(self)
            if cs.selected_obj is None:
                cs.selected_obj = len(cs.lstactive) - 1

    def do_adj(self, _, val):
        self._on_adjust(1 if val > 0 else -1)


class DisobeyRaveAssistant(Screen):
    def __init__(self):
        super().__init__()

        # Optional: customize the focus border color
        color_map[FOCUS] = GREEN

        # Writer for buttons (smaller font)
        self.wri_btn = CWriter(ssd, arial10, GREEN, BLACK, verbose=False)

        # Enable focus handling on buttons
        HiddenActiveWidget(self.wri_btn)

        Config.load()

        # --- LED hardware ---
        self.led_power = Pin(17, Pin.OUT)
        self.led_power.value(1)
        self.led_pin = Pin(18)
        self.active_leds = max(
            1,
            int(
                Config.config.get(RAVE_CONFIG_KEY, {}).get(
                    "rave_led_amount",
                    Config.config.get(RAVE_CONFIG_KEY, {}).get("rave_led_amount", 10),
                )
            ),
        )
        self.np = NeoPixel(self.led_pin, self.active_leds)

        # --- Radio buttons ---
        table = [
            {"text": "Blue Team", "args": ["blue"]},
            {"text": "Red Team", "args": ["red"]},
            {"text": "Script Kiddie", "args": ["kiddie"]},
        ]

        # --- Mode state ---
        self.mode = Config.config.get(RAVE_CONFIG_KEY, {}).get("preset", table[0]["args"][0])
        self.running = True

        # Find the index of the saved preset mode
        selected_index = 0
        for idx, t in enumerate(table):
            if t["args"][0] == self.mode:
                selected_index = idx
                break

        rb = RadioButtons(DARKGREEN, self.set_mode, selected=selected_index)
        col = 16
        button_width = 88
        for t in table:
            btn = rb.add_button(
                self.wri_btn,
                100,
                col,
                width=button_width,
                height=30,
                textcolor=WHITE,
                fgcolor=GREEN,
                **t,
            )
            col += button_width + 8

        self.led_count_lbl = LedCountLabel(
            self.wri_btn,
            140,
            80,
            160,
            self._change_led_count,
        )
        self._update_led_count_label()

    # Radio button callback
    def set_mode(self, button, mode):
        print("Mode selected:", mode)
        self.mode = mode
        self._save_mode()

    def _update_led_count_label(self):
        self.led_count_lbl.value(f"LEDs: {self.active_leds}")

    def _save_config(self):
        if RAVE_CONFIG_KEY not in Config.config:
            Config.config[RAVE_CONFIG_KEY] = {}
        Config.config[RAVE_CONFIG_KEY]["rave_led_amount"] = self.active_leds
        Config.config[RAVE_CONFIG_KEY]["preset"] = self.mode

        try:
            if hasattr(Config, "save"):
                Config.save()
            else:
                with open("/config.json", "w") as f:
                    ujson.dump(Config.config, f)
            print("Saved rave config: leds=", self.active_leds, "preset=", self.mode)
        except (AttributeError, OSError) as e:
            print(f"Error saving rave config: {e}")

    def _save_mode(self):
        self._save_config()

    def _change_led_count(self, delta):
        new_amount = max(1, self.active_leds + delta)
        if new_amount == self.active_leds:
            return
        old_np = self.np
        self.active_leds = new_amount
        self.np = NeoPixel(self.led_pin, self.active_leds)
        clear_leds(old_np)
        self._update_led_count_label()
        self._save_config()

    # Screen lifecycle
    def after_open(self):
        self.reg_task(self.flash_leds(), True)

    def on_hide(self):
        self.running = False
        clear_leds(self.np)
        self.led_power.value(0)

    # LED logic
    async def flash_leds(self):
        calm_colors = dimm_gamma(
            [(0, 0, 255), (30, 100, 255), (20, 20, 255)],
            0.4,
        )

        hacker_colors = dimm_gamma(
            [(255, 0, 0), (180, 0, 50), (255, 0, 100), (255, 0, 255)],
            0.3,
        )

        crazy_colors = dimm_gamma(
            [(255, 0, 0), (0, 255, 0), (0, 0, 255), L_PINK],
            0.6,
        )

        idx = 0

        while self.running:
            led_count = self.active_leds
            if self.mode == "blue":
                colors = calm_colors
                delay = 0.6
                for i in range(led_count):
                    self.np[i] = colors[(idx + i) % len(colors)]

            elif self.mode == "red":
                colors = hacker_colors
                delay = 0.2
                for i in range(led_count):
                    self.np[i] = colors[(idx + i) % len(colors)]

            else:  # script kiddie 😈
                colors = crazy_colors
                delay = 0.08
                for i in range(led_count):
                    self.np[i] = colors[(idx + i * 3) % len(colors)]

            for i in range(led_count, len(self.np)):
                self.np[i] = (0, 0, 0)

            self.np.write()
            idx += 1
            await asyncio.sleep(delay)
            
def badge_game_config():
    """
    Configuration for DisobeyRaveAssistant app

    Returns:
        dict: Game configuration with con_id, title, screen_class, etc.
    """
    return {
        "con_id": 42,
        "title": "Disobey Rave Assistant",
        "screen_class": DisobeyRaveAssistant,
        "screen_args": (), 
        "multiplayer": False,
        "description": "Flashy LEDs with extensions",
    }
