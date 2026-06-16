#!/usr/bin/env python3
"""Build local HTML preview pages for tactile replay outputs."""

from __future__ import annotations

import argparse
import html
import json
import subprocess
from pathlib import Path

import h5py
import numpy as np


STYLE = """
body { margin: 0; font-family: Arial, sans-serif; background: #f6f7f9; color: #17191c; }
main { max-width: 1180px; margin: 0 auto; padding: 24px; }
h1 { margin: 0 0 8px; font-size: 28px; }
.meta { margin: 0 0 20px; color: #4d5663; line-height: 1.5; }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 18px; }
section, .item { background: #fff; border: 1px solid #d9dee7; border-radius: 8px; padding: 14px; }
h2 { margin: 0 0 10px; font-size: 17px; }
video { width: 100%; background: #111; border-radius: 6px; }
.wide { grid-column: 1 / -1; }
code { background: #eceff4; padding: 2px 5px; border-radius: 4px; }
a { color: #0d5bd7; text-decoration: none; }
a:hover { text-decoration: underline; }
.badge { display: inline-block; margin-right: 8px; padding: 2px 7px; border-radius: 999px; font-size: 12px; background: #e9f6ef; color: #17643a; }
.badge.fail { background: #fff0ef; color: #a33128; }
""".strip()


KNOWN_RUNS = {
    "object_pickup": ("Object: alphabet soup into basket", "libero_object task0 demo0"),
    "drawer_open": ("Goal: open middle drawer", "libero_goal task0 demo0"),
    "milk_pickup": ("Object: milk into basket", "libero_object task7 demo0"),
    "stove_knob_turn_on": ("Goal: turn on stove knob", "libero_goal task7 demo0"),
    "book_to_caddy": ("LIBERO-10: book to caddy", "libero_10 task5 demo0"),
    "spatial_bowl_on_stove": ("Spatial: bowl on stove to plate", "libero_spatial task7 demo0"),
    "spatial_bowl_center": ("Spatial: bowl center to plate", "libero_spatial task2 demo0"),
    "bowl_on_stove_goal": ("Goal: bowl on stove", "libero_goal task1 demo0"),
}


def rel(target: Path, base: Path) -> str:
    return target.relative_to(base).as_posix()


def first(run_dir: Path, pattern: str) -> Path | None:
    items = sorted(run_dir.glob(pattern))
    return items[0] if items else None


def read_metrics(h5_path: Path) -> dict[str, float | int | tuple[int, ...]]:
    with h5py.File(h5_path, "r") as handle:
        demo = sorted(handle["data"].keys())[0]
        data = handle["data"][demo]
        actions_shape = tuple(data["actions"].shape)
        force = data["obs/gripper_net_force"][:]
        marker = data["obs/gripper_marker_motion"][:]

    force_norm = np.linalg.norm(force[:, 0], axis=-1).max(axis=1)
    marker_disp = np.linalg.norm(marker[:, :, 1] - marker[:, :, 0], axis=-1).mean(axis=(1, 2))
    frames = int(actions_shape[0])
    return {
        "actions_shape": actions_shape,
        "frames": frames,
        "duration": frames / 20.0,
        "force_max": float(force_norm.max()),
        "force_mean": float(force_norm.mean()),
        "marker_max": float(marker_disp.max()),
        "marker_mean": float(marker_disp.mean()),
    }


def build_combined_video(agent: Path, eye: Path, left: Path, right: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(agent),
            "-i",
            str(eye),
            "-i",
            str(left),
            "-i",
            str(right),
            "-filter_complex",
            (
                "[0:v]scale=480:360,setpts=PTS-STARTPTS[v0];"
                "[1:v]scale=480:360,setpts=PTS-STARTPTS[v1];"
                "[2:v]scale=480:360,setpts=PTS-STARTPTS[v2];"
                "[3:v]scale=480:360,setpts=PTS-STARTPTS[v3];"
                "[v0][v1]hstack=inputs=2[top];"
                "[v2][v3]hstack=inputs=2[bottom];"
                "[top][bottom]vstack=inputs=2[out]"
            ),
            "-map",
            "[out]",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-shortest",
            str(output),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def write_run_page(
    run_dir: Path,
    title: str,
    task: str,
    metrics: dict[str, float | int | tuple[int, ...]],
    agent: Path,
    eye: Path,
    left: Path,
    right: Path,
) -> None:
    viewer = run_dir / "viewer"
    viewer.mkdir(parents=True, exist_ok=True)
    page = f"""<!doctype html>
<html lang="zh-CN">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{html.escape(title)}</title><style>{STYLE}</style></head>
<body><main>
<h1>{html.escape(title)}</h1>
<p class="meta">任务：<code>{html.escape(task)}</code>。输出：{metrics["frames"]} 帧，20 fps，约 {metrics["duration"]:.2f} 秒。动作：<code>{metrics["actions_shape"]}</code>。力最大值：<code>{metrics["force_max"]:.3f}</code>，marker 平均位移最大值：<code>{metrics["marker_max"]:.3f}</code>。</p>
<div class="grid">
<section class="wide"><h2>2x2 合成视图：RGB Cameras + GelSight Markers</h2><video controls loop muted src="tactile_preview_2x2.mp4"></video></section>
<section><h2>Agent View RGB</h2><video controls loop muted src="../{html.escape(rel(agent, run_dir))}"></video></section>
<section><h2>Eye-in-Hand RGB</h2><video controls loop muted src="../{html.escape(rel(eye, run_dir))}"></video></section>
<section><h2>Left GelSight Markers RGB</h2><video controls loop muted src="../{html.escape(rel(left, run_dir))}"></video></section>
<section><h2>Right GelSight Markers RGB</h2><video controls loop muted src="../{html.escape(rel(right, run_dir))}"></video></section>
</div>
</main></body></html>
"""
    (viewer / "index.html").write_text(page, encoding="utf-8")


def write_index(preview_root: Path, results: list[dict]) -> None:
    cards = []
    for item in results:
        title = html.escape(str(item["title"]))
        task = html.escape(str(item["task"]))
        run = html.escape(str(item["run"]))
        if item["complete"]:
            metrics = item["metrics"]
            cards.append(
                f"""<div class="item"><span class="badge">OK</span><a href="tactile/{run}/viewer/index.html"><strong>{title}</strong></a><p class="meta"><code>{task}</code><br>{metrics["frames"]} frames, force_max={metrics["force_max"]:.2f}, marker_max={metrics["marker_max"]:.2f}</p></div>"""
            )
        else:
            cards.append(
                f"""<div class="item"><span class="badge fail">FAILED</span><strong>{title}</strong><p class="meta"><code>{task}</code><br>replay failed or incomplete output</p></div>"""
            )

    page = f"""<!doctype html>
<html lang="zh-CN">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Tabero Tactile Preview Index</title><style>{STYLE}</style></head>
<body><main><h1>Tabero Tactile Preview Index</h1><p class="meta">这里汇总当前本地生成的触觉 replay 预览。成功样例使用 <code>markers_rgb</code>，方便观察 marker 位移和接触区域。</p><div class="grid">{''.join(cards)}</div></main></body></html>
"""
    (preview_root / "index.html").write_text(page, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview-root", default="local_datasets/previews")
    args = parser.parse_args()

    preview_root = Path(args.preview_root)
    tactile_root = preview_root / "tactile"
    results = []

    for run_dir in sorted(path for path in tactile_root.iterdir() if path.is_dir()):
        run = run_dir.name
        title, task = KNOWN_RUNS.get(run, (run.replace("_", " ").title(), run))
        h5s = sorted((run_dir / "replayed_demos").glob("*.hdf5"))
        agent = first(run_dir, "video_datasets/*/videos/demo_0_agentview_rgb.mp4")
        eye = first(run_dir, "video_datasets/*/videos/demo_0_eye_in_hand_rgb.mp4")
        left = first(run_dir, "video_datasets/*/tactile_outputs/demo_0_gsmini_left_markers_rgb.mp4")
        right = first(run_dir, "video_datasets/*/tactile_outputs/demo_0_gsmini_right_markers_rgb.mp4")
        complete = bool(h5s and agent and eye and left and right)
        item = {"run": run, "title": title, "task": task, "complete": complete}

        if complete:
            metrics = read_metrics(h5s[0])
            build_combined_video(agent, eye, left, right, run_dir / "viewer/tactile_preview_2x2.mp4")
            write_run_page(run_dir, title, task, metrics, agent, eye, left, right)
            item["metrics"] = metrics

        results.append(item)

    write_index(preview_root, results)
    print(json.dumps({"success": [r["run"] for r in results if r["complete"]], "failed": [r["run"] for r in results if not r["complete"]]}, indent=2))


if __name__ == "__main__":
    main()
