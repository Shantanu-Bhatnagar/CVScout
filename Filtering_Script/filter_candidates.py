import json
import re
import html


import sys
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--candidates", default="candidates.jsonl")
parser.add_argument("--out", default="candidates_cleaned__20.jsonl")
args = parser.parse_args()

INPUT_FILE = args.candidates
OUTPUT_FILE = args.out

# Regular expressions
TAG_RE = re.compile(r"<[^>]+>")                      # HTML tags
WHITESPACE_RE = re.compile(r"\s+")                   # Multiple spaces/newlines/tabs
ZERO_WIDTH_RE = re.compile(r"[\u200B-\u200D\uFEFF]") # Zero-width Unicode chars

def clean_text(text):
    """Clean text by removing HTML tags, entities and extra whitespace."""
    if not isinstance(text, str):
        return text

    # Remove zero-width Unicode characters
    text = ZERO_WIDTH_RE.sub("", text)

    # Remove HTML tags
    if "<" in text and ">" in text:
        text = TAG_RE.sub(" ", text)

    # Decode HTML entities (&nbsp;, &amp;, etc.)
    text = html.unescape(text)

    # Remove extra whitespace/newlines/tabs
    text = WHITESPACE_RE.sub(" ", text)

    # Remove leading/trailing spaces
    text = text.strip()

import sys
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--candidates", default="candidates.jsonl")
parser.add_argument("--out", default="candidates_cleaned__20.jsonl")
args = parser.parse_args()

INPUT_FILE = args.candidates
OUTPUT_FILE = args.out


TAG_RE = re.compile(r"<[^>]+>")                      # HTML tags
WHITESPACE_RE = re.compile(r"\s+")                   # Multiple spaces/newlines/tabs
ZERO_WIDTH_RE = re.compile(r"[\u200B-\u200D\uFEFF]") # Zero-width Unicode chars

def clean_text(text):
    """Clean text by removing HTML tags, entities and extra whitespace."""
    if not isinstance(text, str):
        return text

    # Remove zero-width Unicode characters
    text = ZERO_WIDTH_RE.sub("", text)

    # Remove HTML tags
    if "<" in text and ">" in text:
        text = TAG_RE.sub(" ", text)

    # Decode HTML entities (&nbsp;, &amp;, etc.)
    text = html.unescape(text)

    # Remove extra whitespace/newlines/tabs
    text = WHITESPACE_RE.sub(" ", text)

    # Remove leading/trailing spaces
    text = text.strip()

    return text


def clean_json(obj):
    """Recursively clean every string in a JSON object."""
    if isinstance(obj, dict):
        return {k: clean_json(v) for k, v in obj.items()}

    if isinstance(obj, list):
        return [clean_json(item) for item in obj]

    if isinstance(obj, str):
        return clean_text(obj)

    return obj


count = 0

import sys
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--candidates", default="candidates.jsonl")
parser.add_argument("--out", default="candidates_cleaned__20.jsonl")
args = parser.parse_args()

INPUT_FILE = args.candidates
OUTPUT_FILE = args.out


TAG_RE = re.compile(r"<[^>]+>")                      # HTML tags
WHITESPACE_RE = re.compile(r"\s+")                   # Multiple spaces/newlines/tabs
ZERO_WIDTH_RE = re.compile(r"[\u200B-\u200D\uFEFF]") # Zero-width Unicode chars

def clean_text(text):
    """Clean text by removing HTML tags, entities and extra whitespace."""
    if not isinstance(text, str):
        return text

    # Remove zero-width Unicode characters
    text = ZERO_WIDTH_RE.sub("", text)

    # Remove HTML tags
    if "<" in text and ">" in text:
        text = TAG_RE.sub(" ", text)

    # Decode HTML entities (&nbsp;, &amp;, etc.)
    text = html.unescape(text)

    # Remove extra whitespace/newlines/tabs
    text = WHITESPACE_RE.sub(" ", text)

    # Remove leading/trailing spaces
    text = text.strip()

    return text


def clean_json(obj):
    """Recursively clean every string in a JSON object."""
    if isinstance(obj, dict):
        return {k: clean_json(v) for k, v in obj.items()}

    if isinstance(obj, list):
        return [clean_json(item) for item in obj]

    if isinstance(obj, str):
        return clean_text(obj)

    return obj


count = 0

with open(INPUT_FILE, "r", encoding="utf-8", errors="ignore") as fin, \
     open(OUTPUT_FILE, "w", encoding="utf-8") as fout:

    for line in fin:
        line = line.strip()

        if not line:
            continue

        try:
            obj = json.loads(line)
            cleaned = clean_json(obj)

            json.dump(cleaned, fout, ensure_ascii=False)
            fout.write("\n")
            count += 1

        except json.JSONDecodeError:
            print(f"Skipping invalid JSON at line {count + 1}")

print(f"\n Done!")
print(f"Processed {count} records.")
print(f"Output saved as: {OUTPUT_FILE}")