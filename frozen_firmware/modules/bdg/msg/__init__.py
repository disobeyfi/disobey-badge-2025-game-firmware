import asyncio

import gc
import random

from time import time

import umsgpack


# Low level messages that handle connection link
class BadgeMsg(object):
    __message_id = random.randint(0,255)

    # store all known message types trough .register decorator
    __msg_type_reg = {}
    __core_types = ()

    @property
    def id(self):
        return  self.__id % 255

    def __init__(self):
        if type(self) in BadgeMsg.__core_types:
            BadgeMsg.__message_id += 1
            self.__id = BadgeMsg.__message_id
        self.msg_type: str = type(self).__name__

    def to_dict(self):
        d = {"_id": self.id} if type(self) in BadgeMsg.__core_types else dict()
        for k, v in self.__dict__.items():
            if k.startswith("__") or callable(v):
                continue
            if isinstance(v, BadgeMsg):
                d.update({k: v.to_dict()})
            else:
                d.update({k: v})

        return d

    def __str__(self):
        return str(self.to_dict())

    def srlz(self):
        return umsgpack.dumps(self.to_dict())

    @classmethod
    def register(cls, subclass):
        def decorator(subclz):
            # print(f"{cls=} ad {subclz=}")
            cls.__msg_type_reg[subclz.__name__] = subclz
            cls.__registered_messages = cls.__msg_type_reg.keys()
            cls.__core_types = tuple(cls.__msg_type_reg.values())
            return subclz

        return decorator(subclass)

    @staticmethod
    def desrlz(dump) -> "BadgeMsg":
        try:
            d = umsgpack.loads(dump)
            ctype, mid, rest = d["msg_type"],d["_id"], {k: v for k, v in d.items() if k not in ["msg_type", "_id"]}
            #print(f"{ctype=} {mid=} {rest=}")
            msg = BadgeMsg.__msg_type_reg.get(ctype)(**rest)
            msg.__id = mid
            return msg
        except Exception as e:
            print(f"Error deserializing msg: {e}")
            return None


# send beacon messages to other


# Low level message that handle connection link
@BadgeMsg.register
class BeaconMsg(BadgeMsg):
    def __init__(self, nick: str):
        super().__init__()
        self.nick: str = nick


# Low level message that handle connection link
@BadgeMsg.register
class AckMsg(BadgeMsg):
    def __init__(self, id: int=None):
        # super().__init__() no super init as this would advance msg_id
        self.msg_type: str = type(self).__name__
        self.__id = id


# ask for connection


# Low level message that handle connection link
@BadgeMsg.register
class OpenConn(BadgeMsg):
    def __init__(self, con_id: int, accept: bool = True):
        super().__init__()
        self.con_id: int = con_id  # if True  request, if False response
        self.accept: bool = accept  # when replying returns state will other connect


# Low level message that handle connection link
@BadgeMsg.register
class ConTerm(BadgeMsg):
    def __init__(self, con_id: int):
        super().__init__()
        self.con_id: int = con_id


# Application to application message header AppMsg contains a msg instance
# and application ID Application is talking to device B to same App id,
# a bit like content type.

# Peer to peer communication happends with
# Connection class passing msg objects from Badge A, Appid x, <-> Badge B, Appid x


@BadgeMsg.register
class AppMsg(BadgeMsg):

    __msg_type_reg = {}

    def __init__(self, content: object, con_id: int = 0):
        super().__init__()
        self.con_id = con_id
        if isinstance(content, BadgeMsg):
            self.content = content
        elif isinstance(content, dict):
            # Improve serialization by filtering out
            # fields that doesn't exist int msg_type
            # Todo: handle serialization errors with single Error type
            ctype, rest = content["msg_type"], {
                k: v for k, v in content.items() if k != "msg_type"
            }
            self.content: BadgeMsg = self.__msg_type_reg.get(ctype)(**rest)


# most basic App msg that is handled by the connection stack
@AppMsg.register
class PingMsg(BadgeMsg):
    def __init__(self, mark: float, reply):
        super().__init__()
        self.mark: float = mark
        self.reply: bool = reply


# Now messages does not have to be defined in this file, it is enough to import
# BadgeMsg and decorate all messages with @BadgeMsg.register.


# Example of AppMsg
@AppMsg.register
class RPSMsg(BadgeMsg):
    def __init__(self, choice: int):
        super().__init__()
        self.choice: int = choice


@AppMsg.register
class VictoryMsg(BadgeMsg):
    def __init__(self, your: int, mine: int, tie: bool = False, me_win: bool = False):
        super().__init__()
        self.your: int = your
        self.mine: int = mine
        self.tie: bool = tie
        self.me_win: bool = me_win


async def send_message(espnow, mac: bytes, msg: bytes, sync=False, retries=3):
    for _ in range(retries):  # tree retries on sending
        try:
            await espnow.asend(mac, msg, sync=sync)
            print(f"<<<{mac}:{msg}")
            return
        except OSError as err:
            print(f"send retry: {err}")
            if len(err.args) < 2:
                raise err
            if err.args[1] == "ESP_ERR_ESPNOW_NOT_INIT":
                espnow.active(True)
                gc.collect()
            elif err.args[1] == "ESP_ERR_ESPNOW_NOT_FOUND":
                espnow.add_peer(mac)
                gc.collect()
            elif err.args[1] == "ESP_ERR_ESPNOW_IF":
                import network

                network.WLAN(network.STA_IF).active(True)
                gc.collect()
            else:
                raise err
        except Exception as e:
            print(f"send message Exeption {e}")
            raise e

    print("msg-send out")


class BadgeAdr(object):
    # BadgeAdr is result in receivers end of receiving BeaconMsg
    def __init__(self, mac: bytes, nick: str, rssi: int, last_seen: float):
        self.mac: bytes = mac
        self.nick: bytes = nick
        self.rssi: int = rssi
        self.last_seen: float = last_seen

    def __hash__(self):
        return hash(self.mac)

    def __repr__(self):
        return f"0x{self.mac.hex()}:{self.nick}({self.rssi})"

    def __eq__(self, other):
        if isinstance(other, BadgeAdr):
            return self.mac == other.mac
        return False


null_badge_adr = BadgeAdr(b"\x00\x00\x00\x00\x00\x00", b"[none]", -1, 0)


class BadgeAdrDict:
    # Dict like class for having fixed number of BadgeAdr instances with mac as key
    def __init__(self, max_size):
        self.max_size = max_size
        self.store = {}
        self.last_index = None

    def _evict_if_necessary(self):
        if len(self.store) >= self.max_size:
            # Find the key with the oldest last_seen value
            oldest_key = min(self.store, key=lambda k: self.store[k].last_seen)
            # Remove that key from the store
            del self.store[oldest_key]

    def __setitem__(self, key, value):
        if not isinstance(value, BadgeAdr):
            raise ValueError("Value must be an instance of BadgeAdr.")

        if key != value.mac:
            raise ValueError("Key must match the 'mac' attribute of the value.")

        self._evict_if_necessary()
        self.store[key] = value
        self.store[key].last_seen = time()
        self.last_index = key

    def __getitem__(self, key):
        if key in self.store:
            return self.store[key]
        raise KeyError(f"Key {key} not found in store.")

    def __delitem__(self, key):
        if key in self.store:
            del self.store[key]
        else:
            raise KeyError(f"Key {key} not found in store.")

    def __contains__(self, key):
        return key in self.store

    def __len__(self):
        return len(self.store)

    def __iter__(self):
        # for casting a simple dict(badge_addr_dict)
        for key in self.store:
            yield key, self.store[key]

    def items(self):
        return self.store.items()

    def values(self):
        return self.store.values()

    def keys(self):
        return self.store.keys()

    def latest(self):
        return self.store[self.last_index]

    def update_last_seen(self, key, last_seen):
        if key in self.store:
            self.store[key].last_seen = last_seen
            self.last_index = key
            return True
        return False



def test():
    a = AppMsg(content=RPSMsg(choice=1), con_id=2)
    print(f"{a.to_dict()=}")
    print(f"{a.srlz()=}")
    aa: AppMsg = BadgeMsg.desrlz(a.srlz())
    print(f"{aa.to_dict()=}")

    print(f"{aa.content.choice=}")
    print(f"{str(aa)=}")

    b = AppMsg(
        content=VictoryMsg(your=aa.content.choice, mine=2, tie=False, me_win=True)
    )
    print(f"{b.to_dict()=}")
    print(f"{b.srlz()=}")
    bb: VictoryMsg = BadgeMsg.desrlz(b.srlz())
    print(f"{bb.to_dict()=}")
    print(f"{AppMsg.__registered_messages =} \n" f"{BadgeMsg.__registered_messages=} ")
