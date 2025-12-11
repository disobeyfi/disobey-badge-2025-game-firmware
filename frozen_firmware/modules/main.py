# This is the file that is run when device starts

# import frozen_fs mounts `frozen_fs` as `/readonly_fs`
import frozen_fs
import network
import aioespnow
import hardware_setup

from gui.core.ugui import Screen, quiet

from bdg.config import Config
from bdg.version import Version
from bdg.repl_helpers import load_app
from bdg.screens.boot_screen import BootScr
from ota import rollback as ota_rollback
from ota import status as ota_status


print(f"Booting..")
print("Disobey 2026")
print(f"Version: {Version().version}")
print(f"Build: {Version().build}")
print(f"")
print(f"Global variables and objects available:")
print(f"  - 'config': Config() object with firmware version info")
print(f"  - 'load_app': Helper function to load apps for testing")
print(f"")
print(f"Check also Badge API documentation in Github")

# Acknowledge OTA was successful and rollback is not needed as we've booted successfully
boot_partition = ota_status.boot_ota()
if not boot_partition.info()[4] == "factory":
    # Do rollback only when we are not booting from factory partition
    ota_rollback.cancel()

Config.load()
globals()["config"] = Config()
globals()["load_app"] = load_app


def start_badge():
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
    # print(f"MAC: \nmac={own_mac} ")
    print(f"")
    print(f"Badge's MAC address: #{own_mac}")

    quiet()

    def tmp():
        print("Ready!")

    Screen.change(BootScr, kwargs={"ready_cb": tmp, "espnow": e, "sta": sta})


start_badge()
