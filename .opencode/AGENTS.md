# YouTube clone (test assignment)
Stack: FastAPI, PostgreSQL, MinIO, ffmpeg worker (PG queue), Vue3+TS+Vite, docker compose, nginx.
Layout: backend/ frontend/ deploy/ docs/ scripts/ install.sh. Lead owns root, deploy/, docs/, git.

## Rules (all agents)
- Talk to user in Russian, terse (caveman style). Code, commits, security warnings: normal wording.
- Locate before read: jcodemunch symbol search / grep → read line ranges. Never re-read an unchanged file. Don't list whole trees, don't read lockfiles, node_modules, old migrations.
- Cap command output: `| tail -n 40`, `-q`, `--maxfail=1`. Never dump full logs; grep the error.
- context7 only when unsure about a library API; narrow query.
- Tests: run only tests affected by the change. Full suite once per milestone, by its owner.
- Same error: max 2 attempts with the same approach, then change diagnosis. After 3 failures → report to Lead in ≤5 lines (cause, tried, need).
- Docker: stack stays up. Code is bind-mounted with reload. No down/recreate/rebuild unless Dockerfile or deps changed. NEVER `down -v`, `volume rm/prune`, `system prune`.
- API contract = FastAPI schemas → /openapi.json. Frontend types via `npm run gen:api`. Contract change → tell Lead in one line.
- No new files/docs/abstractions without clear need. No out-of-scope refactors.
- Secrets only in .env (gitignored); keep .env.example current. Only Lead commits.
- Don't hand back recommendations: find cause, fix, verify, continue. Report only real blockers.
- Final report ≤10 lines: done / files / contract changes / blockers.