# Terminal Hangman Game 🎮

A feature-rich, interactive command-line **Hangman** game built in Python 3. The player attempts to guess a randomly chosen hidden word letter by letter within 6 attempts, accompanied by responsive ASCII gallows art, input sanitization, duplicate guess protection, and a 10,000-word English vocabulary.

---

## ✨ Features

- **Responsive ASCII Gallows Art**: Features 7 visual stages (from an empty gallows at `0` mistakes to the completed figure at `6` mistakes).
- **Word Masking**: Clean spaced letter representation (e.g., `_ A _ H E O N`) that reveals letters as correct guesses are entered.
- **Duplicate Guess & Penalty Protection**:
  - Guessing a previously entered letter triggers a warning and **does not penalize** the player or deduct an attempt.
  - Invalid inputs (non-alphabetical characters, multiple letters, whitespace) are rejected without penalty.
- **Comprehensive Word Bank**:
  - Automatically loads and filters words from [`words.txt`](words.txt) (sourced from the popular [`google-10000-english-no-swears`](https://raw.githubusercontent.com/first20hours/google-10000-english/master/google-10000-english-no-swears.txt) dataset).
  - Filters for valid alphabetical words of length $\ge 3$ (over 9,400 playable English words).
  - Includes a built-in fallback word bank in case the dictionary file is missing.
- **Play & Replay Loop**: Easy replay prompt (`y`/`n`) at the end of each round.
- **Standard Library Only**: No external package installations or third-party dependencies required.

---

## 📁 Project Structure

```text
Project1/
├── hangman.py          # Main game engine, game loop, and ASCII art renderer
├── words.txt           # Word list (Google 10,000 most common English words, no swears)
├── test_hangman.py     # Automated unit test suite
└── README.md           # Project documentation and instructions
```

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.8+** installed on your system.

Verify your Python installation:
```bash
python3 --version
```

### Installation

Clone or navigate to the project directory:
```bash
cd /Users/dhruv/Documents/Project1
```

No external `pip` packages are required; only standard library modules (`random`, `sys`, `os`, `unittest`) are used.

---

## 🕹️ How to Play

1. Run the game from your terminal:
   ```bash
   python3 hangman.py
   ```

2. **Rules**:
   - A secret word is randomly picked from [`words.txt`](words.txt).
   - Enter one letter at a time when prompted (`Enter your guess: `).
   - Input is case-insensitive (`a` is treated the same as `A`).
   - If the letter is in the word, it will reveal all occurrences in the masked word display.
   - If the letter is not in the word, you lose **1 attempt** and the gallows advances to the next stage.
   - You have **6 incorrect attempts** before the game ends.
   - Enter `y` to play another round or `n` to exit.

---

## 🎨 Sample Gameplay

```text
========================================
       WELCOME TO HANGMAN!
========================================

  +---+
  |   |
  O   |
 /|\  |
      |
      |
=========

Word: _ Y T H _ N
Attempts remaining: 2
Guessed letters: E, H, N, P, T, Y, Z
Incorrect guesses: E, Z
----------------------------------------
Enter your guess: o

 Nice! 'O' is in the word!


  +---+
  |   |
  O   |
 /|\  |
      |
      |
=========

Word: P Y T H O N
Attempts remaining: 2
Guessed letters: E, H, N, O, P, T, Y, Z
Incorrect guesses: E, Z
----------------------------------------

 Congratulations! You guessed the word: PYTHON!

Would you like to play again? (y/n):
```

---

## 🧪 Running Unit Tests

An automated test suite is provided in [`test_hangman.py`](test_hangman.py). It validates:
- Correct count and integrity of ASCII gallows stages (`7` stages).
- Word masking formatting and letter reveals.
- Input validation (rejection of symbols, numbers, and strings).
- Duplicate letter penalty immunity.
- Win/loss game mechanics.
- File loading from [`words.txt`](words.txt) and fallback handling.

To run the test suite:
```bash
python3 -m unittest test_hangman.py
```

---

## 📚 Word List Source

The word list file [`words.txt`](words.txt) is based on the [Google 10,000 English (no swears)](https://raw.githubusercontent.com/first20hours/google-10000-english/master/google-10000-english-no-swears.txt) list.

- **Total words in source**: ~9,894
- **Filter**: Alphabetic characters only, length $\ge 3$ characters (9,474 words).
- Custom lists can easily be plugged in by editing or replacing `words.txt`.
