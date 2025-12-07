from gui.core.colors import GREEN, BLACK, RED, YELLOW
from gui.fonts import font6, font10, font14
from gui.core.colors import *
from gui.core.ugui import Screen, ssd
from gui.core.writer import CWriter
from gui.widgets import Label, Textbox, CloseButton
from bdg.widgets.hidden_active_widget import HiddenActiveWidget
from ota import update as ota_update
from ota import status as ota_status
import uasyncio as asyncio
import network
import requests

# TODO/steps for ota
# 1. turn of espnow and connect wifi
# 2. download firmware
# 3. update firmware
# 4. reboot
# 5. if failure, turn wifi off and espnow on


class OTAScreen(Screen):

    def __init__(self, espnow, sta, fw_version: str, ota_config: dict):
        super().__init__()

        self.espnow = espnow
        self.sta = sta
        self.ota_config = ota_config
        self.ota_project = "badge-2025-firmware"
        self.cur_version = fw_version

        self.wri = CWriter(ssd, font10, GREEN, BLACK, verbose=False)
        self.wri_title = CWriter(ssd, font14, GREEN, BLACK, verbose=False)

        Label(self.wri_title, 10, 10, f"Firmware update")

        self.box_out = Textbox(self.wri, 40, 10, 300, 7, active=False, bdcolor=False)

        self.box_out.append(f"Current version: {fw_version}")

        self.reg_task(
            self.start_ota(
                sta, ota_config["wifi"]["ssid"], ota_config["wifi"]["password"]
            )
        )

        HiddenActiveWidget(self.wri)  # Quit the application

    # disconnect from wifi when screen is closed
    def on_hide(self):
        print("OTA Screen closed")
        self.sta.disconnect()
        # Reset sta before leaving, TODO: test this when we have mmenus etc
        self.sta.active(False)
        asyncio.sleep_ms(100)
        self.sta.active(True)
        asyncio.sleep_ms(100)
        if self.espnow:
            from badge.msg.connection import NowListener

            NowListener.start(self.espnow)

    async def start_ota(self, sta, ssid, password):
        if self.espnow:
            from badge.msg.connection import NowListener

            NowListener.stop()
        # Reset sta activity before we start
        sta.active(False)
        await asyncio.sleep_ms(100)
        sta.active(True)
        await asyncio.sleep_ms(100)
        sta.connect(ssid, password)
        self.box_out.append(f"Connecting")
        await asyncio.sleep_ms(100)
        while not sta.isconnected():
            await asyncio.sleep_ms(500)

        # Check status https://docs.micropython.org/en/latest/library/network.WLAN.html#network.WLAN.status

        if sta.status() in [network.STAT_WRONG_PASSWORD, network.STAT_NO_AP_FOUND]:
            self.box_out.append(f"Connecting to {ssid} failed, check password")
            return
        elif sta.status() is network.STAT_GOT_IP:
            self.box_out.append(f"Connected to {ssid} ")

            await asyncio.sleep_ms(200)
            await self.start_ota_update()
        else:
            self.box_out.append(f"Unknown event")

    async def start_ota_update(self):
        updater = OtaUpdater(
            self.ota_config["host"], self.ota_project, self.cur_version
        )
        self.box_out.append("Checking FW-version")
        await asyncio.sleep_ms(200)
        try:
            if updater.update_available():
                self.box_out.append(f"New version {updater.available_version} found")
                await asyncio.sleep_ms(200)
                self.box_out.append(f"Downloading & updating")
                await asyncio.sleep_ms(200)
                updater.update()
                self.box_out.append(f"Update successful, rebooting..")
                await asyncio.sleep_ms(200)
                ota_status.ota_reboot(delay=5)
            else:
                self.box_out.append(f"No new version found")
        except Exception as e:
            self.box_out.append(f"Update failed: {e}")
            print(f"OTA Error: {e}")
            await asyncio.sleep_ms(200)


class OtaUpdater:
    def __init__(self, host, project, current_version):
        self.host = host
        self.project = project
        self.current_version = current_version
        self.available_version = None
        self.json = None

    def update_available(self):
        self.__download_version_json()
        self.available_version = self.json["latest"]

        return self.available_version > self.current_version

    def update(self):
        self.__download_version_json()
        v = self.json["versions"][self.available_version]
        print(v)
        ota_update.from_file(
            self.fw_url(v["url"]), sha=v["sha256"], length=v["size"], reboot=False
        )

    def __download_version_json(self) -> dict:
        if not self.json:
            resp = requests.get(f"{self.host}/{self.project}/ota.json")

            if resp.status_code != 200:
                print(f"Failed to download version.json: {resp.status_code}")
                raise Exception("Failed to check version")

            self.json = resp.json()

    def fw_url(self, path):
        return f"{self.host}{path}"
