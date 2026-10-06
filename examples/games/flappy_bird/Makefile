# Makefile for Flashiibo FEB Application: Flappy Bird
# Targets the Flashiibo Gen3 FEB runtime (Beta / Experimental).

PYTHON ?= python3
BUILD_TOOL = ../../../tools/feb_build.py

APP_TITLE = Flappy Bird
APP_AUTHOR = Flashiibo
APP_VER = 1.0.0

TARGET = flappy_bird.feb

.PHONY: all clean install

all: $(TARGET)

$(TARGET): main.c $(BUILD_TOOL) ../../../include/feb.h
	$(PYTHON) $(BUILD_TOOL) main.c -o $(TARGET) --title "$(APP_TITLE)" --author "$(APP_AUTHOR)" --ver "$(APP_VER)"

install: $(TARGET)
	@mkdir -p ../../../build/games
	cp $(TARGET) ../../../build/games/$(TARGET)
	@echo "[FEB] Copied $(TARGET) to ../../../build/games/$(TARGET)"
clean:
	rm -f $(TARGET)
