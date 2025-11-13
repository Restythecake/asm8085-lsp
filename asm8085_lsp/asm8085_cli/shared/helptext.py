"""CLI help text renderers."""

from .colors import Colors


def print_short_help():
    """Print concise, practical help in 2 columns"""
    print(f"""
{Colors.BOLD}USAGE{Colors.RESET}
  asm [OPTIONS] <file.asm>

{Colors.CYAN}EXECUTION{Colors.RESET}
  -s, --step              -t, --table
  -e, --explain           -w, --auto
      --debug FILE
  -d, --disassemble       -W, --warnings
      --coverage              --diff A B

{Colors.CYAN}DISPLAY{Colors.RESET}
  -r, --registers        -b, --binary
  -H, --highlight            --base MODE
  -v, --verbose

{Colors.CYAN}MEMORY{Colors.RESET}
  -m, --memory RANGE      -S, --stack
      --show-changes          --watch ADDRS
      --memory-map

{Colors.CYAN}TEMPLATES & TOOLS{Colors.RESET}
      --list-templates        --new-from-template T F
      --template-wizard       --cheat-sheet FMT OUT
      --symbols [-v]          --profile

{Colors.CYAN}OTHER{Colors.RESET}
  -x, --export-hex            --hex-format FMT
  -u, --unsafe [N]        -c, --clock MHZ
      --explain-instr INSTR   --repl

{Colors.DIM}Flags can be combined: -sr = -s -r, -dW = -d -W{Colors.RESET}
Use {Colors.BOLD}--help-full{Colors.RESET} for detailed help with examples
""")


def print_full_help():
    """Print detailed help with EBNF syntax"""
    print(f"""
{Colors.BOLD}8085 ASSEMBLER & SIMULATOR{Colors.RESET}

{Colors.CYAN}SYNOPSIS{Colors.RESET}
  asm [OPTIONS] <file>
  asm --diff <fileA> <fileB>
  asm --debug <file>
  asm --explain-instr <instruction>

{Colors.CYAN}EXECUTION MODES{Colors.RESET} (mutually exclusive: -s | -t | -e)
  -s, --step              Step-by-step trace showing registers after each instruction
  -t, --table             Compact table format (one row per instruction)
  -e, --explain           Mathematical explanations for each operation
  -w, --auto              Auto-reload and re-run when source file changes
      --debug <file>      Interactive REPL debugger with breakpoints

{Colors.CYAN}DEBUGGING & ANALYSIS{Colors.RESET}
  -d, --disassemble       Disassembly with opcodes, cycle counts, descriptions
  -W, --warnings          Static analysis warnings (unused labels, optimizations)
      --coverage          Line and branch coverage report with HTML export
      --diff <A> <B>      Side-by-side table comparison of two programs
                          Shows instruction-level differences with color highlighting
      --profile           Performance profiler showing hotspots and instruction frequency
                          Use --profile-top N to show top N items (default: 10)

{Colors.CYAN}DISPLAY OPTIONS{Colors.RESET}
  -r, --registers        Show final register and flag state after execution
  -H, --highlight        Highlight changed registers/flags (combine with -s/-t/-e)
  -b, --binary           Display registers in binary instead of hexadecimal
  -v, --verbose          Show source code context (±5 lines) on assembly errors
      --base <fmt>       Number format: hex (default) | dec | bin

{Colors.CYAN}MEMORY INSPECTION{Colors.RESET}
  -m, --memory <range>    Display memory range after execution
                          Syntax: START-END  (e.g., 1000-1010, 0x800-0x810)
  -S, --stack             Display stack contents with return address detection
      --show-changes      List all memory addresses modified during execution
      --watch <addrs>     Monitor specific memory addresses (comma-separated)
                          Example: --watch 1000,1002,1004
      --memory-map        Visual memory layout showing code, data, and stack regions
                          Includes usage statistics and fragmentation warnings

{Colors.CYAN}OUTPUT & EXPORT{Colors.RESET}
  -x, --export-hex        Export assembled machine code to file
      --hex-format <fmt>  Export format (requires -x):
                          raw   - Human-readable hex dump (.txt)
                          intel - Intel HEX format for EPROM burners (.hex)
                          c     - C array for embedding in firmware (.h)
                          json  - JSON format for tooling integration (.json)

{Colors.CYAN}LEARNING & REFERENCE{Colors.RESET}
      --explain-instr <instr>   Detailed instruction documentation
                                Examples: MVI, "ADD B", CALL
      --cheat-sheet <fmt> <out> Generate instruction set reference
                                Formats: markdown, html
                                Example: --cheat-sheet html ref.html
      --repl                    Interactive REPL mode for experimentation

{Colors.CYAN}PROJECT MANAGEMENT{Colors.RESET}
      --list-templates          Show all available program templates
      --new-from-template <T> <F> [author] [desc]
                                Create new program from template
                                Example: --new-from-template loop myloop.asm
      --template-wizard         Interactive template selection
      --symbols [-v]            Symbol/label explorer with cross-references
                                Add -v for detailed reference locations

{Colors.CYAN}ADVANCED OPTIONS{Colors.RESET}
  -u, --unsafe [N]        Remove step limit (unlimited) or set custom max steps
                          Default limit: 10000 steps
                          Example: --unsafe 100000
  -c, --clock <mhz>       Simulate CPU clock speed for timing calculations
                          Example: --clock 5.0  (5 MHz)

{Colors.CYAN}EBNF SYNTAX{Colors.RESET}
  <file>       ::= <path>.asm
  <range>      ::= <addr> "-" <addr>
  <addr>       ::= <hex> | <decimal>
  <hex>        ::= <digit>+ "H" | "0x" <hexdigit>+
  <addrs>      ::= <addr> ("," <addr>)*
  <fmt>        ::= "hex" | "dec" | "bin"
  <hex-fmt>    ::= "raw" | "intel" | "c"

{Colors.CYAN}FLAG COMBINATIONS{Colors.RESET}
  Short flags can be combined (like Unix tools):
    -sr          →  -s -r          (step + register summary)
    -sH          →  -s -H          (step + highlight)
    -dW          →  -d -W          (disassemble + warnings)
    -srv         →  -s -r -v       (step + register summary + verbose)
    -wsr         →  -w -s -r       (auto + step + register summary)
    -xd          →  -x -d          (export + disassemble)

  Combinable flags: s, t, e, w, r, b, v, d, W, S, x, H
  Non-combinable (need arguments): m, u, c

{Colors.CYAN}COMMON WORKFLOWS{Colors.RESET}
  {Colors.BOLD}Quick Start{Colors.RESET}
    asm --list-templates                 # Browse available templates
    asm --new-from-template basic test.asm  # Create new program
    asm test.asm                         # Run it
    asm -sr test.asm                     # Run with step trace + registers

  {Colors.BOLD}Development{Colors.RESET}
    asm -wsH program.asm                 # Auto-reload with trace + highlights
    asm -W program.asm                   # Check for warnings
    asm --symbols -v program.asm         # Explore all labels

  {Colors.BOLD}Debugging{Colors.RESET}
    asm --debug program.asm              # Interactive debugger with breakpoints
    asm -sHr program.asm                 # Step mode with highlights & registers
    asm --diff old.asm new.asm           # Compare two versions

  {Colors.BOLD}Analysis{Colors.RESET}
    asm --coverage program.asm           # Line and branch coverage
    asm -d program.asm                   # Disassembly with cycle counts
    asm -m 8000-8010 program.asm         # Inspect memory range
    asm --memory-map program.asm         # Visual memory layout
    asm --profile program.asm            # Performance profiling

  {Colors.BOLD}Documentation{Colors.RESET}
    asm --explain-instr MVI              # Learn about instructions
    asm --cheat-sheet html ref.html      # Generate reference guide
    asm -e program.asm                   # Mathematical explanations

  {Colors.BOLD}Production{Colors.RESET}
    asm -xd --hex-format intel prog.asm  # Export + disassembly
    asm -c 5.0 -r program.asm            # Timing at 5 MHz + final state

{Colors.CYAN}EXIT STATUS{Colors.RESET}
  0   Success (program assembled and ran/analyzed)
  1   Assembly error (syntax error, undefined labels)
  2   Command-line usage error

{Colors.DIM}Use -h for short help{Colors.RESET}
""")
