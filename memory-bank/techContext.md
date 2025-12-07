# Technical Context

## Technology Stack

### Core Runtime
- **Python 3.12+**: Modern Python with advanced features and performance improvements
- **UV Package Manager**: Fast, reliable dependency management and workspace handling
- **Pytest Framework**: Comprehensive testing with coverage reporting and mocking

### AI & ML Libraries
- **Google Generative AI**: Gemini models for text generation and summarization
- **OpenAI API**: GPT models for advanced language processing
- **Groq API**: Fast inference for real-time processing needs
- **LangChain**: Framework integration for LLM workflows
- **Transformers**: Hugging Face models for specialized tasks
- **PyTorch**: Deep learning framework for custom ML models
- **Sentence Transformers**: Efficient text embedding generation

### Data Processing & Storage
- **SQLite**: Lightweight database for local data storage
- **Pandas**: Data manipulation and analysis
- **BeautifulSoup4**: HTML parsing and web scraping
- **Feedparser**: RSS/Atom feed processing
- **Librosa**: Audio signal processing
- **Soundfile**: Audio file I/O operations
- **Pydub**: Audio manipulation and effects

### External Integrations
- **Google Text-to-Speech**: High-quality voice synthesis
- **Telegram Bot API**: Automated messaging and file delivery
- **Playwright**: Browser automation for advanced scraping
- **Requests**: HTTP client for API interactions
- **Tenacity**: Retry logic for resilient API calls

### Development Tools
- **Black**: Code formatting for consistency
- **MyPy**: Static type checking
- **Ruff**: Fast linting and code quality
- **Pre-commit Hooks**: Automated code quality checks
- **Coverage.py**: Test coverage measurement and reporting

## Development Environment

### Local Setup
```bash
# Install UV package manager
pip install uv

# Clone repository
git clone <repository-url>
cd tools

# Install dependencies
uv sync

# Set up environment variables
cp .env.example .env
# Edit .env with API keys

# Run tests
uv run pytest
```

### Environment Variables Required
```env
# LLM Providers (choose at least one)
GOOGLE_API_KEY=your_google_api_key
OPENAI_API_KEY=your_openai_api_key
GROQ_API_KEY=your_groq_api_key

# Optional Services
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

### IDE Configuration
- **VS Code**: Recommended with Python extension
- **Python Interpreter**: Use UV-managed virtual environment
- **Type Checking**: Enable MyPy integration
- **Testing**: Configure pytest runner

## Package Structure

### Workspace Members
```
common/          # Shared utilities library
├── src/common/
│   ├── llm.py          # LLM abstraction layer
│   ├── embeddings.py   # Vector storage and retrieval
│   ├── audio.py        # Audio processing utilities
│   ├── telegram.py     # Telegram bot integration
│   ├── config.py       # Configuration management
│   └── logging.py      # Structured logging

newsletter/      # Newsletter automation tool
├── src/newsletter/
│   ├── main.py         # CLI entry point
│   ├── fetcher.py      # RSS feed processing
│   ├── scraper.py      # Web content extraction
│   ├── summarizer.py   # AI-powered summarization
│   ├── digest.py       # Content compilation
│   ├── audio.py        # Audio generation
│   └── telegram.py     # Message delivery

writer/          # AI documentation generator
├── src/writer/
│   ├── cli.py          # Command interface
│   ├── writer_agent.py # Content generation
│   ├── reviewer_agent.py # Quality assessment
│   ├── feedback_loop.py # Iterative improvement
│   ├── indexer.py      # Knowledge base processing
│   └── guidelines/     # Custom writing rules

tts/             # Text-to-speech service
└── src/tts/
    ├── cli.py          # Audio generation CLI
    └── ...

cli/             # Unified CLI aggregator
└── cli/
    └── main.py         # Meta CLI interface
```

## Technical Constraints

### Performance Limitations
- **API Rate Limits**: Respect provider quotas (OpenAI: 10k TPM, Google: regional limits)
- **Memory Usage**: Large embedding models require significant RAM
- **Network Latency**: External API calls introduce processing delays
- **Storage Limits**: Local SQLite database size constraints

### Compatibility Requirements
- **Python Version**: Minimum 3.12 for modern features
- **Platform Support**: Windows, macOS, Linux (primary focus on Linux deployment)
- **Dependency Conflicts**: Careful version pinning to avoid workspace conflicts
- **GPU Requirements**: Optional CUDA support for accelerated ML inference

### Security Considerations
- **API Key Protection**: Environment-only storage, never in code
- **Input Validation**: Sanitize all user inputs and API responses
- **Output Encoding**: Prevent injection attacks in generated content
- **Audit Logging**: Track API usage and sensitive operations

## Dependency Management

### UV Workspace Configuration
- **Shared Dependencies**: Common packages defined at workspace level
- **Version Constraints**: Compatible version ranges across packages
- **Lock File**: Deterministic builds with uv.lock
- **Source Overrides**: Custom PyTorch CUDA builds for GPU support

### Key Dependencies Explained

#### Core AI/ML
- `google-generativeai`: Official Google AI SDK
- `openai`: Official OpenAI Python client
- `groq`: Groq API client for fast inference
- `langchain`: LLM framework integration
- `transformers`: Hugging Face model ecosystem

#### Audio Processing
- `gtts`: Google Text-to-Speech API
- `librosa`: Audio feature extraction
- `pydub`: Audio file manipulation
- `soundfile`: WAV/MP3 file handling

#### Data & Web
- `beautifulsoup4`: HTML parsing
- `feedparser`: RSS feed processing
- `requests`: HTTP client
- `lxml`: Fast XML/HTML processing

#### Development
- `pytest`: Testing framework
- `pytest-cov`: Coverage reporting
- `pytest-mock`: Mocking utilities

## Build & Deployment

### Local Development
- **Hot Reload**: UV supports fast dependency updates
- **Virtual Environment**: Isolated development environment
- **Editable Installs**: Develop packages in-place

### Production Deployment
- **Container Images**: Docker support for all components
- **CI/CD Pipeline**: Automated testing and deployment
- **Environment Separation**: Development, staging, production configs
- **Monitoring**: Logging and metrics collection

### Distribution
- **PyPI Packages**: Individual package publishing
- **Docker Hub**: Container image distribution
- **GitHub Releases**: Pre-built binaries and archives
- **Documentation**: Automated docs generation and hosting
