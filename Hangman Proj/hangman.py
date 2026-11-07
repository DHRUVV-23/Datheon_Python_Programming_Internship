"""Terminal-based Hangman game in Python.

Allows the player to guess a secret word letter by letter with a maximum of
6 incorrect attempts. Includes ASCII gallows art, duplicate guess prevention,
input validation, and replay support.
"""

import os
import random
import sys

# ASCII art for the 7 stages of Hangman (0 to 6 mistakes)
HANGMAN_STAGES = [
    r"""
  +---+
  |   |
      |
      |
      |
      |
=========
""",
    r"""
  +---+
  |   |
  O   |
      |
      |
      |
=========
""",
    r"""
  +---+
  |   |
  O   |
  |   |
      |
      |
=========
""",
    r"""
  +---+
  |   |
  O   |
 /|   |
      |
      |
=========
""",
    r"""
  +---+
  |   |
  O   |
 /|\  |
      |
      |
=========
""",
    r"""
  +---+
  |   |
  O   |
 /|\  |
 /    |
      |
=========
""",
    r"""
  +---+
  |   |
  O   |
 /|\  |
 / \  |
      |
=========
""",
]

MAX_ATTEMPTS = 6

# Default fallback word bank with varied difficulty
DEFAULT_WORD_LIST = [
    "PYTHON",
    "ALGORITHM",
    "DEVELOPER",
    "HANGMAN",
    "PROGRAMMING",
    "COMPUTER",
    "KEYBOARD",
    "TERMINAL",
    "FUNCTION",
    "VARIABLE",
    "SOFTWARE",
    "DATABASE",
    "NETWORK",
    "SECURITY",
    "CHALLENGE",
    "ADVENTURE",
    "DISCOVERY",
    "HORIZON",
    "SYMPHONY",
    "BLIZZARD",
    "VOLCANO",
    "GALAXY",
    "MYSTERY",
    "JOURNEY",
    "TREASURE",
    "WHISPER",
    "ECLIPSE",
    "VELOCITY",
    "PHANTOM",
    "PYRAMID",
]

WORDS_FILE = os.path.join(os.path.dirname(__file__), "words.txt")


def load_words(file_path: str = WORDS_FILE, min_length: int = 3) -> list[str]:
    """Load words from a text file, filtering by length and alphabetic characters.

    Falls back to DEFAULT_WORD_LIST if the file cannot be read or is empty.
    """
    if os.path.isfile(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                loaded = [
                    w.upper()
                    for line in f
                    if (w := line.strip()) and w.isalpha() and len(w) >= min_length
                ]
            if loaded:
                return loaded
        except OSError:
            pass
    return list(DEFAULT_WORD_LIST)


# Active word bank (loaded from words.txt if present)
WORD_LIST = load_words()


def get_random_word(words: list[str] = None) -> str:
    """Select and return a random word in uppercase."""
    words_to_choose = words if words else WORD_LIST
    return random.choice(words_to_choose).upper()


def get_masked_word(secret_word: str, guessed_letters: set[str]) -> str:
    """Return the masked representation of the word (e.g. '_ A _ H E O N')."""
    return " ".join(
        letter if letter in guessed_letters else "_" for letter in secret_word
    )


def display_game_status(
    stage_idx: int,
    secret_word: str,
    guessed_letters: set[str],
    incorrect_guesses: list[str],
) -> None:
    """Display the current gallows stage, word progress, and guess stats."""
    print(HANGMAN_STAGES[stage_idx])
    print(f"Word: {get_masked_word(secret_word, guessed_letters)}")
    print(f"Attempts remaining: {MAX_ATTEMPTS - stage_idx}")

    guessed_sorted = sorted(guessed_letters)
    guessed_str = ", ".join(guessed_sorted) if guessed_sorted else "None"
    print(f"Guessed letters: {guessed_str}")

    wrong_str = ", ".join(incorrect_guesses) if incorrect_guesses else "None"
    print(f"Incorrect guesses: {wrong_str}")
    print("-" * 40)


def prompt_valid_letter(guessed_letters: set[str]) -> str:
    """Prompt the user for a single alphabetical character not already guessed.

    Ensures no penalties for invalid inputs or duplicates.
    """
    while True:
        try:
            raw_input = input("Enter your guess: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGame aborted. Goodbye!")
            sys.exit(0)

        if len(raw_input) != 1 or not raw_input.isalpha():
            print("Invalid input! Please enter a single letter (A-Z).\n")
            continue

        letter = raw_input.upper()
        if letter in guessed_letters:
            print(f"You already guessed '{letter}'! No penalty deducted. Try a different letter.\n")
            continue

        return letter


def play_game(secret_word: str = None) -> bool:
    """Play a single round of Hangman.

    Returns True if the player won, False otherwise.
    """
    if not secret_word:
        secret_word = get_random_word()
    else:
        secret_word = secret_word.upper()

    unique_secret_letters = set(secret_word)
    guessed_letters: set[str] = set()
    incorrect_guesses: list[str] = []
    mistakes = 0

    print("\n" + "=" * 40)
    print("       WELCOME TO HANGMAN!")
    print("=" * 40)

    while mistakes < MAX_ATTEMPTS:
        display_game_status(mistakes, secret_word, guessed_letters, incorrect_guesses)

        # Check win condition before prompting
        if unique_secret_letters.issubset(guessed_letters):
            print(f"\n Congratulations! You guessed the word: {secret_word}!\n")
            return True

        guess = prompt_valid_letter(guessed_letters)
        guessed_letters.add(guess)

        if guess in unique_secret_letters:
            print(f"\n Nice! '{guess}' is in the word!\n")
            if unique_secret_letters.issubset(guessed_letters):
                display_game_status(mistakes, secret_word, guessed_letters, incorrect_guesses)
                print(f"\n Congratulations! You guessed the word: {secret_word}!\n")
                return True
        else:
            mistakes += 1
            incorrect_guesses.append(guess)
            print(f"\n Sorry, '{guess}' is not in the word.\n")

    # If loop exits due to mistakes == MAX_ATTEMPTS
    display_game_status(mistakes, secret_word, guessed_letters, incorrect_guesses)
    print("\n GAME OVER! You've run out of attempts.")
    print(f"The secret word was: {secret_word}\n")
    return False


def main() -> None:
    """Run the Hangman game with replay option."""
    while True:
        play_game()
        try:
            again = input("Would you like to play again? (y/n): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        while again not in ("y", "yes", "n", "no"):
            again = input("Please enter 'y' for yes or 'n' for no: ").strip().lower()

        if again in ("n", "no"):
            print("\nThanks for playing Hangman! See you next time.")
            break


if __name__ == "__main__":
    main()
