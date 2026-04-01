from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import matplotlib.animation as animation
import matplotlib.pyplot as plt
import numpy as np

UNKNOWN = -1
EMPTY = 0
FILLED = 1


def load_log_payload(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    if isinstance(payload, list):
        return {
            "metadata": {},
            "events": payload,
        }

    return payload


def collect_log_paths(
    log_paths: Optional[List[str]],
    log_dir: Optional[str],
) -> List[str]:
    paths: List[Path] = []

    if log_paths:
        paths.extend(Path(path) for path in log_paths)

    if log_dir:
        paths.extend(sorted(Path(log_dir).glob("*.json")))

    if not paths:
        paths = [Path("nonogram_turn_log.json")]

    unique_paths = sorted({path.resolve() for path in paths})
    return [str(path) for path in unique_paths]


def default_gif_path(log_path: str, output_dir: Optional[str]) -> str:
    log_file = Path(log_path)
    if output_dir is None:
        return str(log_file.with_suffix(".gif"))

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    return str(output / f"{log_file.stem}.gif")


def grid_to_image_array(grid: List[List[int]]) -> np.ndarray:
    """
    Map:
    UNKNOWN -> 0.5 (gray)
    EMPTY   -> 1.0 (white)
    FILLED  -> 0.0 (black)
    """
    arr = np.zeros((len(grid), len(grid[0])), dtype=float)
    for r in range(len(grid)):
        for c in range(len(grid[0])):
            if grid[r][c] == UNKNOWN:
                arr[r, c] = 0.5
            elif grid[r][c] == EMPTY:
                arr[r, c] = 1.0
            else:
                arr[r, c] = 0.0
    return arr


def animate_log(
    events: List[Dict[str, Any]],
    row_clues: Optional[List[List[int]]] = None,
    col_clues: Optional[List[List[int]]] = None,
    interval: int = 800,
    save_path: Optional[str] = None,
) -> animation.FuncAnimation:
    frames = [event for event in events if event["action"] in {"start", "write", "pass", "end"}]
    if not frames:
        raise ValueError("No frames found in log")

    n_rows = len(frames[0]["grid_after"])
    n_cols = len(frames[0]["grid_after"][0])

    fig, ax = plt.subplots(figsize=(max(5, n_cols * 0.6), max(5, n_rows * 0.6)))

    img = ax.imshow(
        grid_to_image_array(frames[0]["grid_after"]),
        cmap="gray",
        vmin=0.0,
        vmax=1.0,
        interpolation="nearest",
    )

    ax.set_xticks(np.arange(-0.5, n_cols, 1), minor=True)
    ax.set_yticks(np.arange(-0.5, n_rows, 1), minor=True)
    ax.grid(which="minor", linewidth=1)
    ax.tick_params(which="both", bottom=False, left=False, labelbottom=False, labelleft=False)

    title = ax.set_title("")

    cross_texts = []
    for r in range(n_rows):
        row_texts = []
        for c in range(n_cols):
            text = ax.text(c, r, "", ha="center", va="center", fontsize=16)
            row_texts.append(text)
        cross_texts.append(row_texts)

    if col_clues is not None:
        col_labels = ["\n".join(map(str, clue)) if clue else "0" for clue in col_clues]
        ax.set_xticks(np.arange(n_cols))
        ax.set_xticklabels(col_labels, fontsize=9)
        ax.tick_params(top=True, labeltop=True, bottom=False, labelbottom=False)

    if row_clues is not None:
        row_labels = [" ".join(map(str, clue)) if clue else "0" for clue in row_clues]
        ax.set_yticks(np.arange(n_rows))
        ax.set_yticklabels(row_labels, fontsize=9)
        ax.tick_params(left=True, labelleft=True)

    highlight = plt.Rectangle((-1, -1), 1, 1, fill=False, linewidth=3)
    ax.add_patch(highlight)

    def update(frame_idx: int):
        event = frames[frame_idx]
        grid = event["grid_after"]

        img.set_data(grid_to_image_array(grid))

        for r in range(n_rows):
            for c in range(n_cols):
                if grid[r][c] == EMPTY:
                    cross_texts[r][c].set_text("x")
                else:
                    cross_texts[r][c].set_text("")

        agent = event["agent"]
        action = event["action"]
        turn = event["turn"]
        move = event.get("move")

        if action == "write" and move is not None:
            r = move["row"]
            c = move["col"]
            value_name = move["value_name"]
            title.set_text(f"Turn {turn} | {agent.upper()} | write ({r}, {c}) = {value_name}")
            highlight.set_xy((c - 0.5, r - 0.5))
            highlight.set_width(1)
            highlight.set_height(1)
            highlight.set_visible(True)
        elif action == "pass":
            title.set_text(f"Turn {turn} | {agent.upper()} | pass")
            highlight.set_visible(False)
        else:
            title.set_text(f"Turn {turn} | {agent.upper()} | {action}")
            highlight.set_visible(False)

        artists = [img, title, highlight]
        for r in range(n_rows):
            for c in range(n_cols):
                artists.append(cross_texts[r][c])
        return artists

    ani = animation.FuncAnimation(
        fig,
        update,
        frames=len(frames),
        interval=interval,
        blit=False,
        repeat=False,
    )

    if save_path is not None:
        if save_path.endswith(".gif"):
            ani.save(save_path, writer="pillow")
        elif save_path.endswith(".mp4"):
            ani.save(save_path, writer="ffmpeg")
        else:
            raise ValueError("save_path should end with .gif or .mp4")

    return ani


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a GIF or MP4 from a solver log JSON file.")
    parser.add_argument(
        "--log-path",
        dest="log_paths",
        action="append",
        help="Path to a log JSON file. Repeat this flag to pass multiple logs.",
    )
    parser.add_argument("--log-dir", help="Directory containing multiple log JSON files")
    parser.add_argument("--gif-path", help="Output GIF path for a single-log run")
    parser.add_argument("--output-dir", help="Output directory for auto-named GIFs in batch mode")
    parser.add_argument("--interval", type=int, default=700)
    parser.add_argument("--show", action="store_true", help="Show the animation window after saving")
    args = parser.parse_args()

    log_paths = collect_log_paths(args.log_paths, args.log_dir)
    if len(log_paths) > 1 and args.gif_path:
        raise ValueError("Use --output-dir instead of --gif-path when rendering multiple logs")

    for log_path in log_paths:
        payload = load_log_payload(log_path)
        metadata = payload.get("metadata", {})
        row_clues = metadata.get("row_clues")
        col_clues = metadata.get("col_clues")
        events = payload["events"]
        gif_path = args.gif_path or default_gif_path(log_path, args.output_dir)

        animate_log(
            events=events,
            row_clues=row_clues,
            col_clues=col_clues,
            interval=args.interval,
            save_path=gif_path,
        )
        print(f"Saved animation to {gif_path}")

    if args.show:
        plt.show()
