from auto_argparser import AutoArgParser


def hello(count: int, name: str):
    """    Simple program that greets NAME for a total of COUNT times.
    :param count: The number of times to repeat
    :param name: The name to repeat"""
    for _ in range(count):
        print(f"Hello, {name}!")


if __name__ == '__main__':
    AutoArgParser(hello).call_from_command_line()
