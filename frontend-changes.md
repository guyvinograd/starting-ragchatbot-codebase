# Frontend Changes

## Dark/Light Theme Toggle

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
