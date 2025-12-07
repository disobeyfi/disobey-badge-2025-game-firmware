import machine
import asyncio
from asyncio import sleep
from neopixel import NeoPixel
from bdg.utils import singleton, Timer
from primitives import Queue


L_GREEN = (0x33, 0xFF, 0)
L_PINK = (0xFF, 0, 0xF0)
L_RED = (0xD2, 0x00, 0)
L_BLACK = (0, 0, 0)
L_BLUE = (0, 0, 0xFF)
L_YELLOW = (0xFF, 0xFF, 0)


def clear_leds(np: NeoPixel):
    for i in range(np.n):
        np[i] = (0, 0, 0)
    np.write()


def dimm_gamma(current_colors, fraction, gamma=2.2) -> list[tuple[int, int, int]]:
    """
    Apply gamma-corrected dimming to each (R, G, B) color in the list.

    Parameters
    ----------
    current_colors : list of tuples
        Each tuple is (R, G, B), 0..255.
    fraction : float
        Dimming level [0..1]. 1 means full intensity, 0 means off.
    gamma : float
        Gamma value for human-perceived brightness correction.

    Returns
    -------
    list of tuples
        Gamma-corrected (R, G, B) values scaled by the given fraction.
    """

    def gamma_correct(channel):
        # Convert 0..255 to 0..1, raise to gamma (linear light),
        # scale by fraction, invert gamma, and convert back to 0..255.
        linear = (channel / 255.0) ** gamma  # channel in linear space
        dimmed_linear = linear * fraction  # apply dimming fraction
        corrected = dimmed_linear ** (1.0 / gamma)
        return int(round(corrected * 255))

    return [tuple(gamma_correct(c) for c in color) for color in current_colors]


def show_level(level):
    """
    Calculate LED states for a given level.
    LED5 to LED1 are represented in reverse order for the pattern.
    """
    # Define LED colors in order of progression
    if level < 1:
        return [L_BLACK] * 5
    if level > 25:
        return [L_RED] * 5

    colors = [L_GREEN, L_PINK, L_BLUE, L_YELLOW, L_RED]

    # Determine the current color band and LEDs to light up
    color_band = (level - 1) // 5  # Each color band spans 5 levels
    active_leds = (level - 1) % 5 + 1  # LEDs to light up within the band

    # Ensure color_band stays within range
    current_color = colors[color_band % len(colors)]

    # Build LED state for 5 LEDs (LED5 to LED1)

    leds = [L_BLACK] * 5 if level < 5 else [colors[color_band - 1]] * 5

    for i in range(active_leds):
        leds[4 - i] = current_color  # Fill LEDs from LED1 upwards

    return leds


@singleton
class ScoreLeds:
    """
    The `ScoreLeds` class facilitates LED control and lighting patterns for a connected LED device.

    This class manages LED animations, color updates, and device activation or dimming logic using asynchronous
    methods and a task queue. It allows dynamic changes to the LED's offensive and defensive states and supports
    a demonstration cycle for visual effects, ensuring smooth and coordinated LED behavior.

    """

    DIMMED_LIM = 0.99

    def __init__(self, led_pin: machine.Pin, leds: int, activate_pin: machine.Pin):
        super().__init__()
        self.leds_on = True
        self._task = None
        self.current_colors = []
        self.defensive = 0
        self.offensive = 0
        self.activate_pin = activate_pin
        self.__np = NeoPixel(led_pin, leds)
        self.__queue = Queue(maxsize=3)
        self.__np: NeoPixel
        self.__queue: Queue
        self.LEDS_OFF = [L_BLACK] * leds

    def start_task(self, *args, **kwargs):
        print(f"Starting async {type(self).__name__}")

        if self._task and self._task.done() or not self._task:
            # now start the task with all args except "task"
            self._task = asyncio.create_task(self.task(*args, **kwargs))
            print(f"new task: {self._task=}")
        return self._task

    def raw_leds(self, led_colors: list[tuple[int, int, int]]):
        assert isinstance(led_colors, list), "led_colors must be a list of tuples"
        assert all(
            isinstance(color, tuple) and len(color) == 3 for color in led_colors
        ), "Each color must be a tuple of 3 elements (r, g, b)"
        # print(f"raw_leds: {led_colors}")
        self.__queue.put_nowait(led_colors)

    def turn_off(self):
        self.__queue.put_nowait(None)

    def turn_on(self):
        self.raw_leds(self.current_colors)

    def set_offensive(self, level):
        self.offensive = level
        self.raw_leds(
            dimm_gamma(show_level(self.offensive) + show_level(self.defensive), 0.2)
        )

    def set_defensive(self, level):
        self.defensive = level
        self.raw_leds(
            dimm_gamma(show_level(self.offensive) + show_level(self.defensive), 0.2)
        )

    async def demo_cycle(self):
        np = self.__np
        n = self.__np.n
        # cycle
        for i in range(4 * n):
            for j in range(n):
                np[j] = (0, 0, 0)
            np[i % n] = (255, 255, 255)
            np.write()
            await sleep(0.025)

        # bounce
        for i in range(4 * n):
            for j in range(n):
                np[j] = (0, 0, 128)
            if (i // n) % 2 == 0:
                np[i % n] = (0, 0, 0)
            else:
                np[n - 1 - (i % n)] = (0, 0, 0)
            np.write()
            await sleep(0.060)

        # fade in/out
        for i in range(0, 4 * 256, 8):
            for j in range(n):
                if (i // 256) % 2 == 0:
                    val = i & 0xFF
                else:
                    val = 255 - (i & 0xFF)
                np[j] = (val, 0, 0)
            np.write()
            await sleep(0)

        # clear
        for i in range(n):
            np[i] = (0, 0, 0)
        np.write()

    async def task(self, *args, **kwargs):
        print(f"start task {type(self).__name__}")
        self.activate_pin.value(1)  # activate led driver
        await self.demo_cycle()
        dimm_timer = Timer(15, start=False)
        self.current_colors = []
        np: NeoPixel = self.__np

        while True:
            led_colors = None
            try:
                led_colors = await asyncio.wait_for(
                    self.__queue.get(), 1 if dimm_timer.is_act() else 10
                )
                if led_colors is not None:
                    self.current_colors = led_colors
                dimm_timer.restart()
                self.leds_on = True
                self.activate_pin.value(1)  # turn on led driver

            except asyncio.TimeoutError:
                if dimm_timer.is_act():
                    self.leds_on = True
                    # print(f"dimming {dimm_timer.progress()}")
                    led_colors = dimm_gamma(
                        self.current_colors,
                        1.0 - dimm_timer.progress(lim=self.DIMMED_LIM),
                    )
                if dimm_timer.done():
                    self.leds_on = True  # set the final static value
                    led_colors = dimm_gamma(self.current_colors, 1.0 - self.DIMMED_LIM)

            if not self.leds_on:
                continue

            if led_colors is None:
                led_colors = self.LEDS_OFF

            # all leds are off, turn power off
            if all(x == 0 for tup in led_colors for x in tup):
                print("All null, Turn leds off: None")
                self.leds_on = False
                dimm_timer.reset()
                self.activate_pin.value(0)  # turn off led driver
                ## TODO REMOVE THIS as it is for wired board
                ## when leds are shutdown they forget also the color
                for i, color in enumerate(led_colors):
                    if i >= np.n:
                        break
                    np[i] = color
                np.write()
                ### remove ends here
                continue

            # update actual leds
            for i, color in enumerate(led_colors):
                if i >= np.n:
                    break
                np[i] = color
            np.write()
