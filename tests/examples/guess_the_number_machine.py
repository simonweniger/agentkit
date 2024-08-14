"""
Guess the number flow
========================

An Workflow for the well know game.

Well leave the flow imagine a number and also play the game. Why not?

"""

import random

from workflow import State
from workflow import Workflow


class GuessTheNumberMachine(Workflow):
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

    def __init__(self, max_attempts=5, lower=1, higher=5, seed=42):
        self.max_attempts = max_attempts
        self.lower = lower
        self.higher = higher
        self.guesses = 0

        # lets play a not so random game, or our tests will be crazy
        random.seed(seed)
        self.number = random.randint(self.lower, self.higher)
        super().__init__()

    def max_guesses_reached(self):
        return self.guesses >= self.max_attempts

    def before_guess(self, number):
        self.guesses += 1
        print(f"Your guess is {number}...")

    def guess_is_lower(self, number):
        return number < self.number

    def guess_is_higher(self, number):
        return number > self.number

    def guess_is_equal(self, number):
        return self.number == number

    def on_enter_start(self):
        print(f"(psss.. don't tell anyone the number is {self.number})")
        print(
            f"I'm thinking of a number between {self.lower} and {self.higher}. "
            f"Can you guess what it is?"
        )

    def on_enter_low(self):
        print("Too low. Try again.")

    def on_enter_high(self):
        print("Too high. Try again.")

    def on_enter_won(self):
        print(f"Congratulations, you guessed the number in {self.guesses} guesses!")

    def on_enter_lose(self):
        print(f"Oh, no! You've spent all your {self.guesses} attempts!")


# %%
# Playing
# -------
#

workflow = GuessTheNumberMachine(seed=103)

# %%

workflow.guess(random.randint(1, 5))

# %%

workflow

# %%

workflow.guess(random.randint(1, 5))

# %%

workflow.guess(random.randint(1, 5))


workflow

# %%

# %%

workflow.guess(random.randint(1, 5))

# %%

workflow.guess(random.randint(1, 5))

# %%

workflow

# %%

try:
    workflow.guess(random.randint(1, 5))
except Exception as e:
    print(e)
