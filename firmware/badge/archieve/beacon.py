import random

import aioespnow
import network

from badge.msg import BeaconMsg
from badge.msg.connection import Beacon


def run():
    # A WLAN interface must be active to send()/recv()
    sta = network.WLAN(network.STA_IF)  # Or network.AP_IF
    sta.active(True)
    sta.disconnect()      # For ESP8266

    nick = "Anon" + str(random.randint(1000, 9999))
    beaconmsg = BeaconMsg(nick)

    e = aioespnow.AIOESPNow()
    e.active(True)

    beacon = Beacon(e,beaconmsg)

    # will block
    beacon.start()



run()
