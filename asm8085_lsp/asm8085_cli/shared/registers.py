"""registers helpers extracted from asm8085."""


def snapshot_registers(cpu):
    """Capture current CPU register state."""
    return {
        "A": cpu.A.value,
        "B": cpu.B.value,
        "C": cpu.C.value,
        "D": cpu.D.value,
        "E": cpu.E.value,
        "H": cpu.H.value,
        "L": cpu.L.value,
        "SP": cpu.SP.value,
        "FLAGS": cpu.F.value,
    }


def format_flags(flags_byte):
    """Return a compact textual representation of flags."""
    flags = decode_flags(flags_byte)
    return f"S={flags['S']} Z={flags['Z']} P={flags['P']} CY={flags['CY']}"


def format_register_summary(regs):
    """Format register snapshot for display."""
    if not regs:
        return "<< halted >>"
    return (
        f"A={regs['A']:02X} B={regs['B']:02X} C={regs['C']:02X} D={regs['D']:02X} "
        f"E={regs['E']:02X} H={regs['H']:02X} L={regs['L']:02X} SP={regs['SP']:04X} "
        f"Flags={format_flags(regs['FLAGS'])}"
    )


def compute_register_differences(regs_a, regs_b):
    """Return list of textual differences between two register snapshots."""
    if not regs_a and not regs_b:
        return []

    diff_fields = []
    keys = ["A", "B", "C", "D", "E", "H", "L", "SP"]

    def fmt(value, width):
        if value is None:
            return "--"
        if width == 2:
            return f"{value:02X}"
        return f"{value:04X}"

    for key in keys:
        val_a = regs_a[key] if regs_a else None
        val_b = regs_b[key] if regs_b else None
        width = 4 if key == "SP" else 2
        if val_a != val_b:
            # Add arrow indicators for better visualization
            if val_a is not None and val_b is not None:
                if val_a > val_b:
                    arrow = "↓"
                elif val_a < val_b:
                    arrow = "↑"
                else:
                    arrow = "≠"
                diff_fields.append(f"{key}: {fmt(val_a, width)} {arrow} {fmt(val_b, width)}")
            else:
                diff_fields.append(f"{key}: {fmt(val_a, width)} ≠ {fmt(val_b, width)}")

    flags_a = format_flags(regs_a["FLAGS"]) if regs_a else None
    flags_b = format_flags(regs_b["FLAGS"]) if regs_b else None
    if flags_a != flags_b:
        diff_fields.append(f"Flags: {flags_a or '--'} ≠ {flags_b or '--'}")

    return diff_fields


def decode_flags(flag_byte):
    """Decode 8085 flag register into individual flags"""
    # 8085 Flag format: S Z X AC X P X CY
    # Bit:              7 6 5  4 3 2 1  0
    return {
        "S": (flag_byte >> 7) & 1,  # Sign
        "Z": (flag_byte >> 6) & 1,  # Zero
        "AC": (flag_byte >> 4) & 1,  # Auxiliary Carry
        "P": (flag_byte >> 2) & 1,  # Parity
        "CY": (flag_byte >> 0) & 1,  # Carry
    }
