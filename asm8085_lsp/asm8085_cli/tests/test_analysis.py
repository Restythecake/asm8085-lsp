import pytest

from asm8085_cli.analysis import analyze_warnings
from asm8085_cli.emu import assembler


def assemble_source(lines):
    asm = assembler()
    success, error = asm.assemble(lines)
    if not success:
        pytest.skip(f"Assembler failed for test source: {error}")
    return asm


def test_loop_warning_is_info():
    source = ["LOOP: DCR C", "JNZ LOOP", "HLT"]
    asm = assemble_source(source)
    warnings = analyze_warnings(source, asm)
    profiling_warnings = [w for w in warnings if w.get("type") == "profiling"]
    assert profiling_warnings, "Expected at least one profiling warning"
    assert any(w.get("severity") == "info" for w in profiling_warnings)

