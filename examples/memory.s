# Demonstrate little-endian byte-addressed memory.
li t0, 100        # memory address
li t1, 12345      # value to store
sw t1, 0(t0)      # save a 32-bit word
lw a0, 0(t0)      # load it back
li a7, 1
 ecall
li a7, 10
 ecall
