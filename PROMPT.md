# Build prompt: Jev Tetris Workshop

This is the detailed prompt that specifies this project end to end. Hand it to
a coding agent (or a human) with no other context and it should be able to
reproduce this workshop faithfully. It is also useful as a design record of
the choices already made here, and as a template for adapting the same
pattern to a different game or decision problem.

---

## 1. Goal

Build a single-page, self-contained, light-and-polished web app that plays a
falling-block puzzle game (Tetris-style) completely autonomously, where every
move is decided by **Jev**, TypeSafe AI's "System One" model, called through
its **Choice** primitive. The point of the project is to *test* Jev — not to
build the best possible Tetris bot — so the UI must make Jev's decision
process visible and legible in real time: what options it had, what it
picked, how confident it was, and how long the call took. A human should also
be able to switch AI off and play manually, and a local heuristic bot must
kick in automatically whenever the AI call is unavailable, so the demo never
just stalls.

Constraints given by the requester:
- The backend must be **Python** (not Node).
- The frontend must be **one HTML page** (not a separate JS/CSS file split),
  and should look good — a clean, modern, game-console-like presentation,
  not a bare unstyled canvas.
- Do not copy the branded visual design ("trade dress") of any official,
  trademarked Tetris product — build a generic, original-looking falling-
  block puzzle UI using standard, non-proprietary genre conventions
  (playfield, next-piece box, score panel, hold box). These conventions
  (a bordered grid, a small preview box, a score counter) are functional and
  common to dozens of unrelated puzzle games; the specific colors, chrome,
  logos, and trade dress of any single branded product are not to be
  reproduced.
- Ship as a small, runnable local project (not a hosted service), with a
  README thorough enough that someone unfamiliar with TypeSafe's API can set
  it up and run it unassisted.

## 2. Why this is a good fit for Jev specifically

TypeSafe's System One models are explicitly designed for the shape of
decision this project needs: a **fixed menu of options**, each describable in
a sentence or two, chosen against a piece of structured **state**, in a
single fast round trip — not an open-ended chat turn. Rather than having the
model drive the piece key-by-key (left/right/rotate — an awkward fit for a
model that doesn't generate free text), the right decomposition is:

1. Enumerate every **legal final resting placement** for the falling piece —
   every combination of rotation state and column, simulated all the way
   down to where it would land, including the holes it would create and the
   lines it would clear.
2. Describe each placement in one plain-language sentence.
3. Ask a single **Choice** question: "which placement is best?", with one
   option per legal placement (a handful to a few dozen — always well under
   the Choice primitive's 255-option limit).
4. Apply the chosen placement: rotate and slide the piece into position on
   screen, then hard-drop it.

This turns "play Tetris" into exactly the kind of atomic, structured decision
System One models are built for, and it naturally surfaces Jev's probability
distribution and confidence score as something meaningful: how contested was
this placement against the runner-up?

## 3. TypeSafe API contract to use

Reference: <https://docs.typesafe.ai/> (Introduction, Quickstart, Choice
primitive, Python SDK pages). Key facts the implementation depends on:

- Endpoint: `POST https://api.typesafe.ai/v1/systemone`, auth via
  `Authorization: Bearer <TYPESAFE_API_KEY>`. The Python SDK
  (`pip install typesafe-sdk`, `import typesafe_sdk`) wraps this; prefer the
  SDK over raw HTTP.
- A request has three top-level fields: `state` (a string or a JSON-like
  object — this project uses an object), `model` (defaults to `jev-latest`
  in the SDK), and `questions` (a map from an id you choose to a typed
  question).
- The **Choice** question type takes `instructions` (the question, in plain
  language) and `criteria` (a map from option id → plain-language
  description of that option, up to 255 options). In the Python SDK:
  `Choice(instructions=..., criteria={...})`.
- The response's `answers[<id>]` has `.choice` (the winning option id),
  `.probabilities` (a dict of every option id → probability, summing to 1),
  and `.confidence` (0–1, high when probability mass concentrates on one
  option, low when it's spread across several).
- `Score` and `Noul` question types exist too (rate on a rubric; yes/no) and
  are suggested as extension exercises, not required for the base build.

## 4. Architecture

```
public/index.html   — the entire frontend: game engine, canvas rendering,
                       input handling, and the one fetch() call to our own
                       server. No external JS/CSS files.
server/app.py        — Flask. Serves public/ as static files, and exposes
                       POST /api/decide-placement, the only place that talks
                       to TypeSafe. Reads TYPESAFE_API_KEY from .env via
                       python-dotenv. Never exposes the key to the browser.
requirements.txt      — flask, python-dotenv, typesafe-sdk
.env.example           — TYPESAFE_API_KEY=, PORT=3000
README.md / README.html — setup + architecture + exercises + troubleshooting
```

The browser is the source of truth for game state (board, current piece,
score, queue) and for *placement enumeration* (it already needs this logic
to render a ghost piece and to run the local heuristic fallback, so there's
no reason to duplicate it server-side). The server's only job is to turn a
list of already-computed legal placements into a Choice question and relay
the answer back — it holds no game state of its own.

## 5. Game engine requirements (frontend)

Implement a standard 10×20 board, the 7 standard tetrominoes with a 7-bag
randomizer, and for each piece store only the *unique* rotation shapes
(collapse rotation states that produce an identical silhouette, e.g. the
`O` piece has one shape, `I`/`S`/`Z` have two). For each falling piece,
implement:

- `fits(board, type, rotation, row, col)` — bounds + collision check.
- `dropRow(...)` — simulate a straight hard drop and return the resting row,
  or null if it can't land in bounds.
- `enumeratePlacements(board, type)` — for every unique rotation and every
  column the shape can occupy, compute the resting position, the resulting
  board after locking + line-clearing, and these metrics: `holes`,
  `aggregateHeight` (sum of column heights), `maxHeight`, `bumpiness` (sum of
  abs differences between adjacent column heights), and `linesCleared`.
  Assign each a stable id (`p0`, `p1`, ...).
- A local heuristic fallback: score each placement as
  `-0.51*aggregateHeight + 0.76*linesCleared - 0.36*holes - 0.18*bumpiness`
  and take the max. This must run with zero network access, purely from the
  already-computed placement list.

Sanity checks worth writing before wiring up the UI (these caught real bugs
during development and are worth keeping as a mental checklist even if not
shipped as automated tests): an `O` piece on an empty 10-wide board has
exactly 9 legal placements and creates 0 holes in all of them; an `I` piece
has 17 (7 horizontal + 10 vertical); a completely full board has 0 legal
placements for anything; sideways/vertical orientations of `T`/`S`/`Z`/`J`/`L`
*do* create a hole when hard-dropped on flat ground without a spin — that's
correct Tetris physics, not a bug, because their bottom profile is uneven.

## 6. AI integration (frontend ↔ backend)

On every piece spawn, the frontend:

1. Calls `enumeratePlacements` and builds a payload:
   ```json
   {
     "board": ["..........", "...", "XXXXXXXX.."],
     "currentPiece": "T", "holdPiece": null,
     "nextPiece": "L", "nextNextPiece": "I",
     "score": 1400, "linesCleared": 6,
     "legalPlacements": [
       {"id":"p0","rotation":0,"columns":[3,4,5],"linesCleared":0,"holes":0,"aggregateHeight":12,"maxHeight":3,"bumpiness":2}
     ]
   }
   ```
2. POSTs it to `/api/decide-placement` with a client-side timeout (~4s);
   on any failure (non-200, timeout, network error) it falls back to the
   local heuristic and flags the UI accordingly — the game must never hang
   waiting on a slow or dead API call.
3. On success, reads `chosenId`, `confidence`, `probabilities` from the
   response and matches `chosenId` back to the local placement list to get
   the target `{rotation, col}`.
4. Each subsequent game tick nudges the piece one step toward the target
   (rotate once, or shift one column) until aligned, then hard-drops it —
   so the move is visibly animated, not an instant teleport.

The backend (`server/app.py`), on `POST /api/decide-placement`:

1. Validates `legalPlacements` is a non-empty array (and ≤255).
2. Builds `criteria[id] = f"Rotation state {rotation}, occupies column(s) {columns}. Landing here clears {linesCleared} line(s) and creates {holes} new hole(s). Resulting board: max column height {maxHeight}, total height {aggregateHeight}, surface bumpiness {bumpiness} (lower is flatter)."` for every placement.
3. Calls `client.system_one(state={...board/piece/queue/score...}, questions={"placement": Choice(instructions="Choose the best final placement ... prefer clearing lines, avoiding holes, staying low and flat ...", criteria=criteria)})`.
4. Returns `{chosenId, confidence, probabilities, model, latencyMs}` as JSON,
   or a 502 with an error message on any SDK/network exception — never lets
   an exception bubble up as an unhandled 500.

## 7. UI/visual requirements

Single self-contained `public/index.html` (inline `<style>` and `<script>`,
no external CSS/JS files, no build step, no bundler). Requirements:

- Light, clean outer app shell (soft gray background, white cards, rounded
  corners, subtle shadows, an accent color) — this is the "light UI" the
  requester asked for.
- A dark, console-like playfield panel inside that shell (this is the one
  place a darker "screen" treatment makes sense, echoing a physical device's
  bezel — this is a generic convention, not copied trade dress).
- A side panel with: score/lines/level, next-piece and hold-piece previews,
  an AI/manual toggle switch, a speed slider, and — the most important part —
  a live "Jev's decision" card showing: a status badge (`jev` /
  `heuristic fallback` / `thinking…`), the chosen placement described in the
  same words sent to the model, a confidence bar, a ranked list of the top
  alternative placements with their probabilities, and round-trip latency.
- Keyboard controls for manual mode (arrow keys + rotate + hard drop + hold),
  disabled while AI mode is on.
- Responsive down to phone width (single column below ~760px).
- No dependency on any external asset, font, or script — everything inline
  or system fonts, so the page works completely offline except for the one
  `fetch('/api/decide-placement')` call.

## 8. Deliverables

- The runnable project (`public/index.html`, `server/app.py`,
  `requirements.txt`, `.env.example`, `.gitignore`).
- `README.md` and a nicely styled `README.html` covering: what Jev is (with
  an explicit caveat that TypeSafe's own published speed/cost/accuracy
  numbers are the vendor's claims, not independently verified here),
  architecture diagram, setup steps, how the state/question payload is
  built, at least five hands-on workshop exercises that exercise Jev's
  primitives beyond the base demo (confidence-gating, adding a `Noul`
  question for the hold slot, adding a `Score` question to rate board
  health, tuning behavior via instructions instead of code, measuring
  Jev-vs-heuristic agreement rate), a troubleshooting section, and a
  security note that the API key never leaves the server.
- This `PROMPT.md` itself, checked into the repo, so the design rationale
  travels with the code.

## 9. Explicit non-goals

- Not trying to build the strongest possible Tetris AI — a simple weighted
  heuristic is an intentional, named fallback, not something to out-optimize.
- Not reproducing any specific trademarked game's exact visual design.
- Not a hosted/deployed service — a local dev project meant to be run and
  read by a small workshop audience, then pushed to a GitHub repo for
  reference and reuse.
