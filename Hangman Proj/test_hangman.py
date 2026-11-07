"""Unit tests for hangman.py."""

import unittest
from unittest.mock import patch
import hangman


class TestHangman(unittest.TestCase):

    def test_stages_count_and_content(self):
        """Ensure there are 7 stages corresponding to 0-6 mistakes."""
        self.assertEqual(len(hangman.HANGMAN_STAGES), 7)
        self.assertEqual(hangman.MAX_ATTEMPTS, 6)
        # Verify first stage has gallows but no body parts
        self.assertIn("+---+", hangman.HANGMAN_STAGES[0])
        self.assertNotIn("O", hangman.HANGMAN_STAGES[0])
        # Verify final stage has complete figure
        self.assertIn("O", hangman.HANGMAN_STAGES[6])
        self.assertIn(r"/ \ ", hangman.HANGMAN_STAGES[6])

    def test_random_word(self):
        """Ensure random word selection returns uppercase words from list."""
        custom_words = ["APPLE", "BANANA"]
        word = hangman.get_random_word(custom_words)
        self.assertIn(word, custom_words)

        default_word = hangman.get_random_word()
        self.assertIn(default_word, hangman.WORD_LIST)
        self.assertTrue(default_word.isupper())

    def test_load_words_fallback_and_filtering(self):
        """Test load_words fallback when file doesn't exist and filtering by min_length."""
        fallback = hangman.load_words("non_existent_file_xyz.txt")
        self.assertEqual(fallback, hangman.DEFAULT_WORD_LIST)

        # Ensure active word list has loaded words from words.txt
        self.assertGreater(len(hangman.WORD_LIST), 1000)
        for w in hangman.WORD_LIST[:50]:
            self.assertTrue(w.isalpha())
            self.assertGreaterEqual(len(w), 3)
            self.assertTrue(w.isupper())

    def test_masked_word(self):
        """Ensure get_masked_word returns properly formatted string with spaces."""
        word = "PYTHON"
        guessed = set()
        self.assertEqual(hangman.get_masked_word(word, guessed), "_ _ _ _ _ _")

        guessed = {"P", "O"}
        self.assertEqual(hangman.get_masked_word(word, guessed), "P _ _ _ O _")

        guessed = set("PYTHON")
        self.assertEqual(hangman.get_masked_word(word, guessed), "P Y T H O N")

    @patch("builtins.input", side_effect=["1", "ab", "!", "A"])
    def test_prompt_valid_letter_rejects_invalid_inputs(self, mock_input):
        """Ensure digits, multichar, and symbols are rejected until valid letter is entered."""
        guessed_letters = set()
        chosen = hangman.prompt_valid_letter(guessed_letters)
        self.assertEqual(chosen, "A")

    @patch("builtins.input", side_effect=["A", "a", "b"])
    def test_prompt_valid_letter_rejects_duplicates_without_penalty(self, mock_input):
        """Ensure previously guessed letters (case-insensitive) are rejected without penalty."""
        guessed_letters = {"A"}
        chosen = hangman.prompt_valid_letter(guessed_letters)
        self.assertEqual(chosen, "B")

    @patch("builtins.input", side_effect=["p", "y", "t", "h", "o", "n"])
    def test_play_game_win(self, mock_input):
        """Ensure player wins when all letters are correctly guessed."""
        won = hangman.play_game(secret_word="PYTHON")
        self.assertTrue(won)

    @patch("builtins.input", side_effect=["x", "p", "x", "y", "z", "w", "v", "u", "t", "s"])
    def test_play_game_duplicate_guess_does_not_deduct_attempt(self, mock_input):
        """
        Verify guessing a duplicate wrong letter doesn't count as an extra mistake.
        Sequence:
        - 'x' (mistake 1)
        - 'p' (correct)
        - 'x' (duplicate rejected, no mistake)
        - 'y' (correct)
        - 'z' (mistake 2)
        - 'w' (mistake 3)
        - 'v' (mistake 4)
        - 'u' (mistake 5)
        - 't' (correct)
        - 's' (mistake 6) -> Loss
        """
        won = hangman.play_game(secret_word="PYTHON")
        self.assertFalse(won)

    @patch("builtins.input", side_effect=["a", "b", "c", "d", "e", "f"])
    def test_play_game_loss(self, mock_input):
        """Ensure player loses after 6 incorrect guesses."""
        won = hangman.play_game(secret_word="PYTHON")
        self.assertFalse(won)


if __name__ == "__main__":
    unittest.main()
