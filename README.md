# RISC-V Simulator (Python)

A **beginner-friendly, dependency-free RV32I assembly simulator** written in Python. Learn how CPUs use registers, RAM, the program counter, arithmetic instructions, branches, and jumps—without buying hardware.

> **Scope:** This executes a useful subset of *textual* RV32I assembly, rather than decoding compiled `.elf` or raw binary instructions. It is not cycle-accurate, and its `ecall` print/exit services are educational conveniences, not the Linux RISC-V system-call ABI. The `li`, `mv`, `j`, and `nop` instructions are simplified pseudo-instructions (and may accept values that a real assembler would expand into multiple machine instructions).

## Get started in under a minute

You need **Python 3.10+**. No third-party packages are required.

```bash
python -m riscv_sim examples/arithmetic.s
python -m riscv_sim examples/fibonacci.s
python -m riscv_sim examples/memory.s
```

Expected printed results: `12`, `55`, and `12345`, respectively (followed by an execution summary).

See every executed instruction and register value:

```bash
python -m riscv_sim examples/fibonacci.s --trace --registers
```

Start a small interactive shell:

```bash
python -m riscv_sim
```

Type `li x1, 5`, `li x2, 3`, `add x3, x1, x2`, then `.regs` to inspect the results. `.reset` resets the machine; `.quit` exits. The shell replays the history when you enter a command, so it's meant for simple instruction experiments, not large programs.

## Concept map

| Term | What it means | Implementation |
| --- | --- | --- |
| CPU | Runs one instruction at a time | `Simulator.step()` |
| Register | Tiny fast storage inside the CPU | `regs`, 32 entries (`x0` is always zero) |
| RAM | Larger byte-addressed storage | `memory`, a `bytearray` |
| Program counter (PC) | Byte address of the next instruction | `pc`; incremented by 4 unless jumping |
| Parser | Turns assembly text into instructions | `assemble()` |
| Execution loop | Repeatedly execute instructions | `run()` |

### Example

```asm
li x1, 5         # x1 = 5
li x2, 3         # x2 = 3
add x3, x1, x2   # x3 = x1 + x2 = 8
```

## Supported operations

- **Arithmetic:** `add`, `sub`, `addi`
- **Logic:** `and`, `or`, `xor`, `andi`, `ori`, `xori`
- **Shifts:** `sll`, `srl`, `sra`, `slli`, `srli`, `srai`
- **Comparisons:** `slt`, `sltu`, `slti`, `sltiu`
- **Load/store:** `lb`, `lbu`, `lh`, `lhu`, `lw`, `sb`, `sh`, `sw`; use `offset(register)` syntax
- **Branches:** `beq`, `bne`, `blt`, `bge`, `bltu`, `bgeu`
- **Jumps:** `jal`, `jalr`, `j` (pseudo-instruction)
- **Upper-immediate:** `lui`, `auipc`
- **Convenience:** `li`, `mv`, `nop`, `ecall`
- **Labels**, `#` and `//` comments, multiple labels per instruction

Signed and unsigned 32-bit arithmetic, little-endian loads/stores, alignment, immediate-size checks, and a configurable execution step limit are included. Source line numbers are reported for runtime errors.

### Educational `ecall` services

Set `a7 = 1` to append the signed integer in `a0` to printable output; set `a7 = 10` to exit. These are **not** real RISC-V Linux syscalls.

## Run tests

```bash
python -m unittest discover -s tests -v
```

## Project structure

```text
riscv-simulator/
├── riscv_sim/
│   ├── __init__.py       # public API
│   ├── __main__.py       # CLI and interactive shell
│   └── core.py           # parser, registers, RAM, instruction execution
├── examples/
│   ├── arithmetic.s
│   ├── fibonacci.s
│   └── memory.s
├── tests/
│   └── test_simulator.py
├── .github/workflows/tests.yml
└── README.md
```

## Limitations / possible next steps

- Decode actual 32-bit RISC-V machine instructions from binary.
- Implement other privileged-mode features, traps, and real system calls.
- Add a browser debugger with a memory view and single-step execution.
- Expand to real ELF files, assemble macros/directives and data sections.
- Add RV32M multiplication/division and optional compressed instructions.

**License:** MIT.
