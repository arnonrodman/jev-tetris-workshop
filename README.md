# Jev Tetris Workshop

A hands-on workshop for testing **Jev**, TypeSafe AI's "System One" model, by
having it play Tetris. You get a fully working, light-themed, **single-page**
Tetris game in the browser (`public/index.html` — no separate CSS/JS files,
no build step), a small **Python (Flask)** server that asks Jev for its next
move, and a live panel that shows exactly what Jev chose, how confident it
was, and how the alternatives ranked.

The UI uses generic, standard falling-block-puzzle conventions (a dark
playfield "screen", a next/hold preview box, a score panel) — it does not
reproduce the specific branded visual design of any official, trademarked
Tetris product.

> **What is Jev?** Jev is a model from TypeSafe AI (announced September 2026,
> currently in early access) built to answer typed, structured questions
> against a piece of "state" instead of generating text. You send it a state
> plus one or more *questions* (Choice / Score / Noul) and it returns typed
> answers with probabilities and a confidence score — no text parsing
> required. This project uses the **Choice** question type: "given these N
> legal Tetris moves, which one is best?"
>
> The speed/cost/accuracy numbers on TypeSafe's own site are the vendor's
> published benchmarks, not something independently verified here — treat
> them as a starting claim to test for yourself, which is exactly what this
> workshop lets you do.

---

## 1. What you're building

```
Browser (Tetris UI, light theme)
   │  1. enumerates every legal placement for the falling piece
   │  2. describes each one in plain language
   │  POST /api/decide-placement  { board, piece, legalPlacements }
   ▼
Python/Flask server (server/app.py)
   │  3. turns each placement into one Choice option ("criteria")
   │  4. calls TypeSafe's API with the board as `state`
   │  client.system_one(state=..., questions=...)
   ▼
TypeSafe API → Jev
   │  5. returns { choice, confidence, probabilities } in one response
   ▼
Server → Browser
      6. UI animates the piece into Jev's chosen column/rotation and drops it
```

Rather than asking Jev to control the piece key-by-key (left, right, rotate),
the browser first computes **every legal final resting placement** for the
current piece — every combination of rotation and column, simulated all the
way down, including which lines it would clear and how many holes it would
create. That list becomes the options for a single **Choice** question per
piece. This is deliberately the same shape of problem TypeSafe describes Jev
being good at: a fixed menu of options, described in plain language, chosen
in one fast structured call — a "smart if-statement" rather than a chatbot
you have to prompt-engineer.

If the server can't reach TypeSafe (no API key yet, network hiccup, request
timeout), the browser automatically falls back to a small hand-written
heuristic bot so the demo never just freezes — the UI tells you when this
happens. The game engine, rendering, and this fallback logic all live in
`public/tetris.js` (plain JavaScript) since they run in the browser; only the
one call out to TypeSafe lives in Python.

## 2. Prerequisites

- Python 3.10 or newer (`python3 --version` to check)
- A TypeSafe AI account with API access and a key from
  <https://console.typesafe.ai/keys> (sign up for early access at
  <https://typesafe.ai> if you don't have one yet)

## 3. Setup

```bash
cd jev-tetris-workshop
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Open `.env` and paste your key:

```
TYPESAFE_API_KEY=sk_...your key...
PORT=3000
```

Run it:

```bash
python server/app.py
```

Open <http://localhost:3000>, click **Start**, and watch the "Jev's
decision" panel on the right update every time a new piece spawns.

If you don't have a key yet, it still runs — the AI toggle will show
**heuristic fallback** instead of **jev**, so you can rehearse the workshop
mechanics before your API access comes through.

### 3a. Doing this in PyCharm instead of a terminal

1. Unzip `jev-tetris-workshop.zip` anywhere on disk.
2. **File → Open…** in PyCharm and select the unzipped `jev-tetris-workshop`
   folder (open it as its own project, not as a subfolder of another one).
3. Set up the interpreter: **PyCharm → Settings/Preferences → Project:
   jev-tetris-workshop → Python Interpreter → Add Interpreter → Add Local
   Interpreter → Virtualenv Environment → New**, base interpreter Python 3.10+,
   location defaults to `jev-tetris-workshop/venv` — leave it and click OK.
   PyCharm creates the venv and switches the project to it.
4. Open the built-in **Terminal** tab (bottom of the window) — it auto-activates
   the venv you just created — and run:
   ```bash
   pip install -r requirements.txt
   cp .env.example .env
   ```
5. Open `.env` in the editor and paste your `TYPESAFE_API_KEY`.
6. Right-click `server/app.py` in the Project panel → **Run 'app'**. PyCharm
   creates a run configuration for you; the green ▶ button in the toolbar
   re-runs it from then on. Watch the Run panel for the "running on
   http://localhost:3000" line (and the "⚠️ TYPESAFE_API_KEY is not set"
   warning if `.env` didn't load — double check the file is named `.env`,
   not `.env.example` or `.env.txt`).
7. Open <http://localhost:3000> in your browser and click **Start**.

To track this locally in git before you have a remote yet (see §10 for
pushing once you do): **VCS → Enable Version Control Integration → Git**,
then **VCS → Commit** (⌘K / Ctrl+K) to make your first commit. PyCharm
already respects `.gitignore`, so `.env` and `venv/` won't be tracked.

## 4. Using the UI

- **AI (Jev) control** toggle — switch off to play manually with the arrow
  keys (rotate: `↑`/`Z`/`X`, hard drop: `Space`, hold: `C`). Useful for
  comparing your own placements against Jev's.
- **Speed slider** — controls how fast the piece animates toward Jev's
  chosen placement (and, in manual mode, how fast gravity pulls it down).
- **Jev's decision** card — shows:
  - a badge: `jev`, `heuristic fallback`, or `thinking…`
  - the chosen placement described in the same plain language Jev received
  - a confidence bar (TypeSafe's calibrated confidence score, 0–100%)
  - the top probabilities across the alternative placements Jev considered
  - round-trip latency in milliseconds

## 5. How the state and question are built

Every time a piece spawns, `public/tetris.js` computes the legal placements
and sends a payload like this to the server:

```json
{
  "board": ["..........", "..........", "...", "XXXXXXXX.."],
  "currentPiece": "T",
  "holdPiece": null,
  "nextPiece": "L",
  "nextNextPiece": "I",
  "score": 1400,
  "linesCleared": 6,
  "legalPlacements": [
    { "id": "p0", "rotation": 0, "columns": [3,4,5], "linesCleared": 0, "holes": 0, "aggregateHeight": 12, "maxHeight": 3, "bumpiness": 2 },
    { "id": "p1", "rotation": 1, "columns": [7,8],   "linesCleared": 1, "holes": 0, "aggregateHeight": 9,  "maxHeight": 2, "bumpiness": 1 }
  ]
}
```

`server/app.py` turns each `legalPlacements` entry into a Choice option and
sends this to TypeSafe using the Python SDK:

```python
from typesafe_sdk import Choice, TypeSafeClient

client = TypeSafeClient()  # reads TYPESAFE_API_KEY

response = client.system_one(
    state={
        "board_rows_top_to_bottom": board,
        "falling_piece": current_piece,
        # ...
    },
    questions={
        "placement": Choice(
            instructions=(
                "Choose the best final placement (rotation + column) for the "
                "falling Tetris piece... Prefer placements that clear lines, "
                "avoid creating holes, keep the stack low, and keep the "
                "surface flat."
            ),
            criteria={
                "p0": "Rotation state 0, occupies column(s) 3, 4, 5. Landing here clears 0 line(s) ...",
                "p1": "Rotation state 1, occupies column(s) 7, 8. Landing here clears 1 line(s) ...",
            },
        ),
    },
)

print(response.answers["placement"].choice)       # e.g. "p1"
print(response.answers["placement"].confidence)   # e.g. 0.82
print(response.answers["placement"].probabilities)
```

Jev answers with the chosen id, a confidence score, and a probability for
every option — all in one round trip, however many placements there are (a
single Tetris piece never has more than a few dozen legal placements, well
under the Choice primitive's 255-option limit).

## 6. Workshop exercises

These are meant to be done in order, each building on the last. They're a
good way to actually exercise TypeSafe's primitives rather than just watch
the demo run.

1. **Read the confidence signal.** Play a few dozen pieces and watch the
   confidence bar. Does it drop on genuinely ambiguous boards (several
   similarly-good placements) and stay high when one placement is clearly
   best? Try adding a rule in `server/app.py`: when confidence is below,
   say, 0.3, return a flag the frontend uses to prefer the heuristic bot
   instead of trusting Jev's pick — this mirrors the "confidence-gated
   automation" pattern TypeSafe's docs describe.

2. **Add a Noul question for Hold.** Right now the game never uses the hold
   slot in AI mode. Add a second question to the same request:
   `Noul(instructions="Would holding the current piece and playing the next one instead lead to a better outcome?")`.
   If Jev answers yes with high confidence, tell the frontend to call
   `holdPiece()` before computing placements for the swapped piece.

3. **Add a Score question for board quality.** Ask Jev to
   `Score(instructions="Rate how healthy this board's surface is", criteria=[...])`
   on the *resulting* board after each placement, and log it alongside the
   heuristic's own score in `server/app.py`. Do they agree? This is a good
   way to sanity-check Jev's judgment against a simple formula you fully
   understand.

4. **Change the instructions, not the code.** Edit only the `instructions`
   string passed to `Choice(...)` in `server/app.py` (e.g. "aggressively
   prioritize clearing multiple lines at once even if it means a taller
   stack") and observe how Jev's choices shift — no game logic changes
   needed. This is the "atomic questions, composed in code" idea from
   TypeSafe's docs: behavior changes are supposed to live in the
   instructions/criteria, not in hand-written branching logic.

5. **Measure agreement with the heuristic.** Log `chosenId` (from Jev) vs.
   the heuristic's own pick (computed client-side in `tetris.js`, via
   `pickHeuristic(placements)`) for every piece over a full game and compute
   an agreement percentage. This gives you your own, independently measured
   number to compare against TypeSafe's published benchmarks.

## 7. Troubleshooting

- **"heuristic fallback" always shows, never "jev"** — check that `.env` has
  a real `TYPESAFE_API_KEY` and that you restarted `python server/app.py`
  after editing it. Check the terminal running the server for a logged
  error.
- **401 / 403 from the API** — the key is invalid, expired, or your account
  doesn't have access yet; check the dashboard at
  <https://console.typesafe.ai/keys>.
- **`ModuleNotFoundError: No module named 'typesafe_sdk'`** — make sure your
  virtual environment is activated and `pip install -r requirements.txt`
  completed without errors.
- **Requests always time out (4s, client-side)** — check your network/VPN
  allows outbound HTTPS to `api.typesafe.ai`; corporate proxies sometimes
  block unfamiliar hosts.
- **Port already in use** — change `PORT` in `.env`.
- **Piece appears to "jitter" before dropping** — that's intentional: the
  engine visibly rotates/slides the piece one step per game tick toward
  Jev's chosen placement so you can see the move happening, not just the
  end result. Increase the speed slider to speed this up.

## 8. Security notes

- The TypeSafe API key lives only in `.env` on the server and is read via
  `os.environ["TYPESAFE_API_KEY"]` (through `TypeSafeClient()` and
  `python-dotenv`) — it is never sent to or exposed in the browser. Don't
  move the `client.system_one(...)` call into client-side code.
- `.env` is already listed in `.gitignore`. Don't commit real keys.

## 9. Project structure

```
jev-tetris-workshop/
├── README.md               this file
├── README.html             styled version of this file
├── PROMPT.md               the detailed spec this project was built from
├── requirements.txt        flask, python-dotenv, typesafe-sdk
├── .env.example            copy to .env and add your API key
├── docs/
│   ├── workshop-overview.html   what Jev is and how the workshop works
│   └── participant-guide.html   step-by-step checklist for each participant
├── server/
│   └── app.py               Flask server + the one TypeSafe API call
└── public/
    └── index.html            the entire frontend: layout, light theme,
                                game engine, rendering, and AI networking,
                                all in one self-contained page
```

> Note: `public/style.css`, `public/tetris.js`, `package.json`, and
> `server/index.js` are leftovers from earlier iterations (a multi-file
> frontend, then a Node.js server) and are no longer used — everything they
> contained now lives in `public/index.html` and `server/app.py`
> respectively. All four are safe to delete.

## 10. Push this project to GitHub

This project is meant to be checked into its own repository. Create a new,
**empty** repository on GitHub first (don't let GitHub auto-generate a
README, `.gitignore`, or license for you — that would conflict with the
files already here).

If you haven't initialized git locally yet (e.g. via §3a's PyCharm steps),
do it from inside the `jev-tetris-workshop` folder:

```bash
git init
git add .
git commit -m "Initial commit: Jev Tetris workshop"
git branch -M main
```

Either way, once you have both a local commit and an empty remote repo,
point one at the other and push:

```bash
git remote add origin https://github.com/<your-username>/jev-tetris-workshop.git
git push -u origin main
```

Replace the `origin` URL with the one GitHub shows you right after creating
the repo (the "…or push an existing repository from the command line"
section on the new-repo page gives you these exact three lines already
filled in with your username). `.env` is already excluded via `.gitignore`,
so your API key will not be committed.
