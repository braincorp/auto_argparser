from typing import Sequence
from open.auto_argparser.auto_argparser import AutoArgParser


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
