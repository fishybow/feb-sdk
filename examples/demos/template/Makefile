# Makefile for Flashiibo FEB Application: Template Demo
# Targets the Flashiibo Gen3 FEB runtime (Beta / Experimental).

PYTHON ?= python3
BUILD_TOOL = ../../../tools/feb_build.py

APP_TITLE = Template Demo
APP_AUTHOR = Flashiibo
APP_VER = 1.0.0

TARGET = template.feb

.PHONY: all clean install

all: $(TARGET)

$(TARGET): main.c $(BUILD_TOOL) ../../../include/feb.h
	$(PYTHON) $(BUILD_TOOL) main.c -o $(TARGET) --title "$(APP_TITLE)" --author "$(APP_AUTHOR)" --ver "$(APP_VER)"

# Alternatively build from assembly directly:
from_asm: main.asm $(BUILD_TOOL)
	$(PYTHON) $(BUILD_TOOL) main.asm -o $(TARGET) --title "$(APP_TITLE)" --author "$(APP_AUTHOR)" --ver "$(APP_VER)"

install: $(TARGET)
	@mkdir -p ../../../build
	cp $(TARGET) ../../../build/$(TARGET)
	@echo "[FEB] Copied $(TARGET) to ../../../build/$(TARGET)"

clean:
	rm -f $(TARGET)
