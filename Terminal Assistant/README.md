# Rule-Based Customer Support & Product Assistant

An intelligent, rule-based conversational assistant implemented in Python that parses user input using regular expressions and keyword analysis. It handles business hours, product/internship FAQs, maintains conversational states, provides contextual follow-up handling, executes progressive fallbacks for low-confidence queries, and supports clean exit commands.

---

## 🚀 Key Features

1. **Regular Expression & Keyword Parsing**:
   - Compiled regular expressions for rapid matching of common patterns and intent expressions.
   - Stopword filtering and keyword extraction for robust token overlap scoring.
   - Pre-built domain patterns and synonym maps that support variations in user phrasing (e.g., "timings", "operating hours", "when do you open", "upload project code").

2. **JSON Dataset Integration**:
   - Reads greetings and question-answer pairs directly from [`faqs.json`](faqs.json).
   - Works seamlessly with minimal JSON structures (`question` and `answer`) as well as extended schemas (`keywords`, `patterns`, `id`).
   - Includes graceful internal defaults in case the dataset file is absent or malformed.

3. **Conversational State Management**:
   The assistant tracks the conversation through a deterministic state machine:
   - **`GREETING`**: Initial connection state.
   - **`INTENT_IDENTIFICATION`**: Actively parsing queries, greetings, or help requests.
   - **`RESOLUTION`**: Follows answering a query. Solicits confirmation from the user (`"Did that answer your question?"`).
     - Affirmation ("yes", "thanks"): Acknowledges resolution.
     - Negation ("no", "didn't help"): Offers escalation to human support.
     - Follow-up: Resolves contextual questions linked to the previous topic (`last_intent`).
   - **`EXIT`**: Triggered by clean exit commands (`bye`, `exit`, `quit`, `goodbye`). Closes session gracefully.

4. **Multi-Tier Graceful Fallback**:
   - Evaluates a composite confidence score between `0.0` and `1.0`.
   - If confidence is below the threshold (`0.40`), triggers progressive fallbacks:
     - **Attempt 1**: Polite request to rephrase with suggested topics.
     - **Attempt 2**: Displays a formatted help menu of available capabilities.
     - **Attempt 3+**: Offers escalation to live human support (`support@workspace.edu`).

5. **Clean Exit Commands**:
   - Supports commands such as `bye`, `exit`, `quit`, `goodbye`, `q`, and `see ya` at any point in the conversation.

---

## 📁 Project Structure

```
project3/
├── chatbot.py        # Core chatbot engine with state machine and CLI loop
├── faqs.json         # JSON FAQ and greetings dataset
├── test_chatbot.py   # Comprehensive unit test suite (16 tests)
└── README.md         # Documentation and usage guide
```

---

## 🛠️ Requirements & Installation

- **Python 3.8+** (Uses only Python Standard Library: `re`, `json`, `os`, `typing`, `unittest`).
- No external third-party dependencies required.

---

## 💻 Usage

### 1. Interactive Terminal Mode
Run the assistant directly in your terminal:
```bash
python3 chatbot.py
```

**Example Conversation Session:**
```text
=================================================================
 🤖 Customer Support & Product Assistant (Rule-Based)
 Type your questions, 'help' for options, or 'exit'/'bye' to leave.
=================================================================
Bot: Hello! How can I assist you today?
You: Hello!
Bot: Hello! Welcome to Customer Support. How can I assist you with your projects, business hours, or certificates today?
You: What are your hours of operation?
Bot: We operate Monday through Friday from 9:00 AM to 6:00 PM IST.

Did that answer your question, or is there anything else I can help you with?
You: Yes, thank you!
Bot: Wonderful! Let me know if you have any other questions. (Type 'exit' or 'bye' if you are finished)
You: When will I receive my certificate?
Bot: Certificates are reviewed and issued within 3-5 business days after your code review.

Did that answer your question, or is there anything else I can help you with?
You: bye
Bot: Thank you for reaching out to customer support. Have a wonderful day! Goodbye.
```

---

### 2. Programmatic Python API
You can embed `RuleBasedChatbot` into any service, web API, or messaging webhook:

```python
from chatbot import RuleBasedChatbot

bot = RuleBasedChatbot("faqs.json")

# Process queries
result = bot.respond("How do I submit my internship project?")
print("Bot response:", result["response"])
print("Current State:", result["state"])
print("Intent:", result["intent"])
print("Confidence:", result["confidence"])
print("Should Exit:", result["is_exit"])
```

---

## 🧪 Running Unit Tests

The test suite covers normalization, keyword extraction, regex matching, state machine transitions, contextual follow-ups, multi-tier fallbacks, and exit commands:

```bash
python3 -m unittest test_chatbot.py -v
```
