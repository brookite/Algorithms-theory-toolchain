import io
import re
import os
import argparse
import sys
import time


class MarkovException(Exception):
    pass


class MarkovCompileException(MarkovException):
    pass


class MarkovRuntimeError(MarkovException):
    pass


class Table:
    def __init__(self, array):
        self.fields = []
        self._correct_fields(array)  # rstrip alternative

    def add_field(self, src, dst, comment):
        if dst is None:
            dst = ''
        if src is None:
            src = ''
        if comment is None:
            comment = ''

        if len(comment) == len(src) == len(dst) == 0:
            return

        if src and not dst:
            self.fields.append([src])
        else:
            self.fields.append([src, dst, comment])

    @staticmethod
    def recognize_field(field):
        if len(field) == 0:
            return '', '', ''
        elif len(field) == 1:
            return field[0], '', ''
        elif len(field) == 2:
            return field[0], field[1], ''
        elif len(field) == 3:
            return field[0], field[1], field[2]
        else:
            raise MarkovException("Invalid field value, length > 3")

    def _correct_fields(self, array):
        for field in array:
            self.add_field(*Table.recognize_field(field))

    def __iter__(self):
        return iter(self.fields)

    def __len__(self):
        return len(self.fields)

    def __getitem__(self, key):
        for pair in self:
            if pair[0] == key:
                return pair[1]

    def to_bytes(self):
        return ("\r\n".join(map(
            lambda x: "\t".join(x), self.fields)) + "\r\n").encode("cp1251")

    @classmethod
    def from_bytes(cls, source):
        return cls(tuple(map(lambda x: x.split("\t"),
                             source.decode("cp1251").split("\r\n"))))


class MarkovFile:
    def __init__(self, table, word="", solution=""):
        self._solution = solution
        self._table = table
        self._word = word

    def merge(self, other):
        copy = MarkovFile(self._table, self._word, self._solution)
        copy._table.fields.extend(other._table.fields)

    @property
    def word(self):
        return self._word

    @property
    def table(self):
        return self._table

    @property
    def solution(self):
        return self._solution

    def to_bytes(self):
        f = io.BytesIO()

        solution = self._solution.encode("cp1251")
        solution_length = len(solution).to_bytes(4, "little")
        word = (self._word + "\r\n").encode("cp1251")
        word_length = len(word).to_bytes(4, "little")
        table = self._table.to_bytes()
        table_length = len(table).to_bytes(4, "little")

        f.write(solution_length)
        f.write(solution)
        f.write(word_length)
        f.write(word)
        f.write(table_length)
        f.write(table)
        result = f.getvalue()
        f.close()
        return result

    @classmethod
    def from_bytes(cls, source):
        if isinstance(source, cls):
            return source
        elif isinstance(source, bytes):
            f = io.BytesIO(source)
        elif isinstance(source, io.BytesIO):
            f = source
        else:
            f = open(source, "rb")

        solution_length = int.from_bytes(f.read(4), "little")
        solution = f.read(solution_length).decode("cp1251")

        word_length = int.from_bytes(f.read(4), "little")
        word = f.read(word_length).decode("cp1251").replace("\r\n", "")

        table_length = int.from_bytes(f.read(4), "little")
        table = Table.from_bytes(f.read(table_length))

        return cls(table, word, solution)


class MarkovMachine:
    WORD_TEMPLATE = r"^WORD\s{0,}:\s{0,}(.{0,})$"
    COMMAND_COMMENT_TEMPLATE = r"^(.{0,})->(.{0,})(\s{0,}//(.{0,}))$"
    COMMAND_TEMPLATE = r"^(.{0,})->(.{0,})$"
    SOLUTION_TEMPLATE = r"^SOLUTION\s{0,}:\s{0,}(.{0,})$"

    def __init__(self, object):
        self._solution = ''
        self._table = None
        self._word = ''
        if not isinstance(object, MarkovFile):
            self.compile(object)
            self._file = self.link()
        else:
            self._file = object
            self._table = object.table
            self._word = object.word
            self._solution = object.solution

    @property
    def word(self):
        return self._word

    @word.setter
    def word(self, value):
        self._word = value

    @property
    def table(self):
        return self._table

    @property
    def file(self):
        return self._file

    @property
    def solution(self):
        return self._solution

    @solution.setter
    def solution(self, value: str):
        self._solution = value

    def compile(self, lines):
        fields = []
        is_solution = False
        for line in lines:
            line = line.strip()
            match = re.match(self.COMMAND_TEMPLATE, line)
            comment_match = re.match(self.COMMAND_COMMENT_TEMPLATE, line)
            if comment_match:
                is_solution = False
                pair = [comment_match.group(1),
                        comment_match.group(2),
                        comment_match.group(4)]
                fields.append(pair)
            elif match:
                is_solution = False
                pair = [match.group(1),
                        match.group(2)]
                fields.append(pair)
            else:
                check_word = re.match(self.WORD_TEMPLATE, line)
                check_solution = re.match(self.SOLUTION_TEMPLATE, line)
                if check_word and not check_solution and not self._word:
                    self._word = check_word.group(1)
                    is_solution = False
                elif check_solution and not check_word and not self._solution:
                    self._solution = check_solution.group(1)
                    is_solution = True
                elif is_solution:
                    self._solution += "\n" + line
                else:
                    raise MarkovCompileException(
                        "Unrecognized line: {}".format(line))
        self._table = Table(fields)

    def link(self):
        return MarkovFile(self.table, self.word, self.solution)

    def execute(self,
                input_word=None,
                max_iterations=10000,
                debug_prints=False,
                delay=0):
        replacements = 0
        iterations = 0
        initial_word = input_word or self.word
        word = initial_word
        trace_results = {
            "command_exec_count": {}, "steps": [word],
            "total_replace_templates": len(self.table)}
        failures = 0
        stop_iteration_flag = False
        while failures != len(self.table) and not stop_iteration_flag:
            if iterations > max_iterations:
                raise MarkovRuntimeError("Max iterations limit has reached")
            failures = 0
            for field in self.table:
                src, dst, _ = Table.recognize_field(field)
                if src in word:
                    if dst.startswith("."):
                        stop_iteration_flag = True
                        dst = dst[1:]
                        replacement_pattern = f"{src}->.{dst}"
                    elif dst.endswith("."):
                        stop_iteration_flag = True
                        dst = dst[:-1]
                        replacement_pattern = f"{src}->.{dst}"
                    else:
                        replacement_pattern = f"{src}->{dst}"
                    replacements += 1
                    trace_results["command_exec_count"].setdefault(replacement_pattern, 0)
                    trace_results["command_exec_count"][replacement_pattern] += 1
                    if src == "":
                        word = dst + word
                    else:
                        word = word.replace(src, dst, 1)
                    if debug_prints:
                        print(src, "->", dst, ":", word)
                    trace_results["steps"].append(word)
                    iterations += 1
                    break
                else:
                    failures += 1
                iterations += 1
            time.sleep(delay)
        trace_results["replacements"] = replacements
        trace_results["iterations"] = iterations
        return initial_word, word, trace_results


def compile_file(path):
    name = os.path.splitext(os.path.split(path)[-1])[0]
    with open(path, "r") as fobj:
        lines = fobj.readlines(False)
    program = MarkovMachine(lines)
    with open(os.path.join(
            os.path.dirname(path), name + ".nma"), "wb") as fobj:
        fobj.write(program.file.to_bytes())
    return program


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Альтернативная реализация машины Маркова (поддерживает файлы .nma)",
        prog="Altturing"
    )

    parser.add_argument("action", help="Основное действие:compile,execute,view")
    parser.add_argument("path", help="Основной файл для работы")
    parser.add_argument("--notrace", action="store_true", help="Вывести только результат, без статистики")
    parser.add_argument("-w", "--word", action="store", help="Исходное слово")
    parser.add_argument("-d", "--debug", action="store_true", default=False, help="Включить пошаговое отображение")

    args = parser.parse_args()
    if args.action == "compile":
        if os.path.isdir(args.path):
            for file in os.listdir(args.path):
                path = os.path.join(args.path, file)
                if os.path.splitext(path)[1] == ".altnma":
                    compile_file(path)
        else:
            compile_file(args.path)
    elif args.action == "execute":
        if os.path.splitext(args.path)[1] != ".nma":
            program = compile_file(args.path)
        else:
            program = MarkovMachine(MarkovFile.from_bytes(args.path))
        try:
            if args.word:
                initial_word = args.word
            else:
                initial_word = None
            initial_word, word, results = program.execute(
                initial_word, debug_prints=args.debug)
            print(initial_word, "->", word)
            if not args.notrace:
                print("Выполнено замен:", results["replacements"])
                print("Выполнено итераций:", results["iterations"])
                print("Длина изначального слова:", len(initial_word))
                print("Длина конечного слова:", len(word))
                print("Всего замен в таблице:", results["total_replace_templates"])
                print("Статистика выполненных команд:")
                for key in results["command_exec_count"]:
                    print(key, results["command_exec_count"][key])
        except MarkovRuntimeError as e:
            print("Ошибка:", str(e), file=sys.stderr)
    elif args.action == "view":
        if os.path.splitext(args.path)[1] != ".nma":
            program = compile_file(args.path)
        else:
            program = MarkovMachine(MarkovFile.from_bytes(args.path))
        print(f"WORD:{program.word}")
        for line in program.table:
            if line[2].strip():
                print(f"{line[0]}->{line[1]} //{line[2]}")
            else:
                print(f"{line[0]}->{line[1]}")
