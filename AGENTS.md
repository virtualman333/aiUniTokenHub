# AGENTS.md

## Project Shape
- `backend/` is a Django 4.2 + DRF API service; entrypoints are `backend/manage.py`, `backend/config/settings.py`, and `backend/config/urls.py`.
- `frontend/` is a Vue 3 + Vite + Element Plus app; entrypoints are `frontend/src/main.js` and `frontend/src/router/index.js`.
- Backend API prefixes are mounted in `backend/config/urls.py`: `/api/users/`, `/api/proxy/`, `/api/dashboard/`, `/api/models/`, `/api/tickets/`, and `/api/image-gen/`.
- Frontend routes use `/app` for user pages and `/admin` for the Vue admin UI; Django admin is also `/admin/` on the backend server, not through the Vite proxy.

## Commands
- Backend setup/run from `backend/`: `pip install -r requirements.txt`, then `python manage.py migrate`, then `python manage.py runserver`.
- Create migrations only when model changes require them: `python manage.py makemigrations`, then run `python manage.py migrate`.
- Frontend setup/run/build from `frontend/`: `npm install`, `npm run dev`, `npm run build`, `npm run preview`.
- `npm run build` runs `vite build && node scripts/zip-dist.js`, so it creates both `frontend/dist/` and `frontend/dist.zip`.
- There are no configured frontend lint/test/typecheck scripts and no backend test files discovered; use focused smoke checks such as `python manage.py check` or `npm run build` when appropriate.

## Environment
- Backend reads `.env` via `python-dotenv`; start from `backend/.env.example` and provide MySQL settings plus optional Redis.
- Django settings use MySQL by default and intentionally bypass Django's MySQL version support check for MySQL 5.7 compatibility.
- Frontend API base is `VITE_API_BASE_URL` and defaults to `/api`; `frontend/.env.development` and `.env.production` both set `/api`.
- Vite dev/preview proxy only forwards `/api` to `http://127.0.0.1:8000`; do not add `/admin` proxy unless deliberately replacing the Vue admin route.

## Frontend Notes
- `@` aliases to `frontend/src` in `vite.config.js` and `tsconfig.json`.
- Element Plus components and Vue/Vue Router/Pinia APIs are auto-imported by `unplugin-auto-import` and `unplugin-vue-components`; generated declarations are `frontend/src/auto-imports.d.ts` and `frontend/src/components.d.ts` and are gitignored.
- Router metadata drives SEO through `@vueuse/head`; admin routes set `noIndex`.
- `vite-plugin-prerender` is installed but disabled; enabling it requires the approval/config steps documented in `frontend/SEO-OPTIMIZATION.md` and `vite.config.js` comments.

## Backend Notes
- `AUTH_USER_MODEL` is `users.User`; authentication uses `apps.users.authentication.JWTAuthentication` and the `EmailOrUsernameBackend`.
- API responses commonly use the repo's unified `{code, msg, data}` shape from `apps.utils.response.APIResponse`; frontend Axios unwraps that format in `frontend/src/stores/index.js`.
- OpenAI-compatible proxy routes live under `/api/proxy/v1/...`; unsupported `/v1/*` paths fall through to `ModelsView`.
- The proxy supports OpenAI and Anthropic protocol adaptation in `backend/apps/api_proxy/adapters/`; preserve request/stream/response conversion behavior when touching proxy code.
- Image generation stores generated files under Django `MEDIA_ROOT` and has a cleanup command: `python manage.py cleanup_images`.

## Dependency And Artifact Gotchas
- `frontend/package.json` has npm scripts, but both `pnpm-lock.yaml` and `package-lock.json` are present; avoid updating both lockfiles accidentally when changing dependencies.
- Root `.gitignore` ignores `frontend/package-lock.json`, generated frontend declaration files, `dist/`, `dist.zip`, `.env`, logs, and Django media.
