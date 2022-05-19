import re
import sys


PATTERN = re.compile(
    r"(\d+)\s{1,}([SZTJ])\((\d+),? ?(\d+)?,? ?(\d+)?\)(\s{1,}//(.+))?"
)
PROGRAM_FINAL_PATTERN = re.compile(
    r"(\d+)\s{1,}(\*)(\s{1,}//(.+))?"
)


def parse(lines):
    first_pass = {}
    jmp_markers = []
    for line in lines:
        if not line.strip():
            continue
        main_match = PATTERN.match(line)
        if main_match:
            number = main_match.group(1)
            command = main_match.group(2)
            arg1 = main_match.group(3)
            arg2 = main_match.group(4)
            arg3 = main_match.group(5)
            comment = main_match.group(7)
            if command == "S":
                if not arg1:
                    raise SyntaxError("Incorrect line:", line)
                first_pass[number] = ["inc", arg1, "//", comment]
            elif command == "Z":
                if not arg1:
                    raise SyntaxError("Incorrect line:", line)
                first_pass[number] = ["zero", arg1, "//", comment]
            elif command == "T":
                if not arg1 or not arg2:
                    raise SyntaxError("Incorrect line:", line)
                first_pass[number] = ["mov", arg1, arg2, "//", comment]
            elif command == "J":
                if not arg1 or not arg2 or not arg3:
                    raise SyntaxError("Incorrect line:", line)
                if int(arg3) == len(lines):
                    label = "end"
                else:
                    label = "label_" + arg3
                if arg2 != arg1:
                    first_pass[number] = [
                        "jmp", arg1, arg2, label, "//", comment]
                else:
                    first_pass[number] = [
                        "jmp", label, "//", comment]
                jmp_markers.append(arg3)
        else:
            end_match = PROGRAM_FINAL_PATTERN.match(line)
            if not end_match:
                raise SyntaxError(f"Incorrect line: {line}")

    for marker in jmp_markers:
        if int(marker) != len(lines):
            first_pass[marker] = ["label_" + marker + ":"] + first_pass[marker]

    line = ""
    for key in first_pass:
        tokens = first_pass[key]
        if tokens[-1] is None:
            tokens = tokens[:-2]
        else:
            tokens[-1] = tokens[-1].lstrip()
        line += " ".join(tokens) + "\n"
    return line.strip()


if __name__ == '__main__':
    if len(sys.argv) > 1:
        file = sys.argv[1]
        with open(file, encoding="cp1251") as fobj:
            lines = fobj.readlines()
            try:
                print(parse(lines[2:]))
            except SyntaxError as e:
                print("Error:", str(e), file=sys.stderr)
