import asyncio

from bdg.utils import enum
from primitives import Pushbutton
from machine import Pin


class AsyncBtn(Pushbutton):
    def __init__(self, pin, suppress=False, sense=None):
        super().__init__(pin, suppress, sense)
        self._trigger = asyncio.Event()
        self._pin.irq(
            trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler=self.irq_handler
        )

    def irq_handler(self, pin):
        self._trigger.set()

    async def _go(self):
        while True:
            await self._trigger.wait()
            self._check(self.rawstate())
            await asyncio.sleep_ms(Pushbutton.debounce_ms)
            self._trigger.clear()
            self._check(self.rawstate())


ButAct = enum(ACT_PRESS=0, ACT_RELEASE=1, ACT_DOUBLE=2, ACT_LONG=3)


class ButtonEvents:
    _b_lookup = dict()
    _b_events = set()

    @classmethod
    def init(cls, button_conf):
        # add all buttons to ButtonEvent class

        for attr in dir(button_conf):
            if attr.startswith("btn_"):  # Filter attributes that start with 'btn_'
                b_pin = getattr(button_conf, attr)  # Access the attribute dynamically
                if isinstance(b_pin, Pin):  # Ensure it is a Pin instance
                    print(f"Bind {attr}, pin {b_pin}")
                    button = AsyncBtn(b_pin, suppress=False)
                    button.press_func(None)
                    ev = button.press
                    ButtonEvents._b_events.add(ev)
                    ButtonEvents._b_lookup[ev] = (attr, ButAct.ACT_PRESS)

                    button.release_func(None)
                    ev = button.release
                    ButtonEvents._b_events.add(ev)
                    ButtonEvents._b_lookup[ev] = (attr, ButAct.ACT_RELEASE)

                    button.double_func(None)
                    ev = button.double
                    ButtonEvents._b_events.add(ev)
                    ButtonEvents._b_lookup[ev] = (attr, ButAct.ACT_DOUBLE)

                    button.long_func(None)
                    ev = button.long
                    ButtonEvents._b_events.add(ev)
                    ButtonEvents._b_lookup[ev] = (attr, ButAct.ACT_LONG)

    @classmethod
    def get_event_subset(cls, events: list[tuple[str, ButAct]]):
        """
        Filters a subset of events from the provided set of events based on the
        ''_b_lookup'' dictionary mapping.

        This method compares the provided events with the class attribute
        ''_b_lookup'' and identifies matches. Each match is added to the subset,
        and the matched event is removed from the input events copy to avoid
        duplicating effort while processing. The method ensures the subset
        contains only events that map to the corresponding keys in the
        ''_b_lookup''.

        :param events: A set of tuple pairs where each tuple consists of a string
            and an instance of ''ButAct''.
        :return: A subset of keys from ''_b_lookup'' that correspond to matches
            found in the provided ''events'' set, represented as a set.
        """
        subset = set()
        rem_events = list(events)  # Copy events to avoid modifying the input

        for event_key, lookup_value in cls._b_lookup.items():
            for event in rem_events:
                if event[0] == lookup_value[0] and event[1] == lookup_value[1]:
                    subset.add(event_key)
                    rem_events.remove(event)  # Remove matched event from the copy
                    break  # Exit inner loop once a match is found

        return subset

    def __init__(self, events=None):
        self.ev_set = events or ButtonEvents._b_events

    def get_btn_events(self, events=None):
        class Aiter:
            def __init__(self, button_event, ev_set):
                self.button_event = button_event
                self.any_event = asyncio.Event()
                self.trig_event = None  # event that got triggered
                # map all ev to waiting tasks
                self.tasks = [asyncio.create_task(self.wt(event)) for event in ev_set]

            def __aiter__(self):  # See note below
                return self

            def _cancel(self):
                for task in self.tasks:
                    task.cancel()

            async def wt(self, event):
                try:
                    while True:
                        await event.wait()
                        event.clear()
                        self.any_event.set()
                        self.trig_event = event
                        # await asyncio.sleep(0) # make sure that other code can run
                except asyncio.CancelledError:
                    # iterator exited
                    raise
                finally:
                    # cleanup all event tasks
                    self._cancel()

            async def __anext__(self):
                await self.any_event.wait()
                self.any_event.clear()
                return ButtonEvents._b_lookup[self.trig_event]

        return Aiter(self, ev_set=events or self.ev_set)
