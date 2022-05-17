import io
import os.path
from dataclasses import dataclass
import re
import sys
import time
import argparse


class TuringException(Exception):
    pass


class TuringRuntimeError(TuringException):
    pass


class TuringCompileException(TuringException):
    pass


class Table:
    def __init__(self, fields, q_count):
        self._q_count = q_count
        if "_" not in fields:
            fields["_"] = ["" for i in range(q_count)]
        if " " in fields:
            fields["_"] = fields[" "]
            fields.pop(" ")
        self._fields = fields

    @property
    def fields(self):
        return self._fields

    def action(self, symbol, state):
        if symbol.strip() == "":
            symbol = "_"
        if 0 < state <= self.q_count and symbol in self.fields.keys():
            return self.fields[symbol][state - 1]
        else:
            return None

    def set_action(self, symbol, state, new_symbol, action, new_state):
        if 0 < state <= self.q_count and symbol in self.fields.keys() \
                and new_symbol in self.fields.keys() and action in "<>.":
            # new_state mustn't be checked
            self.fields[symbol][state - 1] = (new_symbol + action + str(new_state))
            return True
        else:
            return False

    def to_bytes(self):
        buf = b"\t" + b"\t".join([
            b"Q" + bytes(str(x), "cp1251") for x in range(1, self.q_count + 1)])
        buf += b"\r\n"
        for field in self.fields:
            if field == b"_":
                buf += b" "
            else:
                buf += field.encode("cp1251")
            buf += b"\t" + b"\t".join(
                map(lambda x: x.encode("cp1251"), self.fields[field]))
            if field != b" ":
                buf += b"\r\n"
        return buf, len(buf)

    @property
    def q_count(self):
        return self._q_count

    @classmethod
    def from_bytes(cls, source, q_count):
        source = source[1:-1]
        fields = {}
        for field in source:
            field = field.split(b"\t")
            if field[0] == b" ":
                field[0] = "_"
            else:
                field[0] = field[0].decode("cp1251")
            fields[field[0]] = list(
                map(lambda x: x.decode("cp1251"), field[1:][:q_count]))
        return cls(fields, q_count)


@dataclass
class Tape:
    begin: int
    end: int
    pointer: int
    tape: str


class TuringFile:
    def __init__(self, table: Table, tape: Tape, comment="", solution=""):
        self._table = table
        self._tape = tape
        self._comment = comment
        self._solution = solution

    @property
    def table(self):
        return self._table

    @property
    def comment(self):
        return self._comment

    @property
    def solution(self):
        return self._solution

    @property
    def tape(self):
        return self._tape

    def to_bytes(self):
        f = io.BytesIO()
        comment = self._comment.encode("cp1251")
        solution = self._solution.encode("cp1251")
        f.write(len(solution).to_bytes(4, "little"))
        f.write(solution)
        f.write((self.table.q_count + 1).to_bytes(4, "little"))
        table, table_length = self.table.to_bytes()
        f.write(table_length.to_bytes(4, "little"))
        f.write(table)
        f.write(len(comment).to_bytes(4, "little"))
        f.write(comment)
        if self.tape.begin < 0:
            begin = 2**32 + self.tape.begin
        else:
            begin = self.tape.begin
        if self.tape.end < 0:
            end = 2**32 + self.tape.end
        else:
            end = self.tape.end
        if self.tape.pointer < 0:
            pointer = 2**32 + self.tape.pointer
        else:
            pointer = self.tape.pointer
        f.write(begin.to_bytes(4, "little"))
        f.write(end.to_bytes(4, "little"))
        f.write(pointer.to_bytes(4, "little"))
        f.write(self.tape.tape.encode("cp1251"))
        result = f.getvalue()
        f.close()
        return result

    def _recount(self, q, fields):
        fields = list(fields)
        for i in range(len(fields)):
            if not len(fields[i]):
                continue
            char, commands = self._split_commands(fields[i])
            state = int(commands[-1])
            if state != 0:
                new_state = (state - 1) + q
                commands[-1] = str(new_state)
            fields[i] = char.join(commands)
        return fields

    def _split_commands(self, command):
        if ">" in command:
            char = ">"
        elif "." in command:
            char = "."
        elif "<" in command:
            char = "<"
        else:
            raise ValueError("Invalid command: {}".format(command))
        return char, command.split(char)

    def merge(self, other):
        if not isinstance(other, TuringFile):
            raise TypeError("Required TuringFile object for merging")
        new_q = self.table.q_count + other.table.q_count
        next_q = self.table.q_count + 1
        fields_1 = dict(self.table.fields)
        fields_2 = dict(other.table.fields)
        for field in fields_1:
            for i in range(len(fields_1[field])):
                if not len(fields_1[field][i]):
                    continue
                char, commands = self._split_commands(fields_1[field][i])
                if int(commands[-1]) == 0:
                    commands[-1] = str(next_q)
                fields_1[field][i] = char.join(commands)
        for field in fields_2:
            if field not in fields_1:
                fields_1[field] = ["" for i in range(self.table.q_count)] + \
                    self._recount(next_q, fields_2[field])
            else:
                fields_1[field] += self._recount(next_q, fields_2[field])
        table = Table(fields_1, new_q)
        return TuringFile(table, self.tape, self._comment, self._solution)

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

        q_count = int.from_bytes(f.read(4), "little") - 1
        table_length = int.from_bytes(f.read(4), "little")
        table = f.read(table_length).split(b"\r\n")
        comment_length = int.from_bytes(f.read(4), "little")
        comment = f.read(comment_length).decode("cp1251")
        begin = int.from_bytes(f.read(4), "little")
        end = int.from_bytes(f.read(4), "little")
        pointer = int.from_bytes(f.read(4), "little")
        if 2**32 - begin < (2**32) / 2:
            begin = -(2 ** 32 - begin)
        if 2**32 - end < (2**32) / 2:
            end = -(2**32 - end)
        if 2**32 - pointer < (2**32) / 2:
            pointer = -(2 ** 32 - pointer)
        tape = f.read().decode("cp1251")
        tape = Tape(begin, end, pointer, tape)
        table = Table.from_bytes(table, q_count)
        f.close()
        return cls(table, tape, comment, solution)


class TuringMachine:
    HEADER_TEMPLATE = r"^DEFINE\s{0,}Q\s{0,}(\d+);TAPE\s{0,}:\s{0,}(\w{0,});POS\s{0,}:\s{0,}(-?\d{0,});{0,}$"
    COMMAND_TEMPLATE = r"^([^>.<]) [Qq](\d+)\s{0,}:\s{0,}([^>.<])([>.<])[Qq]{0,1}(\d+)$"
    COMMENT_TEMPLATE = r"^COMMENT\s{0,}:\s{0,}(.{0,})$"
    SOLUTION_TEMPLATE = r"^SOLUTION\s{0,}:\s{0,}(.{0,})$"

    def __init__(self, object):
        self._comment = ""
        self._solution = ""
        self._table = None
        self._tape = None
        if not isinstance(object, TuringFile):
            self.compile(object)
            self._file = self.link()
        else:
            self._file = object
            self._table = object.table
            self._solution = object.solution
            self._comment = object.comment
            self._tape = object.tape

    @property
    def word(self):
        return self._tape.tape

    @property
    def tape(self):
        return self._tape

    @property
    def table(self):
        return self._table

    @property
    def file(self):
        return self._file

    @property
    def solution(self):
        return self._solution

    @property
    def comment(self):
        return self._comment

    @comment.setter
    def comment(self, value: str):
        self._comment = value

    @solution.setter
    def solution(self, value: str):
        self._solution = value

    @word.setter
    def word(self, value: str):
        self._tape = Tape(
            self.tape.begin, self.tape.end,
            self.tape.pointer, value)

    def compile(self, lines):
        is_solution = False
        is_comment = False
        for line in lines:
            line = line.strip()
            if not self.table:
                match = re.match(self.HEADER_TEMPLATE, line)
                if match:
                    q_count = int(match.group(1))
                    tape = str(match.group(2))
                    alphabet = set(tape)
                    alphabet.update(" ")
                    fields = dict.fromkeys(alphabet)
                    for field in fields:
                        fields[field] = ["" for i in range(q_count)]
                    begin, end = 0, len(tape) - 1
                    pointer = int(match.group(3))
                    if pointer < 0:
                        pointer = (len(tape) + pointer) % len(tape)
                    self._tape = Tape(begin, end, pointer, tape)
                    self._table = Table(fields, q_count)
                else:
                    raise TuringCompileException("Header wasn't found")
            else:
                raw_command = re.match(self.COMMAND_TEMPLATE, line)
                if raw_command:
                    is_solution = False
                    is_comment = False
                    curr_char = raw_command.group(1)
                    curr_state = int(raw_command.group(2))
                    char = raw_command.group(3)
                    action = raw_command.group(4)
                    state = int(raw_command.group(5))
                    result = self.table.set_action(
                        curr_char, curr_state, char, action, state)
                    if not result:
                        raise TuringCompileException(
                            "Invalid command: {}".format(line))
                else:
                    check_comment = re.match(self.COMMENT_TEMPLATE, line)
                    check_solution = re.match(self.SOLUTION_TEMPLATE, line)
                    if check_comment and not self.comment:
                        self.comment = check_comment.group(1)
                        if self.comment is None:
                            self._comment = ''
                        is_comment = True
                        is_solution = False
                    if check_solution and not self.solution:
                        self.solution = check_solution.group(1)
                        if self.solution is None:
                            self._solution = ''
                        is_solution = True
                        is_comment = False

                    if not check_solution and not check_comment:
                        if is_solution:
                            self._solution += "\n" + line
                        elif is_comment:
                            self._comment += "\n" + line
                        else:
                            raise TuringCompileException(
                                "Unrecognized line: {}".format(line))

    def link(self):
        return TuringFile(self.table, self.tape, self.comment, self.solution)

    def execute(self,
                tape=None,
                max_iterations=5096,
                debug_prints=False,
                delay=0):
        tape = tape or Tape(
            self.tape.begin, self.tape.end, self.tape.pointer, self.tape.tape)
        state = 1
        iterations = 0
        used_cells = set([tape.pointer])
        trace_results = {"command_exec_count": {}, "state_use_count": {1: 1}}
        while state != 0:
            if tape.pointer > tape.end:
                tape.tape += " " * (tape.pointer - tape.end)
                tape.end += (tape.pointer - tape.end)
            elif tape.pointer < tape.begin:
                tape.tape = " " * (tape.begin - tape.pointer) + tape.tape
                tape.begin -= (tape.begin - tape.pointer)
            local_pointer = tape.pointer - tape.begin
            if debug_prints:
                print(f"Internal debug: Tape[{tape.begin}:{tape.end}][{tape.pointer}]: {repr(tape.tape)};"
                      f"State: {state}, Local Pointer: {local_pointer}")
                tape_repr = repr(tape.tape[:local_pointer] + ">" + tape.tape[local_pointer:])
                print(f"BEFORE: {tape_repr}, q{state}")
            if iterations > max_iterations:
                raise TuringRuntimeError(
                    "Max iteration limit has reached. "
                    "Maybe, machine execution is infinite")
            action = self.table.action(tape.tape[local_pointer], state)
            if action is None:
                raise TuringRuntimeError(
                    "Action for this state {} and char {} wasn't found".format(
                        state, tape.tape[local_pointer]))
            trace_results["command_exec_count"].setdefault(action, 0)
            trace_results["command_exec_count"][action] += 1
            if ">" in action:
                action = action.split(">")
                shift = 1
            elif "." in action:
                action = action.split(".")
                shift = 0
            elif "<" in action:
                action = action.split("<")
                shift = -1
            else:
                raise TuringRuntimeError(
                    "Invalid action command: {}".format(action))
            if action[0] == "_":
                action[0] = ' '
            tape.tape = tape.tape[:local_pointer] + \
                action[0] + tape.tape[local_pointer + 1:]
            tape.pointer += shift
            used_cells.add(tape.pointer)
            if debug_prints:
                tape_repr = repr(tape.tape[:local_pointer] + ">" + tape.tape[local_pointer:])
                print(f"AFTER: {tape_repr}, q{state}->q{action[1]}")
            state = int(action[1])
            trace_results["state_use_count"].setdefault(state, 0)
            trace_results["state_use_count"][state] += 1
            iterations += 1
            time.sleep(delay)
        trace_results["iterations"] = iterations
        trace_results["used_cells"] = len(used_cells)
        return tape, trace_results


def compile_file(path):
    name = os.path.splitext(os.path.split(path)[-1])[0]
    with open(path, "r") as fobj:
        lines = fobj.readlines(False)
    program = TuringMachine(lines)
    with open(os.path.join(os.path.dirname(path), name + ".tur"),
              "wb") as fobj:
        fobj.write(program.file.to_bytes())
    return program


def merge_two_programs(file1, file2):
    program1 = TuringFile.from_bytes(file1)
    program2 = TuringFile.from_bytes(file2)
    return program1.merge(program2)


def merge_programs(files):
    files.reverse()
    files = list(
        filter(
            lambda x: os.path.splitext(x)[1] == ".tur",
            files
        )
    )
    if len(files) >= 2:
        current = files.pop()
        print("Первый файл на обработку", current)
        while len(files) > 0:
            next = files.pop()
            print("Обработка файла", next)
            current = merge_two_programs(current, next)
    return current


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Альтернативная реализация машины Тьюринга (поддерживает файлы .tur)",
        prog="Altturing"
    )

    parser.add_argument("action", help="Одно из действий: compile,execute,view,merge")
    parser.add_argument("path", help="Основной файл для работы или директория (если merge)")
    parser.add_argument("--notrace", action="store_true", help="Вывести только результат, без статистики")
    parser.add_argument("-w", "--word", action="store", help="Исходное слово")
    parser.add_argument("-d", "--debug", action="store_true", default=False, help="Включить пошаговое отображение")

    args = parser.parse_args()
    if args.action == "compile":
        if os.path.isdir(args.path):
            for file in os.listdir(args.path):
                path = os.path.join(args.path, file)
                if os.path.splitext(path)[1] == ".alttur":
                    compile_file(path)
        else:
            compile_file(args.path)
    elif args.action == "execute":
        if os.path.splitext(args.path)[1] != ".tur":
            program = compile_file(args.path)
        else:
            program = TuringMachine(TuringFile.from_bytes(args.path))
        try:
            tape = None
            if args.word:
                if ">" in args.word:
                    word = args.word.split(">")
                    tape = Tape(
                        0, len(word[0]) + len(word[1]) - 1,
                        len(word[0]), "".join(word))
                else:
                    tape = Tape(0, len(args.word) - 1, 0, args.word)
            tape, results = program.execute(tape, debug_prints=args.debug)
            print(repr(tape.tape))
            if not args.notrace:
                print("Выполнено команд: ", results["iterations"])
                print("Использовано ячеек: ", results["used_cells"])
                print("Статистика выполненных команд:")
                for key in results["command_exec_count"]:
                    print(key, results["command_exec_count"][key])
        except TuringRuntimeError as e:
            print("Ошибка:", str(e), file=sys.stderr)
    elif args.action == "view":
        if os.path.splitext(args.path)[1] != ".tur":
            program = compile_file(args.path)
        else:
            program = TuringMachine(TuringFile.from_bytes(args.path))
        local_pointer = program.tape.pointer - program.tape.begin
        print(
            "DEFINE Q{};TAPE:{};POS:{}".format(
                program.table.q_count, program.tape.tape, local_pointer))
        if program.comment:
            print(f"COMMENT:{program.comment}")
        if program.solution:
            print(f"SOLUTION:{program.solution}")
        for symbol in program.table.fields:
            for q in range(1, program.table.q_count + 1):
                if program.table.action(symbol, q).strip():
                    print("{} q{}: {}".format(
                        symbol, q, program.table.action(symbol, q)))
    elif args.action == "merge":
        if not os.path.isdir(args.path):
            args.path = ""
        files = input("Введите названия файлов для объединения по порядку через запятую: ").split(',')
        file = merge_programs(list(map(lambda x: os.path.join(args.path, x), files)))
        with open(os.path.join(args.path, "merged.tur"), "wb") as fobj:
            fobj.write(file.to_bytes())
