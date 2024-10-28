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

# 'accept4', 'access', 'arch_prctl', 'bind', 'brk', 'chdir', 'clone3', 'close', 'epoll_create1', 'epoll_ctl', 'eventfd2', 'execve', 'exit_group', 'fcntl', 'flock', 'fstat', 'fsync', 'futex', 'getcwd', 'getdents64', 'geteuid', 'getpid', 'getrandom', 'getsockname', 'getuid', 'ioctl', 'listen', 'lseek', 'lstat', 'mkdir', 'mmap', 'mprotect', 'munmap', 'newfstatat', 'openat', 'pipe2', 'poll', 'pread64', 'prlimit64', 'pwrite64', 'read', 'readlink', 'recvfrom', 'rseq', 'rt_sigaction', 'rt_sigprocmask', 'sched_getaffinity', 'sched_yield', 'sendto', 'set_robust_list', 'set_tid_address', 'setsockopt', 'sigaltstack', 'socket', 'socketpair', 'stat', 'statfs', 'statx', 'strace', 'sysinfo', 'tgkill', 'uname', 'unlink', 'wait4', 'write'
