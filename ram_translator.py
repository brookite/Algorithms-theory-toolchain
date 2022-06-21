import pyparsing as pp
import argparse
import os
import sys
import ram2dasm


cmdparser = pp.Forward()

comment_string = pp.Word(pp.alphanums + " _!?,;.<>{}+-*/№()=&^$#@[]'\"" + pp.unicode.Cyrillic.alphas)
comment_postfix = pp.Optional("//" + comment_string)

reg = pp.Word(pp.nums).setParseAction(lambda toks: int(
    toks[0])).addCondition(lambda toks: toks[0] < 10)

tag = pp.Word(pp.alphanums + "_").setParseAction(lambda toks: str(toks[0]))
tag_prefix = pp.Optional(tag + ":")

inc = pp.Group(tag_prefix + 'inc' + reg + comment_postfix)
mov = pp.Group(tag_prefix + 'mov' + reg + reg + comment_postfix)
jmp_cond = pp.Group(tag_prefix + 'jmp' + reg + reg + tag + comment_postfix)
jmp = pp.Group(tag_prefix + 'jmp' + tag + comment_postfix)
zero = pp.Group(tag_prefix + 'zero' + reg + comment_postfix)

cmdparser <<= inc | zero | mov | jmp_cond | jmp


class RAMException(Exception):
    pass


class RAMCompileException(RAMException):
    pass


class RAMParsingException(RAMException):
    pass


class RAMRuntimeError(RAMException):
    pass


class RAMProgram:
    def __init__(self, object):
        if isinstance(object, str):
            object = object.split("\n")
        self._jump_replace = {}
        self._commands = []
        self._parse(object)

    @classmethod
    def from_file(cls, source):
        with open(source, "r", encoding="utf-8") as fobj:
            return cls(fobj.read().split("\n"))

    def _parse(self, lines):
        self._jump_replace["end"] = len(lines) + 1
        for i, line in enumerate(lines):
            try:
                cmds = cmdparser.parseString(line.strip(), parse_all=True)
                if ":" in list(cmds[0]):
                    tag_name = cmds[0][0].lower()
                    if tag_name not in self._jump_replace:
                        self._jump_replace[tag_name] = i + 1
                self._commands.append(tuple(cmds[0]))
            except pp.ParseException as e:
                raise RAMParsingException(
                    "Invalid command: {}. Parser message: {}".format(
                        line, str(e)))

    def _form_postfix(self, command):
        if "//" in command:
            i = command.index("//")
            if (i + 1) < len(command):
                return " //{}\n".format(command[i + 1].strip())
        return "\n"

    def compile(self):
        program = ""
        for i, command in enumerate(self._commands):
            if ":" in command:
                command = command[2:]

            if "//" in command:
                operator_count = len(command[:command.index("//")])
            else:
                operator_count = len(command)

            if command[0] == "inc":
                program += f"{i + 1} S({command[1]})" + \
                    self._form_postfix(command)
            elif command[0] == "mov":
                program += f"{i + 1} T({command[1]},{command[2]})" + \
                    self._form_postfix(command)
            elif command[0] == "zero":
                program += f"{i + 1} Z({command[1]})" + \
                    self._form_postfix(command)
            elif command[0] == "jmp":
                if operator_count == 2:
                    jmp = self._jump_replace.get(command[1])
                    if jmp:
                        program += f"{i + 1} J(1,1,{jmp})" + \
                            self._form_postfix(command)
                    else:
                        raise RAMCompileException(
                            f"Parse failed. Tag '{command[1]}' wasn't found")
                else:
                    jmp = self._jump_replace.get(command[3])
                    if jmp:
                        program += f"{i + 1} J({command[1]},{command[2]},{jmp})" + \
                            self._form_postfix(command)
                    else:
                        raise RAMCompileException(
                            f"Parse failed. Tag '{command[3]}' wasn't found")
            else:
                raise RAMCompileException(f"Unrecognized command: {command}")
        last_line = len(self._commands) + 1
        program += f"{last_line} *"
        return program


class RAMMachine:
    def __init__(self, program):
        self._registers = [0] * 9
        self._program = program

    @property
    def program(self):
        return self._program

    @program.setter
    def program(self, object):
        if isinstance(object, RAMProgram):
            self._program = object
        else:
            raise TypeError("RAMProgram required, not {}".format(
                type(object).__name__))

    @property
    def registers(self):
        return self._registers

    def null_registers(self):
        self._registers = [0] * 9

    def execute(self, max_iterations=10000, debug_prints=False, **kwargs):
        if len(kwargs):
            self.null_registers()
            for key in kwargs:
                if key.startswith("R"):
                    key = key[1:]
                    if key.isdigit():
                        reg = int(key) - 1
                        if 0 <= reg < 10:
                            self._registers[reg] = kwargs["R" + str(key)]
        trace_results = {
            "command_exec_count": {}, "commands_executed": 0,
            "initial_reg": tuple(self.registers)
        }
        instruction_pointer = 0
        iterations = 0
        while True:
            if instruction_pointer >= len(self.program._commands):
                break
            if iterations > max_iterations:
                raise RAMRuntimeError(
                    "Max iteration limit has reached. "
                    "Maybe, machine execution is infinite")
            command = self.program._commands[instruction_pointer]
            if ":" in command:
                command = command[2:]
            if command[0] == "inc":
                cmd = f"S({command[1]})"
                trace_results["command_exec_count"].setdefault(cmd, 0)
                trace_results["command_exec_count"][cmd] += 1

                self._registers[command[1] - 1] += 1

                if debug_prints:
                    print(f"{instruction_pointer+1} {cmd} ", end='')
                    print(f"R{command[1]}={self.registers[command[1] - 1] - 1}"
                          f" + 1 => {self.registers[command[1] - 1]} -->"
                          f"{instruction_pointer + 2}"
                          )
            elif command[0] == "mov":
                cmd = f"T({command[1]}, {command[2]})"
                trace_results["command_exec_count"].setdefault(cmd, 0)
                trace_results["command_exec_count"][cmd] += 1

                self._registers[command[2] - 1] = self._registers[command[1] - 1]
                if debug_prints:
                    print(f"{instruction_pointer+1} {cmd} ", end='')
                    print(f"R{command[2]}={self.registers[command[1] - 1]};"
                          f"R{command[2]}=R{command[1]}="
                          f"{self.registers[command[1] - 1]}"
                          f"--> {instruction_pointer + 2}"
                          )
            elif command[0] == "zero":
                cmd = f"Z({command[1]})"
                trace_results["command_exec_count"].setdefault(cmd, 0)
                trace_results["command_exec_count"][cmd] += 1

                self._registers[command[1] - 1] = 0

                if debug_prints:
                    print(f"{instruction_pointer+1} {cmd} ", end='')
                    print(f"R{command[1]}=0 --> {instruction_pointer + 2}")
            elif command[0] == "jmp":
                if "//" in command:
                    command = command[:command.index("//")]
                if len(command) == 2:
                    jmp = self.program._jump_replace.get(command[-1])
                    if jmp:
                        jmp -= 1
                        cmd = f"J(1, 1, {jmp+1})"
                        trace_results["commands_executed"] += 1
                        trace_results["command_exec_count"].setdefault(cmd, 0)
                        trace_results["command_exec_count"][cmd] += 1
                        if debug_prints:
                            print(f"{instruction_pointer+1} {cmd} ", end='')
                            print(f"R1==R1"
                                  f" -> {jmp+1}")
                        instruction_pointer = jmp
                        continue
                    else:
                        raise RAMRuntimeError(
                            f"Tag '{command[-1]}' wasn't found")
                else:
                    jmp = self.program._jump_replace.get(command[3])
                    if jmp:
                        jmp -= 1
                        cmd = f"J({command[1]}, {command[2]}, {jmp+1})"
                        trace_results["commands_executed"] += 1
                        trace_results["command_exec_count"].setdefault(cmd, 0)
                        trace_results["command_exec_count"][cmd] += 1

                        if self._registers[command[1] - 1] \
                                == self._registers[command[2] - 1]:
                            trace_results["commands_executed"] += 1

                            if debug_prints:
                                print(
                                    f"{instruction_pointer+1} {cmd} ",
                                    end='')
                                print(f"R{command[1]}==R{command[2]}"
                                      f"={self.registers[command[1] - 1]}"
                                      f" -> {jmp+1}")
                            instruction_pointer = jmp
                            continue
                    else:
                        raise RAMRuntimeError(
                            f"Tag '{command[3]}' wasn't found")
            else:
                raise RAMRuntimeError(f"Unknown command: {command}")
            iterations += 1
            instruction_pointer += 1
        trace_results["commands_executed"] = iterations
        trace_results["final_reg"] = self.registers
        return trace_results


def get_filelines(file, encoding="utf-8"):
    with open(file, encoding=encoding) as fobj:
        return fobj.readlines()


def compile_file(file):
    try:
        lines = get_filelines(file)
        program = RAMProgram(lines).compile()
        if program:
            print("\n")
            print(program)
    except RAMException as e:
        print("Error:", str(e), file=sys.stderr)


def get_machine(lines):
    program = RAMProgram(lines)
    return RAMMachine(program)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Реализация МПД машины с удобным синтаксисом (поддерживает компиляцию в .ram файлы)",
        prog="RAM Translator"
    )

    parser.add_argument("action", help="Основное действие: compile, execute")
    parser.add_argument("path", help="Путь к файлу")
    parser.add_argument("-r", "--reg", action="store")
    parser.add_argument("--notrace", action="store_true")
    parser.add_argument("-d", "--debug", action="store_true", default=False)

    args = parser.parse_args()

    if args.action == "compile":
        compile_file(args.path)
    elif args.action == "execute":
        if os.path.splitext(args.path)[1] == ".ram":
            lines = ram2dasm.parse(get_filelines(args.path, encoding="cp1251")).split("\n")
        else:
            lines = get_filelines(args.path)
        machine = get_machine(lines)
        regdict = {}
        if args.reg:
            reg = args.reg.split(";")
            for register in reg:
                register = register.split("=")
                regdict[register[0].upper()] = int(register[1])
        try:
            results = machine.execute(**regdict, debug_prints=args.debug)
            for i in range(len(machine.registers)):
                print(f"R{i+1}=", machine.registers[i])
            if not args.notrace:
                print(f"Всего команд выполнено:", results["commands_executed"])
                print(f"Изначальное состояние регистров:", results["initial_reg"])
                print("Статистика выполненных команд:")
                for key in results["command_exec_count"]:
                    print(key, results["command_exec_count"][key])
        except RAMException as e:
            print("Error:", str(e), file=sys.stderr)
