"""Simple threading demonstration."""

from threading import Thread


def hello_world(name):
    """Print the thread label."""
    print(f"Thread name: {name}")


def run_demo():
    """Start a few short-lived threads and wait for completion."""
    threads = [
        Thread(target=hello_world, args=("foo",)),
        Thread(target=hello_world, args=("bar",)),
        Thread(target=hello_world, args=("baz",)),
    ]
    for worker in threads:
        worker.start()
    for worker in threads:
        worker.join()


if __name__ == "__main__":
    run_demo()
