# include ESP32 base manifest
include("$(PORT_DIR)/boards/manifest.py")

# our own modules
package("drivers", base_path="modules")
# Import gui/* folders one by one so that we can leave gui/demos out of the firmware
package("gui/core", base_path="modules")
package("gui/fonts", base_path="modules")
package("gui/primitives", base_path="modules")
package("gui/widgets", base_path="modules")
package("ota", base_path="modules")
package("primitives", base_path="modules")
module("bdg/widgets/hidden_active_widget.py", base_path="modules")
module("bdg/screens/hw_test.py", base_path="modules")
module("bdg/__init__.py", base_path="modules")
module("bdg/config.py", base_path="modules")
module("bdg/version.py", base_path="modules")
module("bdg/buttons.py", base_path="modules")
module("bdg/utils.py", base_path="modules")
module("bdg/bleds.py", base_path="modules")
module("bdg/screens/ota.py", base_path="modules")
module("hardware_setup.py", base_path="modules")
module("frozen_fs.py", base_path="modules")
module("main.py", base_path="modules_minimal_fw")
