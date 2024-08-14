"""
Async guess the number flow
==============================

An async example of Workflow for the well know game.

In order to pay the game, run this script and type a number between 1 and 5.
The command line should include an extra param to run the script in interactive mode:

On the root folder of the project, run:

    ``python tests/examples/async_guess_the_number_machine.py -i``

It's worth to mention that the same state flow can be used in syncronous code, as shown in the
docstring of the class. You can play on sync contextif you also pass the `-s` flag:

    ``python tests/examples/async_guess_the_number_machine.py -i -s``

"""

import asyncio
import random
import sys

from workflow import State
from workflow import Workflow


class GuessTheNumberMachine(Workflow):
    """
    Guess the number flow.

    This docstring exercises the SAME `GuessTheNumberMachine` in syncronous code.

    >>> workflow = GuessTheNumberMachine(print, seed=103)
    I'm thinking of a number between 1 and 5. Can you guess what it is? >>>

    >>> while not workflow.current_state.final:
    ...     workflow.send("guess", random.randint(1, 5))
    Your guess is 2...
    Too low. Try again. >>>
    Your guess is 1...
    Too low. Try again. >>>
    Your guess is 5...
    Too high. Try again. >>>
    Your guess is 1...
    Too low. Try again. >>>
    Your guess is 4...
    Congratulations, you guessed the number in 5 guesses!

    """

    start = State(initial=True)
    low = State()
    high = State()
    won = State(final=True)
    lose = State(final=True)

    guess = (
        lose.from_(low, high, cond="max_guesses_reached")
        | won.from_(low, high, start, cond="guess_is_equal")
        | low.from_(low, high, start, cond="guess_is_lower")
        | high.from_(low, high, start, cond="guess_is_higher")
    )

    def __init__(self, writer, max_attempts=5, lower=1, higher=5, seed=42):
        self.writer = writer
        self.max_attempts = max_attempts
        self.lower = lower
        self.higher = higher
        self.guesses = 0

        # lets play a not so random game, or our tests will be crazy
        random.seed(seed)
        self.number = random.randint(self.lower, self.higher)
        super().__init__()

    async def max_guesses_reached(self):
        return self.guesses >= self.max_attempts

    async def before_guess(self, number):
        self.guesses += 1
        self.writer(f"Your guess is {number}...")

    async def guess_is_lower(self, number):
        return number < self.number

    async def guess_is_higher(self, number):
        return number > self.number

    async def guess_is_equal(self, number):
        return self.number == number

    async def on_enter_start(self):
        self.writer(
            f"I'm thinking of a number between {self.lower} and {self.higher}. "
            f"Can you guess what it is? >>> "
        )

    async def on_enter_low(self):
        self.writer("Too low. Try again. >>> ")

    async def on_enter_high(self):
        self.writer("Too high. Try again. >>> ")

    async def on_enter_won(self):
        self.writer(f"Congratulations, you guessed the number in {self.guesses} guesses!")

    async def on_enter_lose(self):
        self.writer(f"Oh, no! You've spent all your {self.guesses} attempts!")


# %%
# Async stdin/stdout
# ------------------

# This function will be used to connect the stdin and stdout to the asyncio event loop.


async def connect_stdin_stdout():
    loop = asyncio.get_event_loop()
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: protocol, sys.stdin)
    w_transport, w_protocol = await loop.connect_write_pipe(
        asyncio.streams.FlowControlMixin, sys.stdout
    )
    writer = asyncio.StreamWriter(w_transport, w_protocol, reader, loop)
    return reader, writer


# %%
# Executing
# ---------
#
# This script only run by passing the `-i` flag, avoiding blocking while running automated tests.
#
# To play the game, run this script and type a number between 1 and 5.
#
# Note that when running a WF in async code, the initial state must be activated manually.
# This is done by calling ``await workflow.activate_initial_state()``.


async def main_async():
    reader, writer = await connect_stdin_stdout()
    workflow = GuessTheNumberMachine(
        lambda s: writer.write(b"\n" + s.encode("utf-8")), seed=random.randint(1, 1000)
    )
    await workflow.activate_initial_state()
    while not workflow.current_state.final:
        res = await reader.read(100)
        if not res:
            break
        await workflow.send("guess", int(res))
        await writer.drain()
    writer.close()


def main_sync():
    workflow = GuessTheNumberMachine(print, seed=random.randint(1, 1000))
    workflow.activate_initial_state()
    while not workflow.current_state.final:
        res = sys.stdin.readline()
        if not res:
            break
        workflow.send("guess", int(res))


if __name__ == "__main__" and "-i" in sys.argv:
    if "-s" in sys.argv:
        main_sync()
    else:
        asyncio.run(main_async())
