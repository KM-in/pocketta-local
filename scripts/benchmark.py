#!/usr/bin/env python3
"""Run and validate one PocketTA lecture through the local HTTP API."""

from __future__ import annotations

import argparse
import json
import mimetypes
import platform
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import psutil


TERMINAL = {"completed", "failed"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Upload a local sample, record stage timings, and validate its study pack."
    )
    parser.add_argument("recording", type=Path)
    parser.add_argument("--api", default="http://127.0.0.1:8000/api")
    parser.add_argument("--poll-seconds", type=float, default=0.5)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--markdown-out", type=Path)
    parser.add_argument(
        "--delete-after",
        action="store_true",
        help="Delete the benchmark lecture from PocketTA after collecting the result.",
    )
    return parser.parse_args()


def validate_result(lecture: dict[str, Any]) -> dict[str, Any]:
    transcript = lecture.get("transcript") or {}
    pack = lecture.get("study_pack") or {}
    segments = transcript.get("segments") or []
    segment_ids = {segment["id"] for segment in segments}
    uncertain_ids = {segment["id"] for segment in segments if segment["uncertain"]}
    citations = {
        segment_id
        for collection in ("notes", "concepts", "flashcards", "quiz")
        for item in pack.get(collection, [])
        for segment_id in item.get("segment_ids", [])
    }
    invalid = sorted(citations - segment_ids)
    uncertain_citations = sorted(citations & uncertain_ids)
    counts = {
        "segments": len(segments),
        "uncertain_segments": len(uncertain_ids),
        "notes": len(pack.get("notes", [])),
        "concepts": len(pack.get("concepts", [])),
        "flashcards": len(pack.get("flashcards", [])),
        "quiz": len(pack.get("quiz", [])),
        "distinct_citations": len(citations),
    }
    checks = {
        "completed": lecture.get("status") == "completed",
        "all_evidence_resolves": not invalid,
        "no_uncertain_evidence": not uncertain_citations,
        "has_summary": bool(pack.get("overview")),
        "has_expected_demo_counts": (
            counts["concepts"] >= 3
            and counts["flashcards"] >= 5
            and counts["quiz"] >= 5
        ),
    }
    return {
        "counts": counts,
        "checks": checks,
        "invalid_citations": invalid,
        "uncertain_citations": uncertain_citations,
        "passed": all(checks.values()),
    }


def markdown_report(report: dict[str, Any]) -> str:
    result = report["validation"]
    lines = [
        "# PocketTA benchmark",
        "",
        f"- **Recording:** {report['recording']}",
        f"- **Lecture ID:** {report['lecture_id']}",
        f"- **Audio duration:** {report['audio_duration_seconds']:.1f}s",
        f"- **Total processing:** {report['total_seconds']:.1f}s",
        f"- **Machine:** {report['machine']}",
        f"- **Memory:** {report['memory_gb']:.1f} GB",
        f"- **Result:** {'PASS' if result['passed'] else 'FAIL'}",
        "",
        "## Approximate stage timings",
        "",
        "| Stage | Seconds |",
        "|---|---:|",
    ]
    lines.extend(
        f"| {stage} | {seconds:.1f} |"
        for stage, seconds in report["stage_seconds"].items()
    )
    lines.extend(["", "## Output", "", "| Item | Count |", "|---|---:|"])
    lines.extend(f"| {name} | {count} |" for name, count in result["counts"].items())
    lines.extend(["", "## Checks", ""])
    lines.extend(
        f"- [{'x' if passed else ' '}] {name.replace('_', ' ')}"
        for name, passed in result["checks"].items()
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    recording = args.recording.resolve()
    if not recording.is_file():
        raise SystemExit(f"Recording not found: {recording}")
    api = args.api.rstrip("/")
    transitions: list[dict[str, Any]] = []
    started = time.perf_counter()

    with httpx.Client(timeout=30, trust_env=False) as client:
        health = client.get(f"{api}/health")
        health.raise_for_status()
        health_payload = health.json()
        if not health_payload["ready"]:
            missing = ", ".join(
                name
                for name, component in health_payload["components"].items()
                if not component["ready"]
            )
            raise SystemExit(f"PocketTA is not ready: {missing}")

        mime = mimetypes.guess_type(recording.name)[0] or "application/octet-stream"
        with recording.open("rb") as source:
            response = client.post(
                f"{api}/lectures", files={"file": (recording.name, source, mime)}
            )
        response.raise_for_status()
        lecture_id = response.json()["id"]
        last_status: str | None = None

        while True:
            detail_response = client.get(f"{api}/lectures/{lecture_id}")
            detail_response.raise_for_status()
            lecture = detail_response.json()
            status = lecture["status"]
            if status != last_status:
                transitions.append(
                    {
                        "stage": status,
                        "elapsed_seconds": round(time.perf_counter() - started, 3),
                        "observed_at": datetime.now(UTC).isoformat(),
                    }
                )
                print(f"{transitions[-1]['elapsed_seconds']:8.1f}s  {status}", flush=True)
                last_status = status
            if status in TERMINAL:
                break
            time.sleep(args.poll_seconds)

        total_seconds = time.perf_counter() - started
        stage_seconds: dict[str, float] = {}
        for index, transition in enumerate(transitions):
            end = (
                transitions[index + 1]["elapsed_seconds"]
                if index + 1 < len(transitions)
                else total_seconds
            )
            stage_seconds[transition["stage"]] = round(
                end - transition["elapsed_seconds"], 3
            )
        validation = validate_result(lecture)
        duration_ms = (lecture.get("transcript") or {}).get("duration_ms", 0)
        report = {
            "recording": recording.name,
            "lecture_id": lecture_id,
            "recorded_at": datetime.now(UTC).isoformat(),
            "machine": f"{platform.system()} {platform.machine()} / {platform.processor() or 'unknown CPU'}",
            "memory_gb": round(psutil.virtual_memory().total / (1024**3), 2),
            "audio_duration_seconds": duration_ms / 1000,
            "total_seconds": round(total_seconds, 3),
            "real_time_factor": round(total_seconds / (duration_ms / 1000), 3)
            if duration_ms
            else None,
            "transitions": transitions,
            "stage_seconds": stage_seconds,
            "validation": validation,
            "error": lecture.get("error"),
        }
        json_text = json.dumps(report, indent=2) + "\n"
        markdown = markdown_report(report)
        if args.json_out:
            args.json_out.write_text(json_text, encoding="utf-8")
        if args.markdown_out:
            args.markdown_out.write_text(markdown, encoding="utf-8")
        print(markdown)

        if args.delete_after:
            delete_response = client.delete(f"{api}/lectures/{lecture_id}")
            delete_response.raise_for_status()

    return 0 if validation["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
