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
- There are no configured frontend lint/test/typecheck scripts; use `npm run build` as the frontend smoke check.
- Backend unit tests are **pure Python**: they need neither a database nor Django settings. Run every one of them from `backend/` with `python run_tests.py`. Packages: `apps/api_proxy/tests/` (OpenAI↔Anthropic adapters, streaming state machines, response-id mapping), `apps/dashboard/tests/` (balance runway), `apps/image_gen/tests/` (image pricing, billing copy rules, billing-path invariants).
- `run_tests.py` scans `apps/*/tests/` instead of a hard-coded list, and **fails** if a `tests/` directory lacks `__init__.py` — unittest would otherwise skip it silently. Never enumerate test packages by hand in docs or scripts: `apps/dashboard/` has no `__init__.py`, so `python -m unittest discover -s apps -t .` skipped that whole package **without any error** while the docs claimed it ran.
- Streaming bytes must be decoded through `IncrementalUtf8Decoder`, never `chunk.decode('utf-8', errors='replace')`. A TCP/HTTP fragment can split a multi-byte character; single-shot decoding replaces it with U+FFFD, turning one Chinese character into three `�` — permanently, and the upstream data was fine. The same helper is used by the usage-parsing buffers in `views_openai.py` / `views_responses.py`.
- Billing invariants, all three must stay green: every deduction happens inside `transaction.atomic()` **and** behind `select_for_update()`, with the balance re-read under the lock (`views_openai.calculate_and_deduct_cost` and `image_gen.views._deduct_cost` are two implementations of one thing — fix both). Image generation deducts **before** persisting `GeneratedImage` rows; the reverse order lets a request that fails on insufficient balance leave downloadable images behind. Because of that order, a failure while saving the image must be refunded (`image_gen.views._refund_cost`): credit the balance back, write a `type='refund'` `Bill`, and zero that generation's `cost` as the idempotency marker. The refund takes the same locks in the same order as the deduction (`User` before `ImageGeneration`) — the reverse order lets a concurrent deduct and refund wait on each other. A refund failure is logged and surfaced to the user, never raised: it would hide the original error.
- `_deduct_cost` returns `(cost, DEDUCT_OK | DEDUCT_INSUFFICIENT | DEDUCT_ERROR)`, not a boolean. A server-side failure (DB read/write blew up) must never be reported as "insufficient balance" — that nudges the user to top up and dresses a 500 up as a 400.
- Money and identifier rules have exactly one home: image pricing (including the fallback unit price used when `per_image_price = 0`, which means "unset", not "free") lives in `apps/image_gen/pricing.py`; the user-facing billing copy and amount formatting live in `apps/image_gen/billing.py`; the `chatcmpl…` → `resp…` id mapping lives in `apps/api_proxy/adapters/ids.py` and is imported by both the streaming and the non-streaming adapter. Do not add a second copy under `views.py` / `response_adapter.py` / `streaming_adapter.py`.
- For backend smoke checks beyond the unit tests: `python manage.py check`.

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
