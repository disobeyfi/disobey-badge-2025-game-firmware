# This is the file that is run when device starts

# import frozen_fs mounts `frozen_fs` as `/readonly_fs`
import frozen_fs
import network
import hardware_setup as hardware_setup
from hardware_setup import BtnConfig
from bdg.config import Config

from gui.core.colors import *
from gui.core.ugui import Screen
from ota import rollback as ota_rollback
from ota import status as ota_status
from bdg.screens.hw_test import HwTestScr
from bdg.version import Version
from bdg.buttons import ButtonEvents
from bdg.screens.ota import OTAScreen


print(f"Booting..")
print("Disobey 2026")
print(f"Version: {Version().version}")
print(f"Build: {Version().build}")
print(f"Firmware type: minimal")

# Acknowledge OTA was successful and rollback is not needed as we've booted successfully
boot_partition = ota_status.boot_ota()
if not boot_partition.info()[4] == "factory":
    # Do rollback only when we are not booting from factory partition
    ota_rollback.cancel()


def main():
    # init button even machine
    ButtonEvents.init(BtnConfig)

    Config.load()

    sta = network.WLAN(network.STA_IF)

    Screen.change(
        HwTestScr,
        kwargs={
            "force_run": False,
            "nxt_scr": OTAScreen,
            "scr_kwargs": {
                "espnow": None,
                "sta": sta,
                "fw_version": Version().version,
                "ota_config": Config.config["ota"],
            },
        },
    )


main()
