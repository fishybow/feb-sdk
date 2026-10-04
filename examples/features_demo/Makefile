# Makefile for Flashiibo FEB Application: Features Demo
# Targets the Flashiibo Gen3 FEB runtime (Beta / Experimental).

PYTHON ?= python3
BUILD_TOOL = ../../tools/feb_build.py

APP_TITLE = Features Demo
APP_AUTHOR = Flashiibo
APP_VER = 1.0.0

TARGET = features_demo.feb

.PHONY: all clean install from_asm

all: $(TARGET)

$(TARGET): main.c $(BUILD_TOOL) ../../include/feb.h
	$(PYTHON) $(BUILD_TOOL) main.c -o $(TARGET) --title "$(APP_TITLE)" --author "$(APP_AUTHOR)" --ver "$(APP_VER)"

from_asm: main.asm $(BUILD_TOOL)
	$(PYTHON) $(BUILD_TOOL) main.asm -o $(TARGET) --title "$(APP_TITLE)" --author "$(APP_AUTHOR)" --ver "$(APP_VER)"

install: $(TARGET)
	@mkdir -p ../../build
	cp $(TARGET) ../../build/$(TARGET)
	@echo "[FEB] Copied $(TARGET) to ../../build/$(TARGET)"

clean:
	rm -f $(TARGET)
