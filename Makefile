# Flashiibo FEB (Flashiibo Executable Binary) Root Makefile
# Targets the Flashiibo Gen3 FEB runtime (Beta & Experimental).

EXAMPLES := 2048 template button_demo draw_demo flappy_bird sokoban
BUILD_DIR := build

.DEFAULT_GOAL := help
.PHONY: help all clean test publish $(EXAMPLES)

help:
	@echo "Flashiibo FEB SDK Build System"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Available targets:"
	@echo "  help        Display this help message (default)"
	@echo "  all         Build all example applications into $(BUILD_DIR)/"
	@echo "  test        Run automated verification test suite"
	@echo "  clean       Clean build artifacts and build directory"
	@echo "  publish     Push develop branch to main"
	@echo ""
	@echo "Example applications:"
	@echo "  2048          Build 2048 puzzle game"
	@echo "  template      Build starter template application"
	@echo "  button_demo   Build 4-button hardware demo application"
	@echo "  draw_demo     Build vector geometry & shapes demo application"
	@echo "  flappy_bird   Build Flappy Bird sprite demo application"
	@echo "  sokoban       Build 10-level Sokoban puzzle game"
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

test:
	@echo "=== Running FEB Tooling & Build Verification Tests ==="
	@python3 -m unittest discover -s test -p "test_*.py" -v

publish:
	@echo "=== Publishing develop branch to main ==="
	git push origin develop:main

clean:
	@rm -rf $(BUILD_DIR)
	@for app in $(EXAMPLES); do \
		$(MAKE) -C examples/$$app clean; \
	done
	@echo "Cleaned all FEB build artifacts."
