"""
Thin Flask server for the Jev Tetris workshop.

  - serves the static frontend (../public)
  - proxies one endpoint to the TypeSafe API so the API key never reaches
    the browser

See README.md for setup instructions.
"""

import os
import time
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory
from typesafe_sdk import Choice, TypeSafeClient

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
PUBLIC_DIR = BASE_DIR / "public"

app = Flask(__name__, static_folder=str(PUBLIC_DIR), static_url_path="")

# Reads TYPESAFE_API_KEY from the environment. See .env.example.
client = TypeSafeClient()


@app.route("/")
def index():
    return send_from_directory(PUBLIC_DIR, "index.html")


@app.route("/api/decide-placement", methods=["POST"])
def decide_placement():
    data = request.get_json(force=True, silent=True) or {}

    board = data.get("board")
    current_piece = data.get("currentPiece")
    hold_piece = data.get("holdPiece")
    next_piece = data.get("nextPiece")
    next_next_piece = data.get("nextNextPiece")
    score = data.get("score")
    lines_cleared = data.get("linesCleared")
    legal_placements = data.get("legalPlacements")

    if not isinstance(legal_placements, list) or len(legal_placements) == 0:
        return jsonify({"error": "legalPlacements must be a non-empty array"}), 400
    if len(legal_placements) > 255:
        # The Choice primitive supports up to 255 options; a single Tetris
        # piece never produces anywhere near that many legal placements, but
        # we guard against it defensively.
        return jsonify({"error": "too many legalPlacements (max 255)"}), 400

    # Build one Choice option per legal final placement of the falling piece.
    # Each description is plain language so the model can compare options
    # without needing to know our internal field names.
    criteria = {}
    for p in legal_placements:
        columns = ", ".join(str(c) for c in p["columns"])
        criteria[p["id"]] = (
            f"Rotation state {p['rotation']}, occupies column(s) {columns}. "
            f"Landing here clears {p['linesCleared']} line(s) and creates {p['holes']} new hole(s). "
            f"Resulting board: max column height {p['maxHeight']}, total height {p['aggregateHeight']}, "
            f"surface bumpiness {p['bumpiness']} (lower is flatter)."
        )

    started_at = time.time()
    try:
        response = client.system_one(
            state={
                "board_rows_top_to_bottom": board,
                "falling_piece": current_piece,
                "held_piece": hold_piece or "none",
                "next_piece": next_piece,
                "next_next_piece": next_next_piece,
                "score": score,
                "lines_cleared_so_far": lines_cleared,
            },
            questions={
                "placement": Choice(
                    instructions=(
                        "Choose the best final placement (rotation + column) for the falling Tetris "
                        "piece, out of the given legal options. Prefer placements that clear lines, "
                        "avoid creating holes, keep the stack low, and keep the surface flat (low "
                        "bumpiness). Avoid placements that build a tall or uneven stack that risks a "
                        "future top-out."
                    ),
                    criteria=criteria,
                ),
            },
        )
        answer = response.answers["placement"]
        latency_ms = round((time.time() - started_at) * 1000)
        app.logger.info(
            "[jev] piece %s: jev chose %s (confidence %s, %s ms)",
            current_piece, answer.choice, answer.confidence, latency_ms,
        )
        return jsonify(
            {
                "chosenId": answer.choice,
                "confidence": answer.confidence,
                "probabilities": answer.probabilities,
                "model": response.model,
                "latencyMs": latency_ms,
            }
        )
    except Exception as err:  # noqa: BLE001 - surface any SDK/network error to the client
        app.logger.error("Jev request failed: %s", err)
        return jsonify({"error": "TypeSafe API request failed", "detail": str(err)}), 502


@app.route("/api/log-fallback", methods=["POST"])
def log_fallback():
    # The browser reports every move it made with the local heuristic instead
    # of Jev, so fallbacks are visible here even when the server never saw
    # the failure (e.g. a client-side timeout).
    data = request.get_json(force=True, silent=True) or {}
    app.logger.warning(
        "[heuristic] piece %s: heuristic chose %s — %s",
        data.get("piece"), data.get("chosenId"), data.get("reason") or "unknown reason",
    )
    return "", 204


@app.route("/api/health")
def health():
    return jsonify({"ok": True, "hasApiKey": bool(os.environ.get("TYPESAFE_API_KEY"))})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    if not os.environ.get("TYPESAFE_API_KEY"):
        print(
            "⚠️  TYPESAFE_API_KEY is not set — the game will automatically fall back to "
            "the local heuristic bot until you add a key to .env (see README.md)."
        )
    app.run(host="0.0.0.0", port=port, debug=True)
