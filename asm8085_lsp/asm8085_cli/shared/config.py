"""Configuration file parser for asm8085."""

import configparser
from pathlib import Path


class Config:
    """Handle configuration from ~/.asmrc and .asmrc files."""

    def __init__(self):
        self.config = configparser.ConfigParser()
        self.loaded_files = []
        self._load_configs()

    def _load_configs(self):
        """Load configuration files in order of priority (lower overrides higher)."""
        config_locations = [
            Path.home() / ".asmrc",  # Global config
            Path.cwd() / ".asmrc",  # Project-local config
        ]

        for config_path in config_locations:
            if config_path.exists():
                try:
                    self.config.read(config_path)
                    self.loaded_files.append(str(config_path))
                except Exception as e:
                    print(f"Warning: Could not read {config_path}: {e}")

    def get_bool(self, section: str, key: str, default: bool = False) -> bool:
        """Get a boolean value from config."""
        try:
            return self.config.getboolean(section, key, fallback=default)
        except ValueError:
            return default

    def get_int(self, section: str, key: str, default: int = 0) -> int:
        """Get an integer value from config."""
        try:
            return self.config.getint(section, key, fallback=default)
        except ValueError:
            return default

    def get_string(self, section: str, key: str, default: str = "") -> str:
        """Get a string value from config."""
        return self.config.get(section, key, fallback=default)

    def get_float(self, section: str, key: str, default: float = 0.0) -> float:
        """Get a float value from config."""
        try:
            return self.config.getfloat(section, key, fallback=default)
        except ValueError:
            return default

    def apply_to_args(self, args):
        """Apply config values to argparse args object (if not already set by CLI)."""
        # Only apply config if the argument wasn't explicitly set on command line

        # [defaults] section
        if hasattr(args, "highlight_changes") and args.highlight_changes is None:
            args.highlight_changes = self.get_bool("defaults", "highlight", False)

        if hasattr(args, "show_registers") and args.show_registers is None:
            args.show_registers = self.get_bool("defaults", "show_registers", False)

        if hasattr(args, "binary") and args.binary is None:
            args.binary = self.get_bool("defaults", "binary", False)

        if hasattr(args, "verbose") and args.verbose is None:
            args.verbose = self.get_bool("defaults", "verbose", False)

        if hasattr(args, "warnings") and args.warnings is None:
            args.warnings = self.get_bool("defaults", "warnings", False)

        # Base format (hex, decimal, binary) - only apply if using default
        if hasattr(args, "base") and args.base == "hex":
            base_str = self.get_string("defaults", "base", "hex").lower()
            if base_str in ["hex", "dec", "bin"]:
                args.base = base_str

        # Clock speed - only apply if not set by CLI
        if hasattr(args, "clock") and args.clock is None:
            clock = self.get_float("defaults", "clock", 0.0)
            if clock > 0:
                args.clock = clock

        return args

    def has_config(self) -> bool:
        """Check if any config files were loaded."""
        return len(self.loaded_files) > 0

    def get_loaded_files(self) -> list:
        """Get list of loaded config files."""
        return self.loaded_files


def create_default_config(path: Path):
    """Create a default .asmrc configuration file."""
    config_content = """# asm8085 Configuration File
# This file controls default behavior of the asm command

[defaults]
# Display options
# Highlight register changes (-H flag)
highlight = false
# Show final registers (-r flag)
show_registers = false
# Show registers in binary (-b flag)
binary = false
# Verbose error messages (-v flag)
verbose = false
# Show assembly warnings (-W flag)
warnings = false

# Number format (hex, dec, bin)
base = hex

# Clock speed in MHz (for timing calculations)
clock = 5.0

# Examples of usage:
# - Set highlight = true to always show register changes
# - Set show_registers = true to always show final state
# - Set base = dec to see values in decimal by default
# - Set warnings = true to always check for issues
"""

    with open(path, "w") as f:
        f.write(config_content)


# Convenience function
def load_config() -> Config:
    """Load configuration from standard locations."""
    return Config()
