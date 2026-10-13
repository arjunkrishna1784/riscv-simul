# Compute F(10) = 55 using a loop.
# a0 contains the answer at the end; ecall prints it.
li t0, 0       # first Fibonacci number
li t1, 1       # second Fibonacci number
li t2, 10      # number of iterations
loop:
    beq t2, zero, done
    add t3, t0, t1
    mv t0, t1
    mv t1, t3
    addi t2, t2, -1
    j loop
done:
    mv a0, t0
    li a7, 1
    ecall
    li a7, 10
    ecall
