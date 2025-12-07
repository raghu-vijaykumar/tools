# System Patterns & Architecture

## Core Architecture Principles

### Modular Monorepo Design
- **UV Workspace Structure**: Independent packages with shared dependencies
- **Common Library Pattern**: Shared utilities extracted to `common/` package
- **Independent Deployment**: Each package can be deployed separately
- **Unified Development**: Single repository for coordinated development

### Component Architecture

```
┌─────────────────────────────────────────────────┐
│                CLI Aggregator                   │
│  ┌─────────────┬─────────────┬─────────────┐   │
│  │ Newsletter  │   Writer    │     TTS     │   │
│  │  Tool       │   Tool      │    Tool     │   │
│  └─────────────┴─────────────┴─────────────┘   │
└─────────────────────────────────────────────────┘
                         │
                ┌────────▼────────┐
                │   Common Lib    │
                │  ┌─────────────┬─────────────┬─────────────┐ │
                │  │    LLM      │ Embeddings │   Audio     │ │
                │  │ Abstraction │   Store    │ Processing  │ │
                │  └─────────────┴─────────────┴─────────────┘ │
                └─────────────────────────────────────────────┘
```

## Key Design Patterns

### LLM Abstraction Layer
- **Provider Interface**: Unified interface for Gemini, OpenAI, Groq
- **Configuration-Driven**: Runtime provider selection via environment
- **Fallback Support**: Automatic fallback to alternative providers on failure
- **Structured Responses**: Consistent response formatting across providers

### Pipeline Pattern for Content Processing
```
Input → Fetch → Process → Summarize → Format → Deliver
```

- **Newsletter Pipeline**: RSS → Articles → Summaries → Digest → Audio → Telegram
- **Documentation Pipeline**: Idea → Research → Draft → Review → Iterate → Finalize

### Repository Pattern for Data Management
- **Abstracted Storage**: Database operations separated from business logic
- **Migration Support**: Versioned schema changes
- **Connection Pooling**: Efficient database connection management
- **Error Recovery**: Graceful handling of database failures

### Configuration Management
- **Environment-First**: API keys and settings via environment variables
- **Validation Layer**: Configuration validation at startup
- **Sensible Defaults**: Minimal required configuration for basic functionality
- **Documentation**: Self-documenting configuration with examples

## Component Relationships

### Common Library Dependencies
```
newsletter/ → common/ (llm, telegram, audio, config, logging)
writer/ → common/ (llm, embeddings, config, logging)
tts/ → common/ (audio, config, logging)
cli/ → common/ + all tools
```

### Data Flow Patterns

#### Newsletter Tool
1. **Sources** define RSS feed configurations
2. **Fetcher** retrieves articles from feeds
3. **Scraper** extracts content from web pages
4. **Summarizer** generates AI-powered summaries
5. **Digest** compiles daily summaries
6. **Audio** generates speech from text
7. **Telegram** delivers final content

#### Writer Tool
1. **Indexer** processes knowledge base documents
2. **Writer Agent** generates initial documentation
3. **Reviewer Agent** provides feedback and critiques
4. **Feedback Loop** iterates until quality thresholds met
5. **Output** produces final documentation and metadata

## Error Handling Patterns

### Graceful Degradation
- **Service Fallbacks**: Continue operation when non-critical services fail
- **Partial Success**: Deliver available content even if some processing fails
- **Retry Logic**: Exponential backoff for transient failures
- **User Notification**: Clear error reporting without breaking workflows

### Circuit Breaker Pattern
- **API Rate Limits**: Respect provider quotas with intelligent backoff
- **Service Unavailability**: Temporary suspension during outages
- **Resource Limits**: Memory and CPU monitoring with graceful shutdown

## Testing Patterns

### Mocking Strategy
- **External APIs**: Comprehensive mocking of LLM providers and TTS services
- **Database Layer**: In-memory databases for reliable testing
- **File System**: Temporary directories for I/O testing
- **Network Calls**: Controlled network simulation

### Coverage Goals
- **90%+ Overall**: Workspace-wide test coverage target
- **95% Core Logic**: Critical business logic fully tested
- **Integration Tests**: End-to-end workflow validation
- **Performance Tests**: Load testing for scalability validation

## Deployment Patterns

### Container-First Design
- **Docker Support**: Containerized deployment for all components
- **Multi-Stage Builds**: Optimized images with minimal attack surface
- **Configuration Injection**: Environment-based configuration at runtime
- **Health Checks**: Readiness and liveness probes for orchestration

### CI/CD Pipeline
- **Automated Testing**: Full test suite on every commit
- **Dependency Scanning**: Security vulnerability detection
- **Build Optimization**: Layer caching and parallel builds
- **Release Automation**: Semantic versioning with automated releases

## Security Patterns

### API Key Management
- **Environment Variables**: Keys never committed to version control
- **Validation**: Key format and permission validation at startup
- **Rotation Support**: Easy key updates without code changes
- **Access Logging**: Audit trail for API usage

### Data Protection
- **Encryption at Rest**: Sensitive data encrypted in databases
- **Secure Transmission**: HTTPS for all external communications
- **Input Validation**: Sanitization of all user-provided content
- **Output Encoding**: Safe rendering of generated content
