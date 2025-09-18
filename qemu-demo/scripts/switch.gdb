add-symbol-file ~/qnx/qnx700/target/qnx7/x86_64/boot/sys/procnto-smp-instr \
  0xffff8000000296c0 \
  -s .bss 0xffff8000000fdb40


# break *0x1452460

target remote localhost:1234

# b *(0xffff8000000296c0 + 0x0000000000038D29)


# watch *(kmem_node_t *)(0xFFFF8000000FE9C0)
break x86_64_switch if ((PROCESS *)*active_handle)->pid == 1
  commands
  printf "[-] pid %d <- %d\n", ((PROCESS *)handle)->pid, ((PROCESS *)*active_handle)->pid
end

continue


