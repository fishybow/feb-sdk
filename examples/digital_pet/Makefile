# Makefile for Flashiibo FEB Application: Digital Pet
# Targets the Flashiibo Gen3 FEB runtime (Beta / Experimental).

PYTHON ?= python3
BUILD_TOOL = ../../tools/feb_build.py

APP_TITLE = Digital Pet
APP_AUTHOR = Flashiibo
APP_VER = 1.0.0

TARGET = digital_pet.feb

.PHONY: all clean install

all: $(TARGET)

$(TARGET): main.c $(BUILD_TOOL) ../../include/feb.h
	$(PYTHON) $(BUILD_TOOL) main.c -o $(TARGET) --title "$(APP_TITLE)" --author "$(APP_AUTHOR)" --ver "$(APP_VER)" --require-back

install: $(TARGET)
	@mkdir -p ../../build
	cp $(TARGET) ../../build/$(TARGET)
	@echo "[FEB] Copied $(TARGET) to ../../build/$(TARGET)"

clean:
	rm -f $(TARGET) *.sav
