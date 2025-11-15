# AI Documentation Generator — Design Document  
*(Writer + Reviewer Loop, Single-Folder Knowledge Base, `writer` Python CLI, Switchable LLMs: Gemini / OpenAI)*

---

## 1. Overview

`writer` is a CLI-driven AI documentation generator that produces high-quality technical documents using a **writer–reviewer loop**, a **single folder** as the knowledge base, and **switchable LLM backends** (OpenAI/Gemini).

### Core Workflow
1. **Writer Agent**  
   - Takes a short idea and an optional partial doc.  
   - Retrieves context from a single knowledge folder.  
   - Produces a structured draft in Markdown + metadata.

2. **Reviewer Agent**  
   - Scores the draft.  
   - Returns structured, machine-actionable feedback.  
   - Can require either full rewrite or patch edits.

3. **Loop**  
   - Continues writer → reviewer cycle until acceptance or max iterations.

### Key Capabilities
- Single-folder reference index (`knowledge/`)
- Switchable LLM engines  
- Configurable writer and reviewer guidelines  
- Patch-based editing for minor fixes  
- ASCII/Mermaid diagrams as code supported  
- Output = Markdown + structured JSON metadata

---

## 2. Goals & Non-Goals

### Goals
- Generate clear, concise, reliable design/tech/blog documents.
- Handle partial document continuation.
- Allow guideline customization (writer/reviewer).
- Use local folder as authoritative reference.
- Provide CLI-first experience with `writer`.

### Non-Goals
- No web UI.
- No automatic publishing to Confluence/Notion.
- No guarantee of perfect correctness without human review.
- No document style normalization — flexible based on guidelines.

---

## 3. Architecture (High-Level)

User Idea → Retriever (over folder)
↓
Writer Agent → Draft
↓
Reviewer Agent → Structured feedback
↺ (loop)
Final Markdown + metadata.json

### Components
- **Loader**: scans a single folder, extracts text & metadata.  
- **Chunker**: token-based splitting with overlap.  
- **Embedder**: embedding model for retrieval.  
- **Vector Store**: Chroma (default).  
- **Retriever**: similarity search.  
- **Writer**: generates/edits documents.  
- **Reviewer**: scores, suggests improvements, emits patch instructions.  
- **CLI**: `writer` with `uv run`.

---

## 4. CLI (uv) — Usage

### Command
```bash
uv run writer run [OPTIONS]
Example
bash
uv run writer run \\
  --folder ./knowledge \\
  --idea "Design Kafka → BigQuery ingestion pipeline" \\
  --partial ./drafts/part.md \\
  --llm gemini \\
  --writer-guidelines ./guidelines/writer.md \\
  --reviewer-guidelines ./guidelines/reviewer.md \\
  --out ./output/design.md \\
  --metadata-out ./output/design.json \\
  --max-iters 3
Important Flags
Flag	Description
--folder	Single-folder knowledge base
--idea	Required idea input
--partial	Optional partial doc
--writer-guidelines	Writer rules
--reviewer-guidelines	Reviewer rules
--llm	openai / gemini
--out	Output markdown
--metadata-out	JSON metadata
--max-iters	Loop limit

5. Knowledge Indexing & Retrieval
Supported File Types
.md, .txt, .py, .java, .json, .yaml, .yml, .pdf, .go

Chunking
size ≈ 800 tokens

overlap ≈ 150 tokens

Vector Store
Default → Chroma (persistent local)

Optional → FAISS/Pinecone via wrapper

Metadata stored: filename, relative path, last_modified, chunk_id.

6. LLM Abstraction Layer
The system provides a unified interface for switching models.

Provider Interface (concept)
python
class LLMProvider:
    def chat(self, system, user, temperature=0.0, max_tokens=1500):
        ...
Supported:

OpenAI GPT-4.x / GPT-5.x

Gemini 1.5/2.x

Notes
Model selection configurable via CLI.

Credentials read from environment variables.

Cloud LLMs are optional and require explicit user opt-in.

7. Prompt Templates
Writer Prompt (Template)
Expand from idea.

Continue from partial doc.

Pull in retrieved references.

Follow writer guidelines.

Output JSON with:

markdown

sections

(optional) diff when in edit mode

Reviewer Prompt (Template)
Reviewer evaluates based on reviewer guidelines and returns JSON:

json
{
  "accept": false,
  "score": 0-100,
  "major_rewrite": false,
  "issues": [],
  "suggestions": [],
  "changes": [],
  "clarifying_questions": []
}
8. Patch-Based Editing (Preferred)
Patch-editing ensures minimalistic surgical changes instead of rewriting the entire document.

Key Idea
major_rewrite = true → regenerate full draft

major_rewrite = false → apply patches (replace/insert/append/etc.)

Supported Patch Operations
replace

insert_before

insert_after

append

add_section

Flow
if accept:
    done
else if major_rewrite:
    regenerate
else:
    apply patches
Patch-based editing is reliable, token-efficient, and prevents good content from being overwritten.

9. Feedback Loop Logic
draft = writer(idea, partial_doc, references)

for i in range(max_iters):
    review = reviewer(draft, references)

    if review.accept or review.score >= threshold:
        save(draft, review)
        break

    if review.major_rewrite:
        draft = writer(idea, draft, references, mode="rewrite")
    else:
        patch = review.changes
        draft = writer(idea, draft, references, patches=patch, mode="edit")
10. Output Format
Markdown Output (design.md)
Standard structure:

# Title

## Summary

## Goals

## Assumptions

## Proposed Design

## APIs / Interfaces

## Diagrams
- Mermaid or ASCII (diagram-as-code only)

## Risks & Mitigations

## Open Questions

## References
Metadata Output (design.json)
{
  "llm": "gemini-1.5-pro",
  "score": 92,
  "iterations": 2,
  "timestamp": "2025-11-15T08:00:00+05:30",
  "references": [
    {"file": "knowledge/kafka.md", "chunk": 4}
  ]
}
11. Security & Compliance
Folder scanning should ignore .env, secrets, keys.

Optional secret scrubbing before indexing.

Local vector DB persisted securely.

Warn user before sending internal text to cloud LLMs.

12. Extensibility & Future Enhancements
Reviewer dashboard UI

Multi-review flow (architect + SRE + security)

Automated diagram generation from flows

Notion/Confluence exporters

Local LLM support via GGUF

13. Developer Quickstart
Install minimal deps
pip install langchain chromadb openai pypdf typer rich
Implement
folder loader

chunker

embedder

vector store wrapper

writer agent

reviewer agent

patch engine

CLI with typer

Run
uv run writer run \\
  --folder ./knowledge \\
  --idea "Design webhook service" \\
  --llm openai \\
  --out ./design.md
14. Repo Structure
writer/
├─ cli.py
├─ llm_provider.py
├─ indexer.py
├─ retriever.py
├─ writer_agent.py
├─ reviewer_agent.py
├─ patcher.py
├─ feedback_loop.py
├─ guidelines/
│   ├─ writer.md
│   └─ reviewer.md
├─ knowledge/
└─ output/
