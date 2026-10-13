"""Command-line entry point: python -m riscv_sim examples/fibonacci.s"""
import argparse
from pathlib import Path
from . import Simulator, SimulatorError, s32


def main() -> int:
    parser = argparse.ArgumentParser(description='Educational RV32I assembly simulator')
    parser.add_argument('file', nargs='?', help='Assembly .s file (omit for interactive shell)')
    parser.add_argument('--trace', action='store_true', help='Print each executed instruction')
    parser.add_argument('--registers', action='store_true', help='Print all register values after execution')
    parser.add_argument('--memory-size', type=int, default=65536, help='RAM bytes (default: 65536)')
    parser.add_argument('--max-steps', type=int, default=100000, help='Instruction safety limit')
    args = parser.parse_args()
    try:
        sim = Simulator(args.memory_size)
        if args.file:
            sim.load(Path(args.file).read_text(encoding='utf-8'))
            if args.trace:
                while not sim.halted:
                    if sim.steps >= args.max_steps:
                        raise SimulatorError('Step limit reached')
                    ins = sim.step()
                    if ins:
                        print(f'{sim.steps:5} pc={sim.pc:08x}  {ins.source}')
            else:
                sim.run(args.max_steps)
        else:
            print('RISC-V mini shell. Enter one instruction per line; .regs, .reset, .quit available.')
            source = []
            while True:
                try:
                    line = input('riscv> ').strip()
                except (EOFError, KeyboardInterrupt):
                    print()
                    break
                if line == '.quit':
                    break
                if line == '.regs':
                    print('  '.join(f'x{i}={s32(v)}' for i, v in enumerate(sim.regs)))
                    continue
                if line == '.reset':
                    sim.reset()
                    source = []
                    print('Reset.')
                    continue
                if not line:
                    continue
                # Replay commands on a fresh copy so labels and PC remain consistent.
                candidate = '\n'.join(source + [line])
                trial = Simulator(args.memory_size)
                trial.load(candidate)
                try:
                    trial.run(args.max_steps)
                except SimulatorError as exc:
                    print(f'Error: {exc}')
                    continue
                sim, source = trial, source + [line]
                print('  ' + ', '.join(f'x{i}={s32(v)}' for i, v in enumerate(sim.regs) if v))
        for line in sim.output:
            print(line)
        if args.registers:
            for i, value in enumerate(sim.regs):
                print(f'x{i:02} = {s32(value):12} (0x{value:08x})')
        if args.file:
            print(f'Completed {sim.steps} instructions. PC=0x{sim.pc:08x}')
        return 0
    except (SimulatorError, OSError, ValueError) as exc:
        parser.exit(1, f'Error: {exc}\n')


if __name__ == '__main__':
    raise SystemExit(main())
