"""Interactive debugger helpers."""

import shlex

from ...shared.colors import Colors
from ...shared.disasm import disassemble_instruction, get_instruction_cycles
from ...shared.executor import ProgramExecutor, resolve_step_limit
from ...shared.parsing import parse_address_value
from ...shared.registers import (
    decode_flags,
    format_flags,
    format_register_summary,
    snapshot_registers,
)


class InteractiveDebugger:
    """Full-featured step-by-step debugger for 8085 programs with reverse execution."""

    def __init__(self, filename, args):
        self.args = args
        self.executor = ProgramExecutor(filename, args)
        self.breakpoints = set()
        self.watchpoints = {}  # addr -> last value
        self.step_limit, self.has_limit = resolve_step_limit(args)
        self.execution_history = []  # Stack of execution states for reverse stepping
        self.execution_trace = []  # Trace of executed instructions for display
        self.max_history = 1000  # Maximum history entries to keep
        self.max_trace = 4  # Keep last 4 executed instructions for display
        self.show_context = True  # Show upcoming instructions
        self.context_lines = 4  # Number of upcoming instructions to show
        self.auto_display = True  # Automatically show state after each command

    def save_state_to_history(self):
        """Save current CPU state to execution history for reverse stepping."""
        state = {
            "registers": {
                "A": self.executor.cpu.A.value,
                "B": self.executor.cpu.B.value,
                "C": self.executor.cpu.C.value,
                "D": self.executor.cpu.D.value,
                "E": self.executor.cpu.E.value,
                "H": self.executor.cpu.H.value,
                "L": self.executor.cpu.L.value,
                "SP": self.executor.cpu.SP.value,
                "PC": self.executor.cpu.PC.value,
                "F": self.executor.cpu.F.value,
            },
            "memory_snapshot": {},  # Only store changed memory for efficiency
            "cycles": self.executor.total_cycles,
            "steps": self.executor.steps_executed,
        }

        # Save only non-zero or changed memory regions (efficient)
        for addr in range(0x10000):
            val = self.executor.cpu.memory[addr].value
            if val != 0 or val != self.executor.initial_memory[addr]:
                state["memory_snapshot"][addr] = val

        self.execution_history.append(state)

        # Limit history size
        if len(self.execution_history) > self.max_history:
            self.execution_history.pop(0)

    def restore_state_from_history(self):
        """Restore CPU state from execution history (reverse step)."""
        if not self.execution_history:
            return False

        state = self.execution_history.pop()

        # Restore registers
        self.executor.cpu.A.value = state["registers"]["A"]
        self.executor.cpu.B.value = state["registers"]["B"]
        self.executor.cpu.C.value = state["registers"]["C"]
        self.executor.cpu.D.value = state["registers"]["D"]
        self.executor.cpu.E.value = state["registers"]["E"]
        self.executor.cpu.H.value = state["registers"]["H"]
        self.executor.cpu.L.value = state["registers"]["L"]
        self.executor.cpu.SP.value = state["registers"]["SP"]
        self.executor.cpu.PC.value = state["registers"]["PC"]
        self.executor.cpu.F.value = state["registers"]["F"]

        # Restore memory from snapshot
        for addr, val in state["memory_snapshot"].items():
            self.executor.cpu.memory[addr].value = val

        # Restore counters
        self.executor.total_cycles = state["cycles"]
        self.executor.steps_executed = state["steps"]

        # Mark CPU as not halted (in case we stepped back from HLT)
        self.executor.cpu.haulted = False

        return True

    def show_instruction_context(self):
        """Show execution history (last 4) and upcoming instructions (next 4) in table format."""
        pc = self.executor.cpu.PC.value
        regs = snapshot_registers(self.executor.cpu)
        flags = decode_flags(regs["FLAGS"])

        print(
            f"\n{Colors.BLUE}{Colors.BOLD}{'PC':<8} {'Instruction':<20} {'A':<4} {'B':<4} {'C':<4} {'D':<4} {'E':<4} {'H':<4} {'L':<4} {'SP':<6} {'Flags':<10} [T]{Colors.RESET}"
        )
        print(f"{Colors.DIM}{'─' * 87}{Colors.RESET}")

        # Show last 4 executed instructions from trace
        trace_start = max(0, len(self.execution_trace) - self.max_trace)
        prev_regs = None

        for i in range(trace_start, len(self.execution_trace)):
            entry = self.execution_trace[i]
            addr = entry["pc"]
            instr = entry["instr"]
            cycles = entry["cycles"]
            r = entry["regs"]
            f = decode_flags(r["FLAGS"])
            flags_str = f"{'S' if f['S'] else '-'}{'Z' if f['Z'] else '-'}{'A' if f['AC'] else '-'}{'P' if f['P'] else '-'}{'C' if f['CY'] else '-'}"

            # Build line with individual register highlighting - use consistent spacing
            parts = []
            parts.append(f"{Colors.DIM}  {addr:04X}H")
            parts.append(f"{instr:<20}")

            # Compare each register with previous and highlight if changed
            for reg_name in ["A", "B", "C", "D", "E", "H", "L"]:
                val = r[reg_name]
                if prev_regs and prev_regs[reg_name] != val:
                    parts.append(
                        f"{Colors.RESET}{Colors.HIGHLIGHT}{val:02X}H{Colors.RESET}{Colors.DIM}"
                    )
                else:
                    parts.append(f"{val:02X}H")

            # SP handling
            if prev_regs and prev_regs["SP"] != r["SP"]:
                parts.append(
                    f"{Colors.RESET}{Colors.HIGHLIGHT}{r['SP']:04X}H{Colors.RESET}{Colors.DIM}"
                )
            else:
                parts.append(f"{r['SP']:04X}H")

            # Flags handling
            if prev_regs and prev_regs["FLAGS"] != r["FLAGS"]:
                parts.append(
                    f"{Colors.RESET}{Colors.HIGHLIGHT}{flags_str:<10}{Colors.RESET}{Colors.DIM}"
                )
            else:
                parts.append(f"{flags_str:<10}")

            parts.append(f"{cycles}{Colors.RESET}")
            print("  ".join(parts))
            prev_regs = r.copy()

        # Show current instruction (highlighted row marker, but individual register colors)
        try:
            curr_instr, size = disassemble_instruction(self.executor.cpu.memory, pc)
            curr_cycles = get_instruction_cycles(self.executor.cpu.memory, pc)
            flags_str = f"{'S' if flags['S'] else '-'}{'Z' if flags['Z'] else '-'}{'A' if flags['AC'] else '-'}{'P' if flags['P'] else '-'}{'C' if flags['CY'] else '-'}"

            parts = []
            parts.append(f"{Colors.CYAN}→ {pc:04X}H{Colors.RESET}")
            parts.append(f"{Colors.BOLD}{curr_instr:<20}{Colors.RESET}")

            # Compare with last trace entry
            last_trace = self.execution_trace[-1] if self.execution_trace else None

            for reg_name in ["A", "B", "C", "D", "E", "H", "L"]:
                val = regs[reg_name]
                if last_trace and last_trace["regs"][reg_name] != val:
                    parts.append(f"{Colors.HIGHLIGHT}{val:02X}H{Colors.RESET}")
                else:
                    parts.append(f"{val:02X}H")

            # SP
            if last_trace and last_trace["regs"]["SP"] != regs["SP"]:
                parts.append(f"{Colors.HIGHLIGHT}{regs['SP']:04X}H{Colors.RESET}")
            else:
                parts.append(f"{regs['SP']:04X}H")

            # Flags
            if last_trace and last_trace["regs"]["FLAGS"] != regs["FLAGS"]:
                parts.append(f"{Colors.HIGHLIGHT}{flags_str:<10}{Colors.RESET}")
            else:
                parts.append(f"{flags_str:<10}")

            parts.append(f"{curr_cycles}")
            print("  ".join(parts))
        except:
            print(f"{Colors.CYAN}→ {pc:04X}H  <invalid>{Colors.RESET}")

        # Show next 4 upcoming instructions
        addr = pc
        try:
            _, size = disassemble_instruction(self.executor.cpu.memory, addr)
            addr = (addr + size) & 0xFFFF
        except:
            pass

        for i in range(self.context_lines):
            try:
                instr, size = disassemble_instruction(self.executor.cpu.memory, addr)
                cycles = get_instruction_cycles(self.executor.cpu.memory, addr)

                parts = [
                    f"{Colors.DIM}  {addr:04X}H",
                    f"{instr:<20}",
                    "··",
                    "··",
                    "··",
                    "··",
                    "··",
                    "··",
                    "··",
                    "····",
                    "·····",
                    f"{cycles}{Colors.RESET}",
                ]
                print("  ".join(parts))

                addr = (addr + size) & 0xFFFF
            except:
                break

        print(f"{Colors.DIM}{'─' * 87}{Colors.RESET}")

        # Show stack and memory preview
        sp = regs["SP"]
        hl = (regs["H"] << 8) | regs["L"]

        # Stack preview (4 entries)
        stack_items = []
        for i in range(4):
            addr = (sp + i) & 0xFFFF
            val = self.executor.cpu.memory[addr].value
            if i == 0:
                stack_items.append(
                    f"{Colors.HIGHLIGHT}SP→{addr:04X}:{val:02X}H{Colors.RESET}"
                )
            else:
                stack_items.append(f"{addr:04X}:{val:02X}H")

        # Memory at HL (4 bytes)
        mem_items = []
        for i in range(4):
            addr = (hl + i) & 0xFFFF
            val = self.executor.cpu.memory[addr].value
            if i == 0:
                mem_items.append(
                    f"{Colors.HIGHLIGHT}HL→{addr:04X}:{val:02X}H{Colors.RESET}"
                )
            else:
                mem_items.append(f"{addr:04X}:{val:02X}H")

        print(
            f"{Colors.CYAN}Stack:{Colors.RESET} {' '.join(stack_items)}  {Colors.CYAN}Memory:{Colors.RESET} {' '.join(mem_items)}"
        )
        print(
            f"{Colors.CYAN}Steps:{Colors.RESET} {self.executor.steps_executed}  {Colors.CYAN}Cycles:{Colors.RESET} {self.executor.total_cycles}"
        )

    def repl(self):
        print(
            f"{Colors.BLUE}{Colors.BOLD}╔═══════════════════════════════════════╗{Colors.RESET}"
        )
        print(
            f"{Colors.BLUE}{Colors.BOLD}║   8085 Interactive Step Debugger     ║{Colors.RESET}"
        )
        print(
            f"{Colors.BLUE}{Colors.BOLD}╚═══════════════════════════════════════╝{Colors.RESET}"
        )
        print(f"\n{Colors.CYAN}Program loaded:{Colors.RESET} {self.executor.filename}")
        print(
            f"{Colors.CYAN}Start address:{Colors.RESET} {self.executor.asm_obj.ploadoff:04X}H"
        )
        print(
            f"\nType {Colors.BOLD}'help'{Colors.RESET} for commands, {Colors.BOLD}'s'{Colors.RESET} to step, {Colors.BOLD}'c'{Colors.RESET} to continue, {Colors.BOLD}'q'{Colors.RESET} to quit\n"
        )

        # Show initial state
        self.show_instruction_context()

        while True:
            try:
                command = input("8085> ").strip()
            except (KeyboardInterrupt, EOFError):
                print()
                break

            if not command:
                continue

            try:
                self.handle_command(command)
            except SystemExit:
                break
            except (ValueError, KeyError, IndexError) as exc:
                print(f"{Colors.RED}Error:{Colors.RESET} {exc}")
            except Exception as exc:
                print(f"{Colors.RED}Unexpected error:{Colors.RESET} {exc}")
                print(
                    f"{Colors.DIM}Please report this issue. Stack trace:{Colors.RESET}"
                )
                import traceback

                traceback.print_exc()

    def handle_command(self, command):
        parts = shlex.split(command)
        if not parts:
            return
        cmd = parts[0].lower()
        args = parts[1:]

        if cmd in {"help", "h", "?"}:
            self.print_help()
        elif cmd in {"run", "r", "restart"}:
            self.command_restart()
        elif cmd in {"continue", "c"}:
            self.execute_until_break(skip_current_break=True)
        elif cmd in {"step", "s"}:
            self.command_step()
        elif cmd in {"back", "reverse", "undo", "u"}:
            self.command_back()
        elif cmd in {"next", "n"}:
            self.command_next()
        elif cmd in {"break", "b"}:
            self.command_break(args)
        elif cmd in {"delete", "del"}:
            self.command_delete(args)
        elif cmd == "print" or cmd == "p":
            self.command_print(args)
        elif cmd in {"dump", "x"}:
            self.command_dump(args)
        elif cmd in {"watch", "w"}:
            self.command_watch(args)
        elif cmd in {"unwatch", "unw"}:
            self.command_unwatch(args)
        elif cmd == "info":
            self.command_info(args)
        elif cmd in {"list", "l"}:
            self.command_list(args)
        elif cmd in {"disasm", "disassemble"}:
            self.command_disasm(args)
        elif cmd == "set":
            self.command_set(args)
        elif cmd in {"where", "bt", "backtrace"}:
            self.command_where()
        elif cmd == "history":
            self.command_history()
        elif cmd in {"quit", "exit", "q"}:
            raise SystemExit
        else:
            print(f"Unknown command '{cmd}'. Type 'help' for a list of commands.")

    def command_step(self):
        """Execute one instruction and save state for reverse stepping."""
        if self.executor.cpu.haulted:
            print(
                f"{Colors.YELLOW}Program already halted. Use 'run' to restart.{Colors.RESET}"
            )
            return

        # Save state before executing
        self.save_state_to_history()

        # Store register state before execution
        regs_before = snapshot_registers(self.executor.cpu)

        # Execute instruction
        result = self.executor.step_instruction()

        # Add executed instruction to trace for display
        trace_entry = {
            "pc": result["pc"],
            "instr": result["instr"],
            "cycles": result["cycles"],
            "regs": result["regs"].copy(),
        }
        self.execution_trace.append(trace_entry)

        # Keep trace size limited
        if len(self.execution_trace) > self.max_trace:
            self.execution_trace.pop(0)

        # Show what changed
        regs_after = result["regs"]
        changes = []
        for reg in ["A", "B", "C", "D", "E", "H", "L"]:
            if regs_before[reg] != regs_after[reg]:
                changes.append(
                    f"{reg}: {regs_before[reg]:02X}H → {Colors.HIGHLIGHT}{regs_after[reg]:02X}H{Colors.RESET}"
                )
        if regs_before["SP"] != regs_after["SP"]:
            changes.append(
                f"SP: {regs_before['SP']:04X}H → {Colors.HIGHLIGHT}{regs_after['SP']:04X}H{Colors.RESET}"
            )

        if changes:
            print(f"\n{Colors.DIM}Changed: {', '.join(changes)}{Colors.RESET}")

        # Check watchpoints
        watchpoint_changes = self.refresh_watchpoints(report_changes=False)
        if watchpoint_changes:
            for addr, old, new in watchpoint_changes:
                print(
                    f"{Colors.YELLOW}  Watch {addr:04X}H: {old:02X}H → {new:02X}H{Colors.RESET}"
                )

        if result["halted"]:
            print(f"\n{Colors.GREEN}✓ Program halted.{Colors.RESET}")

        # Always show instruction context table
        if self.show_context:
            self.show_instruction_context()

    def command_back(self):
        """Reverse (undo) the last step."""
        if not self.execution_history:
            print(
                f"{Colors.YELLOW}No execution history. Cannot step backwards.{Colors.RESET}"
            )
            return

        if self.restore_state_from_history():
            # Remove last trace entry when going back
            if self.execution_trace:
                self.execution_trace.pop()

            print(
                f"\n{Colors.CYAN}Stepped back to:{Colors.RESET} Step {self.executor.steps_executed}, PC={self.executor.cpu.PC.value:04X}H"
            )
            if self.show_context:
                self.show_instruction_context()
        else:
            print(f"{Colors.RED}Failed to restore state{Colors.RESET}")

    def command_next(self):
        """Step over CALL instructions (execute until return or next instruction)."""
        if self.executor.cpu.haulted:
            print(f"{Colors.YELLOW}Program already halted.{Colors.RESET}")
            return

        pc = self.executor.cpu.PC.value
        opcode = self.executor.cpu.memory[pc].value

        # Check if current instruction is CALL (CD) or conditional call
        is_call = opcode in [0xCD, 0xC4, 0xCC, 0xD4, 0xDC, 0xE4, 0xEC, 0xF4, 0xFC]

        if is_call:
            # Get the address of the instruction after the CALL
            instr, size = disassemble_instruction(self.executor.cpu.memory, pc)
            next_addr = (pc + size) & 0xFFFF

            # Execute until we reach that address or hit a breakpoint
            print(f"{Colors.CYAN}Stepping over {instr}...{Colors.RESET}")
            steps_taken = 0
            while (
                not self.executor.cpu.haulted
                and self.executor.cpu.PC.value != next_addr
            ):
                self.save_state_to_history()
                result = self.executor.step_instruction()
                steps_taken += 1

                # Check breakpoints
                if self.executor.cpu.PC.value in self.breakpoints:
                    print(
                        f"{Colors.YELLOW}Breakpoint hit at {self.executor.cpu.PC.value:04X}H{Colors.RESET}"
                    )
                    break

                if steps_taken > 10000:
                    print(
                        f"{Colors.RED}Step limit reached (possible infinite loop){Colors.RESET}"
                    )
                    break

            print(f"{Colors.CYAN}Took {steps_taken} steps{Colors.RESET}")
        else:
            # Not a call, just step normally
            self.command_step()

    def command_restart(self):
        """Restart program execution from the beginning."""
        self.executor.reload_program()
        self.execution_history = []
        self.execution_trace = []
        for addr in list(self.watchpoints.keys()):
            self.watchpoints[addr] = None
        print(f"{Colors.GREEN}✓ Program restarted{Colors.RESET}")
        self.show_instruction_context()

    def command_list(self, args):
        """Show source code around current PC."""
        pc = self.executor.cpu.PC.value
        context = 5 if not args else int(args[0])

        # Find the source line for current PC
        if not hasattr(self.executor.asm_obj, "poffset"):
            print(f"{Colors.YELLOW}Source information not available{Colors.RESET}")
            return

        current_line = None
        for idx, offset in enumerate(self.executor.asm_obj.poffset):
            if offset == pc:
                current_line = idx
                break

        if current_line is None:
            print(
                f"{Colors.YELLOW}Source line not found for PC={pc:04X}H{Colors.RESET}"
            )
            return

        print(f"\n{Colors.CYAN}Source Code:{Colors.RESET}")
        start = max(0, current_line - context)
        end = min(len(self.executor.clean_lines), current_line + context + 1)

        for i in range(start, end):
            line = (
                self.executor.clean_lines[i]
                if i < len(self.executor.clean_lines)
                else ""
            )
            if i == current_line:
                print(f"{Colors.HIGHLIGHT}→ {i + 1:4d}  {line}{Colors.RESET}")
            else:
                print(f"  {Colors.DIM}{i + 1:4d}  {line}{Colors.RESET}")

    def command_disasm(self, args):
        """Disassemble memory at current PC or specified address."""
        if args:
            addr = self.parse_address_arg(args[0])
            count = int(args[1]) if len(args) > 1 else 10
        else:
            addr = self.executor.cpu.PC.value
            count = 10

        print(f"\n{Colors.CYAN}Disassembly at {addr:04X}H:{Colors.RESET}")
        for _ in range(count):
            try:
                instr, size = disassemble_instruction(self.executor.cpu.memory, addr)
                cycles = get_instruction_cycles(self.executor.cpu.memory, addr)

                # Get machine code bytes
                bytes_hex = " ".join(
                    f"{self.executor.cpu.memory[addr + i].value:02X}"
                    for i in range(size)
                )

                # Highlight current PC
                if addr == self.executor.cpu.PC.value:
                    print(
                        f"  {Colors.HIGHLIGHT}→ {addr:04X}: {bytes_hex:<12} {instr:<20} [{cycles}T]{Colors.RESET}"
                    )
                else:
                    print(
                        f"    {addr:04X}: {bytes_hex:<12} {instr:<20} {Colors.DIM}[{cycles}T]{Colors.RESET}"
                    )

                addr = (addr + size) & 0xFFFF
            except:
                break

    def command_set(self, args):
        """Set register or memory value."""
        if len(args) < 2:
            print(f"{Colors.YELLOW}Usage: set <register|[addr]> <value>{Colors.RESET}")
            print("  Examples: set A 42, set [0x0800] FF, set SP 1000")
            return

        target = args[0].upper()
        try:
            value = parse_address_value(args[1])
        except ValueError as exc:
            print(f"{Colors.RED}Error: Invalid value - {exc}{Colors.RESET}")
            return

        # Memory modification
        if target.startswith("[") and target.endswith("]"):
            try:
                addr = parse_address_value(target[1:-1])
                self.executor.cpu.memory[addr & 0xFFFF].value = value & 0xFF
                print(f"{Colors.GREEN}✓ [{addr:04X}H] = {value:02X}H{Colors.RESET}")
                return
            except ValueError as exc:
                print(f"{Colors.RED}Error: {exc}{Colors.RESET}")
                return

        # Register modification
        if target in ["A", "B", "C", "D", "E", "H", "L"]:
            reg = getattr(self.executor.cpu, target)
            reg.value = value & 0xFF
            print(f"{Colors.GREEN}✓ {target} = {value:02X}H ({value}){Colors.RESET}")
        elif target in ["SP", "PC"]:
            reg = getattr(self.executor.cpu, target)
            reg.value = value & 0xFFFF
            print(f"{Colors.GREEN}✓ {target} = {value:04X}H ({value}){Colors.RESET}")
        else:
            print(f"{Colors.RED}Error: Unknown target '{target}'{Colors.RESET}")

    def command_where(self):
        """Show execution history/call stack."""
        if not self.execution_history:
            print(f"{Colors.YELLOW}No execution history yet{Colors.RESET}")
            return

        print(f"\n{Colors.CYAN}Execution History (last 10 states):{Colors.RESET}")
        for i, state in enumerate(self.execution_history[-10:]):
            step = state["steps"]
            pc = state["registers"]["PC"]
            print(f"  {Colors.DIM}#{i}: Step {step}, PC={pc:04X}H{Colors.RESET}")

    def command_history(self):
        """Show execution statistics."""
        print(f"\n{Colors.CYAN}Execution Statistics:{Colors.RESET}")
        print(f"  Steps:    {self.executor.steps_executed}")
        print(f"  Cycles:   {self.executor.total_cycles}")
        print(f"  History:  {len(self.execution_history)} saved states")
        print(f"  Max hist: {self.max_history}")
        if self.execution_history:
            print(f"  Can undo: {len(self.execution_history)} steps")

    def command_break(self, args):
        if not args:
            self.list_breakpoints()
            return
        addr = self.parse_address_arg(args[0])
        self.breakpoints.add(addr)
        print(f"Breakpoint set at {addr:04X}H")

    def command_delete(self, args):
        if not args:
            self.list_breakpoints()
            return
        token = args[0].lower()
        if token == "all":
            self.breakpoints.clear()
            print("Removed all breakpoints.")
            return
        addr = self.parse_address_arg(token)
        if addr in self.breakpoints:
            self.breakpoints.remove(addr)
            print(f"Removed breakpoint at {addr:04X}H")
        else:
            print("Breakpoint not found.")

    def command_watch(self, args):
        if not args:
            self.list_watchpoints()
            return
        addr = self.parse_address_arg(args[0])
        value = self.executor.cpu.memory[addr].value
        self.watchpoints[addr] = value
        print(f"Watching address {addr:04X}H (current value {value:02X}H)")

    def command_unwatch(self, args):
        if not args:
            self.list_watchpoints()
            return
        token = args[0].lower()
        if token == "all":
            self.watchpoints.clear()
            print("Removed all watchpoints.")
            return
        addr = self.parse_address_arg(token)
        if addr in self.watchpoints:
            self.watchpoints.pop(addr)
            print(f"Removed watchpoint at {addr:04X}H")
        else:
            print("Watchpoint not found.")

    def command_info(self, args):
        if not args:
            print("Usage: info breakpoints | info watch")
            return
        topic = args[0].lower()
        if topic.startswith("break"):
            self.list_breakpoints()
        elif topic.startswith("watch"):
            self.list_watchpoints()
        else:
            print(f"Unknown info topic '{topic}'.")

    def command_print(self, args):
        regs = snapshot_registers(self.executor.cpu)
        if not args:
            print(format_register_summary(regs))
            return
        target = args[0].upper()
        if target in regs:
            value = regs[target]
            width = 4 if target == "SP" else 2
            print(f"{target} = {value:0{width}X}H ({value})")
            return
        if target == "PC":
            pc = self.executor.cpu.PC.value
            instr, _ = disassemble_instruction(self.executor.cpu.memory, pc)
            print(f"PC = {pc:04X}H -> {instr}")
            return
        if target == "FLAGS":
            print(format_flags(regs["FLAGS"]))
            return
        if target.startswith("[") and target.endswith("]"):
            addr = self.parse_address_arg(target[1:-1])
            value = self.executor.cpu.memory[addr].value
            print(f"[{addr:04X}H] = {value:02X}H ({value})")
            return
        print(f"Unknown print target '{target}'.")

    def command_dump(self, args):
        """Dump memory range in hex format: dump <start> <end> [width]"""
        if len(args) < 2:
            print("Usage: dump <start_addr> <end_addr> [bytes_per_line]")
            print(
                "       dump 1000 1020        - Dump 1000H to 1020H (16 bytes per line)"
            )
            print("       dump 1000 1020 8      - Dump with 8 bytes per line")
            return

        start = self.parse_address_arg(args[0])
        end = self.parse_address_arg(args[1])
        bytes_per_line = 16

        if len(args) >= 3:
            try:
                bytes_per_line = int(args[2])
                if bytes_per_line < 1 or bytes_per_line > 32:
                    print(
                        f"{Colors.YELLOW}Warning: bytes_per_line should be 1-32, using 16{Colors.RESET}"
                    )
                    bytes_per_line = 16
            except ValueError:
                print(f"{Colors.RED}Invalid bytes_per_line: {args[2]}{Colors.RESET}")
                return

        if start > end:
            print(f"{Colors.RED}Start address must be <= end address{Colors.RESET}")
            return

        if end - start > 1024:
            print(
                f"{Colors.YELLOW}Warning: Large range ({end - start + 1} bytes). Limiting to 1024 bytes.{Colors.RESET}"
            )
            end = start + 1023

        print(f"{Colors.BLUE}Memory Dump [{start:04X}H - {end:04X}H]:{Colors.RESET}\n")

        addr = start
        while addr <= end:
            # Address column
            print(f"{Colors.CYAN}{addr:04X}:{Colors.RESET}  ", end="")

            # Hex dump
            hex_values = []
            ascii_values = []
            for i in range(bytes_per_line):
                if addr + i <= end:
                    value = self.executor.cpu.memory[addr + i].value
                    hex_values.append(f"{value:02X}")
                    # ASCII representation (printable chars only)
                    if 32 <= value <= 126:
                        ascii_values.append(chr(value))
                    else:
                        ascii_values.append(".")
                else:
                    hex_values.append("  ")
                    ascii_values.append(" ")

            # Print hex values in groups of 4
            for i in range(0, len(hex_values), 4):
                group = hex_values[i : i + 4]
                print(" ".join(group), end="  ")

            # Print ASCII representation
            print(f" {Colors.DIM}|{''.join(ascii_values)}|{Colors.RESET}")

            addr += bytes_per_line

        print()

    def parse_address_arg(self, token):
        label_map = self.executor.get_label_map()
        return parse_address_value(token, label_map=label_map)

    def execute_until_break(self, reset=False, skip_current_break=False):
        if self.executor.cpu.haulted:
            print(
                f"{Colors.YELLOW}Program already halted. Use 'run' to restart.{Colors.RESET}"
            )
            return

        steps_run = 0
        limit = self.step_limit if self.has_limit else float("inf")
        skip_break = skip_current_break

        while steps_run < limit:
            pc = self.executor.cpu.PC.value
            if pc in self.breakpoints and not skip_break:
                print(f"{Colors.YELLOW}Breakpoint hit at {pc:04X}H{Colors.RESET}")
                self.display_state()
                return
            skip_break = False

            result = self.executor.step_instruction()
            steps_run += 1

            changes = self.refresh_watchpoints(report_changes=True)
            if changes:
                for addr, old, new in changes:
                    print(
                        f"{Colors.YELLOW}Watch {addr:04X}H:{Colors.RESET} "
                        f"{old:02X}H → {Colors.HIGHLIGHT}{new:02X}H{Colors.RESET}"
                    )
                self.display_step(result)
                return

            if result["halted"]:
                print(
                    f"{Colors.GREEN}Program halted after {self.executor.steps_executed} steps.{Colors.RESET}"
                )
                return

        print(
            f"{Colors.RED}Stopped after {int(limit)} steps without hitting a breakpoint."
            f" Use --unsafe to raise the limit.{Colors.RESET}"
        )

    def refresh_watchpoints(self, report_changes=False):
        """Check watchpoints and return changes."""
        changes = []
        for addr in list(self.watchpoints.keys()):
            current = self.executor.cpu.memory[addr].value
            last = self.watchpoints[addr]
            if last is None:
                self.watchpoints[addr] = current
                continue
            if current != last:
                changes.append((addr, last, current))
                self.watchpoints[addr] = current
                if report_changes:
                    print(
                        f"{Colors.YELLOW}Watchpoint: {addr:04X}H changed from {last:02X}H to {current:02X}H{Colors.RESET}"
                    )
        return changes

    def list_breakpoints(self):
        if not self.breakpoints:
            print("No breakpoints set.")
            return
        print("Breakpoints:")
        for addr in sorted(self.breakpoints):
            print(f"  - {addr:04X}H")

    def list_watchpoints(self):
        if not self.watchpoints:
            print("No watchpoints set.")
            return
        print("Watchpoints:")
        for addr, value in self.watchpoints.items():
            display = "--" if value is None else f"{value:02X}H"
            print(f"  - {addr:04X}H (last={display})")

    def display_step(self, result):
        regs = result["regs"]
        print(
            f"{Colors.CYAN}{result['pc']:04X}{Colors.RESET}  {result['instr']:<20}  "
            f"{format_register_summary(regs)}"
        )

    def display_state(self):
        """Show current CPU state with registers and flags."""
        regs = snapshot_registers(self.executor.cpu)
        flags = decode_flags(regs["FLAGS"])
        pc = self.executor.cpu.PC.value

        print(f"\n{Colors.CYAN}Registers:{Colors.RESET}")
        print(
            f"  A={Colors.HIGHLIGHT}{regs['A']:02X}H{Colors.RESET} ({regs['A']:3d})  B={regs['B']:02X}H  C={regs['C']:02X}H  D={regs['D']:02X}H  E={regs['E']:02X}H  H={regs['H']:02X}H  L={regs['L']:02X}H"
        )
        print(
            f"  SP={Colors.HIGHLIGHT}{regs['SP']:04X}H{Colors.RESET}  PC={Colors.HIGHLIGHT}{pc:04X}H{Colors.RESET}"
        )

        print(f"\n{Colors.CYAN}Flags:{Colors.RESET} ", end="")
        print(
            f"S={flags['S']} Z={flags['Z']} AC={flags['AC']} P={flags['P']} CY={flags['CY']}"
        )

        print(f"\n{Colors.CYAN}Execution:{Colors.RESET}")
        print(
            f"  Steps: {self.executor.steps_executed}, Cycles: {self.executor.total_cycles}"
        )

    def print_help(self):
        print(
            f"\n{Colors.BLUE}{Colors.BOLD}╔═══════════════════════════════════════════════════════════╗{Colors.RESET}"
        )
        print(
            f"{Colors.BLUE}{Colors.BOLD}║         8085 Interactive Step Debugger - Commands        ║{Colors.RESET}"
        )
        print(
            f"{Colors.BLUE}{Colors.BOLD}╚═══════════════════════════════════════════════════════════╝{Colors.RESET}\n"
        )

        print(f"{Colors.CYAN}{Colors.BOLD}▸ Execution Control:{Colors.RESET}")
        print(
            f"  {Colors.BOLD}step{Colors.RESET} (s)              - Execute one instruction forward"
        )
        print(
            f"  {Colors.BOLD}back{Colors.RESET} (u, undo)       - Step backwards (undo last instruction)"
        )
        print(
            f"  {Colors.BOLD}next{Colors.RESET} (n)              - Step over CALL instructions"
        )
        print(
            f"  {Colors.BOLD}continue{Colors.RESET} (c)          - Continue until breakpoint/halt"
        )
        print(
            f"  {Colors.BOLD}restart{Colors.RESET} (r, run)      - Restart program from beginning"
        )
        print()

        print(f"{Colors.CYAN}{Colors.BOLD}▸ Code Inspection:{Colors.RESET}")
        print(
            f"  {Colors.BOLD}list{Colors.RESET} [n]              - Show source code (±n lines context)"
        )
        print(
            f"  {Colors.BOLD}disasm{Colors.RESET} [addr] [n]     - Disassemble memory at address"
        )
        print(
            f"  {Colors.BOLD}where{Colors.RESET} (bt)            - Show execution history"
        )
        print(
            f"  {Colors.BOLD}history{Colors.RESET}              - Show execution statistics"
        )
        print()

        print(f"{Colors.CYAN}{Colors.BOLD}▸ Breakpoints & Watchpoints:{Colors.RESET}")
        print(
            f"  {Colors.BOLD}break{Colors.RESET} <addr> (b)      - Set breakpoint at address"
        )
        print(
            f"  {Colors.BOLD}watch{Colors.RESET} <addr> (w)      - Watch memory address for changes"
        )
        print(
            f"  {Colors.BOLD}delete{Colors.RESET} <addr|all>    - Remove breakpoint/watchpoint"
        )
        print(
            f"  {Colors.BOLD}info breakpoints{Colors.RESET}     - List all breakpoints"
        )
        print(
            f"  {Colors.BOLD}info watch{Colors.RESET}           - List all watchpoints"
        )
        print()

        print(f"{Colors.CYAN}{Colors.BOLD}▸ Memory & Registers:{Colors.RESET}")
        print(
            f"  {Colors.BOLD}print{Colors.RESET} <expr> (p)      - Print register or memory value"
        )
        print("                          Examples: print A, print [0x0800]")
        print(
            f"  {Colors.BOLD}dump{Colors.RESET} <addr> [n] (x)   - Dump n bytes of memory"
        )
        print(
            f"  {Colors.BOLD}set{Colors.RESET} <reg> <val>       - Set register or memory"
        )
        print("                          Examples: set A 42, set [0x800] FF")
        print()

        print(f"{Colors.CYAN}{Colors.BOLD}▸ Other:{Colors.RESET}")
        print(f"  {Colors.BOLD}help{Colors.RESET} (h, ?)           - Show this help")
        print(f"  {Colors.BOLD}quit{Colors.RESET} (q, exit)        - Exit debugger")
        print()


def run_debug_mode(filename, args):
    debugger = InteractiveDebugger(filename, args)
    debugger.repl()
