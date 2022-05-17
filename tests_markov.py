from altmarkov import *
import os

#root = "../../../Учёба/Дисциплины/2 семестр/Теория алгоритмов/Лабораторные работы/ЛР4"
root = "train_turing"
file = os.path.join(root, "P6_x+1.nma")

word = "9"
debug_mode = False

program = MarkovMachine(MarkovFile.from_bytes(file))


def get_results(word=None):
    return program.execute(word, debug_prints=debug_mode)


def get_test_result(word, criteria="replacements"):
    return get_results(word)[2][criteria]


if __name__ == '__main__':
    results = get_results(word)
    if results:
        print(results[0], "->", results[1])
        print("Total replacements: ", results[2]["replacements"])
        print("Total iterations for replace: ", results[2]["iterations"])
        print("Replace templates: ", results[2]["total_replace_templates"])
        print("Length of word: ", len(word))
        print("Command count trace:")
        for key in results[2]["command_exec_count"]:
            print(key, results[2]["command_exec_count"][key])
