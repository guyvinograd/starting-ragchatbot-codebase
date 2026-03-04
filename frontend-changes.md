# Frontend Quality Changes

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
