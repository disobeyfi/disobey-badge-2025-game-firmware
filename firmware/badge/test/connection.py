import asyncio
import random

import aioespnow
#python ./micropython/tools/mpremote/mpremote.py baud 460800 u0 mip install aiorepl
import aiorepl

import gc

import network

from badge.msg import BeaconMsg, RPSMsg
from badge.msg.connection import Connection, NowListener, Beacon


async def demo():
    await asyncio.sleep_ms(1000)
    print("async demo")


state = 20


async def \
        task1(c: Connection):

    print("task1 " * 5)
    if await c.connect():
        print("connected")
        await asyncio.sleep(5)

        for choice in range(2):
            r = RPSMsg(choice=choice)
            await asyncio.sleep(1)
            c.send_app_msg(r)

        print(f"{await c.terminate()=}")

        print("sleeping")
        await asyncio.sleep(5)
        print("done sleeping")
    else:
        print("not connected")
    print("task1 out")


async def task2(c: Connection):
    print("task2")
    async for msg in c.get_msg_aiter():
        print(f"task2 got :{msg=}")
    print("task2 out")


async def main():
    sta = network.WLAN(network.STA_IF)  # Or network.AP_IF
    sta.active(True)

    own_mac = sta.config("mac")

    print(f"Starting tasks.. MAC: \nmac={own_mac} ")

    #    sta.disconnect()  # For ESP8266

    e = aioespnow.AIOESPNow()
    e.active(True)

    nick = "Anon" + str(random.randint(1000, 9999))
    beaconmsg = BeaconMsg(nick)

    Beacon.setup(e, beaconmsg)
    Beacon.suspend(True)

    # Start other program tasks.
    tasks = [Beacon.start(task=True), NowListener.start(e)]

    # Start the aiorepl task. These variables can be used
    print(f"connect to another badge:")
    print(
        f"""
# Paste mac from other badge, paste lines below 1 by 1
c = Connection(mac, 1, e)
await c.connect()
await c.ping()

# Start beacon on some other badges
Beacon.suspend(False)

# List other badges found by this
dict(NowListener.last_seen)

"""
    )
    print("--" * 20)
    context = {
        "Beacon": Beacon,
        "NowListener": NowListener,
        "Connection": Connection,
        "c": None,
        "e": e,
        "task1": task1,
    }

    repl = asyncio.create_task(aiorepl.task(context))
    tasks.append(repl)

    gc.collect()

    await asyncio.gather(*tasks)


asyncio.run(main())
