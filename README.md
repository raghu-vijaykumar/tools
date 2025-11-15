# AI Tools Monorepo

A Python UV workspace containing AI-powered tools for newsletter automation, documentation generation, and more. Built with modern LLM integrations and unified CLI access.

## Features

- **Newsletter Automation**
  - Fetches daily newsletters from RSS feeds of tech blogs
  - Summarizes articles using multiple LLM providers (Gemini, Groq, OpenAI)
  - Generates audio versions using Google Text-to-Speech
  - Delivers digests via Telegram bot

- **AI Documentation Writer**
  - Generates technical documentation using writer-reviewer feedback loops
  - Supports Retrieval Augmented Generation (RAG) from knowledge bases
  - Switchable LLM backends with custom guidelines
  - Produces structured Markdown with metadata

- **Shared Utilities**
  - Unified LLM abstraction layer for multiple providers
  - Embedding and vector store management
  - Audio processing and text-to-speech generation
  - Telegram bot integration
  - Logging and configuration management

- **CLI Aggregator**
  - Unified command-line interface for all tools
  - Consistent experience across different utilities

## Setup

1. Install uv if not already installed:
   ```bash
   # Via pip
   pip install uv

   # Or via other methods: https://github.com/astral-sh/uv
   ```

2. Clone or download the project.
3. Install dependencies: `uv sync`
4. Set up environment variables: Copy `.env.example` to `.env` and add your API keys.

### Environment Configuration

Create a `.env` file in the project root with the following API keys:

```env
# Required for LLM features (choose one or more)
GOOGLE_API_KEY=your_google_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
GROQ_API_KEY=your_groq_api_key_here

# Optional: for Telegram newsletter delivery
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

### Telegram Bot Setup (Optional)

To receive newsletter digests via Telegram:

1. Message [@BotFather](https://t.me/botfather) on Telegram
2. Send `/newbot` and follow instructions to create your bot
3. Copy the bot token provided by BotFather
4. Message your bot to start a chat and get your chat ID
5. Add the bot token and chat ID to your `.env` file as shown above

## Usage

### Newsletter Tool

Run newsletter fetching and processing:

```bash
# From newsletter package
uv run newsletter --days 7

# Via CLI aggregator (when implemented)
uv run python cli/cli/main.py newsletter --days 7
```

This will fetch articles from the last 7 days, summarize them, generate digests, create audio files, and optionally send via Telegram.

Data is stored in the `newsletter/data/` directory, organized by date.

### AI Documentation Writer

Generate technical documentation:

```bash
uv run writer run \
  --idea "Design Kafka → BigQuery ingestion pipeline" \
  --references-folder ./writer/knowledge \
  --writer-guidelines ./writer/guidelines/writer.md \
  --reviewer-guidelines ./writer/guidelines/reviewer.md \
  --output ./output/design.md \
  --metadata-out ./output/design.json \
  --max-iters 3
```

Key options:
- `--idea`: The documentation concept
- `--references-folder`: Knowledge base directory for RAG
- `--llm`: LLM provider (gemini/openai/groq)
- `--writer-guidelines`: Custom writing rules
- `--reviewer-guidelines`: Review criteria
- `--partial`: Continue from existing document

### CLI Aggregator (Planned)

Unified interface (currently in development):

```bash
# Planned unified CLI
uv run python cli/cli/main.py --help
```

## Project Structure

```
├── common/           # Shared utilities and LLM abstractions
├── newsletter/       # Newsletter automation tool
├── writer/           # AI documentation generator
├── cli/             # Meta CLI aggregator
├── pyproject.toml   # UV workspace configuration
└── uv.lock         # Dependency lock file
```

Each package is independently runnable but shares common utilities.

## Requirements

- Python 3.12+
- UV package manager (https://github.com/astral-sh/uv)
- API keys for desired LLM providers:
  - Google API key (for Gemini and Text-to-Speech)
  - OpenAI API key (for GPT models)
  - Groq API key (for fast inference)
- Internet connection for fetching RSS feeds and API calls
- Knowledge base directories for documentation writer
