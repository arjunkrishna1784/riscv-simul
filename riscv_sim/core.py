"""Educational RV32I assembly interpreter (not a binary instruction decoder)."""
from __future__ import annotations
from dataclasses import dataclass
import re

MASK = 0xFFFFFFFF
REG_ALIASES = {
    'zero': 0, 'ra': 1, 'sp': 2, 'gp': 3, 'tp': 4,
    **{f't{i}': n for i, n in enumerate([5, 6, 7, 28, 29, 30, 31])},
    **{f's{i}': n for i, n in enumerate([8, 9, *range(18, 28)])},
    **{f'a{i}': i + 10 for i in range(8)},
    'fp': 8,
}


def u32(x: int) -> int:
    return x & MASK


def s32(x: int) -> int:
    x &= MASK
    return x if x < 0x80000000 else x - 0x100000000


class SimulatorError(Exception):
    """Invalid assembly, access, or execution."""


@dataclass(frozen=True)
class Instruction:
    opcode: str
    operands: tuple[str, ...]
    source_line: int
    source: str


def _integer(value: str) -> int:
    try:
        return int(value, 0) if not re.fullmatch(r'[+-]?\d+', value) else int(value, 10)
    except ValueError as exc:
        raise SimulatorError(f'Invalid integer: {value}') from exc


def _register(name: str) -> int:
    name = name.lower().strip()
    if re.fullmatch(r'x(?:[0-9]|[12][0-9]|3[01])', name):
        return int(name[1:])
    if name in REG_ALIASES:
        return REG_ALIASES[name]
    raise SimulatorError(f'Unknown register: {name}')


def assemble(source: str) -> tuple[list[Instruction], dict[str, int]]:
    """Parse assembly with labels; PCs are byte addresses (4 bytes/instruction)."""
    instructions: list[Instruction] = []
    labels: dict[str, int] = {}
    for line_num, original in enumerate(source.splitlines(), 1):
        line = original.split('#', 1)[0].split('//', 1)[0].strip()
        while True:
            match = re.match(r'^([A-Za-z_][\w.]*):', line)
            if not match:
                break
            name = match.group(1)
            if name in labels:
                raise SimulatorError(f'Line {line_num}: duplicate label {name}')
            labels[name] = 4 * len(instructions)
            line = line[match.end():].strip()
        if not line:
            continue
        if line.startswith('.'):
            if line in ('.text', '.globl main', '.global main'):
                continue
            raise SimulatorError(f'Line {line_num}: unsupported directive: {line}')
        parts = line.split(None, 1)
        opcode = parts[0].lower()
        arguments = tuple(x.strip() for x in parts[1].split(',')) if len(parts) > 1 else ()
        if any(not a for a in arguments):
            raise SimulatorError(f'Line {line_num}: empty operand')
        instructions.append(Instruction(opcode, arguments, line_num, original.strip()))
    return instructions, labels


class Simulator:
    """Registers, byte-addressed little-endian RAM, PC, and instruction execution."""
    def __init__(self, memory_size: int = 65536):
        if memory_size < 4:
            raise ValueError('memory_size must be >= 4')
        self.memory_size = memory_size
        self.reset()

    def reset(self) -> None:
        self.regs = [0] * 32
        self.memory = bytearray(self.memory_size)
        self.pc = 0
        self.steps = 0
        self.halted = False
        self.output: list[str] = []
        self.program: list[Instruction] = []
        self.labels: dict[str, int] = {}

    def load(self, source: str) -> None:
        instructions, labels = assemble(source)
        self.reset()
        self.program, self.labels = instructions, labels

    def reg(self, operand: str) -> int:
        return self.regs[_register(operand)]

    def _set(self, operand: str, value: int) -> None:
        index = _register(operand)
        if index:
            self.regs[index] = u32(value)

    def _mem_address(self, address: int, width: int) -> int:
        if address % width:
            raise SimulatorError(f'Unaligned {width}-byte memory access at {address}')
        if address < 0 or address + width > self.memory_size:
            raise SimulatorError(f'Memory access out of bounds at {address}')
        return address

    def read(self, address: int, width: int, signed: bool = False) -> int:
        addr = self._mem_address(address, width)
        return int.from_bytes(self.memory[addr:addr + width], 'little', signed=signed)

    def write(self, address: int, width: int, value: int) -> None:
        addr = self._mem_address(address, width)
        self.memory[addr:addr + width] = (value & ((1 << (width * 8)) - 1)).to_bytes(width, 'little')

    def _offset(self, text: str) -> int:
        if text in self.labels:
            return self.labels[text] - self.pc
        return _integer(text)

    def _address(self, operand: str) -> int:
        match = re.fullmatch(r'\s*([+-]?(?:0x[0-9a-fA-F]+|\d+))\(([^()]+)\)\s*', operand)
        if not match:
            raise SimulatorError(f'Expected offset(register), got {operand}')
        return u32(self.reg(match.group(2)) + _integer(match.group(1)))

    def step(self) -> Instruction | None:
        if self.halted:
            return None
        if self.pc == len(self.program) * 4:
            self.halted = True
            return None
        if self.pc % 4 or self.pc < 0 or self.pc // 4 >= len(self.program):
            raise SimulatorError(f'PC outside program: {self.pc:#x}')
        inst = self.program[self.pc // 4]
        op, args = inst.opcode, inst.operands
        old_pc = self.pc
        next_pc = u32(self.pc + 4)
        try:
            if op == 'nop':
                self._arity(args, 0)
            elif op == 'li':
                self._arity(args, 2)
                self._set(args[0], _integer(args[1]))
            elif op == 'mv':
                self._arity(args, 2)
                self._set(args[0], self.reg(args[1]))
            elif op in ('add', 'sub', 'and', 'or', 'xor', 'sll', 'srl', 'sra', 'slt', 'sltu'):
                self._arity(args, 3)
                a, b = self.reg(args[1]), self.reg(args[2])
                result = {
                    'add': lambda: a + b, 'sub': lambda: a - b,
                    'and': lambda: a & b, 'or': lambda: a | b, 'xor': lambda: a ^ b,
                    'sll': lambda: a << (b & 31), 'srl': lambda: a >> (b & 31),
                    'sra': lambda: s32(a) >> (b & 31),
                    'slt': lambda: int(s32(a) < s32(b)), 'sltu': lambda: int(a < b),
                }[op]()
                self._set(args[0], result)
            elif op in ('addi', 'andi', 'ori', 'xori', 'slti', 'sltiu', 'slli', 'srli', 'srai'):
                self._arity(args, 3)
                a, imm = self.reg(args[1]), _integer(args[2])
                if op in ('slli', 'srli', 'srai'):
                    if not 0 <= imm <= 31:
                        raise SimulatorError('Shift amount must be 0..31')
                elif not -2048 <= imm <= 2047:
                    raise SimulatorError('12-bit immediate must be -2048..2047')
                result = {
                    'addi': lambda: a + imm, 'andi': lambda: a & imm,
                    'ori': lambda: a | imm, 'xori': lambda: a ^ imm,
                    'slti': lambda: int(s32(a) < imm),
                    'sltiu': lambda: int(a < u32(imm)),
                    'slli': lambda: a << imm, 'srli': lambda: a >> imm,
                    'srai': lambda: s32(a) >> imm,
                }[op]()
                self._set(args[0], result)
            elif op in ('lb', 'lbu', 'lh', 'lhu', 'lw'):
                self._arity(args, 2)
                width = {'lb': 1, 'lbu': 1, 'lh': 2, 'lhu': 2, 'lw': 4}[op]
                self._set(args[0], self.read(self._address(args[1]), width, op in ('lb', 'lh')))
            elif op in ('sb', 'sh', 'sw'):
                self._arity(args, 2)
                self.write(self._address(args[1]), {'sb': 1, 'sh': 2, 'sw': 4}[op], self.reg(args[0]))
            elif op in ('beq', 'bne', 'blt', 'bge', 'bltu', 'bgeu'):
                self._arity(args, 3)
                a, b = self.reg(args[0]), self.reg(args[1])
                taken = {'beq': a == b, 'bne': a != b, 'blt': s32(a) < s32(b),
                         'bge': s32(a) >= s32(b), 'bltu': a < b, 'bgeu': a >= b}[op]
                if taken:
                    offset = self._offset(args[2])
                    if offset % 2 or not -4096 <= offset <= 4094:
                        raise SimulatorError('Branch offset must be even and within -4096..4094')
                    next_pc = u32(self.pc + offset)
            elif op == 'jal':
                self._arity(args, 2)
                offset = self._offset(args[1])
                if offset % 2 or not -(1 << 20) <= offset < (1 << 20):
                    raise SimulatorError('JAL offset out of range or odd')
                self._set(args[0], next_pc)
                next_pc = u32(self.pc + offset)
            elif op == 'j':
                self._arity(args, 1)
                offset = self._offset(args[0])
                if offset % 2 or not -(1 << 20) <= offset < (1 << 20):
                    raise SimulatorError('Jump offset out of range or odd')
                next_pc = u32(self.pc + offset)
            elif op == 'jalr':
                self._arity(args, 3)
                offset = _integer(args[2])
                if not -2048 <= offset <= 2047:
                    raise SimulatorError('JALR immediate must be -2048..2047')
                target = u32(self.reg(args[1]) + offset) & ~1
                self._set(args[0], next_pc)
                next_pc = target
            elif op in ('lui', 'auipc'):
                self._arity(args, 2)
                imm = _integer(args[1])
                if not -(1 << 19) <= imm < (1 << 20):
                    raise SimulatorError('Upper immediate must fit 20 bits')
                self._set(args[0], (imm << 12) + (self.pc if op == 'auipc' else 0))
            elif op == 'ecall':
                self._arity(args, 0)
                code = self.reg('a7')
                if code == 1:
                    self.output.append(str(s32(self.reg('a0'))))
                elif code == 10:
                    self.halted = True
                else:
                    raise SimulatorError(f'Unsupported educational ecall service: {code}; use a7=1 (print integer) or a7=10 (exit)')
            else:
                raise SimulatorError(f'Unsupported instruction: {op}')
        except SimulatorError as exc:
            raise SimulatorError(f'Line {inst.source_line} (PC {old_pc:#x}): {exc}') from exc
        self.pc = next_pc
        self.regs[0] = 0
        self.steps += 1
        if self.pc == len(self.program) * 4:
            self.halted = True
        return inst

    @staticmethod
    def _arity(args: tuple[str, ...], count: int) -> None:
        if len(args) != count:
            raise SimulatorError(f'Expected {count} operands, got {len(args)}')

    def run(self, max_steps: int = 100_000) -> int:
        while not self.halted:
            if self.steps >= max_steps:
                raise SimulatorError(f'Step limit of {max_steps} reached (possible infinite loop)')
            self.step()
        return self.steps
