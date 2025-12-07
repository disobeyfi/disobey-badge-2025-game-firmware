import asyncio

import aioespnow
import network
from collections import deque

from tests.wait_any_coro import WaitAnyCoro

stop_event = None


class EspNowScanner:
    def __init__(self):
        self.stop_event = asyncio.Event()
        self.update_event = asyncio.Event()
        self.main_task = None
        self.last_seen = deque([], 10)

    async def scanner(self, e):
        while True:
            async for mac, msg in e:
                if mac is None:
                    continue
                str_mac = ":".join(f"{byte:02x}" for byte in mac)
                rssi = e.peers_table[mac][0]
                self.last_seen.appendleft((str_mac, rssi, msg))
                self.update_event.set()
            # print(f"{str_mac} [{rssi}dBm] {msg} :")

    async def stop_handler(self):
        await self.stop_event.wait()

    def get_updates(self):
        """
        Coroutine function `get_updates` returns a generator that yields the last seen updates.
        :return: A generator that yields the last seen updates.
        :rtype: generator
        """

        class AsyncIterable:
            def __init__(self, scanner):
                self.scanner = scanner

            def __aiter__(self):  # See note below
                return self

            async def __anext__(self):
                await self.scanner.update_event.wait()
                self.scanner.update_event.clear()
                return self.scanner.last_seen[0]

        return AsyncIterable(self)

    async def run(self):
        print("Scanner starting:#1")
        wlan = network.WLAN(network.STA_IF)
        if not wlan.active():
            wlan.active(True)

        e = aioespnow.AIOESPNow()
        e.active(True)
        self.stop_event.clear()

        print("Scanner starting:")
        # Wait for the first task to complete
        done, pending = await WaitAnyCoro(self.scanner(e), self.stop_handler()).wait(
            cancel=True
        )

        e.active(False)
        print("Scanner exit")
        self.main_task = None

    def start(self, task=False):
        print("Starting async scanner")
        if task:
            asyncio.create_task(self.run())
        else:
            asyncio.run(self.run())

    def stop(self):
        print("Stopping async scanner")
        if self.stop_event:
            self.stop_event.set()
