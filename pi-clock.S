.syntax unified
.arch armv7-a
.arch_extension idiv
.arm
.text
.global clock_cycles
clock_cycles:
 push {r7,lr}
 sub sp,sp,#8
 mov r0,#1
 mov r1,sp
 movw r7,#263
 svc #0
 ldr r0,[sp]
 ldr r1,[sp,#4]
 movw r2,#0xc6c0
 movt r2,#0x2d
 mul r0,r0,r2
 movw r2,#333
 udiv r1,r1,r2
 add r0,r0,r1
 mov r1,#0
 add sp,sp,#8
 pop {r7,pc}
