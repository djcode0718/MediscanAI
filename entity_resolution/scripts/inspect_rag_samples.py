#!/usr/bin/env python3

import json
from pathlib import Path


BASE = Path(__file__).resolve().parents[1]

ROOT = (
    BASE
    / "results"
    / "final_v2"
    / "profile"
    / "sample_records"
)

OUTPUT = (
    BASE
    / "results"
    / "final_v2"
    / "profile"
    / "sample_inspection.json"
)

SOURCES = [
    "fda",
    "dailymed",
    "clinical_trials",
]


def shorten(value, n=500):

    value = str(value)

    if len(value) <= n:
        return value

    return value[:n] + "\n... [TRUNCATED FOR DISPLAY]"


def inspect_sample(item):

    record = item.get("record", {})

    result = {
        "file": Path(
            item.get("file", "")
        ).name,

        "line": item.get("line"),

        "document_id": item.get(
            "document_id"
        ),

        "text_chars": item.get(
            "text_chars"
        ),

        "chars_lost_by_8k_cutoff": item.get(
            "chars_lost_by_8k_cutoff"
        ),

        "top_level_keys": sorted(
            record.keys()
        ),

        "headings": item.get(
            "headings",
            []
        ),

        "metadata": {},

        "text_preview": "",
    }

    # Preserve all metadata, but shorten only for inspection.
    for key, value in record.items():

        if key in (
            "text",
            "content",
            "body",
            "description",
        ):
            continue

        if isinstance(value, (dict, list)):

            try:
                preview = json.dumps(
                    value,
                    ensure_ascii=False,
                    default=str,
                )
            except Exception:
                preview = str(value)

        else:
            preview = str(value)

        result["metadata"][key] = shorten(
            preview,
            350,
        )

    text = (
        record.get("text")
        or record.get("content")
        or record.get("body")
        or record.get("description")
        or ""
    )

    result["text_preview"] = shorten(
        text,
        1200,
    )

    return result


def inspect_source(source):

    normal_path = (
        ROOT
        / source
        / "normal_samples.json"
    )

    long_path = (
        ROOT
        / source
        / "long_samples.json"
    )

    result = {
        "normal_samples": [],
        "long_samples": [],
    }

    # Normal samples
    if normal_path.exists():

        with open(
            normal_path,
            "r",
            encoding="utf-8",
        ) as f:

            samples = json.load(f)

        result["normal_samples"] = [
            inspect_sample(item)
            for item in samples[:5]
        ]

    # Long samples
    if long_path.exists():

        with open(
            long_path,
            "r",
            encoding="utf-8",
        ) as f:

            samples = json.load(f)

        result["long_samples"] = [
            inspect_sample(item)
            for item in samples[:5]
        ]

    return result


def main():

    print("Inspecting RAG samples...")
    print(f"Output: {OUTPUT}")

    inspection = {
        "description": (
            "Inspection of normal and long RAG samples "
            "for source-aware V2 chunking design."
        ),

        "root": str(ROOT),

        "sources": {},
    }

    for source in SOURCES:

        print(f"  Inspecting {source}...")

        inspection["sources"][source] = (
            inspect_source(source)
        )

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        OUTPUT,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            inspection,
            f,
            ensure_ascii=False,
            indent=2,
        )

    print()
    print("Inspection complete.")
    print()
    print(f"JSON saved to:")
    print(OUTPUT)
    print()
    print("Upload this JSON file here.")


if __name__ == "__main__":
    main()