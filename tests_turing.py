from altturing import *
import os

# root = "../../../Учёба/Дисциплины/2 семестр/Теория алгоритмов/Лабораторные работы/ЛР3"
root = "train_turing"
file = os.path.join(root, "3_3_15.tur")

tape_word = "311"
tape_end = len(tape_word) - 1
tape = Tape(0, tape_end, tape_end, tape_word)

program = TuringMachine(TuringFile.from_bytes(file))


def get_results(tape=None):
    return program.execute(tape, debug_prints=False)


def form_tape(tape_word, is_tape_end=True):
    if not tape_word.strip():
        tape_word = ' '
    tape_end = len(tape_word) - 1
    return Tape(0, tape_end, tape_end if is_tape_end else 0, tape_word)


def get_test_result(word, is_tape_end=True, criteria="iterations"):
    return get_results(form_tape(word, is_tape_end))[1][criteria]


if __name__ == '__main__':
    results = get_results(tape)
    if results:
        print("Result:", repr(results[0].tape))
        print("Total commands: ", results[1]["iterations"])
        print("Used cells: ", results[1]["used_cells"])
        print("Length of word: ", len(tape_word))
        print("Command count trace:")
        for key in results[1]["command_exec_count"]:
            print(key, results[1]["command_exec_count"][key])
