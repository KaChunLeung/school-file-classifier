"""LLM-based file sub-classification using Groq API."""

import requests

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.1-8b-instant"

VALID_CATEGORIES = {"Lectures", "Tutorials", "Assignments", "Other"}

SYSTEM_PROMPT = """\
You are a file classifier for university course materials.
Given a filename, classify it into exactly ONE of these categories:

- Lectures  (lecture slides, lecture notes, class presentations)
- Tutorials (tutorial sheets, tutorial solutions, practice questions, quizzes, problem sets)
- Assignments (coursework, group assignments, homework, individual assignments, exams, mock exams)
- Other (case studies, datasets, code examples, admin documents, supplementary materials, anything else)

Respond with ONLY the category name. No explanation, no punctuation.\
"""


def _normalise(text: str) -> str:
    """Normalise an LLM response to one of the valid categories."""
    cleaned = text.strip().rstrip(".").strip()
    if cleaned in VALID_CATEGORIES:
        return cleaned
    lower = cleaned.lower()
    for cat in VALID_CATEGORIES:
        if lower == cat.lower() or lower == cat.lower().rstrip("s"):
            return cat
    return "Other"


def classify_batch(filenames: list[str], api_key: str) -> list[str]:
    """Classify multiple filenames in a single API call.

    Returns list of categories in the same order as input.
    """
    if not api_key or not filenames:
        return ["Other"] * len(filenames)

    numbered = "\n".join(f"{i+1}. {fn}" for i, fn in enumerate(filenames))
    user_prompt = (
        f"Classify each file. Respond with ONLY a numbered list, one per line.\n"
        f"Example format:\n1. Lectures\n2. Tutorials\n3. Assignments\n\n"
        f"Files:\n{numbered}"
    )

    try:
        resp = requests.post(
            GROQ_API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0,
                "max_tokens": len(filenames) * 15,
            },
            timeout=30,
        )
        resp.raise_for_status()
        answer = resp.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        return ["Other"] * len(filenames)

    # Parse "1. Lectures\n2. Tutorials\n..." format
    results: list[str] = []
    for line in answer.splitlines():
        line = line.strip()
        if not line:
            continue
        # Strip leading number + punctuation: "1. ", "1) ", "1: " etc.
        for i, ch in enumerate(line):
            if not ch.isdigit():
                # Skip separator chars after the number
                rest = line[i:].lstrip(".):- ").strip()
                results.append(_normalise(rest))
                break
        else:
            # Line was all digits (shouldn't happen)
            results.append("Other")

    # Pad if LLM returned fewer lines than expected
    while len(results) < len(filenames):
        results.append("Other")

    return results[: len(filenames)]
