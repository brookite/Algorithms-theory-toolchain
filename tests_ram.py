from ram_translator import *
import os

root = "../../../Учёба/Дисциплины/2 семестр/Теория алгоритмов/Лабораторные работы/ЛР5/code"
file = os.path.join(root, "18.txt")

debug_mode = False

registry_preset = {
    "R0": 0,
    "R1": 0,
    "R2": 0,
    "R3": 0,
    "R4": 0,
    "R5": 0,
    "R6": 0,
    "R7": 0,
    "R8": 0,
    "R9": 0
}

machine = RAMMachine(RAMProgram.from_bytes(file))


def print_registers():
    for i in range(len(machine.registers)):
        print(f"R{i+1}=", machine.registers[i])


def get_results(**registries):
    return machine.execute(debug_prints=debug_mode, **registries)


def get_test_result(word, is_tape_end=True, criteria="command_executed"):
    return get_results(word)[criteria]


if __name__ == '__main__':
    # print(machine.program.compile())
    results = get_results()
    print_registers()
