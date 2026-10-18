# Dynamic styles and reusable JavaScript

## Source of truth
- `web/styles/palette.css`: centralized literal color palette. All application stylesheets reference CSS variables from this file rather than embedding color literals.
- `web/styles/theme-tokens.css`: web theme and design tokens; runtime overrides are supported.
- `web/styles/theme.css`, `web/styles/design-system.css`, `web/styles/invoice.css`, `mobile/styles/shared.css`: component/layout rules only.
- `web/js/tokens.js`: backward-compatible theme loader and settings integration.
- `web/js/styles.js`: standalone ES module API, importable by any module.

## Import from any JavaScript module
```js
import { setTokens, setTheme, cssVar, toggleTheme } from '/web/js/styles.js';

setTokens({ '--gap-page': '24px', '--card': 'var(--c-xxxxxxxx)' });
setTheme({ color: '#2f7bff', radius: 16, font_scale: 100, mode: 'dark' });
const brandColor = cssVar('--bl');
toggleTheme();
```

## Add a dynamic style
Define a variable in `web/styles/palette.css` (for palette colors) or the appropriate token stylesheet, then consume it with `var(--token-name)` from CSS or SVG presentation attributes. Avoid `style="..."` attributes and direct visual styling in JavaScript. JavaScript should manage behavior and state; styling belongs in CSS and SVG should reference CSS custom properties.

The project keeps the existing classic-script entry points for compatibility and exposes the ESM API through `web/js/styles.js`.


ساختار پوشه‌ها و ورودی‌های واحد CSS/JS در `FRONTEND_STRUCTURE.md` توضیح داده شده است.

## Form controls and editors (`web/styles/controls.css`)
Every native control is styled from `--ctl-*` tokens, so one `Tokens.set()` / `setTheme()` call restyles all of them live (web and mobile PWAs share the file through `index.css`):

- text-like inputs (text, number, date, time, search, password...), `textarea`, `select` (custom arrow), checkbox, radio, range, color, file (`::file-selector-button`), `progress`/`meter`
- `contenteditable` / `.ds-editor` (+ `.ds-editor-bar` toolbar, `data-placeholder`), autofill, validation (`:user-invalid`, `[aria-invalid=true]`), read-only, disabled
- unclassed `button`, links, `details/summary`, `code/pre`, `dialog`, `fieldset`, scrollbars, `::selection`, Leaflet popups/zoom controls

```js
import { setTokens } from '/web/js/styles.js';
setTokens({ '--ctl-h': '46px', '--ctl-radius': '12px', '--ctl-check': '20px' });
```
Theme payloads may also carry `vars: { '--ctl-h': '46px' }`; only `--ctl-*` / `--ds-*` keys with safe values are accepted.
