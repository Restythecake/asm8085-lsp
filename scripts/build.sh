#!/usr/bin/env bash
# Build script for asm8085-lsp standalone binary
# Uses PyInstaller to create a single executable file

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DIST_DIR="$PROJECT_ROOT/dist"
BUILD_DIR="$PROJECT_ROOT/build"
SPEC_DIR="$PROJECT_ROOT/build"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Building asm8085-lsp binary ===${NC}"

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: python3 is required but not found${NC}"
    exit 1
fi

# Check for PyInstaller
if ! python3 -c "import PyInstaller" &> /dev/null; then
    echo -e "${YELLOW}PyInstaller not found. Installing...${NC}"
    pip3 install pyinstaller
fi

# Clean previous builds
echo -e "${BLUE}Cleaning previous builds...${NC}"
rm -rf "$DIST_DIR" "$BUILD_DIR" "$SPEC_DIR"/*.spec

# Generate instruction database
echo -e "${BLUE}Generating instruction database...${NC}"
cd "$PROJECT_ROOT"
python3 scripts/generate_db.py

# Build with PyInstaller
echo -e "${BLUE}Building standalone binary...${NC}"
pyinstaller \
    --clean \
    --onefile \
    --name asm8085-lsp \
    --distpath "$DIST_DIR" \
    --workpath "$BUILD_DIR" \
    --specpath "$SPEC_DIR" \
    --noconfirm \
    --console \
    asm8085-lsp

# Verify build
BINARY_NAME="asm8085-lsp"
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    BINARY_NAME="asm8085-lsp.exe"
fi

BINARY_PATH="$DIST_DIR/$BINARY_NAME"

if [ -f "$BINARY_PATH" ]; then
    # Make executable on Unix
    chmod +x "$BINARY_PATH"

    FILE_SIZE=$(du -h "$BINARY_PATH" | cut -f1)
    echo -e "${GREEN}✓ Build successful!${NC}"
    echo -e "${GREEN}Binary: $BINARY_PATH ($FILE_SIZE)${NC}"

    # Test the binary
    echo -e "${BLUE}Testing binary...${NC}"
    if "$BINARY_PATH" --help &> /dev/null || true; then
        echo -e "${GREEN}✓ Binary is executable${NC}"
    fi
else
    echo -e "${RED}✗ Build failed: Binary not found at $BINARY_PATH${NC}"
    exit 1
fi

echo -e "${GREEN}=== Build complete ===${NC}"
echo -e "Binary location: ${BLUE}$BINARY_PATH${NC}"
echo ""
echo -e "To install the binary in the Zed extension:"
echo -e "  cp $BINARY_PATH ../zed-8085-asm/bin/"
