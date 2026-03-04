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

---

## Feature: Frontend Quality Tooling (Prettier)

## Overview

Added Prettier as the standard code formatter for all frontend files, equivalent to how `black` works for Python. This establishes consistent, automatic formatting across `script.js`, `index.html`, and `style.css`.

---

## New Files

### `frontend/package.json`
Node package manifest introducing Prettier as a dev dependency with three npm scripts:
- `npm run format` — auto-formats all frontend files in place
- `npm run format:check` — checks formatting without modifying files (for CI)
- `npm run quality` — alias for format check with a success message

### `frontend/.prettierrc`
Prettier configuration matching the project's existing style:
- 4-space indentation (`tabWidth: 4`)
- Single quotes in JavaScript (`singleQuote: true`)
- Trailing commas where valid in ES5 (`trailingComma: "es5"`)
- Semicolons on (`semi: true`)
- 80-character print width

### `frontend/.prettierignore`
Excludes `node_modules/` from formatting runs.

### `scripts/format-frontend.sh`
Shell script that installs Prettier if needed and runs `prettier --write` on all frontend files. Run from the project root:
```bash
./scripts/format-frontend.sh
```

### `scripts/check-frontend.sh`
Shell script that checks formatting without modifying files. Exits with a non-zero code if any file is out of format — suitable for CI pipelines:
```bash
./scripts/check-frontend.sh
```

---

## Modified Files

### `frontend/script.js`
- Removed double blank lines between function blocks (now consistently single blank line)
- Extracted the inline `sources.map(...)` expression from the long template-literal line into a named `sourceLinks` variable, keeping lines within the 80-char print width
- Wrapped the `createNewSession` fetch call so the `method` option sits on its own line (consistent multi-line object style)
- Wrapped the long `addMessage(...)` welcome call to avoid exceeding 80 characters
- Wrapped long ternary in `loadCourseStats` for `courseTitles.innerHTML` assignments
- Arrow function parameters consistently use parentheses: `(e) =>`, `(button) =>`, `(s) =>`

### `frontend/index.html`
- Re-indented with 4-space indentation at every nesting level (Prettier's HTML formatting)
- Each HTML attribute placed on its own line for multi-attribute elements (buttons with `class` + `data-question`, input with multiple attributes, SVG element)
- Void elements use self-closing syntax: `<meta ... />`, `<link ... />`, `<input ... />`
- Removed trailing blank line before `</body>`

### `frontend/style.css`
- `*, *::before, *::after` selector expanded so each pseudo-element is on its own line
- `.no-courses, .loading, .error` grouped selector expanded so each selector is on its own line
- Single-line heading rules (`h1 { font-size: 1.5rem; }`) expanded to multi-line blocks for consistency

---

## Usage

Install Prettier once:
```bash
cd frontend && npm install
```

Format all files:
```bash
npm run format          # from frontend/
# or
./scripts/format-frontend.sh   # from project root
```

Check formatting (no writes):
```bash
npm run format:check    # from frontend/
# or
./scripts/check-frontend.sh    # from project root
```
