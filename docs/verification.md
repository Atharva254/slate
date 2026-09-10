# Verification and submission checklist

The assignment is an IIFL Finance 2–3 hour prototype exercise. Keep scope small: no auth, deployment, containers, RAG, or agents are implemented.

## Final review on 10 September 2026

- Backend test suite: 32 tests passed, including disk persistence after creating a new application instance and permanent single-entry deletion.
- Frontend production build: passed.
- Two Playwright browser tests passed on Chromium: create/open/reload/delete, AI failure recovery, bounded history scrolling, 390-pixel mobile layout, and a delayed detail request racing with deletion. A failed delete leaves the item visible.
- Desktop and mobile screenshots: visually inspected; no horizontal overflow or clipped content found.
- Python test tooling emitted two upstream deprecation warnings (Starlette/httpx and AnyIO); tests passed. No global packages were upgraded.
- Real OpenRouter generation: **verified** with `deepseek/deepseek-v4-flash-0731`; browser submit/save/reload/detail and exactly three relevant tags passed. The summary preserved the pilot decisions, Friday deadline, and unconfirmed launch date. See `live-verification.json` and the refreshed `screenshot.png`. Direct Gemini remains fixture-tested only.
- GitHub's unauthenticated repository API confirmed [Atharva254/briefly](https://github.com/Atharva254/briefly) is public. `.env.example` contains configuration names with blank values; `.env` and SQLite files are ignored. No OpenRouter/Gemini credential patterns were found in tracked files (a targeted scan, not a guarantee covering every possible secret).

## Additional provider check on 10 September 2026

- Changed the OpenRouter default to `deepseek/deepseek-v4-flash-0731`.
- A real request passed through FastAPI and the OpenRouter adapter with HTTP 201 and valid JSON-schema output.
- The result contained a nonblank summary and exactly three distinct tags; create, detail, list, and retrieval after a fresh app instance all passed against a temporary SQLite database.
- The final live browser check used temporary ports 8002/5175 and a separate database under ignored `tmp/`; normal saved entries were not changed.

## Readability and UX fixes from the review

- Formatted Python consistently at 100 columns; kept routes, persistence, schemas, and provider adapters separate.
- Added comments explaining synchronous action locks, request ordering, and cancellation of pending detail reads during deletion. Existing comments explain database transaction boundaries, provider error sanitization, and original-text preservation.
- Serialized deletion against submit/refresh/open actions and ignored superseded list responses, preventing stale results from reviving a deleted row.
- Reset history scroll on refresh and detail scroll on selection; made the detail frame keyboard-focusable and kept card focus outlines visible.
- Corrected save/delete notices and generic network-error wording; refreshed README screenshot and verification dates.

## Requirement mapping

| Requirement | Implementation / evidence |
| --- | --- |
| Modern frontend, form, loading/error, list/detail/delete | `frontend/src/App.jsx` |
| Python REST API | `backend/main.py`: POST/GET `/entries`, GET/DELETE `/entries/{id}` |
| Real LLM integration | `backend/ai.py` + `backend/providers/`: real OpenRouter success; interchangeable direct Gemini adapter |
| Concise summary and exactly three tags | Provider JSON Schema plus strict `AIResult` validation |
| Persistent original + output | `backend/schema.sql`, `data/entries.db`; automated app-restart check |
| AI failure handling | Deadline, HTTP failure, invalid JSON/schema, incomplete/blocked output |
| Useful automated test | `backend/tests/test_app.py` |
| Setup, six concise README answers | `README.md` |
| No committed credentials | Names-only `.env.example`, `.gitignore` |
| Screenshot of working flow | `docs/screenshot.png`: actual OpenRouter output; separate fixture evidence is labelled |
| Public repository | `main` published at [Atharva254/briefly](https://github.com/Atharva254/briefly) |

## Repeat live verification (requires the selected provider key)

1. Create `.env` from `.env.example`. Fill `OPENROUTER_API_KEY` locally, or supply it in the environment. Select provider/model as described in `providers.md`; the default uses OpenRouter.
2. Start both servers using README instructions. Do not use real customer or financial data.
3. Submit the built-in sample. Confirm a concise summary and exactly three relevant tags. Compare the summary with the original; reject invented claims.
4. Reload the page, reopen the entry, stop/restart the backend, and reopen it again.
5. Capture the full browser view with the generated summary, three tags, and original visible as `docs/screenshot.png`. The README currently uses this real screenshot. `npm run verify:live` automates submission, reload/detail checks, and capture; it may consume credits.
6. Check `git status --short` before publishing. Exclude `.env`, SQLite, private notes, logs, and test artifacts. Create your public repository and push the source when ready.

## Reproduce browser checks without a key

Tests use dedicated ports 8001 and 5174, leaving the normal app on 8000 and 5173. They refuse to reuse an existing test server.

```powershell
cd frontend
npx playwright install chromium
npm run test:e2e
```

Playwright starts the frontend and the explicit `backend.tests.browser_server` test harness. Only the OpenRouter HTTP transport is replaced. Each run uses a new database under ignored `tmp/browser-tests/`. The test submits, checks loading, validates the displayed original and three tags, reloads/reopens, injects invalid provider output, retries successfully, and checks mobile overflow. Its screenshot includes a visible fixture label. This verifies application wiring but cannot substitute for the required real LLM call.

## Scope and known trade-offs

- No key is discovered by scanning unrelated files, browser sessions, or credentials stores. Tests use an obviously fake key and an isolated SQLite file.
- All runtime generations use the real provider path. Tests can inject an HTTP transport; there is no runtime demo mode or silent mock fallback.
- JSON/schema validity does not establish factual accuracy or prompt-injection immunity. The model has no tools, file access, history, or database access; source content is isolated as its user message. React renders strings as text.
- SQLite serializes writes. Short writes and a five-second lock wait are suitable for this prototype; multiple instances and high write throughput need a server database.
- Offset pagination is simple; newly inserted records can shift later pages. The UI deduplicates loaded IDs; cursor pagination is a production improvement.
- Delete permanently removes the local row without undo. There is no authentication or per-user ownership; this remains a localhost prototype.
- UI polish, provider interchangeability, deletion, and the interview notes were later user-requested additions. They exceed the original minimum; this repository should not be represented as proof that all work fit the suggested 2–3 hour timebox.
- A lost browser response or database commit acknowledgment creates uncertainty. The UI recommends checking history before retrying. No exactly-once promise is made.
- Character and output limits bound normal inputs, not adversarial network upload sizes. A production reverse proxy should impose byte-size and concurrency limits.
- The development/preview proxy keeps frontend API calls same-origin. No permissive CORS policy is enabled. `vite preview` is local build verification, not a production server.
- No claim of provider availability, pricing, data-retention guarantees, or live model quality is made without account-specific verification.
