"""OS information and directory operation examples."""

import os
import platform
from pathlib import Path


def collect_system_info():
    """Return a dictionary with useful runtime/system info."""
    info = {
        "python_version": platform.python_version(),
        "cwd": os.getcwd(),
        "pid": os.getpid(),
        "hostname": os.uname().nodename,
    }
    if hasattr(os, "getuid"):
        info["uid"] = os.getuid()
    return info


def demo_temp_dir(workdir):
    """Create and remove a demo folder in a safe, idempotent way."""
    target = Path(workdir) / "foo"
    target.mkdir(exist_ok=True)
    exists_after_create = target.exists()
    target.rmdir()
    exists_after_remove = target.exists()
    return exists_after_create, exists_after_remove


def main():
    """Run OS demos."""
    info = collect_system_info()
    print(f"PYTHON VERSION {info['python_version']}")
    print(f"GETCWD {info['cwd']}")
    print(f"PID {info['pid']}")
    print(f"UNAME {info['hostname']}")
    if "uid" in info:
        print(f"GETUID {info['uid']}")
    print(os.listdir(info["cwd"]))
    created, removed = demo_temp_dir(info["cwd"])
    print(f"FOO EXIST AFTER CREATE? {created}")
    print(f"FOO EXIST AFTER REMOVE? {removed}")


if __name__ == "__main__":
    main()
