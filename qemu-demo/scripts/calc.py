#!/bin/env python3
import sys


def calculate_page_table_entry(virtual_address):
    # 页表相关参数
    page_size = 4096  # 页大小
    page_table_size = 1 << 9  # 页表项数目
    page_offset_bits = 12  # 页内偏移位数
    level_1_bits = 9  # 一级页表位数
    level_2_bits = 9  # 二级页表位数
    level_3_bits = 9  # 三级页表位数

    # 计算页表索引
    offset = virtual_address & (page_size - 1)
    level_1_index = (virtual_address >> page_offset_bits) & (page_table_size - 1)
    level_2_index = (virtual_address >> (page_offset_bits + level_1_bits)) & (
        page_table_size - 1
    )
    level_3_index = (
        virtual_address >> (page_offset_bits + level_1_bits + level_2_bits)
    ) & (page_table_size - 1)
    level_4_index = (
        virtual_address
        >> (page_offset_bits + level_1_bits + level_2_bits + level_3_bits)
    ) & (page_table_size - 1)

    # 打印结果
    print("Virtual Address: 0x{:X} 0b{:b}".format(virtual_address, virtual_address))

    print("Offset: 0x{:X}".format(offset))
    print("Level 4 Index: 0x{:X}\tOffset: 0x{:X}".format(level_4_index, level_4_index << 3))
    print("Level 3 Index: 0x{:X}\tOffset: 0x{:X}".format(level_3_index, level_3_index << 3))
    print("Level 2 Index: 0x{:X}\tOffset: 0x{:X}".format(level_2_index, level_2_index << 3))
    print("Level 1 Index: 0x{:X}\tOffset: 0x{:X}".format(level_1_index, level_1_index << 3))

# 输入虚拟地址并计算页表项
if len(sys.argv) > 1:
    virtual_address = int(sys.argv[1], 16)
else:
    virtual_address = int(input("Input vaddr (HEX): "), 16)

calculate_page_table_entry(virtual_address)
