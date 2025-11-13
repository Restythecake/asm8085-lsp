# Makefile for asm8085-lsp Language Server
# Provides convenient commands for development and building

.PHONY: help install dev clean build test lint format run

# Default target
help:
	@echo "asm8085-lsp Development Commands"
	@echo "================================="
	@echo ""
	@echo "  make install     - Install the package"
	@echo "  make dev         - Install in development mode"
	@echo "  make clean       - Remove build artifacts"
	@echo "  make build       - Build standalone binary with PyInstaller"
	@echo "  make test        - Run tests (if available)"
	@echo "  make lint        - Run linters (if available)"
	@echo "  make format      - Format code with black (if available)"
	@echo "  make run         - Run the LSP server directly"
	@echo "  make db          - Generate instruction database"
	@echo ""

# Install the package
install:
	pip install .

# Install in development mode (editable)
dev:
	pip install -e .

# Generate instruction database
db:
	python3 scripts/generate_db.py

# Clean build artifacts
clean:
	rm -rf build/ dist/ *.egg-info/
	rm -rf asm8085_lsp/__pycache__/ asm8085_lsp/*/__pycache__/
	rm -rf asm8085_lsp/asm8085_cli/__pycache__/
	rm -f asm8085_lsp/asm8085_cli/instruction_db.json
	rm -f *.spec
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete

# Build standalone binary
build: db
	@echo "Building standalone binary..."
	bash scripts/build.sh

# Run tests
test:
	@if command -v pytest >/dev/null 2>&1; then \
		pytest; \
	else \
		echo "pytest not installed. Install with: pip install pytest"; \
	fi

# Run linters
lint:
	@if command -v pylint >/dev/null 2>&1; then \
		pylint asm8085_lsp/; \
	else \
		echo "pylint not installed. Install with: pip install pylint"; \
	fi

# Format code
format:
	@if command -v black >/dev/null 2>&1; then \
		black asm8085_lsp/; \
	else \
		echo "black not installed. Install with: pip install black"; \
	fi

# Run the LSP server directly
run:
	python3 -m asm8085_lsp

# Check if PyInstaller is available
check-pyinstaller:
	@if ! python3 -c "import PyInstaller" 2>/dev/null; then \
		echo "PyInstaller not found. Installing..."; \
		pip install pyinstaller; \
	fi

# Build for distribution (with checks)
dist: clean check-pyinstaller build
	@echo "Distribution build complete!"
	@ls -lh dist/

# Quick rebuild (no clean)
rebuild: db
	bash scripts/build.sh
