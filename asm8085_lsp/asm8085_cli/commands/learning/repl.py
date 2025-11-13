"""Interactive REPL extracted from asm8085."""

import io
import os
import re
import shutil
import sys
from contextlib import redirect_stderr, redirect_stdout

from ...shared import assembler, emu8085
from ...shared.colors import Colors, strip_ansi
from ...shared.disasm import disassemble_instruction, get_instruction_cycles
from ...shared.parsing import parse_address_value
from ...shared.registers import decode_flags

try:
    import readline  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    readline = None

# REPL Constants
REPL_DEFAULT_BASE_ADDRESS = 0x0800
REPL_MAX_RUN_STEPS = 10000
REPL_MAX_LOG_LINES = 400
REPL_MEMORY_WINDOW_SIZE = 32
REPL_STACK_PREVIEW_DEPTH = 8
REPL_MEMORY_DUMP_LIMIT = 0x0100
REPL_DIRTY_MEMORY_THRESHOLD = 1024  # Track dirty pages instead of full copy


class InteractiveREPL:
    """Interactive 8085 Assembly REPL with session management."""

    def __init__(self):
        self.base_address = REPL_DEFAULT_BASE_ADDRESS
        self.max_run_steps = REPL_MAX_RUN_STEPS
        self.decimal_mode = False  # False = hex (default), True = decimal
        self.history = []  # [{'display': str, 'canonical': str}]
        self.undo_stack = []  # [{'entry': {...}, 'state': snapshot, 'cycles': int}]
        self.session_lines = []  # canonical lines that form the program
        self.panel_modes = ["all", "overview", "registers", "memory", "stack"]
        self.current_panel_idx = 0
        self.memory_panel_start = self.base_address
        self.memory_window_size = REPL_MEMORY_WINDOW_SIZE
        self.stack_preview_depth = REPL_STACK_PREVIEW_DEPTH
        self.log_lines = []
        self.max_log_lines = REPL_MAX_LOG_LINES
        self.alt_screen_active = False
        self.readline_enabled = False
        self.panel_render_width = 0
        self.breakpoints = set()  # Set of addresses for breakpoints
        self.unsaved_changes = False  # Track if session has unsaved changes
        self.last_render_state = None  # Cache for UI optimization
        self.command_aliases = {  # Command aliases
            "?": "help",
            "h": "help",
            "q": "quit",
            "m": "memory",
            "s": "show",
            "u": "undo",
            "r": "run",
            "l": "load",
            "b": "break",
            "c": "continue",
        }
        self.reset_cpu_state()

    def reset_cpu_state(self):
        """Reset CPU internals without touching the session."""
        self.cpu = emu8085()
        self.current_addr = self.base_address
        self.instruction_count = 0
        self.total_cycles = 0

    def save_state(self):
        """Save current CPU state for undo. Only saves modified memory regions."""
        # Only save memory around program area and stack for efficiency
        prog_start = max(0, self.base_address - 256)
        prog_end = min(65535, self.current_addr + 256)
        stack_start = max(0, self.cpu.SP.value - 256)
        stack_end = min(65535, self.cpu.SP.value + 256)

        # Combine ranges and save only those regions
        save_ranges = []
        if prog_start <= prog_end:
            save_ranges.append((prog_start, prog_end))
        if stack_start <= stack_end and (
            stack_start > prog_end or stack_end < prog_start
        ):
            save_ranges.append((stack_start, stack_end))

        memory_snapshot = {}
        for start, end in save_ranges:
            for i in range(start, end + 1):
                memory_snapshot[i] = self.cpu.memory[i].value

        return {
            "A": self.cpu.A.value,
            "B": self.cpu.B.value,
            "C": self.cpu.C.value,
            "D": self.cpu.D.value,
            "E": self.cpu.E.value,
            "H": self.cpu.H.value,
            "L": self.cpu.L.value,
            "SP": self.cpu.SP.value,
            "PC": self.cpu.PC.value,
            "FLAGS": self.cpu.F.value,
            "memory": memory_snapshot,
            "memory_ranges": save_ranges,
        }

    def restore_state(self, state):
        """Restore CPU state for undo."""
        self.cpu.A.value = state["A"]
        self.cpu.B.value = state["B"]
        self.cpu.C.value = state["C"]
        self.cpu.D.value = state["D"]
        self.cpu.E.value = state["E"]
        self.cpu.H.value = state["H"]
        self.cpu.L.value = state["L"]
        self.cpu.SP.value = state["SP"]
        self.cpu.PC.value = state["PC"]
        self.cpu.F.value = state["FLAGS"]

        # Restore memory from snapshot
        memory_snapshot = state.get("memory", {})
        if isinstance(memory_snapshot, dict):
            for addr, value in memory_snapshot.items():
                self.cpu.memory[addr].value = value
        else:
            # Fallback for old format (full array)
            for i in range(min(len(memory_snapshot), 65536)):
                self.cpu.memory[i].value = memory_snapshot[i]

        self.current_addr = self.cpu.PC.value

    def get_register_snapshot(self):
        """Get current register values."""
        return {
            "A": self.cpu.A.value,
            "B": self.cpu.B.value,
            "C": self.cpu.C.value,
            "D": self.cpu.D.value,
            "E": self.cpu.E.value,
            "H": self.cpu.H.value,
            "L": self.cpu.L.value,
            "SP": self.cpu.SP.value,
            "PC": self.cpu.PC.value,
            "FLAGS": self.cpu.F.value,
        }

    def display_state(self, before=None, cycles=0):
        """Display CPU state with changes highlighted."""
        current = self.get_register_snapshot()
        reg_line = ""
        for reg in ["A", "B", "C", "D", "E", "H", "L"]:
            value = current[reg]
            if before and before[reg] != value:
                reg_line += f"{reg}={Colors.HIGHLIGHT}{value:02X}{Colors.RESET} "
            else:
                reg_line += f"{reg}={Colors.CYAN}{value:02X}{Colors.RESET} "

        sp_val = current["SP"]
        if before and before["SP"] != sp_val:
            reg_line += f"SP={Colors.HIGHLIGHT}{sp_val:04X}{Colors.RESET} "
        else:
            reg_line += f"SP={Colors.DIM}{sp_val:04X}{Colors.RESET} "

        flags = decode_flags(current["FLAGS"])
        flag_str = f"S={flags['S']} Z={flags['Z']} AC={flags['AC']} P={flags['P']} CY={flags['CY']}"

        if before:
            before_flags = decode_flags(before["FLAGS"])
            if flags != before_flags:
                flag_str = f"{Colors.YELLOW}{flag_str}{Colors.RESET}"
            else:
                flag_str = f"{Colors.DIM}{flag_str}{Colors.RESET}"
        else:
            flag_str = f"{Colors.DIM}{flag_str}{Colors.RESET}"

        print(f"  {reg_line}")
        print(f"  {flag_str}  {Colors.DIM}[{cycles}T]{Colors.RESET}")

    def convert_to_hex(self, line):
        """Convert decimal numbers to hex if in decimal mode."""
        if not self.decimal_mode:
            return line

        def replace_num(match):
            num_str = match.group(0)
            if num_str.endswith("H") or num_str.startswith(("0x", "0X")):
                return num_str
            if num_str.endswith(("D", "d")):
                return num_str
            try:
                dec_val = int(num_str)
                return f"{dec_val:X}H"
            except ValueError:
                return num_str

        return re.sub(r"\b\d+\b", replace_num, line)

    def append_log(self, text):
        if text is None:
            return
        if not isinstance(text, str):
            text = str(text)
        text = text.replace("\r", "")
        lines = text.split("\n")
        for line in lines:
            self.log_lines.append(line)
        if len(self.log_lines) > self.max_log_lines:
            self.log_lines = self.log_lines[-self.max_log_lines :]

    def command_completer(self, text, state):
        """Tab completion for commands."""
        commands = [
            "help",
            "quit",
            "exit",
            "show",
            "set",
            "history",
            "undo",
            "view",
            "step",
            "run",
            "continue",
            "load",
            "save",
            "labels",
            "memory",
            "break",
            "breakpoint",
            "disasm",
            "disassemble",
            "search",
            "find",
            "calc",
            "eval",
            "decimal",
            "hex",
            "clear",
            "reset",
        ]
        matches = [cmd for cmd in commands if cmd.startswith(text.lower())]
        if state < len(matches):
            return matches[state]
        return None

    def setup_readline(self):
        if readline is None or self.readline_enabled:
            return
        try:
            readline.set_history_length(1000)
            readline.parse_and_bind("set editing-mode emacs")
            readline.parse_and_bind("tab: complete")
            readline.set_completer(self.command_completer)
            # Set completer delimiters to include : for command mode
            readline.set_completer_delims(" \t\n;")
            self.readline_enabled = True
        except Exception:
            self.readline_enabled = False

    def add_history_entry(self, line):
        if not self.readline_enabled or not line.strip():
            return
        try:
            length = readline.get_current_history_length()
            last_item = readline.get_history_item(length) if length else None
            if last_item != line:
                readline.add_history(line)
        except Exception:
            pass

    def format_cell(self, text, width):
        if text is None:
            text = ""
        plain = strip_ansi(text)
        # Truncate if needed
        if len(plain) > width:
            ellipsis = "..."
            trimmed = plain[: max(1, width - len(ellipsis))] + ellipsis
            text = trimmed
            plain = trimmed
        padding = max(0, width - len(plain))
        return text + " " * padding

    def format_flag_badge(self, label, enabled):
        color = Colors.GREEN if enabled else Colors.DIM
        return f"{color}{label}{Colors.RESET}"

    def format_register_cell(self, name, value):
        width = 4 if name in {"PC", "SP"} else 2
        hex_fmt = f"{value:0{width}X}H"
        return (
            f"{Colors.CYAN}{name:<2}{Colors.RESET} "
            f"{hex_fmt:<6} {Colors.DIM}{value:>5}{Colors.RESET}"
        )

    def build_overview_section(self, regs):
        pc = regs["PC"]
        sp = regs["SP"]
        lines = []
        lines.append(
            f"  {Colors.CYAN}PC{Colors.RESET} {pc:04X}H   "
            f"{Colors.CYAN}SP{Colors.RESET} {sp:04X}H   "
            f"{Colors.CYAN}Next{Colors.RESET} {self.current_addr:04X}H"
        )
        lines.append(
            f"  {Colors.CYAN}Instrs{Colors.RESET} {self.instruction_count:<6} "
            f"{Colors.CYAN}Cycles{Colors.RESET} {self.total_cycles:<8} "
            f"{Colors.CYAN}Window{Colors.RESET} {self.memory_panel_start:04X}H"
        )
        flags = decode_flags(regs["FLAGS"])
        badges = [
            self.format_flag_badge("S", flags["S"]),
            self.format_flag_badge("Z", flags["Z"]),
            self.format_flag_badge("AC", flags["AC"]),
            self.format_flag_badge("P", flags["P"]),
            self.format_flag_badge("CY", flags["CY"]),
        ]
        lines.append("  Flags " + " ".join(badges))
        if self.history:
            last_cmd = self.history[-1]["display"] or self.history[-1]["canonical"]
            lines.append(
                f"  {Colors.CYAN}Last:{Colors.RESET} {(last_cmd or '').strip()[:24]}"
            )
        return lines

    def build_register_section(self, regs):
        order = ["A", "B", "C", "D", "E", "H", "L"]
        lines = [
            f"{Colors.DIM}    Reg   Hex      Dec{Colors.RESET}",
            f"{Colors.DIM}    ----  ------   ------{Colors.RESET}",
        ]
        for name in order + ["PC", "SP"]:
            width = 4 if name in {"PC", "SP"} else 2
            hex_fmt = f"{regs[name]:0{width}X}H"
            dec_fmt = f"{regs[name]:>6}"
            lines.append(
                f"    {Colors.CYAN}{name:<2}{Colors.RESET}   {hex_fmt:<6}   "
                f"{Colors.DIM}{dec_fmt:<6}{Colors.RESET}"
            )
        flags = decode_flags(regs["FLAGS"])
        flag_text = (
            f"{'S' if flags['S'] else '-'}"
            f"{'Z' if flags['Z'] else '-'}"
            f"{'A' if flags['AC'] else '-'}"
            f"{'P' if flags['P'] else '-'}"
            f"{'C' if flags['CY'] else '-'}"
        )
        lines.append(f"{Colors.DIM}    ----  ------   ------{Colors.RESET}")
        lines.append(
            f"    {Colors.CYAN}Flags{Colors.RESET} {flag_text:<8} {Colors.DIM}(SZAPC){Colors.RESET}"
        )
        return lines

    def build_memory_section(self, start, count, row_width=8):
        lines = []
        end_addr = (start + max(0, count - 1)) & 0xFFFF
        lines.append(
            f"    {Colors.CYAN}Window{Colors.RESET} {start:04X}H - {end_addr:04X}H"
        )
        addr = start
        remaining = count
        while remaining > 0:
            chunk_len = min(row_width, remaining)
            chunk = [self.read_memory((addr + i) & 0xFFFF) for i in range(chunk_len)]
            bytes_str = " ".join(f"{b:02X}" for b in chunk)
            ascii_str = "".join(chr(b) if 32 <= b <= 126 else "." for b in chunk)
            lines.append(
                f"    {Colors.CYAN}{addr:04X}{Colors.RESET}: "
                f"{bytes_str:<23}  {Colors.DIM}{ascii_str}{Colors.RESET}"
            )
            addr = (addr + chunk_len) & 0xFFFF
            remaining -= chunk_len
        return lines

    def build_stack_section(self, regs, depth):
        sp = regs["SP"]
        lines = []
        lines.append(
            f"    {Colors.CYAN}SP{Colors.RESET} {sp:04X}H  "
            f"{Colors.DIM}(top shown first){Colors.RESET}"
        )
        for i in range(depth):
            addr = (sp + i) & 0xFFFF
            val = self.read_memory(addr)
            marker = f"{Colors.YELLOW}→{Colors.RESET}" if i == 0 else " "
            lines.append(
                f"    {marker} {addr:04X}: {val:02X}H  {Colors.DIM}{val:>3}{Colors.RESET}"
            )
        return lines

    def combine_columns(self, left, right, gap=""):
        """Combine two column lists within dashboard width."""
        total = max(self.panel_render_width, 32)
        right_width = max(18, min(30, total // 3))
        left_width = total - len(gap) - right_width

        result = []
        max_len = max(len(left), len(right))
        for i in range(max_len):
            left_line = left[i] if i < len(left) else ""
            right_line = right[i] if i < len(right) else ""

            left_cell = self.format_cell(left_line, left_width)
            right_cell = self.format_cell(right_line, right_width) if right_line else ""
            if right_cell.strip():
                combined = f"{left_cell}{gap}{right_cell}"
            else:
                combined = left_cell.rstrip()
            result.append(combined)
        return result

    def render_ui(self):
        width, height = shutil.get_terminal_size((100, 28))
        log_width = max(40, int(width * 0.6))
        panel_width = max(32, width - log_width - 3)
        log_height = max(12, height - 5)

        self.panel_render_width = panel_width
        mode = self.current_panel_mode() or "overview"
        kwargs = {}
        if mode == "memory":
            kwargs["start"] = self.memory_panel_start
        panel_lines = self.render_panel(mode, **kwargs)
        panel_lines = panel_lines[:log_height] + [""] * max(
            0, log_height - len(panel_lines)
        )

        log_view = self.log_lines[-log_height:]
        log_view = [""] * max(0, log_height - len(log_view)) + log_view

        sys.stdout.write("\033[2J\033[H")
        sys.stdout.flush()

        top_border = f"┌{'─' * log_width}┬{'─' * panel_width}┐"
        print(top_border)
        for left, right in zip(log_view, panel_lines):
            left_cell = self.format_cell(left, log_width)
            right_cell = self.format_cell(right, panel_width)
            print(f"│{left_cell}│{right_cell}│")
        bottom_border = f"└{'─' * log_width}┴{'─' * panel_width}┘"
        print(bottom_border)
        sys.stdout.flush()

    def enter_alt_screen(self):
        if self.alt_screen_active:
            return
        sys.stdout.write("\033[?1049h")
        sys.stdout.write("\033[H")
        sys.stdout.flush()
        self.alt_screen_active = True

    def exit_alt_screen(self):
        if not self.alt_screen_active:
            return
        sys.stdout.write("\033[?1049l")
        sys.stdout.flush()
        self.alt_screen_active = False

    def capture_output(self, func):
        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()
        try:
            with redirect_stdout(stdout_buf), redirect_stderr(stderr_buf):
                return func()
        except SystemExit:
            raise
        except Exception as exc:
            import traceback

            self.append_log(f"{Colors.RED}Unexpected error:{Colors.RESET} {exc}")
            self.append_log(traceback.format_exc())
        finally:
            out = stdout_buf.getvalue().rstrip()
            err = stderr_buf.getvalue().rstrip()
            if out:
                self.append_log(out)
            if err:
                self.append_log(f"{Colors.RED}{err}{Colors.RESET}")

    def read_memory(self, addr):
        return self.cpu.memory[addr & 0xFFFF].value

    def render_panel(self, mode, **kwargs):
        regs = self.get_register_snapshot()
        header = f"{Colors.BLUE}{Colors.BOLD}Dashboard · {mode.upper()}{Colors.RESET}"
        lines = [header]

        def add_section(title, body_lines):
            if not body_lines:
                return
            lines.append("")
            lines.append(f"{Colors.CYAN}{Colors.BOLD}{title}{Colors.RESET}")
            lines.extend(body_lines)

        if mode == "overview":
            add_section("Overview", self.build_overview_section(regs))
        elif mode == "registers":
            add_section("Register File", self.build_register_section(regs))
        elif mode == "memory":
            start = kwargs.get("start")
            if start is None:
                start = self.memory_panel_start or regs["PC"]
            self.memory_panel_start = start & 0xFFFF
            count = kwargs.get("count", self.memory_window_size)
            add_section(
                "Memory Window",
                self.build_memory_section(self.memory_panel_start, count),
            )
        elif mode == "stack":
            depth = kwargs.get("depth", self.stack_preview_depth)
            add_section("Stack View", self.build_stack_section(regs, depth))
        elif mode == "all":
            left = [
                f"{Colors.CYAN}{Colors.BOLD}Registers & Flags{Colors.RESET}",
                *self.build_register_section(regs),
                "",
                f"{Colors.CYAN}{Colors.BOLD}Memory Window{Colors.RESET}",
                *self.build_memory_section(
                    self.memory_panel_start, min(16, self.memory_window_size)
                ),
            ]
            right = [
                f"{Colors.CYAN}{Colors.BOLD}Stack View{Colors.RESET}",
                *self.build_stack_section(regs, min(8, self.stack_preview_depth)),
            ]
            lines.extend(self.combine_columns(left, right))
        else:
            lines.append(f"{Colors.YELLOW}Unknown panel '{mode}'{Colors.RESET}")

        return [line for line in lines if line is not None]

    def print_command_hint(self):
        hint = "[view next/prev/registers/memory/stack/all]  [load/save/run]  [decimal|hex]  [quit]"
        print(f"{Colors.DIM}{hint}{Colors.RESET}")

    def current_panel_mode(self):
        if not self.panel_modes:
            return None
        return self.panel_modes[self.current_panel_idx % len(self.panel_modes)]

    def cmd_view(self, args):
        """Cycle through structured data panels."""
        if not args:
            self.current_panel_idx = (self.current_panel_idx + 1) % len(
                self.panel_modes
            )
            mode = self.current_panel_mode()
            self.append_log(f"{Colors.CYAN}View → {mode.upper()}{Colors.RESET}")
            return

        token = args[0].lower()
        if token in {"next", "n"}:
            self.current_panel_idx = (self.current_panel_idx + 1) % len(
                self.panel_modes
            )
        elif token in {"prev", "p"}:
            self.current_panel_idx = (self.current_panel_idx - 1) % len(
                self.panel_modes
            )
        elif token in self.panel_modes:
            self.current_panel_idx = self.panel_modes.index(token)
        else:
            valid_modes = ", ".join(self.panel_modes)
            self.append_log(
                f"{Colors.YELLOW}Unknown view '{token}'. Valid: {valid_modes}{Colors.RESET}"
            )
            return

        mode = self.current_panel_mode()
        if mode == "memory" and len(args) > 1:
            try:
                addr = parse_address_value(args[1])
                self.memory_panel_start = addr & 0xFFFF
            except ValueError as exc:
                self.append_log(f"{Colors.RED}✗ Error:{Colors.RESET} {exc}")
                return
        if mode == "stack" and len(args) > 1:
            try:
                depth = int(args[1])
                if depth < 1 or depth > 64:
                    self.append_log(
                        f"{Colors.YELLOW}Stack depth must be 1-64{Colors.RESET}"
                    )
                    return
                self.stack_preview_depth = depth
            except ValueError:
                self.append_log(
                    f"{Colors.YELLOW}Stack depth must be numeric{Colors.RESET}"
                )
                return

        self.append_log(f"{Colors.CYAN}View → {mode.upper()}{Colors.RESET}")

    def iter_session_instructions(self):
        for line in self.session_lines:
            stripped = line.strip()
            if not stripped or stripped.startswith(";"):
                continue
            yield line

    def build_session_source(self):
        if not self.session_lines:
            return []
        pattern = re.compile(r"^\s*(?:[A-Za-z_]\w*\s*:)?\s*ORG\b", re.IGNORECASE)
        has_org = any(
            pattern.match(line) for line in self.session_lines if line.strip()
        )
        source = []
        if not has_org:
            source.append(f"ORG {self.base_address:04X}H")
        source.extend(self.session_lines)
        return source

    def assemble_session(self):
        source = self.build_session_source()
        if not source:
            return None, "No instructions in session"
        asm_obj = assembler()
        success, error = asm_obj.assemble(source)
        if not success:
            return None, error or "Assembly failed"
        return asm_obj, None

    def execute_instruction(self, line):
        """Execute a single assembly instruction immediately."""
        line = line.strip()
        if not line or line.startswith(";"):
            return

        original_line = line
        canonical_line = self.convert_to_hex(line)
        before_state = self.save_state()
        before_regs = self.get_register_snapshot()

        try:
            asm_lines = [f"ORG {self.base_address:04X}H", canonical_line, "HLT"]
            asm_obj = assembler()
            success, error = asm_obj.assemble(asm_lines)
            if not success:
                error_msg = error if error else "Assembly failed"
                print(f"{Colors.RED}✗ Error:{Colors.RESET} {error_msg}")
                return

            pc = self.base_address
            instr, size = disassemble_instruction(asm_obj.pmemory, pc)
            cycles = get_instruction_cycles(asm_obj.pmemory, pc)

            for i in range(size):
                self.cpu.memory[self.current_addr + i].value = asm_obj.pmemory[pc + i]

            self.cpu.PC.value = self.current_addr
            self.cpu.runcrntins()

            self.instruction_count += 1
            self.total_cycles += cycles
            entry = {"display": original_line, "canonical": canonical_line}
            self.history.append(entry)
            self.session_lines.append(canonical_line)
            # Fix: Save cycles in undo stack
            self.undo_stack.append(
                {"entry": entry, "state": before_state, "cycles": cycles}
            )
            self.current_addr = self.cpu.PC.value
            self.unsaved_changes = True

            print(f"{Colors.GREEN}✓{Colors.RESET} {Colors.BOLD}{instr}{Colors.RESET}")
            self.display_state(before=before_regs, cycles=cycles)

        except Exception as exc:
            print(f"{Colors.RED}✗ Error:{Colors.RESET} {exc}")

    def cmd_show(self, args):
        """Show CPU state."""
        current = self.get_register_snapshot()
        if not args:
            print(f"\n{Colors.CYAN}Registers:{Colors.RESET}")
            print(
                f"  A={current['A']:02X}  B={current['B']:02X}  C={current['C']:02X}  D={current['D']:02X}"
            )
            print(
                f"  E={current['E']:02X}  H={current['H']:02X}  L={current['L']:02X}  SP={current['SP']:04X}"
            )
            print(f"\n{Colors.CYAN}Flags:{Colors.RESET}")
            flags = decode_flags(current["FLAGS"])
            print(
                f"  S={flags['S']} Z={flags['Z']} AC={flags['AC']} P={flags['P']} CY={flags['CY']}"
            )
            print(f"\n{Colors.CYAN}Stats:{Colors.RESET}")
            print(f"  Instructions: {self.instruction_count}")
            print(f"  Total Cycles: {self.total_cycles}")
            return

        target = args[0].upper()
        if target in ["A", "B", "C", "D", "E", "H", "L"]:
            print(f"  {target} = {current[target]:02X}H ({current[target]})")
        elif target in ["SP", "PC"]:
            val = current[target]
            print(f"  {target} = {val:04X}H ({val})")
        elif target == "FLAGS":
            flags = decode_flags(current["FLAGS"])
            print(
                f"  S={flags['S']} Z={flags['Z']} AC={flags['AC']} P={flags['P']} CY={flags['CY']}"
            )
        else:
            print(
                f"{Colors.YELLOW}Unknown register '{target}'. Valid: A-H, L, SP, PC, FLAGS{Colors.RESET}"
            )

    def cmd_reset(self):
        """Reset CPU state but keep the current session."""
        self.reset_cpu_state()
        self.undo_stack = []
        print(f"{Colors.GREEN}✓{Colors.RESET} CPU reset (session preserved)")

    def cmd_clear(self):
        """Clear the session and reset everything."""
        self.session_lines = []
        self.history = []
        self.undo_stack = []
        self.reset_cpu_state()
        print(f"{Colors.GREEN}✓{Colors.RESET} Session cleared")

    def cmd_undo(self):
        """Undo last instruction."""
        if not self.undo_stack:
            print(f"{Colors.YELLOW}Nothing to undo{Colors.RESET}")
            return

        entry = self.undo_stack.pop()
        if self.history:
            self.history.pop()
        if self.session_lines:
            self.session_lines.pop()

        prev_state = entry["state"]
        self.restore_state(prev_state)
        self.instruction_count = max(0, self.instruction_count - 1)
        # Fix: Restore cycles from saved state
        cycles_undone = entry.get("cycles", 0)
        self.total_cycles = max(0, self.total_cycles - cycles_undone)
        self.unsaved_changes = True
        print(f"{Colors.GREEN}✓{Colors.RESET} Undone: {entry['entry']['display']}")

    def cmd_history(self):
        """Show instruction history."""
        if not self.history:
            print(f"{Colors.DIM}No history yet{Colors.RESET}")
            return

        print(f"\n{Colors.CYAN}History:{Colors.RESET}")
        for idx, entry in enumerate(self.history, 1):
            text = entry["display"] or entry["canonical"]
            print(f"  {Colors.DIM}{idx:3d}{Colors.RESET}  {text}")

    def cmd_decimal(self):
        """Switch to decimal mode."""
        self.decimal_mode = True
        print(
            f"{Colors.GREEN}✓{Colors.RESET} Decimal mode ON - numbers interpreted as decimal"
        )
        print(f"  {Colors.DIM}Example: MVI A, 55  →  A = 55 (decimal){Colors.RESET}")

    def cmd_hex(self):
        """Switch to hex mode."""
        self.decimal_mode = False
        print(
            f"{Colors.GREEN}✓{Colors.RESET} Hex mode ON - numbers interpreted as hexadecimal"
        )
        print(
            f"  {Colors.DIM}Example: MVI A, 55  →  A = 55H (85 decimal){Colors.RESET}"
        )

    def cmd_load(self, args):
        """Load instructions from a file without running."""
        if not args:
            print(f"{Colors.YELLOW}Usage:{Colors.RESET} load <file.asm>")
            return
        path = args[0]
        if not os.path.exists(path):
            print(f"{Colors.RED}✗ Error:{Colors.RESET} File '{path}' not found")
            return
        try:
            with open(path) as f:
                lines = [line.rstrip("\n") for line in f]
        except OSError as exc:
            print(f"{Colors.RED}✗ Error:{Colors.RESET} {exc}")
            return

        previous_session = list(self.session_lines)
        self.session_lines = lines
        asm_obj, error = self.assemble_session()
        if not asm_obj:
            print(f"{Colors.RED}✗ Error:{Colors.RESET} {error}")
            self.session_lines = previous_session
            return

        self.history = []
        self.undo_stack = []
        self.reset_cpu_state()
        self.current_addr = asm_obj.ploadoff + asm_obj.cprogmemoff
        count = sum(1 for _ in self.iter_session_instructions())
        print(f"{Colors.GREEN}✓{Colors.RESET} Loaded {count} instructions from {path}")

    def cmd_save(self, args):
        """Save current session to disk."""
        if not args:
            print(f"{Colors.YELLOW}Usage:{Colors.RESET} save <file.asm>")
            return
        if not self.session_lines:
            print(f"{Colors.YELLOW}Nothing to save{Colors.RESET}")
            return
        path = args[0]
        try:
            with open(path, "w") as f:
                for line in self.session_lines:
                    f.write(f"{line}\n")
        except OSError as exc:
            print(f"{Colors.RED}✗ Error:{Colors.RESET} {exc}")
            return
        self.unsaved_changes = False  # Mark as saved
        print(f"{Colors.GREEN}✓{Colors.RESET} Saved session to {path}")

    def execute_program(self, cpu):
        """Run CPU until halt or step limit."""
        steps = 0
        cycles = 0
        while steps < self.max_run_steps:
            if cpu.haulted:
                break
            pc = cpu.PC.value
            cycles += get_instruction_cycles(cpu.memory, pc)
            cpu.runcrntins()
            steps += 1
        return steps, cycles

    def update_history_from_session(self, force=False):
        session_instr = list(self.iter_session_instructions())
        if not force and len(self.history) == len(session_instr):
            return
        self.history = [{"display": line, "canonical": line} for line in session_instr]

    def cmd_run(self):
        """Assemble the full session and execute it."""
        asm_obj, error = self.assemble_session()
        if not asm_obj:
            print(f"{Colors.RED}✗ Error:{Colors.RESET} {error}")
            return
        if asm_obj.cprogmemoff == 0:
            print(
                f"{Colors.YELLOW}Nothing to run — add some instructions first{Colors.RESET}"
            )
            return
        cpu = emu8085()
        for offset in range(asm_obj.cprogmemoff):
            cpu.memory[asm_obj.ploadoff + offset].value = asm_obj.pmemory[
                asm_obj.ploadoff + offset
            ]
        cpu.PC.value = asm_obj.ploadoff

        steps, cycles = self.execute_program(cpu)
        self.cpu = cpu
        self.undo_stack = []
        self.instruction_count = steps
        self.total_cycles = cycles
        # Fix: Sync current_addr with actual PC value after execution
        self.current_addr = self.cpu.PC.value
        self.update_history_from_session(force=not self.history)

        if cpu.haulted:
            print(
                f"{Colors.GREEN}✓{Colors.RESET} Executed {steps} instructions, {cycles} T-states"
            )
        else:
            print(
                f"{Colors.YELLOW}!{Colors.RESET} Stopped after {steps} instructions "
                f"(step limit {self.max_run_steps}). Add HLT or use shorter runs."
            )

    def cmd_labels(self):
        """List labels from the current session."""
        asm_obj, error = self.assemble_session()
        if not asm_obj:
            print(f"{Colors.RED}✗ Error:{Colors.RESET} {error}")
            return
        labels = getattr(asm_obj, "labeloff", {})
        if not labels:
            print(f"{Colors.DIM}No labels defined{Colors.RESET}")
            return
        print(f"\n{Colors.CYAN}Labels:{Colors.RESET}")
        for name, addr in sorted(labels.items(), key=lambda item: item[1]):
            print(f"  {name:<12} = {addr:04X}H")

    def format_memory_row(self, addr, values):
        bytes_str = " ".join(f"{b:02X}" for b in values)
        ascii_str = "".join(chr(b) if 32 <= b <= 126 else "." for b in values)
        bytes_str = bytes_str.ljust(3 * len(values) - 1)
        return f"{addr:04X}: {bytes_str}  {Colors.DIM}{ascii_str}{Colors.RESET}"

    def cmd_memory(self, args):
        """Dump memory range."""

        def parse_value(token):
            return parse_address_value(token)

        if not args:
            start = self.base_address
            end = start + 0x10 - 1
        elif len(args) == 1 and "-" in args[0]:
            start_token, end_token = args[0].split("-", 1)
            start = parse_value(start_token)
            end = parse_value(end_token)
        elif len(args) == 1:
            start = parse_value(args[0])
            end = start + 0x10 - 1
        else:
            start = parse_value(args[0])
            if args[1].startswith("+"):
                length = parse_value(args[1][1:])
                end = start + max(0, length - 1)
            else:
                end = parse_value(args[1])

        start &= 0xFFFF
        end &= 0xFFFF
        if end < start:
            start, end = end, start
        if end - start > REPL_MEMORY_DUMP_LIMIT:
            print(
                f"{Colors.YELLOW}Range too large; showing {REPL_MEMORY_DUMP_LIMIT} bytes max{Colors.RESET}"
            )
            end = start + REPL_MEMORY_DUMP_LIMIT - 1

        print(f"\n{Colors.CYAN}Memory {start:04X}H-{end:04X}H:{Colors.RESET}")
        addr = start
        while addr <= end:
            chunk = []
            for _ in range(min(8, end - addr + 1)):
                chunk.append(self.cpu.memory[addr].value)
                addr += 1
            print(self.format_memory_row(addr - len(chunk), chunk))

    def cmd_set(self, args):
        """Set register or memory value."""
        if len(args) < 2:
            print(f"{Colors.YELLOW}Usage:{Colors.RESET} set <register|[addr]> <value>")
            print("  Examples: set A 42, set [0x0800] FF, set SP 1000")
            return

        target = args[0].upper()
        try:
            value = parse_address_value(args[1])
        except ValueError as exc:
            print(f"{Colors.RED}✗ Error:{Colors.RESET} Invalid value: {exc}")
            return

        # Memory modification
        if target.startswith("[") and target.endswith("]"):
            try:
                addr = parse_address_value(target[1:-1])
                self.cpu.memory[addr & 0xFFFF].value = value & 0xFF
                print(f"{Colors.GREEN}✓{Colors.RESET} [{addr:04X}H] = {value:02X}H")
                self.unsaved_changes = True
                return
            except ValueError as exc:
                print(f"{Colors.RED}✗ Error:{Colors.RESET} {exc}")
                return

        # Register modification
        if target in ["A", "B", "C", "D", "E", "H", "L"]:
            reg = getattr(self.cpu, target)
            reg.value = value & 0xFF
            print(f"{Colors.GREEN}✓{Colors.RESET} {target} = {value:02X}H ({value})")
            self.unsaved_changes = True
        elif target in ["SP", "PC"]:
            reg = getattr(self.cpu, target)
            reg.value = value & 0xFFFF
            if target == "PC":
                self.current_addr = value & 0xFFFF
            print(f"{Colors.GREEN}✓{Colors.RESET} {target} = {value:04X}H ({value})")
            self.unsaved_changes = True
        else:
            print(f"{Colors.RED}✗ Error:{Colors.RESET} Unknown target '{target}'")

    def cmd_break(self, args):
        """Manage breakpoints."""
        if not args:
            # List breakpoints
            if not self.breakpoints:
                print(f"{Colors.DIM}No breakpoints set{Colors.RESET}")
                return
            print(f"\n{Colors.CYAN}Breakpoints:{Colors.RESET}")
            for addr in sorted(self.breakpoints):
                print(f"  {addr:04X}H")
            return

        action = args[0].lower()
        if action == "clear":
            self.breakpoints.clear()
            print(f"{Colors.GREEN}✓{Colors.RESET} All breakpoints cleared")
            return

        # Set breakpoint
        try:
            addr = parse_address_value(args[0])
            self.breakpoints.add(addr & 0xFFFF)
            print(f"{Colors.GREEN}✓{Colors.RESET} Breakpoint set at {addr:04X}H")
        except ValueError as exc:
            print(f"{Colors.RED}✗ Error:{Colors.RESET} {exc}")

    def cmd_step(self, args):
        """Step through session instructions one at a time."""
        if not self.session_lines:
            print(
                f"{Colors.YELLOW}No session to step through. Add instructions first.{Colors.RESET}"
            )
            return

        # Count how many steps to execute
        count = 1
        if args:
            try:
                count = int(args[0])
                if count < 1:
                    print(
                        f"{Colors.RED}✗ Error:{Colors.RESET} Step count must be positive"
                    )
                    return
            except ValueError:
                print(f"{Colors.RED}✗ Error:{Colors.RESET} Invalid step count")
                return

        # Execute session to get assembled program
        asm_obj, error = self.assemble_session()
        if not asm_obj:
            print(f"{Colors.RED}✗ Error:{Colors.RESET} {error}")
            return

        # Initialize CPU if needed
        if self.instruction_count == 0:
            self.cpu = emu8085()
            for offset in range(asm_obj.cprogmemoff):
                self.cpu.memory[asm_obj.ploadoff + offset].value = asm_obj.pmemory[
                    asm_obj.ploadoff + offset
                ]
            self.cpu.PC.value = asm_obj.ploadoff

        # Step through instructions
        for _ in range(count):
            if self.cpu.haulted:
                print(f"{Colors.YELLOW}Program halted{Colors.RESET}")
                break

            pc = self.cpu.PC.value
            if pc in self.breakpoints:
                print(f"{Colors.YELLOW}Breakpoint at {pc:04X}H{Colors.RESET}")
                break

            before_regs = self.get_register_snapshot()
            instr, _ = disassemble_instruction(self.cpu.memory, pc)
            cycles = get_instruction_cycles(self.cpu.memory, pc)

            self.cpu.runcrntins()
            self.instruction_count += 1
            self.total_cycles += cycles

            after_regs = self.get_register_snapshot()
            print(f"{Colors.CYAN}{pc:04X}{Colors.RESET}  {instr:<20}")
            self.display_state(before=before_regs, cycles=cycles)

    def cmd_disasm(self, args):
        """Disassemble memory or session."""
        if not args:
            # Disassemble current session
            asm_obj, error = self.assemble_session()
            if not asm_obj:
                print(f"{Colors.RED}✗ Error:{Colors.RESET} {error}")
                return

            print(f"\n{Colors.CYAN}Session Disassembly:{Colors.RESET}\n")
            addr = asm_obj.ploadoff
            end = addr + asm_obj.cprogmemoff
            while addr < end:
                instr, size = disassemble_instruction(asm_obj.pmemory, addr)
                cycles = get_instruction_cycles(asm_obj.pmemory, addr)
                print(
                    f"{addr:04X}:  {instr:<20}  {Colors.DIM}[{cycles}T]{Colors.RESET}"
                )
                addr += size
            return

        # Disassemble memory range
        try:
            start = parse_address_value(args[0])
            count = 10
            if len(args) > 1:
                count = int(args[1])

            print(f"\n{Colors.CYAN}Memory Disassembly:{Colors.RESET}\n")
            addr = start & 0xFFFF
            for _ in range(count):
                try:
                    instr, size = disassemble_instruction(self.cpu.memory, addr)
                    cycles = get_instruction_cycles(self.cpu.memory, addr)
                    print(
                        f"{addr:04X}:  {instr:<20}  {Colors.DIM}[{cycles}T]{Colors.RESET}"
                    )
                    addr = (addr + size) & 0xFFFF
                except Exception:
                    break
        except ValueError as exc:
            print(f"{Colors.RED}✗ Error:{Colors.RESET} {exc}")

    def cmd_search(self, args):
        """Search memory for byte pattern."""
        if not args:
            print(f"{Colors.YELLOW}Usage:{Colors.RESET} search <pattern> [start] [end]")
            print('  Example: search "48 65 6C 6C 6F" 0800 0900')
            return

        # Parse pattern
        pattern_str = " ".join(args[0].split())
        try:
            pattern = [int(b, 16) for b in pattern_str.split()]
        except ValueError:
            print(f"{Colors.RED}✗ Error:{Colors.RESET} Invalid hex pattern")
            return

        start = REPL_DEFAULT_BASE_ADDRESS
        end = 0xFFFF
        if len(args) > 1:
            try:
                start = parse_address_value(args[1])
            except ValueError as exc:
                print(f"{Colors.RED}✗ Error:{Colors.RESET} {exc}")
                return
        if len(args) > 2:
            try:
                end = parse_address_value(args[2])
            except ValueError as exc:
                print(f"{Colors.RED}✗ Error:{Colors.RESET} {exc}")
                return

        # Search
        matches = []
        addr = start & 0xFFFF
        while addr <= (end & 0xFFFF) - len(pattern) + 1:
            match = True
            for i, byte_val in enumerate(pattern):
                if self.cpu.memory[(addr + i) & 0xFFFF].value != byte_val:
                    match = False
                    break
            if match:
                matches.append(addr)
            addr += 1

        if matches:
            print(f"\n{Colors.CYAN}Found {len(matches)} match(es):{Colors.RESET}")
            for addr in matches[:20]:  # Limit to 20 matches
                print(f"  {addr:04X}H")
            if len(matches) > 20:
                print(f"  {Colors.DIM}... and {len(matches) - 20} more{Colors.RESET}")
        else:
            print(f"{Colors.YELLOW}Pattern not found{Colors.RESET}")

    def cmd_calc(self, args):
        """Evaluate arithmetic expression."""
        if not args:
            print(f"{Colors.YELLOW}Usage:{Colors.RESET} calc <expression>")
            print("  Examples: calc 0x800 + 16, calc FF & 0F, calc 100 << 2")
            return

        expr = " ".join(args)
        # Replace hex notation
        expr = re.sub(r"\b([0-9A-Fa-f]+)H\b", r"0x\1", expr)

        try:
            # Safe eval with limited globals
            result = eval(expr, {"__builtins__": {}}, {})
            if isinstance(result, (int, float)):
                if isinstance(result, int):
                    print(
                        f"  = {result:04X}H  ({result} decimal)  (0b{result:b} binary)"
                    )
                else:
                    print(f"  = {result}")
            else:
                print(f"  = {result}")
        except Exception as exc:
            print(f"{Colors.RED}✗ Error:{Colors.RESET} {exc}")

    def cmd_help(self):
        """Show help."""
        mode = (
            f"{Colors.YELLOW}DECIMAL{Colors.RESET}"
            if self.decimal_mode
            else f"{Colors.CYAN}HEX{Colors.RESET}"
        )
        print(f"""
{Colors.BOLD}8085 Interactive REPL{Colors.RESET} [Mode: {mode}]

{Colors.CYAN}Assembly Instructions:{Colors.RESET}
  Type any 8085 instruction and it executes immediately.

{Colors.CYAN}Session Commands:{Colors.RESET}
  show [reg]       Show registers/flags/statistics
  set <reg> <val>  Set register or memory ([addr]) value
  history          List executed instructions
  undo             Undo last instruction
  view [mode]      Cycle data panels (next/prev/registers/memory/stack/all)
  step [n]         Step through n session instructions (default: 1)
  run              Assemble entire session and execute from scratch
  load FILE        Load instructions from FILE
  save FILE        Save current session to FILE
  labels           List labels resolved in the session
  memory [..]      Dump memory (memory 0800 0810, memory 0800 +32)
  break [addr]     Set/list breakpoints, 'break clear' to remove all
  disasm [addr] [n] Disassemble session or memory range
  search <pattern> [start] [end]  Search memory for hex byte pattern
  calc <expr>      Evaluate arithmetic expression
  decimal / hex    Switch number interpretation mode
  help             Show this help
  quit / exit      Leave the REPL (quit! to force)

{Colors.CYAN}Examples:{Colors.RESET}
  MVI A, 55        Execute instruction immediately
  :set A 42        Set register A to 42H
  :set [0800] FF   Set memory at 0800H to FFH
  :break 0805      Set breakpoint at address 0805H
  :step 5          Step through 5 instructions
  :search "48 65"  Search for bytes 48 65 in memory
  :calc 0x800 + 16 Calculate 0x800 + 16
""")

    def confirm_quit(self):
        """Ask for confirmation if there are unsaved changes."""
        if not self.unsaved_changes or not self.session_lines:
            return True
        self.append_log(
            f"{Colors.YELLOW}You have unsaved changes. Type ':quit!' to force quit, or ':save <file>' first.{Colors.RESET}"
        )
        return False

    def run_command(self, cmd, args, raw_line):
        """Execute REPL commands entered via command mode."""
        # Apply command aliases
        cmd = self.command_aliases.get(cmd, cmd)

        try:
            if cmd in {"quit", "exit"}:
                if self.confirm_quit():
                    self.append_log(f"{Colors.DIM}Goodbye!{Colors.RESET}")
                    return True
                return False
            elif cmd in {"quit!", "exit!"}:
                self.append_log(f"{Colors.DIM}Goodbye!{Colors.RESET}")
                return True
            elif cmd == "help":
                self.capture_output(self.cmd_help)
            elif cmd == "show":
                self.capture_output(lambda: self.cmd_show(args))
            elif cmd == "set":
                self.capture_output(lambda: self.cmd_set(args))
            elif cmd == "reset":
                self.capture_output(self.cmd_reset)
            elif cmd == "undo":
                self.capture_output(self.cmd_undo)
            elif cmd in {"history", "hist"}:
                self.capture_output(self.cmd_history)
            elif cmd in {"decimal", "dec"}:
                self.capture_output(self.cmd_decimal)
            elif cmd == "hex":
                self.capture_output(self.cmd_hex)
            elif cmd in {"view", "panel", "table"}:
                self.cmd_view(args)
            elif cmd == "load":
                self.capture_output(lambda: self.cmd_load(args))
            elif cmd == "save":
                self.capture_output(lambda: self.cmd_save(args))
            elif cmd in {"run", "continue"}:
                self.capture_output(self.cmd_run)
            elif cmd == "step":
                self.capture_output(lambda: self.cmd_step(args))
            elif cmd == "labels":
                self.capture_output(self.cmd_labels)
            elif cmd == "memory":
                self.capture_output(lambda: self.cmd_memory(args))
            elif cmd in {"break", "breakpoint", "bp"}:
                self.capture_output(lambda: self.cmd_break(args))
            elif cmd in {"disasm", "disassemble", "dis"}:
                self.capture_output(lambda: self.cmd_disasm(args))
            elif cmd in {"search", "find"}:
                self.capture_output(lambda: self.cmd_search(args))
            elif cmd in {"calc", "eval"}:
                self.capture_output(lambda: self.cmd_calc(args))
            elif cmd == "clear":
                self.capture_output(self.cmd_clear)
            else:
                self.append_log(f"{Colors.YELLOW}Unknown command '{cmd}'{Colors.RESET}")
        except SystemExit:
            return True
        return False

    def run(self):
        """Main REPL loop with split output UI."""
        self.append_log(f"{Colors.BOLD}Type 'help' for commands.{Colors.RESET}")
        self.setup_readline()

        self.enter_alt_screen()

        try:
            while True:
                try:
                    self.render_ui()
                    # Add mode indicator to prompt
                    mode_indicator = (
                        f"{Colors.YELLOW}DEC{Colors.RESET}"
                        if self.decimal_mode
                        else f"{Colors.CYAN}HEX{Colors.RESET}"
                    )
                    prompt = f"{Colors.BLUE}8085{Colors.RESET}[{mode_indicator}]> "
                    raw_line = input(prompt)
                    if raw_line.startswith("\x1b["):
                        continue
                    if raw_line == "\x1b":
                        continue
                    line = raw_line.strip()
                    if line == ":":
                        self.print_command_hint()
                        cmd_prompt = (
                            f"{Colors.BLUE}8085> {Colors.YELLOW}:{Colors.RESET} "
                        )
                        try:
                            line = input(cmd_prompt).strip()
                        except KeyboardInterrupt:
                            self.append_log(
                                f"{Colors.DIM}Command mode cancelled{Colors.RESET}"
                            )
                            continue  # Fix: was break, should continue
                        except EOFError:
                            self.append_log(f"{Colors.DIM}Goodbye!{Colors.RESET}")
                            break
                        if not line:
                            self.append_log(
                                f"{Colors.DIM}Command mode cancelled{Colors.RESET}"
                            )
                            continue
                        line = ":" + line
                except KeyboardInterrupt:
                    self.append_log(
                        f"{Colors.DIM}Ctrl+C pressed — exiting{Colors.RESET}"
                    )
                    break
                except EOFError:
                    self.append_log(f"{Colors.DIM}Goodbye!{Colors.RESET}")
                    break

                if not line:
                    continue

                if line.startswith(":"):
                    display_text = line
                    self.append_log(f"{Colors.DIM}› {display_text}{Colors.RESET}")
                    parts = line[1:].strip().split()
                    if not parts:
                        self.append_log(
                            f"{Colors.DIM}Command mode cancelled{Colors.RESET}"
                        )
                        continue
                    cmd = parts[0].lower()
                    args = parts[1:]
                    should_quit = self.run_command(cmd, args, display_text)
                    if should_quit:
                        break
                    continue

                self.append_log(f"{Colors.DIM}› {line}{Colors.RESET}")
                self.add_history_entry(line)
                self.capture_output(lambda: self.execute_instruction(line))
        finally:
            self.exit_alt_screen()
