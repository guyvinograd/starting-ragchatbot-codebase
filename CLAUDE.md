# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A RAG (Retrieval-Augmented Generation) chatbot that answers questions about course materials. Users interact via a web chat UI; the backend uses ChromaDB for vector search and Anthropic's Claude API (with tool use) to generate answers.

## Commands

### Run the app
```bash
cd backend && uv run uvicorn app:app --reload --port 8000
```
Or use `./run.sh` from the project root. The app serves at http://localhost:8000.

### Install dependencies
```bash
uv sync
```

### Environment setup
A `.env` file in the project root must contain `ANTHROPIC_API_KEY=<key>`. Loaded by `python-dotenv` in `backend/config.py`.

## Architecture

### Query Flow
1. Frontend (`frontend/script.js`) POSTs `{ query, session_id }` to `/api/query`
2. `backend/app.py` FastAPI handler delegates to `RAGSystem.query()`
3. `RAGSystem` (orchestrator) wraps the query, retrieves session history, and calls `AIGenerator.generate_response()` with a `search_course_content` tool definition
4. Claude decides whether to answer directly or call the search tool
5. If tool is called: `CourseSearchTool` → `VectorStore.search()` → ChromaDB semantic search → results sent back to Claude in a **second API call** (without tools) for synthesis
6. Response + sources returned to frontend, rendered as markdown

### Key Components
- **`backend/rag_system.py`** — Central orchestrator wiring all components together
- **`backend/ai_generator.py`** — Anthropic API client; handles the two-call tool-use pattern (initial call with tools → tool execution → follow-up call without tools)
- **`backend/vector_store.py`** — ChromaDB wrapper with two collections: `course_catalog` (metadata, used for fuzzy course name resolution) and `course_content` (chunked text for search)
- **`backend/search_tools.py`** — Abstract `Tool` base class + `CourseSearchTool` + `ToolManager`; tools are registered and exposed to Claude as callable functions
- **`backend/document_processor.py`** — Parses course files (expected format: header lines for title/link/instructor, then `Lesson N:` markers), chunks text by sentence boundaries with overlap
- **`backend/session_manager.py`** — In-memory per-session conversation history (max 2 exchanges), formatted as plain text for the system prompt
- **`backend/config.py`** — Dataclass with all settings (model, chunk size, embedding model, etc.)

### Document Format
Course text files in `docs/` follow this structure:
```
Course Title: <title>
Course Link: <url>
Course Instructor: <name>

Lesson 0: <title>
Lesson Link: <url>
<content...>

Lesson 1: <title>
<content...>
```

### Data Flow at Startup
On startup (`app.py` startup event), all `.txt/.pdf/.docx` files in `docs/` are processed, chunked, embedded with `all-MiniLM-L6-v2`, and stored in ChromaDB (persisted at `./chroma_db`). Existing courses are skipped by title.

### Frontend
Static HTML/CSS/JS served by FastAPI's `StaticFiles` mount. Uses `marked.js` for markdown rendering. No build step required.

## Tech Stack
- **Python 3.13+**, managed with **uv**
- **FastAPI + uvicorn** — web server
- **ChromaDB** — vector database (persistent, stored in `backend/chroma_db/`)
- **sentence-transformers** (`all-MiniLM-L6-v2`) — embedding model
- **Anthropic SDK** — Claude API with tool use (model: `claude-sonnet-4-20250514`)

## Rules
- Always use `uv` for package management, never `pip`. Use `uv add` to add dependencies and `uv sync` to install.
- Always use `uv run` to execute Python files (e.g., `uv run python script.py`), never bare `python`.

## Important Patterns
- All backend imports use bare module names (e.g., `from config import config`), so the server must be started from the `backend/` directory
- The tool system uses an abstract base class (`Tool`) with `get_tool_definition()` and `execute()` — new tools should follow this pattern and be registered with `ToolManager`
- Vector search supports optional `course_name` (fuzzy-matched via catalog) and `lesson_number` filters
