# Changes Made

## Feature: API Testing Infrastructure

The following files were created/modified to add API endpoint testing for the RAG chatbot backend.

---

### New Files

#### `backend/tests/__init__.py`
Empty package marker so pytest treats the directory as a Python package.

#### `backend/tests/conftest.py`
Shared test fixtures and one-time setup:
- Adds `backend/` to `sys.path` so bare module imports (`from config import config`) work during tests.
- Stubs `chromadb`, `sentence_transformers`, and `anthropic` in `sys.modules` before any backend code is imported, preventing heavyweight model downloads and API calls in the test environment.
- Imports the FastAPI `app` with `RAGSystem` and `StaticFiles` patched so the module-level instantiation and static file mount don't fail (no frontend directory exists in the test environment).
- Provides session-scoped `mock_rag` and `client` fixtures for use across all test modules.
- Provides an `autouse` fixture that resets mock call history before each test for clean assertions.
- Provides `sample_query` and `sample_course_data` helper fixtures.

#### `backend/tests/test_api.py`
Tests for all three API endpoint groups:

**`POST /api/query`**
- Returns correct answer, sources, and session_id.
- Auto-creates a session_id when none is provided.
- Passes query and session_id through to `RAGSystem.query()`.
- Handles empty sources list.
- Returns HTTP 500 when `RAGSystem.query()` raises an exception.
- Returns HTTP 422 when the required `query` field is missing.
- Accepts an empty query string.

**`GET /api/courses`**
- Returns `total_courses` and `course_titles` from `RAGSystem.get_course_analytics()`.
- Response matches the `CourseStats` schema (correct types).
- Calls `get_course_analytics()` exactly once per request.
- Returns HTTP 500 when analytics raises an exception.
- Handles a catalog with zero courses.

**`DELETE /api/clear-session/{session_id}`**
- Returns `{"status": "cleared"}` with HTTP 200.
- Delegates to `session_manager.clear_session()` with the correct session_id.

---

### Modified Files

#### `pyproject.toml`
- Added `httpx>=0.27.0` to the `dev` dependency group (required by FastAPI's `TestClient`).
- Added `[tool.pytest.ini_options]` section with `testpaths = ["backend/tests"]` so `uv run pytest` discovers tests without extra arguments.

---

### Running the Tests

```bash
# From the project root
uv run pytest

# With verbose output
uv run pytest -v

# Run a specific test class
uv run pytest backend/tests/test_api.py::TestQueryEndpoint -v
```

---

## Feature: Dark/Light Theme Toggle

### Feature
Added a dark/light theme toggle button that persists the user's preference across sessions.

### Files Modified

#### `frontend/index.html`
- Added a `<button id="themeToggle">` element positioned fixed at top-right, containing SVG sun and moon icons.
- Bumped CSS cache-bust version (`style.css?v=12`) and JS version (`script.js?v=10`).

#### `frontend/style.css`
- Added `[data-theme="light"]` CSS variable overrides for all color tokens (background, surface, text, border, etc.) providing a clean light theme with good contrast.
- Added a `*` transition rule (`background-color`, `border-color`, `color`, `box-shadow` — 0.25s ease) for smooth theme switching animations.
- Added `.theme-toggle` button styles: fixed position top-right, circular, 40px, adapts to theme variables, hover scale effect, focus ring.
- Sun icon shown in dark mode; moon icon shown in light mode via `[data-theme="light"]` display toggling.

#### `frontend/script.js`
- Added `initTheme()` — reads saved preference from `localStorage` and applies `data-theme="light"` on `<html>` if needed; attaches click handler to the toggle button.
- Added `toggleTheme()` — toggles `data-theme` attribute on `document.documentElement` and persists the choice to `localStorage`.
- Both functions called on `DOMContentLoaded`.
