import numpy as np
import warnings


warnings.filterwarnings("ignore")


def test_steps(tests, func, *args, **kwargs):
    steps = list(map(lambda x: func(x, *args, **kwargs), tests))
    return list(zip(map(lambda x: len(x), tests), steps))


def _measureO(coefs):
    i = 0
    while round(coefs[i]) == 0:
        i += 1
    return len(coefs) - 1 - i, coefs[i:]


def test_asymptotic(results, max_pow=5):
    for On in range(1, max_pow + 1):
        matrix = []
        steps_matrix = []
        for n, steps in results:
            line = []
            for k in range(0, On + 1):
                line.append(n ** k)
            steps_matrix.append(steps)
            line.reverse()
            matrix.append(line)
        try:
            x = np.linalg.solve(matrix, steps_matrix)
            return *_measureO(x), matrix
        except np.linalg.LinAlgError:
            pass
    return None, None, None


def coef_function(coefs):
    coefs = coefs[::-1]

    def g(n):
        result = 0
        for i, c in enumerate(coefs):
            result += (n ** i) * c
        return result

    return g


def manual_test_complexity(manual_test_results, manual_check_results):
    On, coefs, matrix = test_asymptotic(manual_test_results)
    if On is None or coefs is None:
        return -1, None, None, None
    else:
        difs = {}
        g = coef_function(coefs)
        for item, value in manual_check_results:
            n = len(item)
            difs[n] = g(n) - value
        return On, coefs, difs, manual_test_results, matrix


def test_complexity(test_func, test_data, check_data, *args, **kwargs):
    detailed_info = kwargs.get("detailed_info")
    kwargs.pop("detailed_info")
    if callable(test_func):
        test_results = test_steps(test_data, test_func, *args, **kwargs)
    else:
        test_results = test_func
    On, coefs, matrix = test_asymptotic(test_results)
    if On is None or coefs is None:
        return -1, None, None, None
    else:
        difs = {}
        g = coef_function(coefs)
        for item in check_data:
            n = len(item)
            if kwargs.get("detailed_info"):
                difs[n] = {
                    "g(n)": g(n),
                    "program": test_func(item, *args, **kwargs),
                    "dif": g(n) - test_func(item, *args, **kwargs)
                }
            else:
                difs[n] = g(n) - test_func(item, *args, **kwargs)
        return On, coefs, difs, test_results, matrix


def approximation_test(results, func_type="polynomial", max_pow=5):
    n, t = list(zip(*results))
    result = []
    coef_array = []
    if func_type == "polynomial":
        for pow in range(0, max_pow + 1):
            coefs = np.polyfit(n, t, pow)
            result.append(coef_function(coefs))
            coef_array.append(coefs)
    elif func_type == "log":
        coefs = np.polyfit(np.log(n), t, 1)
        result.append(coef_function(coefs))
        coef_array.append(coefs)
    elif func_type == "exp":
        coefs = np.polyfit(n, np.log(t), 1)
        result.append(coef_function(coefs))
        coef_array.append(coefs)
    return result, coef_array


def test_complexity_approximation(
        test_func, test_data, check_data, *args, **kwargs):
    test_results = test_steps(test_data, test_func, *args, **kwargs)
    functions_map = {}
    # polynomial
    functions, coefs = approximation_test(test_results)
    for i, function in enumerate(functions):
        functions_map[function] = "polynomial", coefs[i]

    # log
    functions, coefs = approximation_test(test_results, func_type="log")
    for i, function in enumerate(functions):
        functions_map[function] = "log", coefs[i]

    # exp
    functions, coefs = approximation_test(test_results, func_type="exp")
    for i, function in enumerate(functions):
        functions_map[function] = "exp", coefs[i]

    min_function = None
    min_mid_dif = float("inf")
    for function in functions_map:
        s = 0
        for item in check_data:
            n = len(item)
            dif = function(n) - test_func(item, *args, **kwargs)
            s += dif
        mid_dif = s / len(check_data)
        if mid_dif < min_mid_dif and mid_dif > -1:
            min_function = function
            min_mid_dif = mid_dif
    return min_function, functions_map[min_function]
