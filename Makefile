# Flashiibo FEB (Flashiibo Executable Binary) Root Makefile
# Targets the Flashiibo Gen3 FEB runtime (Beta & Experimental).

EXAMPLES := 2048 template button_test
BUILD_DIR := build

.PHONY: all clean test $(EXAMPLES)

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
	@python3 -m unittest discover -s test -p "test_*.py" -v || python3 tools/test_tooling.py

clean:
	@rm -rf $(BUILD_DIR)
	@for app in $(EXAMPLES); do \
		$(MAKE) -C examples/$$app clean; \
	done
	@echo "Cleaned all FEB build artifacts."
