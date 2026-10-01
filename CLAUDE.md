# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A workshop project that tests **Jev** (TypeSafe AI's "System One" model) by having it play Tetris. A single-page browser game enumerates every legal placement for the falling piece, a small Flask server turns those into one TypeSafe **Choice** question, and the UI animates Jev's pick while showing its confidence, top probabilities, and latency.

## Commands

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then set TYPESAFE_API_KEY (PORT defaults to 3000)
python server/app.py          # serves http://localhost:3000 (Flask debug mode, auto-reload)
curl localhost:3000/api/health   # {"ok": true, "hasApiKey": ...}
```

There is no build step, linter config, or test suite. The app runs without an API key: the frontend falls back to its local heuristic bot and the UI badge shows "heuristic fallback".

## Architecture

Two runtime files hold all the logic:

- **`public/index.html`**: the whole frontend in one file (inline `<style>` and `<script>`). This is a hard requirement from the spec (`PROMPT.md`): keep it one page and don't split out CSS/JS. The script covers:
  - game engine: `SHAPES`, `fits`, `dropRow`, `clearLines`, 7-bag queue, hold
  - placement enumeration: `enumeratePlacements` simulates every rotation × column down to its resting spot and computes `linesCleared`, `holes`, `aggregateHeight`, `maxHeight`, `bumpiness`
  - heuristic fallback: `heuristicScore` / `pickHeuristic`
  - AI networking: `requestAIDecision` POSTs to `/api/decide-placement` with a **4s client-side timeout**. On any failure, or if the returned `chosenId` doesn't match a placement, it uses the heuristic instead.
  - AI execution: `stepAIExecution` rotates/slides the piece **one step per tick** toward `state.aiTarget` and then hard-drops it. The visible "jitter" is intentional.
  - rendering (canvas) and the `requestAnimationFrame` loop / `tick`
- **`server/app.py`**: a thin Flask proxy that keeps the API key server-side. `/api/decide-placement` checks that there are between 1 and 255 placements (255 is the Choice option limit). It turns each placement into a plain-language criterion string keyed by placement id (`p0`, `p1`, …) and calls `client.system_one(state=..., questions={"placement": Choice(...)})` from `typesafe_sdk`. It returns `{chosenId, confidence, probabilities, model, latencyMs}`, or 502 on any SDK/network error.

Without `TYPESAFE_API_KEY`, `client` is `None` and `/api/decide-placement` returns 503, which triggers the frontend heuristic. The frontend reports every heuristic move to `/api/log-fallback` (204, logged as a warning) so client-side timeouts show up in the server terminal. `/api/health` reports `hasApiKey`.

Contract coupling: the placement fields that `enumeratePlacements` produces, the fields `requestAIDecision` sends, and the keys `app.py` reads (`p["columns"]`, `p["holes"]`, etc.) must stay in sync. If you add a placement feature, update all three.

Jev's behavior is meant to be tuned through the `instructions` string and criteria text in `app.py`, not through branching game logic (see README §6 workshop exercises).

## Gotchas

- `public/tetris.js`, `public/style.css`, `server/index.js`, and `package.json` are deprecated stubs from earlier iterations (multi-file frontend, Node server). Nothing references them. Don't add code there.
- The API key must never reach the browser. Keep the `client.system_one(...)` call server-side. `.env` is gitignored.
- The UI must not copy the branded trade dress of any official Tetris product. Stick to generic falling-block conventions (see `PROMPT.md` §1).
- `docs/workshop-overview.html` and `docs/participant-guide.html` are hand-written workshop handouts. Update them if setup steps or the Jev call flow change.
- `README.html` is a hand-maintained styled copy of `README.md`. If you change one, update the other.
