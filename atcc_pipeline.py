"""
ATCC Processing Pipeline
- Split a full-day video into fixed-duration clips (15 or 30 minutes)
- Run YOLO detection + tracking sequentially on clips
- Count vehicles by category per interval
- Save consolidated CSV/XLSX with an additional Pedestrian column at the end
- Compute morning/evening peak hour and save a summary CSV

Usage (CLI):
    python atcc_pipeline.py \
        --video /path/to/full_day.mp4 \
        --outdir /path/to/output \
        --interval-mins 15 \
        --model yolov8n.pt \
        --base-start 00:00 \
        --line 0,0.6;1,0.6

Notes:
- "--line" defines a virtual counting line using normalized coordinates
  "x,y;x,y" in image space, each between 0..1. Default is a horizontal
  line across the middle (0,0.5;1,0.5).
- Morning/Evening periods are configurable; defaults: morning 06–12, evening 16–21
- Class/category mapping can be customized by providing a JSON file via --class-map
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import pandas as pd

# Optional heavy imports are inside functions to allow fast help/--version


# ------------------------- Utility: File and time helpers -------------------------

def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def hhmm(minutes_from_midnight: int) -> str:
    hours = minutes_from_midnight // 60
    minutes = minutes_from_midnight % 60
    return f"{hours:02d}:{minutes:02d}"


# ------------------------- Video splitting (FFmpeg) -------------------------

def split_video_ffmpeg(
    input_video: Path, output_dir: Path, segment_seconds: int
) -> List[Path]:
    """Split video into fixed-duration segments using ffmpeg-python.

    Returns list of generated clip paths in chronological order.
    """
    ensure_dir(output_dir)

    try:
        import ffmpeg  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "ffmpeg-python not installed. Please install requirements first."
        ) from exc

    # Output naming
    output_pattern = str(output_dir / "clip_%03d.mp4")

    # Build and run ffmpeg command
    (
        ffmpeg
        .input(str(input_video))
        .output(
            output_pattern,
            c="copy",
            map="0",
            f="segment",
            segment_time=segment_seconds,
        )
        .overwrite_output()
        .run(quiet=True)
    )

    # Collect created files
    clips = sorted(output_dir.glob("clip_*.mp4"))
    if not clips:
        raise RuntimeError("FFmpeg did not produce any clips. Check input video path.")
    return clips


# ------------------------- Geometry helpers for line crossing -------------------------

@dataclass
class Line:
    # Endpoints in absolute pixel coordinates
    p1: Tuple[float, float]
    p2: Tuple[float, float]

    def side(self, point: Tuple[float, float]) -> float:
        """Signed side of point relative to directed line p1->p2 using cross product.
        >0: left, <0: right, 0: on the line.
        """
        (x1, y1), (x2, y2) = self.p1, self.p2
        px, py = point
        return (x2 - x1) * (py - y1) - (y2 - y1) * (px - x1)


# ------------------------- YOLO-based counting per video -------------------------

@dataclass
class CountingConfig:
    class_map_overrides: Optional[Dict[str, str]] = None  # model class name -> our category
    categories_order: Tuple[str, ...] = (
        "2W", "3W", "Car", "LCV", "Bus", "Truck"
    )
    include_others: bool = True
    pedestrian_label: str = "Pedestrian"


DEFAULT_CLASS_TO_CATEGORY: Dict[str, str] = {
    # COCO defaults; extend/override via --class-map for custom Indian classes
    "person": "Pedestrian",
    "bicycle": "2W",
    "motorbike": "2W",
    "motorcycle": "2W",
    "car": "Car",
    "bus": "Bus",
    "truck": "Truck",
    # Common India-specific labels if using custom models
    "auto": "3W",
    "autorickshaw": "3W",
    "rickshaw": "3W",
    "three-wheeler": "3W",
    "mini-truck": "LCV",
    "pickup": "LCV",
    "van": "LCV",
}


def load_yolo(model_path: str):
    from ultralytics import YOLO  # Lazy import

    return YOLO(model_path)


def parse_normalized_line(line_str: str, frame_w: int, frame_h: int) -> Line:
    """Parse normalized 'x,y;x,y' into absolute pixel coordinates."""
    try:
        p1_str, p2_str = line_str.split(";")
        x1s, y1s = p1_str.split(",")
        x2s, y2s = p2_str.split(",")
        x1 = float(x1s) * frame_w
        y1 = float(y1s) * frame_h
        x2 = float(x2s) * frame_w
        y2 = float(y2s) * frame_h
        return Line((x1, y1), (x2, y2))
    except Exception as exc:
        raise ValueError(
            "Invalid --line format. Expected 'x1,y1;x2,y2' with 0..1 values"
        ) from exc


def category_for_class(
    class_name: str,
    names_map: Dict[str, str],
    cfg: CountingConfig,
) -> Tuple[str, bool]:
    """Map model class name to category.

    Returns (category, is_pedestrian_boolean)
    """
    lower = class_name.lower()
    # Overrides first
    if cfg.class_map_overrides and lower in cfg.class_map_overrides:
        mapped = cfg.class_map_overrides[lower]
        return mapped, mapped == cfg.pedestrian_label

    # Defaults
    mapped = names_map.get(lower) or DEFAULT_CLASS_TO_CATEGORY.get(lower)
    if mapped:
        return mapped, mapped == cfg.pedestrian_label

    # Fallbacks
    if lower in {"person", "pedestrian"}:
        return cfg.pedestrian_label, True

    return ("Others" if cfg.include_others else "Unknown"), False


def count_vehicles_in_video(
    video_path: Path,
    model_path: str,
    line_norm: str,
    cfg: CountingConfig,
) -> Dict[str, int]:
    """Run YOLO + ByteTrack and count unique IDs crossing the line.

    Returns counts dict per category; includes 'Pedestrian' and 'Others' if enabled.
    """
    import cv2  # Lazy import

    model = load_yolo(model_path)

    # Create a tiny video capture to know width/height
    cap_meta = cv2.VideoCapture(str(video_path))
    if not cap_meta.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")
    frame_w = int(cap_meta.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_h = int(cap_meta.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap_meta.release()

    counting_line = parse_normalized_line(line_norm, frame_w, frame_h)

    # Prepare counters
    counts: Dict[str, int] = {cat: 0 for cat in cfg.categories_order}
    if cfg.include_others:
        counts["Others"] = 0
    counts[cfg.pedestrian_label] = 0

    # Track state per object ID
    last_side: Dict[int, float] = {}
    counted_ids: set[int] = set()

    names_lookup: Dict[str, str] = {}
    # Build lookup from model names to categories using defaults
    for _, name in model.names.items():
        mapped, is_ped = category_for_class(name, {}, cfg)
        names_lookup[name.lower()] = mapped

    # Run tracker streaming to avoid loading full video into memory
    # persist=True keeps IDs between frames; tracker='bytetrack' by default
    results = model.track(
        source=str(video_path),
        stream=True,
        verbose=False,
        persist=True,
    )

    for r in results:
        if r.boxes is None or r.boxes.id is None:
            continue

        ids = r.boxes.id.int().cpu().tolist()
        cls_ids = r.boxes.cls.int().cpu().tolist()
        xyxy = r.boxes.xyxy.cpu().tolist()

        for obj_id, cls_id, box in zip(ids, cls_ids, xyxy):
            # Skip already counted IDs
            if obj_id in counted_ids:
                continue

            x1, y1, x2, y2 = box
            cx = (x1 + x2) / 2.0
            cy = (y1 + y2) / 2.0

            side_now = counting_line.side((cx, cy))
            prev = last_side.get(obj_id)
            last_side[obj_id] = side_now

            if prev is None:
                continue

            # Detect crossing when sign changes and magnitude is meaningful
            if side_now == 0:
                continue
            if prev == 0:
                continue
            if (side_now > 0) == (prev > 0):
                continue

            # Crossing detected
            class_name = model.names[int(cls_id)]
            category, is_ped = category_for_class(class_name, names_lookup, cfg)
            # Count only once per ID per clip
            if category not in counts:
                counts[category] = 0
            counts[category] += 1
            counted_ids.add(obj_id)

    return counts


# ------------------------- Orchestration for a full-day video -------------------------

@dataclass
class PeakHour:
    label: str  # e.g., "Morning" or "Evening"
    interval: str  # e.g., "08:00-09:00"
    total: int


def process_full_day(
    input_video: Path,
    output_dir: Path,
    interval_minutes: int,
    model_path: str,
    base_start_hhmm: str,
    line_norm: str,
    class_map_json: Optional[Path],
    morning_range: Tuple[int, int] = (6, 12),  # inclusive start, exclusive end hours
    evening_range: Tuple[int, int] = (16, 21),
) -> Tuple[pd.DataFrame, Dict[str, PeakHour]]:
    ensure_dir(output_dir)

    # Load class overrides if provided
    class_overrides: Optional[Dict[str, str]] = None
    if class_map_json and class_map_json.exists():
        with open(class_map_json, "r", encoding="utf-8") as f:
            class_overrides = json.load(f)

    cfg = CountingConfig(class_map_overrides=class_overrides)

    # Split
    clips_dir = output_dir / "clips"
    segment_seconds = interval_minutes * 60
    clips = split_video_ffmpeg(input_video, clips_dir, segment_seconds)

    # Determine base start time
    try:
        base_dt = datetime.strptime(base_start_hhmm, "%H:%M")
    except ValueError:
        base_dt = datetime.strptime("00:00", "%H:%M")

    # Process sequentially
    records: List[Dict[str, int | str]] = []

    for i, clip_path in enumerate(sorted(clips)):
        start_minutes = i * interval_minutes
        end_minutes = start_minutes + interval_minutes
        interval_str = f"{hhmm(start_minutes)}-{hhmm(end_minutes)}"

        counts = count_vehicles_in_video(
            clip_path, model_path=model_path, line_norm=line_norm, cfg=cfg
        )

        # Normalize to our output schema
        row: Dict[str, int | str] = {"Interval": interval_str}
        for col in cfg.categories_order:
            row[col] = int(counts.get(col, 0))
        # Others (optional)
        if cfg.include_others:
            row["Others"] = int(counts.get("Others", 0))

        # Total excludes pedestrians by convention
        total_no_ped = sum(int(row.get(col, 0)) for col in cfg.categories_order)
        if cfg.include_others:
            total_no_ped += int(row.get("Others", 0))
        row["Total"] = total_no_ped

        # Pedestrian last
        row[cfg.pedestrian_label] = int(counts.get(cfg.pedestrian_label, 0))

        records.append(row)

    df = pd.DataFrame(records)

    # Daily Totals row
    totals = {col: (int(df[col].sum()) if col != "Interval" else "Daily Total") for col in df.columns}
    # Keep Interval string as label
    totals["Interval"] = "Daily Total"
    df = pd.concat([df, pd.DataFrame([totals])], ignore_index=True)

    # Peak hour analysis using 60-min bins computed from interval rows
    def compute_hour_bins(data: pd.DataFrame) -> pd.Series:
        # Exclude the total row
        data = data[data["Interval"] != "Daily Total"].copy()
        # Parse hour start from Interval
        data["start_min"] = data["Interval"].str.slice(0, 5).str.split(":").apply(lambda x: int(x[0]) * 60 + int(x[1]))
        # Group each set of 60 minutes
        group_key = (data["start_min"] // 60)
        hourly_totals = data.groupby(group_key)["Total"].sum()
        hourly_totals.index.name = "hour"
        return hourly_totals

    hourly = compute_hour_bins(df)

    def peak_in_range(series: pd.Series, start_h: int, end_h: int, label: str) -> PeakHour:
        # Filter inclusive start, exclusive end
        window = series[(series.index >= start_h) & (series.index < end_h)]
        if window.empty:
            return PeakHour(label=label, interval="N/A", total=0)
        hour = int(window.idxmax())
        return PeakHour(label=label, interval=f"{hour:02d}:00-{(hour+1)%24:02d}:00", total=int(window.loc[hour]))

    morning_peak = peak_in_range(hourly, morning_range[0], morning_range[1], "Morning")
    evening_peak = peak_in_range(hourly, evening_range[0], evening_range[1], "Evening")

    peaks = {
        "morning": morning_peak,
        "evening": evening_peak,
    }

    # Save outputs
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = output_dir / f"Traffic_Count_Report_{timestamp}.csv"
    xlsx_path = output_dir / f"Traffic_Count_Report_{timestamp}.xlsx"
    summary_path = output_dir / f"Traffic_Peak_Summary_{timestamp}.csv"

    # Ensure column order for export
    export_cols = [
        "Interval",
        *list(cfg.categories_order),
        *( ["Others"] if cfg.include_others else [] ),
        "Total",
        cfg.pedestrian_label,
    ]
    df[export_cols].to_csv(csv_path, index=False)
    try:
        df[export_cols].to_excel(xlsx_path, index=False)
    except Exception:
        # openpyxl may be missing at runtime; CSV is always written
        pass

    # Save summary CSV
    peak_rows = [
        {"Period": peaks[k].label, "Peak Interval": peaks[k].interval, "Total Vehicles": peaks[k].total}
        for k in ["morning", "evening"]
    ]
    pd.DataFrame(peak_rows).to_csv(summary_path, index=False)

    print(f"Saved interval table: {csv_path}")
    print(f"Saved peak summary:   {summary_path}")

    return df[export_cols], peaks


# ------------------------- CLI -------------------------

def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="ATCC full-day processing pipeline")
    p.add_argument("--video", required=True, help="Path to full-day video file")
    p.add_argument("--outdir", default="./atcc_output", help="Output directory")
    p.add_argument("--interval-mins", type=int, default=15, choices=[15, 30], help="Clip interval in minutes")
    p.add_argument("--model", default="yolov8n.pt", help="YOLO model path")
    p.add_argument("--base-start", default="00:00", help="Base start time HH:MM for labeling intervals")
    p.add_argument("--line", default="0,0.5;1,0.5", help="Normalized counting line x,y;x,y (0..1)")
    p.add_argument("--class-map", default=None, help="Optional JSON file mapping model class -> category")
    p.add_argument("--morning", default="6-12", help="Morning hours window start-end, e.g., 6-12")
    p.add_argument("--evening", default="16-21", help="Evening hours window start-end, e.g., 16-21")
    return p.parse_args(argv)


def parse_range(s: str) -> Tuple[int, int]:
    try:
        a, b = s.split("-")
        return int(a), int(b)
    except Exception as exc:
        raise ValueError("Hour range must be 'start-end', e.g., 6-12") from exc


def main(argv: Optional[Iterable[str]] = None) -> None:
    args = parse_args(argv)
    input_video = Path(args.video)
    output_dir = Path(args.outdir)
    class_map = Path(args.class_map) if args.class_map else None

    morning = parse_range(args.morning)
    evening = parse_range(args.evening)

    df, peaks = process_full_day(
        input_video=input_video,
        output_dir=output_dir,
        interval_minutes=args.interval_mins,
        model_path=args.model,
        base_start_hhmm=args.base_start,
        line_norm=args.line,
        class_map_json=class_map,
        morning_range=morning,
        evening_range=evening,
    )

    # Print concise summary to console
    print("\nPeak hour results:")
    for label, peak in peaks.items():
        print(f"  {peak.label}: {peak.interval} -> {peak.total} vehicles")


if __name__ == "__main__":
    main()
