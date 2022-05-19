from asymptotic import *
# from tests_turing import *
from tests_markov import *


def print_function(coefs):
    string = ''
    for i, c in enumerate(coefs):
        i = len(coefs) - (i + 1)
        c = round(c, 2)
        string += f"({c})x^{i} + "
    return string[:-2]


tests = [
    "1",
    "10001",
    "10000001"
]
check = [
    "10111100001"
]
main_criteria = 'replacements'
is_tape_end = False


manual_test_results = []
manual_check_results = []


detailed_info = False
if not manual_test_results:
    On, coefs, difs, test_results, matrix = test_complexity(
        get_test_result,
        tests, check,
        detailed_info=detailed_info,
        criteria=main_criteria,
        #is_tape_end=is_tape_end,
    )
else:
    On, coefs, difs, test_results, matrix = manual_test_complexity(
        manual_test_results,
        manual_check_results
    )
print("Test results: {}".format(test_results))
if On == -1:
    print("Complexity is undefined")
else:
    if manual_test_results:
        print("WARNING! Using manual test results")
    print(f"Complexity: O(n^{On})")
    print("Matrix:", matrix)
    print("Function: ", print_function(coefs))
    print("Confidence info:")
    print(difs)
appr_results = test_complexity_approximation(
    manual_test_results or get_test_result,
    tests, check,
    criteria=main_criteria,
    #is_tape_end=is_tape_end
)
print("Using approximation:", appr_results[1])
