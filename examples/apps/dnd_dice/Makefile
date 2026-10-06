# Makefile for Flashiibo FEB Application: D&D Dice
# Targets the Flashiibo Gen2 & Gen3 FEB runtime.

PYTHON ?= python3
BUILD_TOOL = ../../../tools/feb_build.py

APP_TITLE = D&D Dice
APP_AUTHOR = Flashiibo
APP_VER = 1.0.0

TARGET = dnd_dice.feb

.PHONY: all clean install

all: $(TARGET)

$(TARGET): main.c $(BUILD_TOOL) ../../../include/feb.h
	$(PYTHON) $(BUILD_TOOL) main.c -o $(TARGET) --title "$(APP_TITLE)" --author "$(APP_AUTHOR)" --ver "$(APP_VER)"

install: $(TARGET)
	@mkdir -p ../../../build
	@cp $(TARGET) ../../../build/

clean:
	rm -f $(TARGET)
