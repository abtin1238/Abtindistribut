# Shared frontend runtime

`core.js` is loaded before page-specific scripts on web, invoice, visitor and driver pages. It owns the shared API client, HTML escaping, POST/PATCH helpers, and offline sync queue orchestration.

## Usage (classic-script pages)

```js
Shared.configure({ apiBase: '/api', token: () => currentToken });
const api = Shared.api;
const esc = Shared.esc;
const post = Shared.post;
```

Configure the token getter once per application entry point; the shared API client reads the current token at request time. Do not redefine API clients or HTML escaping in feature files.

## Offline sync

Use `Shared.syncQueue({ Q, REJ, jget, jset, flush, onResults })`. Feature-specific callbacks should contain only behavior that differs by app (for example, mapping server result IDs to visitor references). Queue retry/rejection handling stays centralized.

## Theme

Theme values and persistence are owned by `/web/js/tokens.js` and CSS custom properties. Mobile `Theme` is only an adapter for the mobile UI; it delegates state changes to `Tokens`.
