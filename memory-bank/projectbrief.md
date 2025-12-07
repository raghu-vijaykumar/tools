# AI Tools Monorepo - Project Brief

## Core Purpose
A comprehensive Python-based monorepo providing AI-powered automation tools for content creation, newsletter management, and technical documentation generation.

## Primary Goals
1. **Newsletter Automation**: Daily fetching, summarization, and delivery of tech news from RSS feeds
2. **AI Documentation Generation**: Automated technical writing using LLM-powered writer-reviewer feedback loops
3. **Unified Tool Ecosystem**: Shared utilities and consistent CLI interfaces across all tools
4. **Modular Architecture**: Independently deployable packages with shared common utilities

## Key Requirements
- **Multi-LLM Support**: Integration with Google Gemini, OpenAI GPT, and Groq for flexible AI processing
- **Audio Generation**: Text-to-speech capabilities for newsletter digests
- **Telegram Integration**: Bot-based delivery system for automated content distribution
- **RAG Capabilities**: Knowledge base integration for enhanced documentation generation
- **High Test Coverage**: 90%+ test coverage across all packages with comprehensive mocking
- **Modern Python Stack**: Python 3.12+ with UV package management and workspace structure

## Success Criteria
- Automated daily newsletter generation and delivery
- High-quality AI-generated technical documentation
- Consistent user experience across all CLI tools
- Maintainable codebase with clear separation of concerns
- Comprehensive test suite ensuring reliability
- Easy setup and deployment for end users

## Scope Boundaries
- Focus on automation tools rather than general-purpose applications
- Target technical users who need content automation solutions
- Support major LLM providers but avoid becoming a generic AI framework
- Maintain monorepo structure for shared development but allow independent deployment
