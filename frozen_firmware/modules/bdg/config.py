import re
from random import seed, choice

import machine
import ujson


# import frozen_fs mounts `frozen_fs` as `/readonly_fs`


def gen_nick(boadr_id):
    # Cyberpunk-themed Prefixes
    # fmt: off
    prefixes = ['Neuro', 'Silent', 'Neon', 'Cyber', 'Zero', 'Alpha', 'Evo', 'Cryo',
                'Neo', 'Ghost', 'Syn', 'Mecha', 'Hyper', 'Rogue', 'Meta', 'Pulse',
                'Nano', 'Dark', 'Shadow', 'Quantum', 'Techno', 'Void',]

    # Cyberpunk-themed Middles
    middles = [
        'Blade', 'Net', 'Cipher', 'Phantom', 'Hack', 'Code', 'R01', 'Ghost', 'Stream',
        'Runner', 'Hunter', 'Rogue', 'Echo', 'Core', 'Pulse', 'Byte', 'Ctrl', '_X',
        'Grid', 'xXx', 'Ninja', 'Bot', 'Void', 'Wave'
    ]

    # Cyberpunk-themed Suffixes
    suffixes = ['404', '001', '73', '42', '69', 'SYS', '99', '808', '1337', '101', 'XX',
                'D4RK', '665', '007', 'XOR', '1999', 'Z3R0', '010', 'X', '77', 'X1', '88'
    ]
    # fmt: on

    # Function to generate a cyberpunk-style nickname
    seed(int.from_bytes(boadr_id, "big"))
    prefix = choice(prefixes)
    middle = choice(middles)
    suffix = choice(suffixes)
    return f"{prefix}{middle}{suffix}"


def clean_user_nick(config):
    nick = config.get("espnow", {}).get("nick", "")
    if not nick or len(nick) < 5:
        nick = gen_nick(machine.unique_id())

    nick = nick.replace(" ", "_")[:15]
    return re.sub(r"[^0-9a-zA-Z<>\[\]\-!\*#]+", "", nick)


class Config:
    config = {}

    @staticmethod
    def load() -> dict:
        config = {}
        for path in ["/config.json", "/readonly_fs/config.json"]:
            try:
                with open(path) as f:
                    config = ujson.load(f)
                    print(f"Loaded config from {path}")
                    break
            except OSError:
                print(f"No config-file: {path}")

        Config.config = {
            "ota": {
                "host": config.get("ota", {}).get("host"),
                "wifi": {
                    "ssid": config.get("ota", {}).get("wifi", {}).get("ssid"),
                    "password": config.get("ota", {}).get("wifi", {}).get("password"),
                },
            },
            "espnow": {
                "ch": 1,
                "beacon": 20,
                "nick": clean_user_nick(config),
                "b_needed": 10,
            },
        }
        return Config.config
