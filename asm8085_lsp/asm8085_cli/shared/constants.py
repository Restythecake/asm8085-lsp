"""Constants and configuration values for the 8085 assembler."""

# Memory and addressing
MEMORY_SIZE = 0x10000  # 64KB address space
DEFAULT_LOAD_ADDRESS = 0x8000  # Default program load address (32KB)
STACK_TOP = 0xFFFF  # Stack starts at top of memory

# Execution limits
DEFAULT_STEP_LIMIT = 100000  # Default maximum steps before timeout
REPL_MAX_RUN_STEPS = 10000  # Maximum steps in REPL run command
COVERAGE_PROGRESS_THRESHOLD = 1000  # Show progress indicator if > this many steps

# Watch mode
WATCH_POLL_INTERVAL = 0.5  # Seconds between file checks in watch mode

# Display
MAX_ERROR_CONTEXT_LINES = 5  # Lines before/after error to show in verbose mode
ERROR_CONTEXT_TOTAL = 10  # Total lines in error context window
MEMORY_BYTES_PER_LINE = 16  # Bytes to display per line in hex dumps
DISASM_BAR_WIDTH = 80  # Width of separator bars in disassembly

# Performance
SIMILARITY_THRESHOLD = 0.5  # Minimum similarity for fuzzy matching suggestions
MAX_SUGGESTIONS = 3  # Maximum number of suggestions to show
PROFILER_DEFAULT_TOP_N = 10  # Default number of items in profiler reports

# Benchmarking
DEFAULT_BENCHMARK_RUNS = 3  # Default number of runs for benchmarking

# Clock speeds (MHz)
DEFAULT_CLOCK_SPEED = 5.0  # Default 8085 clock speed in MHz
MIN_CLOCK_SPEED = 0.1
MAX_CLOCK_SPEED = 100.0

# File extensions
ASM_EXTENSION = ".asm"
HEX_EXTENSIONS = {
    "raw": ".txt",
    "intel": ".hex",
    "c": ".h",
    "json": ".json",
}

# ANSI color codes (can be disabled via NO_COLOR environment variable)
COLOR_CODES = {
    "RED": "\033[91m",
    "GREEN": "\033[92m",
    "YELLOW": "\033[93m",
    "BLUE": "\033[94m",
    "MAGENTA": "\033[95m",
    "CYAN": "\033[96m",
    "WHITE": "\033[97m",
    "BOLD": "\033[1m",
    "DIM": "\033[2m",
    "RESET": "\033[0m",
}

# Numeric bases for display
NUMERIC_BASES = {
    "hex": 16,
    "dec": 10,
    "bin": 2,
}

# Warning types
WARNING_TYPES = {
    "unused_label": "🏷️",
    "unreachable_code": "⛔",
    "optimization": "⚡",
    "redundant": "♻️",
}

# Template categories
TEMPLATE_CATEGORIES = [
    "General",
    "Arithmetic",
    "Loops",
    "Subroutines",
    "Arrays",
    "I/O",
    "Control Flow",
    "Stack",
    "Interrupts",
]

# Instruction categories for cheat sheet
INSTRUCTION_CATEGORIES = [
    "Data Transfer",
    "Arithmetic",
    "Logical",
    "Branch",
    "Stack",
    "I/O",
    "Control",
]

# Coverage thresholds for color coding
COVERAGE_EXCELLENT = 90  # Green
COVERAGE_GOOD = 70  # Yellow
COVERAGE_POOR = 50  # Red below this

# Profiler hotspot thresholds (percentage of total cycles)
HOTSPOT_CRITICAL = 20  # Red
HOTSPOT_HIGH = 10  # Yellow
HOTSPOT_MEDIUM = 5  # Cyan
