"""
Rule-Based Customer Support & Product Assistant.

Features:
- Regex and keyword-based query parsing.
- Handles business hours, product/internship FAQs, and contextual follow-ups.
- Conversational state management: GREETING -> INTENT_IDENTIFICATION -> RESOLUTION -> EXIT.
- Fallback handling with progressive escalation for unrecognized queries.
- Clean exit commands ('bye', 'exit', 'quit').
- Loads from JSON dataset or falls back to built-in rules.
"""

import json
import os
import re
from typing import Any, Dict, List, Optional, Set, Tuple


class ConversationState:
    """Conversational states for state machine management."""
    GREETING = "GREETING"
    INTENT_IDENTIFICATION = "INTENT_IDENTIFICATION"
    RESOLUTION = "RESOLUTION"
    EXIT = "EXIT"


class RuleBasedChatbot:
    """A rule-based customer support assistant with regex, keyword parsing, and state management."""

    DEFAULT_DATA_PATH = "faqs.json"

    # Stopwords removed during keyword extraction
    STOPWORDS: Set[str] = {
        "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
        "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
        "below", "between", "both", "but", "by", "can", "can't", "cannot", "could", "couldn't",
        "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down", "during",
        "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't",
        "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here",
        "here's", "hers", "herself", "him", "himself", "his", "how", "how's", "i",
        "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it", "it's",
        "its", "itself", "let's", "me", "more", "most", "mustn't", "my", "myself",
        "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other", "ought",
        "our", "ours", "ourselves", "out", "over", "own", "same", "shan't", "she",
        "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such",
        "than", "that", "that's", "the", "their", "theirs", "them", "themselves",
        "then", "there", "there's", "these", "they", "they'd", "they'll", "they're",
        "they've", "this", "those", "through", "to", "too", "under", "until", "up",
        "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were",
        "weren't", "what", "what's", "when", "when's", "where", "where's", "which",
        "while", "who", "who's", "whom", "why", "why's", "with", "won't", "would",
        "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours",
        "yourself", "yourselves"
    }

    # Pre-compiled regular expressions for control intents
    EXIT_REGEX = re.compile(
        r"^\s*(bye|exit|quit|goodbye|q|close|see\s+ya|farewell)\b",
        re.IGNORECASE
    )
    GREETING_REGEX = re.compile(
        r"\b(hello|hi|hey|good\s+morning|good\s+afternoon|good\s+evening|howdy|greetings)\b",
        re.IGNORECASE
    )
    AFFIRMATION_REGEX = re.compile(
        r"^\s*(yes|yeah|yep|yup|sure|correct|thanks|thank\s+you|that\s+helped|solved|ok|okay)\b",
        re.IGNORECASE
    )
    NEGATION_REGEX = re.compile(
        r"^\s*(no|nope|nah|not\s+really|didn'?t\s+help|doesn'?t\s+help|unresolved|negative)\b",
        re.IGNORECASE
    )
    HELP_REGEX = re.compile(
        r"^\s*(help|options|menu|commands|topics)\b|\b(need\s+help|help\s+me|can\s+you\s+help|what\s+can\s+you\s+do)\b",
        re.IGNORECASE
    )
    HUMAN_SUPPORT_REGEX = re.compile(
        r"\b(human|agent|representative|live\s+support|talk\s+to\s+someone|contact\s+support)\b",
        re.IGNORECASE
    )

    # Pre-built domain patterns to guarantee robust regex parsing across variations
    DOMAIN_PATTERNS: Dict[str, List[str]] = {
        "business_hours": [
            r"\b(hours?|timings?|schedule|operating\s+hours|business\s+hours)\b",
            r"\b(what\s+time|when)\b.*\b(open|close|work|operate|available)\b",
            r"\b(when\s+are\s+you\s+(open|available|operating))\b",
            r"\b(open(ing)?|clos(ing)?)\s+(time|hours)\b"
        ],
        "project_submission": [
            r"\b(how|where)\b.*\b(submit|upload|turn\s+in|send|share)\b.*\b(project|assignment|internship|code|repo|repository)\b",
            r"\b(submit|submission|upload)\b.*\b(project|internship|assignment|code)\b",
            r"\b(project|internship)\b.*\b(submit|submission|upload)\b",
            r"\b(student\s+workspace|github\s+repo|public\s+github|repository\s+link)\b"
        ],
        "certificate_issuance": [
            r"\b(when|how\s+long|timeline|how\s+many\s+days)\b.*\b(certificate|cert|certification)\b",
            r"\b(receive|get|obtain|issued?|download)\b.*\b(certificate|cert|certification)\b",
            r"\b(certificate|certification)\b.*\b(status|issue|issuance|download|ready|timeline)\b",
            r"\bcode\s+review\b.*\b(certificate|cert)\b"
        ]
    }

    # Domain synonyms to automatically enrich keyword matching
    SYNONYM_MAP: Dict[str, List[str]] = {
        "hours": ["hours", "hour", "timing", "timings", "schedule", "open", "close", "operating", "available", "time"],
        "operation": ["operation", "operating", "work", "business", "service"],
        "submit": ["submit", "submission", "upload", "turn in", "send", "share", "link"],
        "project": ["project", "internship", "assignment", "code", "repo", "repository", "github", "workspace"],
        "certificate": ["certificate", "cert", "certification", "completion", "credential", "diploma"],
        "receive": ["receive", "get", "obtain", "issue", "issued", "timeline", "review", "days", "when"]
    }

    CONFIDENCE_THRESHOLD = 0.40

    def __init__(self, data_path: Optional[str] = None):
        """Initialize chatbot instance, load dataset, and set initial state."""
        self.state: str = ConversationState.GREETING
        self.last_intent: Optional[str] = None
        self.fallback_count: int = 0
        self.data_path = data_path or self.DEFAULT_DATA_PATH
        
        self.greetings: List[str] = []
        self.faqs: List[Dict[str, Any]] = []
        self.compiled_faqs: List[Dict[str, Any]] = []

        self.load_data(self.data_path)

    def load_data(self, file_path: str) -> None:
        """Load greetings and FAQ knowledge base from a JSON file."""
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.greetings = data.get("greetings", [])
                    self.faqs = data.get("faqs", [])
            except Exception as e:
                print(f"[Warning] Failed to load {file_path}: {e}. Loading default knowledge base.")
                self._load_fallback_data()
        else:
            self._load_fallback_data()

        self._compile_faq_patterns()

    def _load_fallback_data(self) -> None:
        """Fallback knowledge base if JSON file is missing."""
        self.greetings = ["hello", "hi", "hey", "good morning", "good afternoon"]
        self.faqs = [
            {
                "id": "business_hours",
                "question": "What are your hours of operation?",
                "answer": "We operate Monday through Friday from 9:00 AM to 6:00 PM IST."
            },
            {
                "id": "project_submission",
                "question": "How do I submit my internship project?",
                "answer": "You can submit your public GitHub repository link through your Student Workspace."
            },
            {
                "id": "certificate_issuance",
                "question": "When will I receive my certificate?",
                "answer": "Certificates are reviewed and issued within 3-5 business days after your code review."
            }
        ]

    def _infer_intent_id(self, question: str, index: int) -> str:
        """Infer an intent identifier from the question text."""
        q_lower = question.lower()
        if any(term in q_lower for term in ["hour", "operation", "time", "open"]):
            return "business_hours"
        elif any(term in q_lower for term in ["submit", "project", "internship", "github"]):
            return "project_submission"
        elif any(term in q_lower for term in ["certificate", "cert", "receive"]):
            return "certificate_issuance"
        return f"faq_{index}"

    def _compile_faq_patterns(self) -> None:
        """Compile regexes and enrich keywords for fast, accurate matching."""
        self.compiled_faqs = []
        for index, item in enumerate(self.faqs):
            question = item.get("question", "")
            answer = item.get("answer", "")
            item_id = item.get("id") or self._infer_intent_id(question, index)

            # Extract base keywords from question text
            keywords = set(k.lower() for k in item.get("keywords", []))
            if not keywords and question:
                keywords = self.extract_keywords(question)

            # Enrich keywords using domain synonym maps
            enriched_keywords = set(keywords)
            for kw in list(keywords):
                for syn_key, syn_list in self.SYNONYM_MAP.items():
                    if kw == syn_key or kw in syn_list:
                        enriched_keywords.update(syn_list)

            # Compile existing or domain-based regex patterns
            compiled_patterns: List[re.Pattern] = []
            raw_patterns = list(item.get("patterns", []))

            # Automatically inject domain regex patterns if matching known domain
            if item_id in self.DOMAIN_PATTERNS:
                raw_patterns.extend(self.DOMAIN_PATTERNS[item_id])

            for p in raw_patterns:
                try:
                    compiled_patterns.append(re.compile(p, re.IGNORECASE))
                except re.error:
                    pass

            # Fallback pattern if none found
            if not compiled_patterns and question:
                key_tokens = [re.escape(w) for w in list(enriched_keywords)[:4]]
                if key_tokens:
                    pattern_str = r"\b(" + "|".join(key_tokens) + r")\b"
                    compiled_patterns.append(re.compile(pattern_str, re.IGNORECASE))

            self.compiled_faqs.append({
                "id": item_id,
                "question": question,
                "answer": answer,
                "keywords": enriched_keywords,
                "patterns": compiled_patterns
            })

    def normalize(self, text: str) -> str:
        """Normalize user input: lowercase, strip punctuation, trim whitespace."""
        if not text:
            return ""
        text = text.lower().strip()
        # Keep word characters, spaces, and essential single quotes
        text = re.sub(r"[^\w\s\']", " ", text)
        # Collapse multiple whitespace characters into a single space
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def extract_keywords(self, text: str) -> Set[str]:
        """Extract meaningful keywords by removing stopwords and tokenizing."""
        normalized = self.normalize(text)
        tokens = normalized.split()
        keywords = {t for t in tokens if t not in self.STOPWORDS and len(t) > 1}
        return keywords

    def calculate_confidence(self, normalized_text: str, user_keywords: Set[str], faq_item: Dict[str, Any]) -> float:
        """
        Calculate matching confidence score between 0.0 and 1.0.

        Combines regex pattern detection with keyword overlap scoring.
        """
        score = 0.0

        # 1. Regex Pattern Matching (High confidence boost)
        patterns: List[re.Pattern] = faq_item.get("patterns", [])
        pattern_matched = False
        for pattern in patterns:
            if pattern.search(normalized_text):
                pattern_matched = True
                score = max(score, 0.85)
                break

        # 2. Keyword Matching & Overlap
        faq_keywords: Set[str] = faq_item.get("keywords", set())
        if faq_keywords and user_keywords:
            common_keywords = user_keywords.intersection(faq_keywords)
            overlap_ratio = len(common_keywords) / max(len(user_keywords), 1)
            keyword_score = min(1.0, overlap_ratio * 0.9)

            if pattern_matched:
                score = min(1.0, 0.85 + (len(common_keywords) * 0.05))
            else:
                score = max(score, keyword_score)

        return round(score, 2)

    def identify_intent(self, text: str) -> Tuple[Optional[Dict[str, Any]], float]:
        """Identify the FAQ intent with the highest confidence score."""
        normalized = self.normalize(text)
        user_keywords = self.extract_keywords(text)

        best_match: Optional[Dict[str, Any]] = None
        highest_confidence: float = 0.0

        for item in self.compiled_faqs:
            conf = self.calculate_confidence(normalized, user_keywords, item)
            if conf > highest_confidence:
                highest_confidence = conf
                best_match = item

        return best_match, highest_confidence

    def handle_contextual_followup(self, cleaned_input: str) -> Optional[Dict[str, Any]]:
        """
        Check for contextual follow-up questions linked to the last discussed intent.
        """
        if not self.last_intent:
            return None

        normalized = self.normalize(cleaned_input)

        # Follow-ups for Project Submission
        if self.last_intent == "project_submission":
            if re.search(r"\b(where|link|url|github|repo|private|public|format)\b", normalized):
                return {
                    "response": (
                        "Regarding project submission: Ensure your GitHub repository is public "
                        "and submit the full URL via your Student Workspace portal.\n\n"
                        "Does this clarify your question?"
                    ),
                    "state": ConversationState.RESOLUTION,
                    "intent": "project_submission_followup",
                    "confidence": 0.90,
                    "is_exit": False
                }

        # Follow-ups for Certificate Issuance
        elif self.last_intent == "certificate_issuance":
            if re.search(r"\b(timeline|who|reviewer|fast|expedite|days|code\s+review)\b", normalized):
                return {
                    "response": (
                        "Regarding your certificate: The 3-5 business days window starts immediately "
                        "after a reviewer completes your code evaluation.\n\n"
                        "Does this resolve your query?"
                    ),
                    "state": ConversationState.RESOLUTION,
                    "intent": "certificate_issuance_followup",
                    "confidence": 0.90,
                    "is_exit": False
                }

        # Follow-ups for Business Hours
        elif self.last_intent == "business_hours":
            if re.search(r"\b(weekend|saturday|sunday|holiday|timezone|ist)\b", normalized):
                return {
                    "response": (
                        "We are closed on weekends (Saturday and Sunday) and national holidays. "
                        "Our operating hours are strictly 9:00 AM to 6:00 PM IST, Monday through Friday.\n\n"
                        "Is there anything else you would like to know?"
                    ),
                    "state": ConversationState.RESOLUTION,
                    "intent": "business_hours_followup",
                    "confidence": 0.90,
                    "is_exit": False
                }

        return None

    def get_help_menu(self) -> str:
        """Return the available topics the bot can assist with."""
        return (
            "Here are the topics I can help you with:\n"
            "  1. Business Hours & Operating Schedule\n"
            "  2. Internship Project Submission\n"
            "  3. Certificate Issuance & Review Timelines\n"
            "  4. Live Agent / Human Support\n"
            "You can type your query in natural language, or type 'bye' to exit."
        )

    def get_fallback_response(self) -> str:
        """Return progressive fallback responses based on consecutive unhandled queries."""
        self.fallback_count += 1
        if self.fallback_count == 1:
            return (
                "I'm sorry, I didn't quite catch that. Could you please rephrase your query? "
                "You can ask about our business hours, project submission, or certificate timelines."
            )
        elif self.fallback_count == 2:
            return (
                "I am still having trouble understanding your request.\n"
                + self.get_help_menu()
            )
        else:
            return (
                "It seems I'm unable to answer your query. "
                "Would you like to speak to a human representative? "
                "You can reach our support team directly at support@workspace.edu or call +1-800-555-0199."
            )

    def respond(self, user_input: str) -> Dict[str, Any]:
        """
        Process user input and return a structured response with state management.

        Returns:
            dict with fields:
                - response (str): Bot's response message.
                - state (str): Current conversational state.
                - intent (str | None): Identified intent or None.
                - confidence (float): Match confidence (0.0 to 1.0).
                - is_exit (bool): True if the session should terminate.
        """
        cleaned_input = user_input.strip() if user_input else ""
        normalized = self.normalize(cleaned_input)

        # 1. Clean Exit Commands ('bye', 'exit', 'quit', 'goodbye', etc.)
        if self.EXIT_REGEX.search(cleaned_input):
            self.state = ConversationState.EXIT
            return {
                "response": "Thank you for reaching out to customer support. Have a wonderful day! Goodbye.",
                "state": self.state,
                "intent": "exit",
                "confidence": 1.0,
                "is_exit": True
            }

        # Handle empty input
        if not cleaned_input:
            return {
                "response": "Please enter a question or topic so I can assist you. (Type 'help' for options)",
                "state": self.state,
                "intent": None,
                "confidence": 0.0,
                "is_exit": False
            }

        # 2. Handle Conversational Affirmation / Negation in RESOLUTION State
        if self.state == ConversationState.RESOLUTION:
            # User affirms that previous answer was helpful
            if self.AFFIRMATION_REGEX.search(cleaned_input):
                self.fallback_count = 0
                return {
                    "response": "Wonderful! Let me know if you have any other questions. (Type 'exit' or 'bye' if you are finished)",
                    "state": self.state,
                    "intent": "affirmation",
                    "confidence": 0.95,
                    "is_exit": False
                }
            # User indicates issue is unresolved
            if self.NEGATION_REGEX.search(cleaned_input):
                self.fallback_count = 0
                return {
                    "response": (
                        "I apologize that didn't fully resolve your question. "
                        "Please rephrase your query or type 'agent' to reach out to human support."
                    ),
                    "state": ConversationState.INTENT_IDENTIFICATION,
                    "intent": "negation",
                    "confidence": 0.95,
                    "is_exit": False
                }

        # 3. Check for Help / Menu Request
        if self.HELP_REGEX.search(cleaned_input):
            self.state = ConversationState.INTENT_IDENTIFICATION
            self.fallback_count = 0
            return {
                "response": self.get_help_menu(),
                "state": self.state,
                "intent": "help",
                "confidence": 1.0,
                "is_exit": False
            }

        # 4. Check for Human Support Request
        if self.HUMAN_SUPPORT_REGEX.search(cleaned_input):
            self.state = ConversationState.RESOLUTION
            self.fallback_count = 0
            return {
                "response": (
                    "Connecting you to support resources: You can email support@workspace.edu "
                    "or chat live during business hours (Mon-Fri 9:00 AM - 6:00 PM IST). "
                    "Is there anything else I can assist with?"
                ),
                "state": self.state,
                "intent": "human_support",
                "confidence": 1.0,
                "is_exit": False
            }

        # 5. Check for Standalone Greetings
        # If the input contains a greeting AND question tokens, treat it as a query rather than pure greeting
        is_greeting = bool(self.GREETING_REGEX.search(cleaned_input))
        words = normalized.split()
        if is_greeting and len(words) <= 3:
            self.state = ConversationState.INTENT_IDENTIFICATION
            self.fallback_count = 0
            return {
                "response": "Hello! Welcome to Customer Support. How can I assist you with your projects, business hours, or certificates today?",
                "state": self.state,
                "intent": "greeting",
                "confidence": 1.0,
                "is_exit": False
            }

        # 6. Check for Contextual Follow-Up Query
        contextual_resp = self.handle_contextual_followup(cleaned_input)
        if contextual_resp:
            self.fallback_count = 0
            return contextual_resp

        # 7. Intent Identification (Query Matching)
        best_match, confidence = self.identify_intent(cleaned_input)

        if best_match and confidence >= self.CONFIDENCE_THRESHOLD:
            self.state = ConversationState.RESOLUTION
            self.last_intent = best_match["id"]
            self.fallback_count = 0

            greeting_prefix = ""
            if is_greeting:
                greeting_prefix = "Hello! "

            answer = best_match["answer"]
            full_response = (
                f"{greeting_prefix}{answer}\n\n"
                f"Did that answer your question, or is there anything else I can help you with?"
            )
            return {
                "response": full_response,
                "state": self.state,
                "intent": best_match["id"],
                "confidence": confidence,
                "is_exit": False
            }

        # 8. Low Confidence / Graceful Fallback
        self.state = ConversationState.INTENT_IDENTIFICATION
        fallback_msg = self.get_fallback_response()
        return {
            "response": fallback_msg,
            "state": self.state,
            "intent": None,
            "confidence": confidence,
            "is_exit": False
        }

    def reset(self) -> None:
        """Reset conversation state, memory, and fallback counter."""
        self.state = ConversationState.GREETING
        self.last_intent = None
        self.fallback_count = 0

    def run(self) -> None:
        """Interactive command-line chat session."""
        print("=" * 65)
        print(" 🤖 Customer Support & Product Assistant (Rule-Based)")
        print(" Type your questions, 'help' for options, or 'exit'/'bye' to leave.")
        print("=" * 65)

        self.state = ConversationState.GREETING
        print("Bot: Hello! How can I assist you today?")

        while True:
            try:
                user_input = input("You: ")
            except (KeyboardInterrupt, EOFError):
                print("\nBot: Session terminated. Goodbye!")
                break

            result = self.respond(user_input)
            print(f"Bot: {result['response']}")

            if result["is_exit"]:
                break


def main():
    chatbot = RuleBasedChatbot()
    chatbot.run()


if __name__ == "__main__":
    main()
