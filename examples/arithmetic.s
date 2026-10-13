# 7 + 5 = 12
li x1, 7
li x2, 5
add x3, x1, x2
mv a0, x3
li a7, 1
ecall
li a7, 10
ecall
