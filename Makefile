.PHONY: all submodules micro_init build_firmware clean_frozen_py rebuild_mpy_cross
SHELL := /bin/bash

# Detect Python command (prefer uv venv, then python3, then python)
ifneq (,$(wildcard .venv/bin/python))
    PYTHON := .venv/bin/python
else
    PYTHON := $(shell command -v python3 2>/dev/null || command -v python 2>/dev/null)
endif
ifeq ($(PYTHON),)
$(error Python is not installed. Please install Python 3)
endif

# Default value for FW_TYPE
FW_TYPE ?= normal
# Check that FW_TYPE is either normal or minimal
ifneq ($(FW_TYPE),normal)
ifneq ($(FW_TYPE),minimal)
$(error FW_TYPE must be either 'normal' or 'minimal')
endif
endif

all: build_firmware

build_firmware: dist/firmware_$(FW_TYPE).bin

build_and_deploy: build_firmware deploy

# init own submopdules before micropython init
submodules:
	git submodule update --init
	pushd micropython/ports/esp32 && \
	git submodule update --init 'user-cmodules/ucrypto' &&\
	popd
	pushd micropython && \
	git submodule update --init --depth 1 && \
	popd


set_environ.sh:
	@cp set_environ.example set_environ.sh

micro_init: micro_init.stamp
	@echo "micro_init has been completed!"

micro_init.stamp: submodules set_environ.sh
	FW_TYPE=$(FW_TYPE) source ./set_environ.sh && \
	pushd micropython && \
	ci_esp32_idf_setup && \
	ci_esp32_build_common && \
	popd
	touch micro_init.stamp

dist/firmware_$(FW_TYPE).bin: micro_init
	@echo "Building firmware type: $(FW_TYPE)"
	git rev-parse --short HEAD > frozen_fs/BUILD
	PYTHONPATH=libs/freezefs $(PYTHON) -m freezefs ./frozen_fs frozen_firmware/modules/frozen_fs.py --target "/readonly_fs"  --compress
	FW_TYPE=$(FW_TYPE) source ./set_environ.sh && \
	pushd micropython && \
	ci_esp32_idf_setup && \
	ci_esp32_build_common && \
	make ${MAKEOPTS} -C ports/esp32 && \
	popd && \
	cp micropython/ports/esp32/build-$$BOARD-$$BOARD_VARIANT/firmware.bin dist/firmware_$(FW_TYPE).bin

deploy: 
	@if [ -z "$$PORT" ]; then \
		esptool --chip esp32s3 -b 460800 --before=default-reset --after=hard-reset write-flash --flash-size detect 0x0 dist/firmware_$(FW_TYPE).bin; \
	else \
		esptool --chip esp32s3 -p $$PORT -b 460800 --before=default-reset --after=hard-reset write-flash --flash-size detect 0x0 dist/firmware_$(FW_TYPE).bin; \
	fi

repl_with_firmware_dir:
	@echo "Starting REPL with firmware directory mounted..."
	@if [ -z "$$PORT" ]; then \
		$(PYTHON) micropython/tools/mpremote/mpremote.py baud 460800 u0 mount -l firmware; \
	else \
		$(PYTHON) micropython/tools/mpremote/mpremote.py baud 460800 connect $$PORT mount -l firmware; \
	fi

         
clean_frozen_py:
	rm -rf ports/esp32/build-ESP32_GENERIC_S3-DEVKITW2/frozen_mpy

rebuild_mpy_cross:
	pushd micropython/mpy-cross && \
	make clean && \
	make && \
	popd

clean: 
	rm -fr micropython/ports/esp32/build-ESP32_GENERIC_S3-DEVKITW2