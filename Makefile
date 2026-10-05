# Flashiibo FEB (Flashiibo Executable Binary) Root Makefile
# Targets the Flashiibo Gen3 FEB runtime (Beta & Experimental).

GAMES := 2048 flappy_bird sokoban
DEMOS := template button_demo draw_demo
EXAMPLES := $(GAMES) $(DEMOS)
BUILD_DIR := build
DIST_DIR := dist
PACKAGE_ZIP := flashiibo-feb-games.zip
VERSION ?= $(shell date +'%y.%m.%d')

.DEFAULT_GOAL := help
.PHONY: help all clean test dist publish $(EXAMPLES)

help:
	@echo "Flashiibo FEB SDK Build System"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Available targets:"
	@echo "  help        Display this help message (default)"
	@echo "  all         Build all applications (games & demos) into $(BUILD_DIR)/"
	@echo "  dist        Package public release games and checksums into $(DIST_DIR)/"
	@echo "  test        Run automated verification test suite"
	@echo "  clean       Clean build artifacts and build directory"
	@echo "  publish     Tag commit with version ($(VERSION)) and push develop to main"
	@echo ""
	@echo "Games (included in public release):"
	@echo "  2048          Build 2048 puzzle game"
	@echo "  flappy_bird   Build Flappy Bird sprite demo application"
	@echo "  sokoban       Build 10-level Sokoban puzzle game"
	@echo ""
	@echo "Developer Examples & Demos (kept in examples/):"
	@echo "  template      Build starter template application"
	@echo "  button_demo   Build 4-button hardware demo application"
	@echo "  draw_demo     Build vector geometry & shapes demo application"
	@echo ""

all: $(EXAMPLES)
	@echo ""
	@echo "=== All FEB Applications Built Successfully ==="
	@ls -la $(BUILD_DIR)

$(EXAMPLES):
	@mkdir -p $(BUILD_DIR)
	@echo "--- Building $@ ---"
	@$(MAKE) -C examples/$@
	@cp examples/$@/$@.feb $(BUILD_DIR)/
	@echo "Installed $(BUILD_DIR)/$@.feb"

dist: all
	@mkdir -p $(DIST_DIR)
	@rm -rf $(DIST_DIR)/*
	@for game in $(GAMES); do \
		cp $(BUILD_DIR)/$$game.feb $(DIST_DIR)/; \
	done
	@echo "Flashiibo Executable Binary (.feb) Games - Release $(VERSION)" > $(DIST_DIR)/README.txt
	@echo "============================================================" >> $(DIST_DIR)/README.txt
	@echo "Compatible with Flashiibo Pro Gen3 (firmware >= 26.10.4)." >> $(DIST_DIR)/README.txt
	@echo "" >> $(DIST_DIR)/README.txt
	@echo "Installation:" >> $(DIST_DIR)/README.txt
	@echo "1. Connect your Flashiibo Pro Gen3 via USB or Web Bluetooth using Flashiibo Pro Tools." >> $(DIST_DIR)/README.txt
	@echo "2. Upload the .feb file(s) to the /feb/ folder on the device flash storage." >> $(DIST_DIR)/README.txt
	@echo "3. On your Flashiibo, navigate to 'FEB Runner', select the game, and press OK!" >> $(DIST_DIR)/README.txt
	@echo "" >> $(DIST_DIR)/README.txt
	@echo "Emergency Exit Chord:" >> $(DIST_DIR)/README.txt
	@echo "Press UP and DOWN simultaneously to return to the FEB Runner menu." >> $(DIST_DIR)/README.txt
	@echo "" >> $(DIST_DIR)/README.txt
	@echo "Included games:" >> $(DIST_DIR)/README.txt
	@for game in $(GAMES); do \
		echo "  - $$game.feb" >> $(DIST_DIR)/README.txt; \
	done
	@rm -f $(DIST_DIR)/$(PACKAGE_ZIP) $(DIST_DIR)/sha256sums.txt
	@cd $(DIST_DIR) && zip -9 $(PACKAGE_ZIP) *.feb README.txt
	@cd $(DIST_DIR) && sha256sum *.feb $(PACKAGE_ZIP) > sha256sums.txt
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
	@for app in $(EXAMPLES); do \
		$(MAKE) -C examples/$$app clean; \
	done
	@echo "Cleaned all FEB build artifacts."
