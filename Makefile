# Flashiibo FEB (Flashiibo Executable Binary) Root Makefile
# Targets the Flashiibo Gen3 FEB runtime (Beta & Experimental).

GAMES := 2048 flappy_bird sokoban digital_pet mastermind snake falling_blocks
DEMOS := template button_demo draw_demo
APPS := stopwatch flashlight sos dice dnd_dice
EXAMPLES := $(GAMES) $(DEMOS) $(APPS)
BUILD_DIR := build
DIST_DIR := dist
PACKAGE_ZIP := all-flashiibo-febs.zip
VERSION ?= $(shell date +'%y.%m.%d')

.DEFAULT_GOAL := help
.PHONY: help all clean test dist publish sim run $(EXAMPLES)

help:
	@echo "Flashiibo FEB SDK Build System"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Available targets:"
	@echo "  help           Display this help message (default)"
	@echo "  all            Build all applications (games, demos, apps) into $(BUILD_DIR)/"
	@echo "  sim            Run FEB Simulator (e.g. make sim APP=stopwatch, make sim GAME=sokoban)"
	@echo "  dist           Package public release games/apps and checksums into $(DIST_DIR)/"
	@echo "  test           Run automated verification test suite"
	@echo "  clean          Clean build artifacts and build directory"
	@echo "  publish        Tag commit with version ($(VERSION)) and push develop to main"
	@echo ""
	@echo "Games (in examples/games/):"
	@echo "  2048           Build 2048 puzzle game"
	@echo "  mastermind     Build Master Mind code-breaking game"
	@echo "  snake          Build Snake arcade game"
	@echo "  falling_blocks Build Falling Blocks portrait arcade game"
	@echo "  flappy_bird    Build Flappy Bird sprite demo application"
	@echo "  sokoban        Build 10-level Sokoban puzzle game"
	@echo "  digital_pet    Build advanced virtual pet simulation with persistence"
	@echo ""
	@echo "Developer Examples & Demos (in examples/demos/):"
	@echo "  template       Build starter template application"
	@echo "  button_demo    Build 4-button hardware demo application"
	@echo "  draw_demo      Build vector geometry & shapes demo application"
	@echo ""
	@echo "Utility Apps (in examples/apps/):"
	@echo "  stopwatch      Build precision digital stopwatch"
	@echo "  flashlight     Build screen flashlight utility"
	@echo "  sos            Build Morse code SOS emergency beacon"
	@echo "  dice           Build standard 6-sided dice roller"
	@echo "  dnd_dice       Build D&D polyhedral dice roller"
	@echo ""

all: $(EXAMPLES)
	@echo ""
	@echo "=== All FEB Applications Built Successfully ==="
	@echo "--- Games: ---" && ls -la $(BUILD_DIR)/games/
	@echo "--- Demos: ---" && ls -la $(BUILD_DIR)/demos/
	@echo "--- Apps: ---" && ls -la $(BUILD_DIR)/apps/

$(GAMES):
	@mkdir -p $(BUILD_DIR)/games
	@echo "--- Building game $@ ---"
	@$(MAKE) -C examples/games/$@
	@cp examples/games/$@/$@.feb $(BUILD_DIR)/games/
	@echo "Installed $(BUILD_DIR)/games/$@.feb"

$(DEMOS):
	@mkdir -p $(BUILD_DIR)/demos
	@echo "--- Building demo $@ ---"
	@$(MAKE) -C examples/demos/$@
	@cp examples/demos/$@/$@.feb $(BUILD_DIR)/demos/
	@echo "Installed $(BUILD_DIR)/demos/$@.feb"

$(APPS):
	@mkdir -p $(BUILD_DIR)/apps
	@echo "--- Building app $@ ---"
	@$(MAKE) -C examples/apps/$@
	@cp examples/apps/$@/$@.feb $(BUILD_DIR)/apps/
	@echo "Installed $(BUILD_DIR)/apps/$@.feb"

SIM_TARGET ?= $(if $(APP),$(APP),$(if $(GAME),$(GAME),$(if $(DEMO),$(DEMO),$(TARGET))))
SIM_FEB = $(if $(SIM_TARGET),$(if $(wildcard $(SIM_TARGET)),$(SIM_TARGET),$(firstword $(wildcard $(BUILD_DIR)/*/$(SIM_TARGET).feb $(BUILD_DIR)/$(SIM_TARGET).feb $(SIM_TARGET).feb))),)

sim run:
	@python3 tools/feb_sim.py $(SIM_FEB) $(SIM_ARGS)

dist: all
	@mkdir -p $(DIST_DIR)/games $(DIST_DIR)/apps $(DIST_DIR)/demos
	@rm -rf $(DIST_DIR)/*
	@mkdir -p $(DIST_DIR)/games $(DIST_DIR)/apps $(DIST_DIR)/demos
	@for game in $(GAMES); do \
		if [ -f $(BUILD_DIR)/games/$$game.feb ]; then \
			cp $(BUILD_DIR)/games/$$game.feb $(DIST_DIR)/games/; \
		fi; \
	done
	@for app in $(APPS); do \
		if [ -f $(BUILD_DIR)/apps/$$app.feb ]; then \
			cp $(BUILD_DIR)/apps/$$app.feb $(DIST_DIR)/apps/; \
		fi; \
	done
	@for demo in $(DEMOS); do \
		if [ -f $(BUILD_DIR)/demos/$$demo.feb ]; then \
			cp $(BUILD_DIR)/demos/$$demo.feb $(DIST_DIR)/demos/; \
		fi; \
	done
	@echo "Flashiibo Executable Binary (.feb) Applications & Games - Release $(VERSION)" > $(DIST_DIR)/README.txt
	@echo "============================================================" >> $(DIST_DIR)/README.txt
	@echo "Compatible with Flashiibo Pro Gen3 and Gen2 (firmware >= 26.10.6)." >> $(DIST_DIR)/README.txt
	@echo "" >> $(DIST_DIR)/README.txt
	@echo "Installation:" >> $(DIST_DIR)/README.txt
	@echo "1. Connect your Flashiibo Pro via USB or Web Bluetooth using Flashiibo Pro Tools." >> $(DIST_DIR)/README.txt
	@echo "2. Upload the .feb file(s) to the /feb/ folder on the device flash storage." >> $(DIST_DIR)/README.txt
	@echo "3. On your Flashiibo, navigate to 'FEB Runner', select the application, and press OK!" >> $(DIST_DIR)/README.txt
	@echo "" >> $(DIST_DIR)/README.txt
	@echo "Emergency Exit Chord:" >> $(DIST_DIR)/README.txt
	@echo "Press UP and DOWN simultaneously to return to the FEB Runner menu." >> $(DIST_DIR)/README.txt
	@echo "" >> $(DIST_DIR)/README.txt
	@echo "Games (games/):" >> $(DIST_DIR)/README.txt
	@for game in $(GAMES); do \
		echo "  - games/$$game.feb" >> $(DIST_DIR)/README.txt; \
	done
	@echo "" >> $(DIST_DIR)/README.txt
	@echo "Apps (apps/):" >> $(DIST_DIR)/README.txt
	@for app in $(APPS); do \
		echo "  - apps/$$app.feb" >> $(DIST_DIR)/README.txt; \
	done
	@echo "" >> $(DIST_DIR)/README.txt
	@echo "Developer Demos (demos/):" >> $(DIST_DIR)/README.txt
	@for demo in $(DEMOS); do \
		echo "  - demos/$$demo.feb" >> $(DIST_DIR)/README.txt; \
	done
	@rm -f $(DIST_DIR)/$(PACKAGE_ZIP) $(DIST_DIR)/sha256sums.txt
	@cd $(DIST_DIR) && zip -9 -r $(PACKAGE_ZIP) games apps demos README.txt
	@cd $(DIST_DIR) && find games apps demos -name "*.feb" | sort | xargs sha256sum > sha256sums.txt
	@cd $(DIST_DIR) && sha256sum $(PACKAGE_ZIP) >> sha256sums.txt
	@echo ""
	@echo "=== Distribution Artifacts Packaged in $(DIST_DIR)/ (v$(VERSION)) ==="
	@ls -la $(DIST_DIR)

test:
	@echo "=== Running FEB Tooling & Build Verification Tests ==="
	@python3 -m unittest discover -s test -p "test_*.py" -v

publish:
	@echo "=== Tagging commit with version $(VERSION) and publishing to main ==="
	git tag -f $(VERSION)
	git push origin $(VERSION) -f
	git push origin develop:main

clean:
	@rm -rf $(BUILD_DIR) $(DIST_DIR)
	@for game in $(GAMES); do \
		if [ -d examples/games/$$game ]; then $(MAKE) -C examples/games/$$game clean; fi; \
	done
	@for demo in $(DEMOS); do \
		if [ -d examples/demos/$$demo ]; then $(MAKE) -C examples/demos/$$demo clean; fi; \
	done
	@for app in $(APPS); do \
		if [ -d examples/apps/$$app ]; then $(MAKE) -C examples/apps/$$app clean; fi; \
	done
	@echo "Cleaned all FEB build artifacts."
