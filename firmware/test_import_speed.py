"""Quick import test for badge.main"""

import time
import os

# Prevent auto-start to measure import time only
os.environ["BADGE_NO_AUTOSTART"] = "1"

start = time.ticks_ms()
import badge.main

end = time.ticks_ms()

print(f"\n{'='*60}")
print(f"Import badge.main completed in: {time.ticks_diff(end, start)}ms")
print(f"{'='*60}")
print(f"\nBadge did not auto-start (BADGE_NO_AUTOSTART set)")
print(f"To start manually, call: badge.main.start_badge()")
