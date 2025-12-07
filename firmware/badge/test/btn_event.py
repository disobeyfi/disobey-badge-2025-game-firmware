from badge.asyncbutton import *
from badge.asyncbutton import ButtonEvents, ButAct
from hardware_setup import BtnConfig

# global button event init, do once
ButtonEvents.init(BtnConfig)


async def main():
    i = 0

    be = ButtonEvents()

    print("Listening all buttons, all events, make 30 events to continue:")
    async for btn_ev in be.get_btn_events():
        print(btn_ev)
        i += 1
        if i == 30:
            break
    print("done:")

    print("Listening to A / B buttons, make  10 events to continue:")
    ev_subset = ButtonEvents.get_event_subset(
            [("btn_a", ButAct.ACT_PRESS),
            ("btn_b", ButAct.ACT_RELEASE),
            ("btn_a", ButAct.ACT_LONG),
            ("btn_b", ButAct.ACT_DOUBLE)],
    )

    be = ButtonEvents(ev_subset)
    i=0
    async for btn_ev in be.get_btn_events():
        print(btn_ev)
        i += 1
        if i == 10:
            break
    print("done:")

    #example of button handler
    print("Button handler example for  A / B buttons, make  10 events to continue:")

    be = ButtonEvents(ev_subset)
    i=0

    handlers = {'btn_a' : lambda e:print(f'handle btn_a ev:{e}'),
                'btn_b': lambda e: print(f'handle btn_b ev:{e}')
                }

    async for btn, ev in be.get_btn_events():
        handlers.get(btn, lambda e:print(f'unknown {btn} {e}'))(ev)
        i += 1
        if i == 10:
            break
    print("done:")



asyncio.run(main())
