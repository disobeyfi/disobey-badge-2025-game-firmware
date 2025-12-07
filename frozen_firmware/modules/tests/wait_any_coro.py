import asyncio


class WaitAnyCoro:
    """
    This module provides the `WaitAnyCoro` class, which allows for waiting on multiple
    coroutines and triggering returning the completed coroutine and the remaining coroutines.

    :class:`WaitAnyCoro` is initialized with a variable number of coroutines, passed as arguments.

    Example usage:
        >>> async def coroutine1():
        ...     await asyncio.sleep(1)
        ...     return "Coroutine 1 complete"

        >>> async def coroutine2():
        ...     await asyncio.sleep(2)
        ...     return "Coroutine 2 complete"

        >>> wait_any_coro = WaitAnyCoro(coroutine1(), coroutine2())
        >>> done, remaining = await wait_any_coro.wait(cancel=False)
        >>> for task in remaining:
        ...     result = await task
        ...     print(result)
        ...
        Coroutine 1 complete
    """

    def __init__(self, *coros):
        self.coros = list(coros)
        self.trig_event = None
        self.evt = asyncio.Event()
        self.evt.clear()
        self.tasks = None

    async def wait(self, cancel=False):
        """
        Asynchronously waits for coroutines to finnish

        :param cancel: Boolean flag indicating whether to cancel all pending tasks
            if `True`, default is `False`.
        :return: A tuple containing the task(s) that have been completed and all pending tasks.
        """
        tasks = self.tasks or {
            coro: asyncio.create_task(self.wt(coro)) for coro in self.coros
        }
        try:
            # print("wait on evt")
            await self.evt.wait()
        finally:
            # print("event triggered")
            self.evt.clear()
            if cancel:
                for task in tasks.values():
                    # print(f"task {task.done()=}")
                    task.cancel()
            done = tasks.pop(self.trig_event)
            self.tasks = tasks
        return done, tasks.values()

    async def wt(self, coro):
        try:
            # print("waiting on", coro)
            return await coro
        finally:
            if not self.evt.is_set():
                self.trig_event = coro
            self.evt.set()
