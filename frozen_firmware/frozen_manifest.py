# include ESP32 base manifest
include("$(PORT_DIR)/boards/manifest.py")
# include crypto library
# include("$(PORT_DIR)/user-cmodules/ucrypto/modules/manifest.py")

# todo: check will these be needed at all
# package("gui", base_path="../libs/micropython-micro-gui/gui/fonts")
# package("gui.primitives", base_path="../libs/micropython-micro-gui/gui/primitives")
# package("gui.widgets", base_path="../libs/micropython-micro-gui/gui/widgets")
# package("gui.demos", base_path="../libs/micropython-micro-gui/gui/demos")

# our own modules
freeze("modules")
