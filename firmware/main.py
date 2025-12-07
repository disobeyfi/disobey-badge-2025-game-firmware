import gc
import sys  # Fix
def reload(mod):
  mod_name = mod.__name__
  del sys.modules[mod_name]
  gc.collect()
  return __import__(mod_name)

#print("autostart badge gui test")
#import tests.badge_gui

#import badge.scanner.test
#import badge.main