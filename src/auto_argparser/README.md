

# Auto Argparser

Auto Argparser is a tool for making any type-annotated Python function callable from command line.  It builds upon the built-in `argparse.ArgumentParser()`, and aims to be cleaner and more intuitive than other argument-parsing packages like [Click](https://github.com/pallets/click).

## A Simple Example

Lets make an analog of [this example from Click](https://github.com/pallets/click/blob/main/README.rst#a-simple-example), in a file called `hello_auto_argparser.py` containing:

```python
from auto_argparser import AutoArgParser


def hello(count: int, name: str):
    """
    Simple program that greets NAME for a total of COUNT times.
    :param count: The number of times to repeat 
    :param name: The name to repeat
    """
    for _ in range(count):
        print(f"Hello, {name}!")


if __name__ == '__main__':
    AutoArgParser(hello).call_from_command_line()
```

You can now call this script from commandline by passing arguments in order:

```text
$ python3 hello_auto_argparser.py 3 world
Hello, world!
Hello, world!
Hello, world!
```

Or by keyword: `python3 hello_auto_argparser.py --name=world --count=3`.

The type-annotations tell AutoArgparser how to parse the arguments.

You can view documentation on a function by passing `--help`: 

```text
$ python3 hello_auto_argparser.py --help
usage: hello_auto_argparser.py [-h] [--count COUNT] [--name NAME]

    Simple program that greets NAME for a total of COUNT times.
    :param count: The number of times to repeat
    :param name: The name to repeat

optional arguments:
  -h, --help     show this help message and exit
  --count COUNT  The number of times to repeat
  --name NAME    The name to repeat

```

## A Complex example

The following example computes an exponential moving average of a sequence and prints the result: 

```python 
from typing import Sequence
from auto_argparser import AutoArgParser


def exponential_moving_average(items: Sequence[float], decay: float = 0.25, start_average_at_first: bool = False
                               ) -> Sequence[float]:
    """ Compute an exponential moving average of the input items """
    averages = []
    for item in items:
        if len(averages) == 0:
            avg = item if start_average_at_first else 0.
        else:
            avg = averages[-1] * (1-decay) + item * decay
        averages.append(avg)
    return averages


if __name__ == '__main__':
    AutoArgParser(exponential_moving_average, print_report=True, short_names=dict(start_average_at_first='s')
                  ).call_from_command_line()
```
In this example we demonstrate a few features of autoargparser: 
- Using `,` to delimit items in a sequence.
- Passing boolean arguments with `--arg=True`/`--arg=False` or, for short, just `--arg` to pass True. 
- Using `short_names` defined above by passing just `-s` instead of `--start_average_at_first`
- Printing return value with `print_report=True`

```text
python3 exponential_moving_average.py 2,2,0,0,1 -s
........
Call to 'exponential_moving_average 2,2,0,0,1 -s' took 0.00s and returned [2.0, 2.0, 1.5, 1.125, 1.09375]
```

For futher examples of advanced usage, look in `test_auto_argparser.py`


## More Open Source Packages from BrainCorp

Check out more open-source code at https://github.com/braincorp

Interested in working at BrainCorp?  Visit https://www.braincorp.com/company/careers/ 