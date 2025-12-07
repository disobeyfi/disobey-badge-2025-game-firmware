import asyncio
from time import ticks_ms, ticks_diff, time

import aioespnow
from collections import namedtuple, deque

from badge.msg import (
    OpenConn,
    send_message,
    ConTerm,
    PingMsg,
    AppMsg,
    BadgeMsg,
    BeaconMsg,
    BadgeAdr,
    BadgeAdrDict,
    AckMsg,
)

from bdg.utils import AProc
from primitives import Queue


OutQueMsg = namedtuple("OutQueMsg", ["msg", "mac", "id", "retry"])
OutQueAck = namedtuple("OutQueMsg", ["mac", "id"])


class Connection(object):
    """
    Connection is a bidirectional communication channel between two badges.

    Attributes:
        c_mac (bytes): MAC address of the recipient
        espnow: The ESP-NOW instance used for communication.
        active (bool): Status of whether the connection is active or not.
        last_msg (timestamp): Timestamp of the last message received.
        con_id: Unique identifier for the app that uses this connection. Like content-type
        in_q (Queue): Queue to store incoming messages.

    Methods:
        async connect(self, rcvr=False):
            Initiates a connection or responds to a connection request. Returns True if successful, False otherwise.

        async terminate(self):
            Terminates the connection by sending a termination message and setting the connection to inactive.

        async ping(self):
            Sends a ping message and waits for a reply.

        async recv_msg(self, msg: BadgeMsg):
            Handles the reception of messages internally and processes different types of messages. Called by NowListener.

        async send_app_msg(self, msg: BadgeMsg, sync=False):
            Sends an application message over the connection. Receiving end gets the same class as the sender sent.

        async send_msg_b(self, msg: bytes, sync=False):
            Sends a byte message over the connection.

        async send_wait_reply(self, msg: bytes, sync=False, timeout=5.0):
            Sends a message and waits for a reply within a timeout period. Raises TimeoutError if timeout exceeded.

        get_msg_aiter(self):
            Returns an asynchronous iterator to iterate over incoming messages.
    """

    # Connection is a bidirectional communication channel between two badges
    #
    def __init__(self, mac: bytes, con_id, espnow):
        self._sender_t: asyncio.Task = None
        self.espnow: espnow = espnow
        self.c_mac: bytes = mac
        # self.call_chnl = 1
        # self.talk_chnl = 3
        self.active = False
        self.closed = False
        self.last_msg = time()
        self.con_id = con_id
        self.in_q = Queue(maxsize=5)
        self.out_q = Queue(maxsize=3)

        NowListener.register_con(self)

    def __del__(self):
        print("conn closed")

    async def terminate(self, send_out=True, reply_to_id=None):
        # send connection terminated to local listeners
        ct = ConTerm(con_id=self.con_id)
        self.in_q.put_nowait(ct)
        if send_out:
            if reply_to_id:
                ct.__id = reply_to_id
            self.send_msg(ct)
            NowListener.unregister_con(self)
        self.active = False
        self.closed = True

    async def connect(self, rcvr=False):
        try:
            oc = OpenConn(con_id=self.con_id)
            if rcvr:
                self.send_msg(oc)
                self.active = True
                return True
            else:
                reply = await self.send_wait_reply(oc, timeout=20)
            if (
                not isinstance(reply, OpenConn)
                or reply.accept is False
                or reply.con_id != self.con_id
            ):
                # print(f'not accepted reply: {type(reply)} {reply=}')
                return await self.terminate(False)
            # connection made
            self.active = True
            return True
        except asyncio.TimeoutError:
            await self.terminate()
            return False
        except Exception as err:
            print(f"conn err {err}")
            return False

    async def ping(self):
        print(f"ping: ")
        mark = ticks_ms()
        self.send_app_msg(PingMsg(mark, False), sync=False)
        reply = await asyncio.wait_for(self.in_q.get(), 5)
        print(f"ping reply: {ticks_diff(ticks_ms(), mark)}ms {reply=}")
        return reply

    async def _sender(self):
        # sender task to decouple sync calls to async.
        # micro gui callbacks are sync so this is needed
        # if in async context self.send_app_msg can be called directly
        if not self.active:
            print(f"cannot send con {self.con_id} terminated")
            return  # cannot send on closed connection
        while self.out_q.qsize() > 0 or self.active:
            msg = await asyncio.wait_for(self.out_q.get(), 5000)
            print(f"_s:  {msg}")
            self.send_app_msg(msg, sync=False)

    async def recv_msg(self, msg: BadgeMsg):
        # internal recv_msg that is called from NowListener
        print(f"recv-msg {msg=}")
        if isinstance(msg, ConTerm):
            if self.active:
                await self.terminate(send_out=False)
                print(f"connection {self.con_id} terminated")
        elif isinstance(msg, OpenConn):
            if not self.active:
                self.in_q.put_nowait(msg)
                self.active = True
                print(f"connection {self.con_id} activated")
            # self.send_msg(AckMsg(id=msg.id), retry=0)
        elif isinstance(msg, PingMsg):
            if msg.reply:
                self.in_q.put_nowait(msg)
                return
            msg.reply = True
            self.send_app_msg(msg)
        elif not self.active:
            print("connection not active")
        else:
            # this can block, should check quefull and return something to client B
            self.in_q.put_nowait(msg)

    def send_app_msg(self, msg: BadgeMsg, sync=False):
        amsg = AppMsg(con_id=self.con_id, content=msg)
        if self.closed:
            print(f"cannot send {self.con_id=} is terminated")
            return  # cannot send on closed connection
        NowListener.send_msg(amsg, self.c_mac, sync=sync)

    def send_msg(self, msg: BadgeMsg, sync=False, retry=3):
        if self.closed:
            print(f"cannot send {self.con_id=} is terminated")
            return  # cannot send on closed connection # TODO :raise
        NowListener.send_msg(msg, self.c_mac, sync=sync, retry=retry)

    async def send_wait_reply(self, msg: BadgeMsg, sync=False, timeout=5.0):
        # raises TimeoutError if timeout exceeded
        self.send_msg(msg, sync=sync)
        return await asyncio.wait_for(self.in_q.get(), timeout)

    def get_msg_aiter(self):
        class Aiter:
            def __init__(self, conn: Connection):
                self.conn = conn

            def __aiter__(self):  # See note below
                return self

            async def __anext__(self):
                msg: AppMsg = await self.conn.in_q.get()
                print(f"__anext__ ")
                if isinstance(msg, ConTerm):
                    raise StopAsyncIteration
                self.conn.last_msg = time()
                return msg

        return Aiter(self)


async def def_con_cb(con: Connection, req=False):
    """
    Callback for handling incoming connections.

    Args:
        con (Connection): The incoming connection instance.
        :param req: Incoming conn or self made request
    """
    if not req:
        print(f"Incoming connection {con.con_id}")
    else:
        print(f"Connect request {con.con_id}")
    return True


def wait_index(msg):
    return msg.mac + bytes([msg.id])


def wait_index_mac(mac, msg_id):
    return mac + bytes([msg_id])


class NowListener(object):
    """
    The NowListener class listens and processes incoming ESP-NOW messages. It manages connections,
    handles incoming messages, and maintains an update mechanism for the seen devices.

    This class is designed to function as a singleton to ensure that only one instance handles
    the ESP-NOW communication. It provides mechanisms for registering, unregistering, and dispatching
    messages to connections.

    Attributes:
        __instance (NowListener): Singleton instance of the class.
        connections (dict): Dictionary holding active connections indexed by connection ID.
        last_seen (BadgeAdrDict): Dict like object with eviction after max_size reached
        update_event (asyncio.Event): Asyncio event to notify updates.
        conn_request (asyncio.Event): Asyncio event for new connection requests.
        __espnow (aioespnow.AIOESPNow): AIOESPNow instance to handle ESP-NOW communication.

    Methods:
        incoming_con_cb(con): Callback for handling incoming connections.
        task(): Main task to listen and process incoming ESP-NOW messages.
        get_updates(): Returns a generator that yields the last seen updates.
        register_con(connection): Registers a new connection and adds the respective peer in ESP-NOW.
        unregister_con(connection): Unregisters a connection and removes it from the active connections.
        start(espnow): Starts the NowListener instance if not already started.
        stop(): Stops the NowListener instance if it is running.
        dispatch_app_msg(app_msg): Dispatches an application message to the corresponding connection.
        dispatch_msg(msg, con_id): Dispatches a message to the corresponding connection based on connection ID.
    """

    __task = None
    __instance = None
    _sender_t = None
    connections = {}
    delivered = deque([], 5)
    last_seen = BadgeAdrDict(max_size=20)

    update_event = asyncio.Event()
    conn_request = asyncio.Event()
    out_q = Queue(maxsize=5)

    __espnow: aioespnow.AIOESPNow = None
    con_cb = def_con_cb

    def __init__(self, e, con_cb=None):
        if not NowListener.__espnow:
            NowListener.__espnow = e
        if con_cb:
            NowListener.con_cb = con_cb

    def ack_msg(self, mac, msg_id):
        self.out_q.put_nowait(OutQueAck(mac, msg_id))
        # start sender task to eat the out_q
        if self._sender_t is None or self._sender_t.done():
            self._sender_t = asyncio.create_task(self._sender())

    async def task(self):
        """
        Main task to listen and process incoming ESP-NOW messages.
        Handles different types of messages (BeaconMsg, OpenConn, ConTerm, AppMsg) and updates connections.
        """
        print("NowListener active")
        no_ack = 0
        async for mac, msg in self.__espnow:
            if mac is None:
                continue

            rssi = self.__espnow.peers_table[mac][0]
            if rssi < -70:
                continue

            incm_msg = BadgeMsg.desrlz(msg)
            print(f">>>{mac}:{incm_msg if incm_msg else msg}")

            if isinstance(incm_msg, BeaconMsg):
                NowListener.last_seen[mac] = BadgeAdr(mac, incm_msg.nick, rssi, time())
                self.update_event.set()  # trigger updates function
            elif isinstance(incm_msg, AckMsg):
                NowListener.last_seen.update_last_seen(mac, time())
                # mark for retry buffer that msg is acked
                self.ack_msg(mac, incm_msg.id)

            elif isinstance(incm_msg, OpenConn):
                NowListener.last_seen.update_last_seen(mac, time())
                if await self.dispatch_msg(incm_msg, incm_msg.con_id, mac):
                    # we found an active connection for the message, this was a reply
                    self.ack_msg(mac, incm_msg.id)
                    # ack our own OpenConn msg
                    continue

                # Add new incoming connection, ack the incoming OpenConn
                await send_message(
                    self.__espnow, mac, AckMsg(id=incm_msg.id).srlz(), sync=False
                )

                # proto connection, not yet capable of receiving other messages
                conn = Connection(mac, incm_msg.con_id, self.__espnow)
                conn.active = True

                try:
                    # ask user process can we accept connection
                    (await NowListener.con_cb(conn)) or 1 / 0
                except (asyncio.TimeoutError, ZeroDivisionError):
                    # connection was not opened in time, or it returned false
                    NowListener.unregister_con(conn)
                    await asyncio.sleep(0.1)  # Allow now esp stack to run
                    await conn.terminate()
                    continue

                # connection accepted, register to allow subsequent messages
                NowListener.register_con(conn)
                await asyncio.sleep(0.1)  # Allow now esp stack to run
                # Opening connection by replying OpenConn back with same msg id
                oc = OpenConn(incm_msg.con_id, accept=True)
                oc.__id = incm_msg.id
                NowListener.send_msg(oc, mac)
                # await send_message(self.__espnow, mac, msg, sync=False)

            elif isinstance(incm_msg, ConTerm):
                self.ack_msg(mac, incm_msg.id)
                NowListener.last_seen.update_last_seen(mac, time())

                if incm_msg.con_id in self.connections:
                    print(f"con term for {incm_msg=}")
                    conn = self.connections[incm_msg.con_id]
                    await conn.terminate(send_out=True, reply_to_id=incm_msg.id)
                    NowListener.unregister_con(conn)
                else:
                    await send_message(
                        self.__espnow, mac, AckMsg(id=incm_msg.id).srlz(), sync=False
                    )

            elif isinstance(incm_msg, AppMsg):
                NowListener.last_seen.update_last_seen(mac, time())
                await send_message(
                    self.__espnow, mac, AckMsg(id=incm_msg.id).srlz(), sync=False
                )

                if not await self.dispatch_app_msg(incm_msg, mac):
                    print(f"No receiver for RCV:{mac}->{incm_msg=}")

            else:
                tmp = ":".join(f"{byte:02x}" for byte in mac)
                print(f"{tmp} [{rssi}dBm] {msg} :")
            await asyncio.sleep(
                0.1
            )  # Do not touch, MSG stack crashes when running without

    @classmethod
    def updates(cls, filter_mac=None):
        return cls.__instance.get_updates(filter_mac=filter_mac)

    def get_updates(self, filter_mac=None):
        """
        `get_updates` returns a generator that yields the latest BadgeAddr.

        Returns:
            generator: A generator that yields the last seen updates.
            filter_mac: bytes(6) mac return only updates to this mac
        """

        class Aiter:
            def __init__(self, scanner):
                self.scanner = scanner

            def __aiter__(self):
                return self

            async def __anext__(self):
                while True:
                    await self.scanner.update_event.wait()
                    self.scanner.update_event.clear()
                    latest = self.scanner.last_seen.latest()
                    if filter_mac is None or filter_mac == latest.mac:
                        return latest

        return Aiter(self)

    async def _sender(self):
        # temporary task to send messages for retry times or until ack arrives
        timeout_ms = 500
        waiting_ack = {}
        start = ticks_ms()
        while self.out_q.qsize() > 0 or waiting_ack:
            try:
                out_q_t: OutQueMsg | OutQueAck = await asyncio.wait_for(
                    self.out_q.get(), timeout_ms / 1000
                )
                if type(out_q_t) == OutQueMsg:
                    waiting_ack[wait_index(out_q_t)] = out_q_t
                    await send_message(
                        self.__espnow, out_q_t.mac, out_q_t.msg, sync=False
                    )
                elif type(out_q_t) == OutQueAck:
                    w_index = wait_index(out_q_t)
                    if w_index in waiting_ack:
                        print(f"ack mach {out_q_t=}")
                        del waiting_ack[w_index]

                if ticks_diff(ticks_ms(), start) > timeout_ms:
                    raise asyncio.TimeoutError

            except asyncio.TimeoutError:
                ack_items = waiting_ack.items()
                for k, out_que_msg in ack_items:
                    if out_que_msg.retry <= 0:
                        print(f"retry timeout {k=} {out_que_msg=}")
                        del waiting_ack[k]
                        continue

                    print(f"<<{'r'*out_que_msg.retry}{out_que_msg.msg} {out_que_msg=}")
                    await send_message(
                        self.__espnow, out_que_msg.mac, out_que_msg.msg, sync=False
                    )
                    waiting_ack[k] = OutQueMsg(
                        out_que_msg.msg,
                        out_que_msg.mac,
                        out_que_msg.id,
                        out_que_msg.retry - 1,
                    )

                start = ticks_ms()

        print("sender done")

    @classmethod
    def send_msg(cls, msg: BadgeMsg, mac, sync=False, retry=3):
        out_q = cls.__instance.out_q
        out_q.put_nowait(OutQueMsg(msg.srlz(), mac, msg.id, retry))

        # start sender task
        if cls.__instance._sender_t is None or cls.__instance._sender_t.done():
            cls.__instance._sender_t = asyncio.create_task(cls.__instance._sender())

    @classmethod
    def register_con(cls, connection: "Connection"):
        """
        Registers a new connection and adds the respective peer in ESP-NOW.

        Args:
            connection (Connection): The connection instance to register.
        """
        print(f"register: {connection.con_id}")
        cls.connections[connection.con_id] = connection
        try:
            cls.__espnow.add_peer(connection.c_mac)
        except Exception:
            pass

    @classmethod
    def unregister_con(cls, connection: "Connection"):
        """
        Unregisters a connection and removes it from the active connections.

        Args:
            connection (Connection): The connection instance to unregister.
        """
        if connection.con_id in cls.connections:
            print(f"unregister: {connection.con_id}")
            del cls.connections[connection.con_id]

    @classmethod
    def start(cls, espnow):
        """
        Starts the NowListener instance if not already started.

        Args:
            espnow (aioespnow.AIOESPNow): ESP-NOW instance to handle communication.

        Returns:
            asyncio.Task: The asyncio task running the main task.
        """
        if not cls.__instance:
            cls.__instance = cls(espnow)
            cls.__task = asyncio.create_task(cls.__instance.task())
            return cls.__task

    @classmethod
    def stop(cls):
        """
        Stops the NowListener instance if it is running.
        """
        if cls.__task:
            cls.__task.cancel()
            cls.__task = None

    async def dispatch_app_msg(self, app_msg: AppMsg, s_mac):
        """
        Dispatches an application message to the corresponding connection.

        Args:
            app_msg (AppMsg): The application message.

        Returns:
            bool: True if the message was dispatched, False otherwise.
        """
        if app_msg.con_id in self.connections:
            if self.connections[app_msg.con_id].c_mac != s_mac:
                print(f"con_id mismatch {app_msg.con_id=} {s_mac=}")
                # TODO: send ConTerm for mismached
                return False
            # Pass only the inner content to app
            # filter out retries, don't deliver message with same id
            w_index = wait_index_mac(s_mac, msg_id=app_msg.id)
            if w_index not in NowListener.delivered:
                await self.connections[app_msg.con_id].recv_msg(app_msg.content)
                NowListener.delivered.append(w_index)
                return True
            else:
                print(f"Filtered out {w_index=} {app_msg=}")

        return False

    async def dispatch_msg(self, msg: BadgeMsg, con_id, s_mac):
        """
        Dispatches a message to the corresponding connection based on connection ID.

        Args:
            msg (BadgeMsg): The message to dispatch.
            con_id: The connection ID.

        Returns:
            bool: True if the message was dispatched, False otherwise.
        """
        if con_id in self.connections:
            if self.connections[con_id].c_mac != s_mac:
                print(f"con_id mismatch {con_id=} {s_mac=}")
                # TODO: send ConTerm for mismached
                return False

            # filter out retries, don't deliver message with same id
            w_index = wait_index_mac(s_mac, msg_id=msg.id)
            if w_index not in NowListener.delivered:
                await self.connections[con_id].recv_msg(msg)
                NowListener.delivered.append(w_index)

            # despite was msg retry or not send ack
            await send_message(
                self.__espnow, s_mac, AckMsg(id=msg.id).srlz(), sync=False
            )
            return True
        return False  # Connection was not found

    @classmethod
    async def conn_req(cls, mac, app_id):
        # Send connection request for app_id to other badge
        # and if then conn is accepted open same app in current badge
        c = Connection(mac, app_id, NowListener.__espnow)
        if await c.connect():  # send connection request
            # change app if request accepted
            await cls.con_cb(c, req=True)
            return True

        return False


class Beacon(AProc):
    # >>> Beacon.setup(espnow, id: BeaconMsg)
    # will setup the Beacon class to use the given espnow instance,
    # Beacon.start(task=True) will return a asyncio.task ans start running Beacon
    # Beacon.stop() will cancel the running task
    # Beacon.suspend(True|False) will suspend/resume the Beacon task # why not to use stop start?
    __espnow: aioespnow.AIOESPNow = None
    __id: BeaconMsg = None
    peer = None
    _susp = asyncio.Event()
    timeout = 5
    _task = None

    @classmethod
    def suspend(cls, value: bool):
        cls._susp.clear() if value else cls._susp.set()

    @classmethod
    async def task(cls, *args, **kwargs):
        try:
            while not cls.stop_event.is_set():
                msg = BeaconMsg(nick=cls.__id.nick).srlz()
                await send_message(cls.__espnow, cls.peer, msg)
                await asyncio.sleep(cls.timeout)
                if not cls._susp.is_set():
                    print("Beacon suspended...")
                    await cls._susp.wait()
                    print("...Beacon resumed")
        except Exception as e:
            print(f"Beacon exeption {e}")

    @classmethod
    def setup(cls, espnow, id: BeaconMsg, peer=b"\xbb\xbb\xbb\xbb\xbb\xbb", timeout=5):
        Beacon.__id = id
        Beacon.__espnow = espnow
        Beacon.timeout = timeout
        Beacon._susp.set()
        Beacon.peer = peer
        try:
            Beacon.__espnow.add_peer(peer)
        except OSError as err:
            if len(err.args) < 2:
                raise err
            if err.args[1] == "ESP_ERR_ESPNOW_EXIST":
                print("Addr exist")
