# Web application

The Phase 4 web client is a Next.js App Router application with strict TypeScript. It provides registration and login, a protected assistant workspace, a responsive chat shell, and persistent light/dark/system themes.

## Commands

```bash
npm ci
npm run dev
npm run lint
npm run typecheck
npm test
npm run build
```

The browser calls `/api/v1/*` on the web origin. Next.js proxies those requests to `API_INTERNAL_URL` (default `http://localhost:8000`), which keeps the session cookie same-origin and avoids exposing backend secrets.

The chat composer is intentionally a UI-only preview until the provider-neutral agent API is delivered in Phase 5. Authentication is fully connected to the Phase 3 API.
