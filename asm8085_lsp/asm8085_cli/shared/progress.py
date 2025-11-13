"""Simple progress indicators without external dependencies."""

import sys
import time
from contextlib import contextmanager

from .colors import Colors


class ProgressSpinner:
    """Simple spinner for indeterminate progress."""

    def __init__(self, message="Processing", color=True):
        self.message = message
        self.color = color
        self.frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self.current = 0
        self.running = False
        self._start_time = None

    def start(self):
        """Start the spinner."""
        self._start_time = time.time()
        self.running = True
        self._update()

    def _update(self):
        """Update spinner frame."""
        if not self.running:
            return

        frame = self.frames[self.current]
        elapsed = time.time() - self._start_time
        elapsed_str = f"{elapsed:.1f}s"

        if self.color:
            msg = f"\r{Colors.CYAN}{frame}{Colors.RESET} {self.message}... {Colors.DIM}({elapsed_str}){Colors.RESET}"
        else:
            msg = f"\r{frame} {self.message}... ({elapsed_str})"

        sys.stderr.write(msg)
        sys.stderr.flush()
        self.current = (self.current + 1) % len(self.frames)

    def stop(self, success=True, final_message=None):
        """Stop the spinner."""
        self.running = False
        elapsed = time.time() - self._start_time
        elapsed_str = f"{elapsed:.2f}s"

        if success:
            icon = "✓"
            color = Colors.GREEN if self.color else ""
        else:
            icon = "✗"
            color = Colors.RED if self.color else ""

        msg = final_message or self.message
        reset = Colors.RESET if self.color else ""
        dim = Colors.DIM if self.color else ""

        sys.stderr.write(f"\r{color}{icon}{reset} {msg} {dim}({elapsed_str}){reset}\n")
        sys.stderr.flush()

    def tick(self):
        """Update the spinner (call periodically in loop)."""
        if self.running:
            self._update()


class ProgressBar:
    """Simple progress bar for determinate progress."""

    def __init__(self, total, message="Progress", width=40, color=True):
        self.total = total
        self.current = 0
        self.message = message
        self.width = width
        self.color = color
        self._start_time = None

    def start(self):
        """Start the progress bar."""
        self._start_time = time.time()
        self._update()

    def update(self, current=None, increment=1):
        """Update progress."""
        if current is not None:
            self.current = current
        else:
            self.current += increment

        self._update()

    def _update(self):
        """Render the progress bar."""
        if self.total == 0:
            percent = 100
        else:
            percent = min(100, int((self.current / self.total) * 100))

        filled = int((percent / 100) * self.width)
        bar = "█" * filled + "░" * (self.width - filled)

        if self.color:
            bar_display = f"{Colors.CYAN}{bar}{Colors.RESET}"
            percent_display = f"{Colors.BOLD}{percent:3d}%{Colors.RESET}"
        else:
            bar_display = bar
            percent_display = f"{percent:3d}%"

        msg = f"\r{self.message}: {bar_display} {percent_display} ({self.current}/{self.total})"
        sys.stderr.write(msg)
        sys.stderr.flush()

    def finish(self, success=True, final_message=None):
        """Finish the progress bar."""
        elapsed = time.time() - self._start_time
        elapsed_str = f"{elapsed:.2f}s"

        if success:
            icon = "✓"
            color = Colors.GREEN if self.color else ""
        else:
            icon = "✗"
            color = Colors.RED if self.color else ""

        msg = final_message or self.message
        reset = Colors.RESET if self.color else ""
        dim = Colors.DIM if self.color else ""

        sys.stderr.write(f"\r{color}{icon}{reset} {msg} {dim}({elapsed_str}){reset}\n")
        sys.stderr.flush()


@contextmanager
def spinner(message="Processing", color=True):
    """Context manager for spinner.

    Usage:
        with spinner("Loading data"):
            # long operation
            pass
    """
    s = ProgressSpinner(message, color)
    s.start()
    try:
        yield s
        s.stop(success=True)
    except Exception as e:
        s.stop(success=False, final_message=f"{message} failed")
        raise


@contextmanager
def progress_bar(total, message="Progress", width=40, color=True):
    """Context manager for progress bar.

    Usage:
        with progress_bar(100, "Processing") as bar:
            for i in range(100):
                # do work
                bar.update()
    """
    bar = ProgressBar(total, message, width, color)
    bar.start()
    try:
        yield bar
        bar.finish(success=True)
    except Exception as e:
        bar.finish(success=False, final_message=f"{message} failed")
        raise


def format_duration(seconds):
    """Format duration in human-readable format."""
    if seconds < 0.001:
        return f"{seconds * 1_000_000:.0f} µs"
    elif seconds < 1:
        return f"{seconds * 1000:.1f} ms"
    elif seconds < 60:
        return f"{seconds:.2f} s"
    else:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.1f}s"


def format_size(bytes_count):
    """Format byte size in human-readable format."""
    for unit in ["B", "KB", "MB", "GB"]:
        if bytes_count < 1024:
            return f"{bytes_count:.1f} {unit}"
        bytes_count /= 1024
    return f"{bytes_count:.1f} TB"
