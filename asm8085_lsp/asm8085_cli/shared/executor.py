"""Program execution helpers."""

from . import emu8085
from .assembly import assemble_or_exit, load_source_file
from .disasm import disassemble_instruction, get_instruction_cycles
from .registers import snapshot_registers


def resolve_step_limit(args):
    """Determine step limit and whether a hard cap is enforced."""
    unsafe_value = getattr(args, "unsafe", None)
    if unsafe_value is None:
        return 1000, True
    if unsafe_value == -1:
        return float("inf"), False
    return unsafe_value, True


class ProgramExecutor:
    """Utility for loading and stepping through a program."""

    def __init__(self, filename, args):
        self.filename = filename
        self.args = args
        self.load_program()

    def load_program(self):
        self.clean_lines, self.original_lines = load_source_file(self.filename)
        self.asm_obj = assemble_or_exit(
            self.filename, self.clean_lines, self.original_lines, self.args
        )
        self.reset_state()

    def reset_state(self):
        self.cpu = emu8085()
        for i, byte_val in enumerate(self.asm_obj.pmemory):
            self.cpu.memory[i].value = byte_val
        self.cpu.PC.value = self.asm_obj.ploadoff
        self.initial_memory = [
            self.cpu.memory[i].value for i in range(len(self.cpu.memory))
        ]
        self.total_cycles = 0
        self.steps_executed = 0

    def reload_program(self):
        self.load_program()

    def get_label_map(self):
        if hasattr(self.asm_obj, "labeloff"):
            return self.asm_obj.labeloff
        return {}

    def step_instruction(self):
        """Execute one instruction and return metadata."""
        if self.cpu.haulted:
            return {
                "halted": True,
                "pc": self.cpu.PC.value,
                "instr": "HLT",
                "cycles": 0,
                "size": 1,
                "pc_after": self.cpu.PC.value,
                "branch_taken": False,
                "regs": snapshot_registers(self.cpu),
            }

        pc = self.cpu.PC.value
        instr, size = disassemble_instruction(self.cpu.memory, pc)
        cycles = get_instruction_cycles(self.cpu.memory, pc)
        regs_before = snapshot_registers(self.cpu)
        self.cpu.runcrntins()
        pc_after = self.cpu.PC.value
        regs_after = snapshot_registers(self.cpu)
        self.total_cycles += cycles
        self.steps_executed += 1
        fallthrough_pc = (pc + size) & 0xFFFF
        branch_taken = pc_after != fallthrough_pc
        return {
            "pc": pc,
            "instr": instr,
            "cycles": cycles,
            "size": size,
            "pc_after": pc_after,
            "branch_taken": branch_taken,
            "regs_before": regs_before,
            "regs": regs_after,
            "halted": self.cpu.haulted,
        }
