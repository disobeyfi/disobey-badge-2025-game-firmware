import gc

import hardware_setup as hardware_setup
from badge.bleds import ScoreLeds
import machine
import aiorepl
import asyncio

async def main():
    sleds = ScoreLeds( )
    #sleds = ScoreLeds(machine.Pin(18), 8, machine.Pin(19), )


    tasks = [sleds.start_task()]
    # Start the aiorepl task. These variables can be used
    print(f"led tester:")
    print(
f"""
from badge.bleds import *
leds.raw_leds([L_RED,L_GREEN,L_BLUE,L_YELLOW,L_RED,L_GREEN,L_BLUE,L_YELLOW])

leds.set_offensive(6)
leds.set_offensive(16)
leds.set_offensive(21)
leds.set_offensive(25)

leds.set_defensive(6)
leds.set_defensive(16)
leds.set_defensive(21)
leds.set_defensive(25)
leds.turn_off()
leds.turn_on()


"""
    )
    print("--" * 20)
    context = {
        "leds": sleds,
    }

    repl = asyncio.create_task(aiorepl.task(context))
    tasks.append(repl)

    gc.collect()

    await asyncio.gather(*tasks)

asyncio.run(main())