"""
Unit tests for the Rule-Based Customer Support & Product Assistant.
"""

import json
import os
import unittest
from chatbot import ConversationState, RuleBasedChatbot


class TestRuleBasedChatbot(unittest.TestCase):
    """Test suite for RuleBasedChatbot functionality."""

    @classmethod
    def setUpClass(cls):
        cls.chatbot = RuleBasedChatbot("faqs.json")

    def setUp(self):
        self.chatbot.reset()

    # --- 1. Normalization & Keyword Extraction Tests ---
    def test_normalization(self):
        """Test input normalization (lowercase, stripping punctuation and whitespace)."""
        raw = "   HELLO,   World!!!  What are YOUR Hours???  "
        normalized = self.chatbot.normalize(raw)
        self.assertEqual(normalized, "hello world what are your hours")

    def test_extract_keywords(self):
        """Test extraction of meaningful keywords after stopword filtering."""
        text = "How do I submit my internship project on GitHub?"
        keywords = self.chatbot.extract_keywords(text)
        expected = {"submit", "internship", "project", "github"}
        self.assertTrue(expected.issubset(keywords))

    # --- 2. Exit Commands Tests ---
    def test_clean_exit_commands(self):
        """Test that 'bye', 'exit', 'quit', and 'goodbye' cleanly exit."""
        for exit_cmd in ["bye", "exit", "quit", "goodbye", "BYE", "  quit  "]:
            with self.subTest(cmd=exit_cmd):
                self.chatbot.reset()
                res = self.chatbot.respond(exit_cmd)
                self.assertTrue(res["is_exit"])
                self.assertEqual(res["state"], ConversationState.EXIT)
                self.assertEqual(res["intent"], "exit")
                self.assertIn("Goodbye", res["response"])

    # --- 3. Greetings Tests ---
    def test_greetings(self):
        """Test standard greetings from dataset and regex."""
        greetings = ["hello", "hi", "hey", "good morning", "good afternoon"]
        for g in greetings:
            with self.subTest(greeting=g):
                self.chatbot.reset()
                res = self.chatbot.respond(g)
                self.assertFalse(res["is_exit"])
                self.assertEqual(res["state"], ConversationState.INTENT_IDENTIFICATION)
                self.assertEqual(res["intent"], "greeting")
                self.assertIn("Hello! Welcome to Customer Support", res["response"])

    def test_combined_greeting_and_query(self):
        """Test user input that includes both a greeting and a query."""
        res = self.chatbot.respond("Hello! What are your hours of operation?")
        self.assertFalse(res["is_exit"])
        self.assertEqual(res["state"], ConversationState.RESOLUTION)
        self.assertEqual(res["intent"], "business_hours")
        self.assertIn("Hello! We operate Monday through Friday", res["response"])

    def test_noisy_punctuation_and_casing(self):
        """Test queries with aggressive casing and punctuation."""
        res = self.chatbot.respond("WHAT??? ARE YOUR HOURS OF OPERATION?!?!")
        self.assertEqual(res["state"], ConversationState.RESOLUTION)
        self.assertEqual(res["intent"], "business_hours")
        self.assertGreaterEqual(res["confidence"], 0.85)

    def test_empty_input(self):
        """Test empty or whitespace-only inputs."""
        res = self.chatbot.respond("   ")
        self.assertEqual(res["confidence"], 0.0)
        self.assertIn("Please enter a question", res["response"])

    def test_human_support_request(self):
        """Test requests to speak to a real person/human agent."""
        res = self.chatbot.respond("Can I speak to a human representative?")
        self.assertEqual(res["intent"], "human_support")
        self.assertIn("support@workspace.edu", res["response"])

    # --- 4. Business Hours Queries Tests ---
    def test_business_hours_queries(self):
        """Test diverse phrasings for business hours."""
        queries = [
            "What are your hours of operation?",
            "What time are you open?",
            "When do you close?",
            "What are your working hours?",
            "Can you tell me your operating schedule?"
        ]
        for q in queries:
            with self.subTest(query=q):
                self.chatbot.reset()
                res = self.chatbot.respond(q)
                self.assertFalse(res["is_exit"])
                self.assertEqual(res["state"], ConversationState.RESOLUTION)
                self.assertEqual(res["intent"], "business_hours")
                self.assertIn("9:00 AM to 6:00 PM IST", res["response"])

    # --- 5. Project Submission Queries Tests ---
    def test_project_submission_queries(self):
        """Test diverse phrasings for internship project submission."""
        queries = [
            "How do I submit my internship project?",
            "Where do I upload my project code?",
            "How can I submit my GitHub repo?",
            "Project submission instructions please"
        ]
        for q in queries:
            with self.subTest(query=q):
                self.chatbot.reset()
                res = self.chatbot.respond(q)
                self.assertFalse(res["is_exit"])
                self.assertEqual(res["state"], ConversationState.RESOLUTION)
                self.assertEqual(res["intent"], "project_submission")
                self.assertIn("Student Workspace", res["response"])
                self.assertIn("GitHub repository link", res["response"])

    # --- 6. Certificate Issuance Queries Tests ---
    def test_certificate_issuance_queries(self):
        """Test diverse phrasings for certificate issuance and review."""
        queries = [
            "When will I receive my certificate?",
            "How long does certificate issuance take?",
            "When do I get my certificate after code review?",
            "What is the timeline for my certificate?"
        ]
        for q in queries:
            with self.subTest(query=q):
                self.chatbot.reset()
                res = self.chatbot.respond(q)
                self.assertFalse(res["is_exit"])
                self.assertEqual(res["state"], ConversationState.RESOLUTION)
                self.assertEqual(res["intent"], "certificate_issuance")
                self.assertIn("3-5 business days", res["response"])

    # --- 7. Conversational State Management Tests ---
    def test_state_flow_greeting_to_intent_to_resolution_to_exit(self):
        """Test full conversational lifecycle: Greeting -> Intent -> Resolution -> Exit."""
        # 1. Start / Greeting
        res1 = self.chatbot.respond("Hello")
        self.assertEqual(res1["state"], ConversationState.INTENT_IDENTIFICATION)
        self.assertEqual(res1["intent"], "greeting")

        # 2. Intent Identification
        res2 = self.chatbot.respond("What are your hours of operation?")
        self.assertEqual(res2["state"], ConversationState.RESOLUTION)
        self.assertEqual(res2["intent"], "business_hours")
        self.assertIn("9:00 AM to 6:00 PM IST", res2["response"])

        # 3. Resolution confirmation
        res3 = self.chatbot.respond("Yes, thank you!")
        self.assertEqual(res3["state"], ConversationState.RESOLUTION)
        self.assertEqual(res3["intent"], "affirmation")
        self.assertIn("Wonderful!", res3["response"])

        # 4. Clean exit
        res4 = self.chatbot.respond("bye")
        self.assertEqual(res4["state"], ConversationState.EXIT)
        self.assertTrue(res4["is_exit"])

    def test_resolution_negation_escalation(self):
        """Test that saying 'no' in RESOLUTION state transitions to rephrasing/escalation."""
        # Ask question
        self.chatbot.respond("When will I receive my certificate?")
        self.assertEqual(self.chatbot.state, ConversationState.RESOLUTION)

        # User says no
        res = self.chatbot.respond("No, that didn't help")
        self.assertEqual(res["state"], ConversationState.INTENT_IDENTIFICATION)
        self.assertIn("apologize", res["response"])

    def test_contextual_follow_up(self):
        """Test contextual follow-up recognition based on last intent."""
        # 1. Ask project submission
        self.chatbot.respond("How do I submit my project?")
        self.assertEqual(self.chatbot.last_intent, "project_submission")

        # 2. Ask follow-up about link/url
        followup = self.chatbot.respond("What link should I use?")
        self.assertEqual(followup["state"], ConversationState.RESOLUTION)
        self.assertEqual(followup["intent"], "project_submission_followup")
        self.assertIn("GitHub repository", followup["response"])

    # --- 8. Graceful Fallback Handling Tests ---
    def test_progressive_fallback_handling(self):
        """Test multi-tier fallback when query confidence is low."""
        # First unknown query
        res1 = self.chatbot.respond("quantum mechanics formula")
        self.assertIn("didn't quite catch that", res1["response"])
        self.assertEqual(self.chatbot.fallback_count, 1)

        # Second unknown query
        res2 = self.chatbot.respond("supercalifragilistic")
        self.assertIn("Here are the topics I can help you with", res2["response"])
        self.assertEqual(self.chatbot.fallback_count, 2)

        # Third unknown query
        res3 = self.chatbot.respond("asdfghjkl zxcvbnm")
        self.assertIn("support@workspace.edu", res3["response"])
        self.assertEqual(self.chatbot.fallback_count, 3)

    # --- 9. JSON Dataset Loading Tests ---
    def test_json_loading_and_fallback(self):
        """Test loading from custom JSON and missing file fallback."""
        temp_file = "test_custom_faqs.json"
        try:
            custom_data = {
                "greetings": ["hey there"],
                "faqs": [
                    {
                        "question": "Where is the library located?",
                        "answer": "The library is on Building B, 2nd Floor."
                    }
                ]
            }
            with open(temp_file, "w") as f:
                json.dump(custom_data, f)

            bot = RuleBasedChatbot(temp_file)
            res = bot.respond("Where is the library located?")
            self.assertEqual(res["state"], ConversationState.RESOLUTION)
            self.assertIn("Building B, 2nd Floor", res["response"])

            # Nonexistent file should load built-in fallback data without crashing
            fallback_bot = RuleBasedChatbot("non_existent_file_xyz.json")
            res_fb = fallback_bot.respond("What are your hours of operation?")
            self.assertIn("9:00 AM to 6:00 PM IST", res_fb["response"])
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)


if __name__ == "__main__":
    unittest.main()
