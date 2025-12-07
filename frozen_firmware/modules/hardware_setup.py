import gc

from machine import Pin, SPI, freq

from drivers.st7789.st7789_16bit import ST7789 as SSD, PORTRAIT, ADAFRUIT_1_9

# Create and export an SSD instance
pdc = Pin(15, Pin.OUT, value=0)  # data command (violet)
prst = Pin(7, Pin.OUT, value=1)  # reset (blue)
pcs = Pin(6, Pin.OUT, value=1)  # chip select (green)
pbl = Pin(19, Pin.OUT, value=1)  # chip select (green)

gc.collect()  # Precaution before instantiating framebuf
spi = SPI(
    1, baudrate=80_000_000, sck=Pin(4), mosi=Pin(5), miso=Pin(16)
)  # No need to wire MISO.
freq(240_000_000)
gc.collect()  # Precaution before instantiating framebuf
ssd = SSD(spi, cs=pcs, dc=pdc, rst=prst, height=170, width=320, display=ADAFRUIT_1_9)


# STATIC CONFIG CLASS
class BtnConfig:
    btn_u = Pin(11, Pin.IN, Pin.PULL_UP)
    btn_d = Pin(1, Pin.IN, Pin.PULL_UP)
    btn_l = Pin(21, Pin.IN, Pin.PULL_UP)
    btn_r = Pin(2, Pin.IN, Pin.PULL_UP)
    btn_stick = Pin(14, Pin.IN, Pin.PULL_UP)
    btn_a = Pin(13, Pin.IN, Pin.PULL_UP)
    btn_b = Pin(38, Pin.IN, Pin.PULL_UP)
    btn_start = Pin(12, Pin.IN, Pin.PULL_UP)
    btn_select = Pin(45, Pin.IN, Pin.PULL_DOWN)


# Led configuration
LED_PIN = Pin(18)
LED_AMOUNT = 8
LED_ACTIVATE_PIN = Pin(17, Pin.OUT)


display = None


def init_display():
    global display, ssd
    from gui.core.ugui import (
        Display,
    )  # Must perform this import after instantiating SSD (see other examples)

    gc.collect()  # Precaution before instantiating framebuf
    # Create and export a Display instance
    # Define control buttons

    display = Display(
        ssd,
        nxt=BtnConfig.btn_r,
        sel=BtnConfig.btn_a,
        prev=BtnConfig.btn_l,
        incr=BtnConfig.btn_u,
        decr=BtnConfig.btn_d,
    )


init_display()
