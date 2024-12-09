import re

syscall_logs: list[str] = [
    "core/syscalls_core_test.txt",
    "examples/chat/syscalls_p1.txt",
    "examples/chat/syscalls_p2.txt",
]

syscall_names: set[str] = set()

for each in syscall_logs:
    with open(each, "r", encoding="utf-8") as f:
        while line := f.readline().strip():
            if (match_res := re.match(r"^([_a-zA-Z][_a-zA-Z0-9]*)", line)) is None:
                continue
            syscall_name: str = match_res.group(1)
            syscall_names.add(syscall_name)

syscall_names_list = sorted(syscall_names)
print(syscall_names_list)
