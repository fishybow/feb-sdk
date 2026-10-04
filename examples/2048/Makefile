# Makefile for Flashiibo FEB Application: 2048
# Targets the Flashiibo Gen3 FEB runtime (Beta / Experimental).

PYTHON ?= python3
BUILD_TOOL = ../../tools/feb_build.py

APP_TITLE = 2048
APP_AUTHOR = Flashiibo
APP_VER = 1.0.0
APP_ICON ?= icon.txt

TARGET = 2048.feb

.PHONY: all clean install

all: $(TARGET)

$(TARGET): main.c $(BUILD_TOOL) ../../include/feb.h $(APP_ICON)
	$(PYTHON) $(BUILD_TOOL) main.c -o $(TARGET) --title "$(APP_TITLE)" --author "$(APP_AUTHOR)" --ver "$(APP_VER)" --icon $(APP_ICON)

install: $(TARGET)
	@mkdir -p ../../build
	cp $(TARGET) ../../build/$(TARGET)
	@echo "[FEB] Copied $(TARGET) to ../../build/$(TARGET)"

clean:
	rm -f $(TARGET)
