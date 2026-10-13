import unittest
from riscv_sim import Simulator, SimulatorError, assemble, s32


class SimulatorTests(unittest.TestCase):
    def execute(self, source, memory_size=256, max_steps=1000):
        sim = Simulator(memory_size)
        sim.load(source)
        sim.run(max_steps)
        return sim

    def test_registers_and_zero(self):
        sim = self.execute('li x1, 5\nli x2, 3\nadd x3, x1, x2\naddi x0, x3, 8')
        self.assertEqual(sim.regs[3], 8)
        self.assertEqual(sim.regs[0], 0)

    def test_signed_overflow_and_shifts(self):
        sim = self.execute('li t0, -1\naddi t1, t0, 1\nsrli t2, t0, 31\nsrai t3, t0, 31\nslli t4, t2, 31')
        self.assertEqual(sim.regs[1], 0)
        self.assertEqual(sim.regs[6], 0)
        self.assertEqual(sim.regs[7], 1)
        self.assertEqual(s32(sim.regs[28]), -1)
        self.assertEqual(sim.regs[29], 0x80000000)

    def test_arithmetic_logic_comparisons(self):
        sim = self.execute('li x1, -1\nli x2, 2\nslt x3, x1, x2\nsltu x4, x1, x2\nand x5, x1, x2\nxori x6, x2, 7')
        self.assertEqual([sim.regs[i] for i in (3, 4, 5, 6)], [1, 0, 2, 5])

    def test_memory_byte_order_and_sign_extension(self):
        sim = self.execute('li x1, 16\nli x2, -1\nsw x2, 0(x1)\n' +
                           'lb x3, 0(x1)\nlbu x4, 0(x1)\nlh x5, 0(x1)\n' +
                           'lhu x6, 0(x1)\nlw x7, 0(x1)')
        self.assertEqual(list(sim.memory[16:20]), [255] * 4)
        self.assertEqual([sim.regs[i] for i in (3, 4, 5, 6, 7)],
                         [0xFFFFFFFF, 255, 0xFFFFFFFF, 65535, 0xFFFFFFFF])

    def test_store_byte(self):
        sim = self.execute('li x1, 16\nli x2, 291\nsb x2, 0(x1)\nlbu x3, 0(x1)')
        self.assertEqual(sim.regs[3], 35)

    def test_branch_labels_loop(self):
        sim = self.execute('li t0, 0\nli t1, 5\nagain: addi t0, t0, 1\nblt t0, t1, again')
        self.assertEqual(sim.regs[5], 5)

    def test_jump_and_link(self):
        sim = self.execute('jal ra, skip\nli x5, 99\nskip: li x6, 3')
        self.assertEqual(sim.regs[1], 4)
        self.assertEqual(sim.regs[5], 0)
        self.assertEqual(sim.regs[6], 3)

    def test_jalr(self):
        sim = self.execute('li x1, 12\njalr x2, x1, 0\nli x3, 42\nli x4, 7')
        self.assertEqual(sim.regs[2], 8)
        self.assertEqual(sim.regs[3], 0)
        self.assertEqual(sim.regs[4], 7)

    def test_upper_immediates(self):
        sim = self.execute('lui x1, 0x12345\nauipc x2, 1')
        self.assertEqual(sim.regs[1], 0x12345000)
        self.assertEqual(sim.regs[2], 4100)

    def test_output_and_exit(self):
        sim = self.execute('li a0, 33\nli a7, 1\necall\nli a7, 10\necall\nli x1, 5')
        self.assertEqual(sim.output, ['33'])
        self.assertEqual(sim.regs[1], 0)

    def test_bad_register(self):
        with self.assertRaisesRegex(SimulatorError, 'Unknown register'):
            self.execute('add x32, x1, x2')

    def test_out_of_bounds(self):
        with self.assertRaisesRegex(SimulatorError, 'out of bounds'):
            self.execute('li x1, 256\nlw x2, 0(x1)')

    def test_unaligned_memory(self):
        with self.assertRaisesRegex(SimulatorError, 'Unaligned'):
            self.execute('li x1, 3\nlw x2, 0(x1)')

    def test_infinite_loop_guard(self):
        with self.assertRaisesRegex(SimulatorError, 'Step limit'):
            self.execute('loop: j loop', max_steps=10)

    def test_duplicate_labels(self):
        with self.assertRaisesRegex(SimulatorError, 'duplicate label'):
            assemble('loop: nop\nloop: nop')

    def test_immediate_limit(self):
        with self.assertRaisesRegex(SimulatorError, '12-bit immediate'):
            self.execute('addi x1, x0, 5000')


if __name__ == '__main__':
    unittest.main()
