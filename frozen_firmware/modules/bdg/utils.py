import asyncio

from time import time

from gui.primitives import launch


def enum(**enums: int):
    # https://github.com/micropython/micropython-lib/issues/269#issuecomment-1046314507
    return type("Enum", (), enums)


def copy_img_to_mvb(img_file, ssd):
    with open(img_file, "rb") as f:
        rows = int.from_bytes(f.read(2), "big")
        cols = int.from_bytes(f.read(2), "big")
        f.readinto(ssd.mvb)


from framebuf import RGB565, GS4_HMSB, GS8

size = {RGB565: 2, GS4_HMSB: 0, GS8: 1}


def blit(ssd, img, row=0, col=0):
    def scale(x, sz):
        return x * sz if sz else x // 2

    mvb = ssd.mvb  # Memoryview of display's bytearray.
    irows = min(img.rows, ssd.height - row)  # Clip rows
    icols = min(img.cols, ssd.width - col)  # Clip cols
    if (mode := img.mode) != ssd.mode:
        raise ValueError("Image and display have differing modes.")
    sz = size[mode]  # Allow for no. of bytes per pixel
    ibytes = scale(img.cols, sz)  # Bytes per row of unclipped image data
    dbytes = scale(icols, sz)  # Bytes per row to output to display
    dwidth = scale(ssd.width, sz)  # Display width in bytes
    d = scale(row * ssd.width + col, sz)  # Destination index
    s = 0  # Source index
    while irows:
        mvb[d : d + dbytes] = img.data[s : s + dbytes]
        s += ibytes
        d += dwidth
        irows -= 1


def blit_to_buf(ssd, t_mvb, img_height, img_width, pos_y=0, pos_x=0):
    def scale(x, sz):
        return x * sz if sz else x // 2

    mvb = ssd.mvb  # Memoryview of display's bytearray.
    irows = min(img_height, ssd.height - pos_y)  # Clip rows
    icols = min(img_width, ssd.width - pos_x)  # Clip cols
    sz = 2  # Allow for no. of bytes per pixel
    ibytes = scale(img_width, sz)  # Bytes per row of unclipped image data
    dbytes = scale(icols, sz)  # Bytes per row to output to display
    dwidth = scale(ssd.width, sz)  # Display width in bytes
    d = scale(pos_y * ssd.width + pos_x, sz)  # Destination index
    s = 0  # Source index
    while irows:
        #        mvb[d : d + dbytes] = img.data[s : s + dbytes]
        t_mvb[s : s + dbytes] = mvb[d : d + dbytes]

        s += ibytes
        d += dwidth
        irows -= 1


class AProc:
    # A mixed class that ensures that the task() coro is running only once
    # >>> Aproc.start(task=True) returns a task, a new one or the running one
    # >>> Aproc.stop()  # will cancel the running task
    stop_event = asyncio.Event()
    _task = None

    def __init__(self):
        pass

    async def task(self, *args, **kwargs):
        # This needs to be overridden
        print("ERROR: AProc task started!!!!!")
        pass

    async def wait_stop(self):
        await self.stop_event.wait()

    @classmethod
    def start(cls, *args, **kwargs):
        print(f"Starting async {type(cls).__name__}")
        task = kwargs.pop("task", None)
        if task:
            if cls._task and cls._task.done() or not cls._task:
                # now start the task with all args except "task"
                cls._task = asyncio.create_task(cls.task(*args, **kwargs))
                print(f"new task: {cls._task=}")
            return cls._task
        else:
            # sync run, this is missing the logic to ensure single task
            loop = asyncio.get_event_loop()
            loop.run_until_complete(cls.task(*args, **kwargs))

    @classmethod
    def is_running(cls):
        if cls._task and not cls._task.done():
            return True
        return False

    @classmethod
    def stop(cls):
        print(f"Stopping async {cls.__name__}")
        if cls.stop_event:
            cls.stop_event.set()
            cls._task.cancel()
            cls._task = None


def singleton(cls):
    instance = None

    def getinstance(*args, **kwargs):
        nonlocal instance
        if instance is None:
            instance = cls(*args, **kwargs)
        return instance

    return getinstance


class Timer:
    """
    A timer class for managing timeouts and executing callback functions.

    This class allows managing a timeout period with an optional callback
    function to execute when the timeout elapses. It provides methods
    to start, stop, and check the timer's status, as well as measure
    elapsed or remaining time.

    Attributes:
        _timeout_t (asyncio.Task or None): The active asyncio task tracking the timer.
        args (tuple): Arguments passed to the callback function.
        start_time (float or None): Timestamp of when the timer was started.
        end_time (float or None): Timestamp of when the timer was stopped.
        cb (callable or None): Callback function to execute after the timeout.
        timout_s (float): The configured timeout duration, in seconds.
    """

    def __init__(self, timout_s, cb=None, args=(), start=True):
        self._timeout_t = None
        self.args = args
        self.start_time = None
        self.end_time = None
        self.cb = cb
        assert timout_s > 0, "Timeout must be a positive number of seconds."
        self.timout_s = timout_s
        if start:
            self.start()

    def start(self):
        if not self.is_act():
            self.start_time = time()
            self.end_time = None
            self._timeout_t = asyncio.create_task(self._timeout())

    def reset(self):
        "return to original state, is_act() == False, done() == False, time() == 0"
        self.start_time = None
        self.end_time = None
        if self._timeout_t:
            self._timeout_t.cancel()
            self._timeout_t = None

    def stop(self):
        self.end_time = time()
        if self._timeout_t:
            self._timeout_t.cancel()
            self._timeout_t = None

    def done(self):
        if self.start_time is None:
            return False
        if self.end_time is None:
            return False
        return not self.is_act()

    def is_act(self):
        if self.start_time is None:
            return False
        if self.end_time is None:
            return (time() - self.start_time) < self.timout_s
        return False

    def time(self) -> float:
        if self.is_act():
            return 0.0
        return self.end_time - self.start_time

    def time_left(self) -> float:
        if not self.is_act():
            return 0.0
        return max(0.0, self.timout_s - (time() - self.start_time))

    def progress(self, lim=1.0) -> float:
        if self.done():
            return 1.0

        if not self.is_act():
            return 0.0

        elapsed = time() - self.start_time
        return min(lim, max(0.0, elapsed / self.timout_s))

    async def _timeout(self):
        await asyncio.sleep(self.timout_s)
        self.end_time = time()
        if self.cb:
            launch(self.cb, self.args)

    def restart(self):
        """
        Restart the timer by resetting its state and starting it again.

        This ensures the timeout starts fresh without requiring a new Timer instance.
        """
        self.reset()
        self.start()
