"""Small auto-graded coding test for local Ollama models.

Each task asks for one Python function; the reply's code is run in a separate
process together with hidden asserts. Pass = all asserts succeed.

Usage: python3 -I bench/coding_test.py [model ...]
  NUM_CTX=32768  context length (default 8192)
  THINK=01       thinking off (0) and/or on (1), default both
Uses each model's default temperature: temperature 0 made gemma4:12b loop while thinking.
"""
import json, os, re, subprocess, sys, tempfile, time, urllib.request

URL = "http://127.0.0.1:11434/api/chat"
MODELS = sys.argv[1:] or ["gemma4:12b", "ornith-1.5:9b"]

TASKS = {
    "roman_to_int": (
        "Write a Python function roman_to_int(s: str) -> int that converts a Roman numeral to an integer.",
        """
assert roman_to_int("III") == 3
assert roman_to_int("LVIII") == 58
assert roman_to_int("MCMXCIV") == 1994
assert roman_to_int("XLIX") == 49
""",
    ),
    "merge_intervals": (
        "Write a Python function merge_intervals(intervals: list[list[int]]) -> list[list[int]] that merges "
        "overlapping (or touching) intervals and returns them sorted by start. The input may be unsorted.",
        """
assert merge_intervals([[1,3],[2,6],[8,10],[15,18]]) == [[1,6],[8,10],[15,18]]
assert merge_intervals([[1,4],[4,5]]) == [[1,5]]
assert merge_intervals([[5,7],[1,2]]) == [[1,2],[5,7]]
assert merge_intervals([]) == []
assert merge_intervals([[1,10],[2,3],[4,5]]) == [[1,10]]
""",
    ),
    "parse_duration": (
        "Write a Python function parse_duration(s: str) -> int that converts strings like '1h30m', '45s', "
        "'2h5s' or '1h30m15s' into a total number of seconds. Units are h, m, s; each appears at most once, "
        "in that order. Raise ValueError for an empty or invalid string such as '' or '10x' or 'h'.",
        """
assert parse_duration("1h30m") == 5400
assert parse_duration("45s") == 45
assert parse_duration("2h5s") == 7205
assert parse_duration("1h30m15s") == 5415
for bad in ["", "10x", "h", "5m1h"]:
    try:
        parse_duration(bad)
    except ValueError:
        pass
    else:
        raise AssertionError("no ValueError for " + repr(bad))
""",
    ),
    "fix_binary_search": (
        "This function should return the index of target in the sorted list xs, or -1 if it is missing, "
        "but it has bugs. Return the corrected function, keeping the name.\n\n"
        "def binary_search(xs, target):\n"
        "    lo, hi = 0, len(xs)\n"
        "    while lo < hi:\n"
        "        mid = (lo + hi) // 2\n"
        "        if xs[mid] == target:\n"
        "            return mid\n"
        "        elif xs[mid] < target:\n"
        "            lo = mid\n"
        "        else:\n"
        "            hi = mid - 1\n"
        "    return -1\n",
        """
xs = [1, 3, 5, 7, 9, 11]
for i, x in enumerate(xs):
    assert binary_search(xs, x) == i, x
for missing in [0, 2, 4, 12]:
    assert binary_search(xs, missing) == -1, missing
assert binary_search([], 3) == -1
assert binary_search([4], 4) == 0
""",
    ),
    "top_words": (
        "Write a Python function top_words(text: str, k: int) -> list[tuple[str, int]] that returns the k most "
        "common words with their counts. Words are lowercase sequences of letters a-z (case-insensitive; "
        "everything else separates words). Sort by count descending, ties alphabetically.",
        """
t = "The cat and the hat. THE end, and... cat!"
assert top_words(t, 3) == [("the", 3), ("and", 2), ("cat", 2)]
assert top_words(t, 1) == [("the", 3)]
assert top_words("b a c a b", 5) == [("a", 2), ("b", 2), ("c", 1)]
assert top_words("", 2) == []
""",
    ),
}

SUFFIX = "\nReply with only the Python code in one ```python code block, no explanation and no example usage."


def ask(model, prompt, think):
    body = json.dumps({
        "model": model, "stream": False, "think": think,
        "messages": [{"role": "user", "content": prompt + SUFFIX}],
        "options": {"num_ctx": int(os.environ.get("NUM_CTX", 8192))},
    }).encode()
    t = time.time()
    with urllib.request.urlopen(urllib.request.Request(URL, body), timeout=600) as r:
        d = json.load(r)
    return d["message"]["content"], time.time() - t, d.get("eval_count", 0)


def extract(reply):
    blocks = re.findall(r"```(?:python|py)?\s*\n(.*?)```", reply, re.S)
    return max(blocks, key=len) if blocks else reply


def grade(code, tests):
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(code + "\n\n" + tests)
    try:
        p = subprocess.run([sys.executable, "-I", f.name], capture_output=True, text=True, timeout=10)
    except subprocess.TimeoutExpired:
        return False, "timeout"
    err = (p.stderr.strip().splitlines() or [""])[-1]
    return p.returncode == 0, err[:90]


results = []
for model in MODELS:
    for think in [{"0": False, "1": True}[x] for x in os.environ.get("THINK", "01")]:
        for name, (prompt, tests) in TASKS.items():
            reply, secs, toks = ask(model, prompt, think)
            ok, err = grade(extract(reply), tests)
            results.append((model, think, name, ok, secs, toks, err))
            print(f"{model:15} think={str(think):5} {name:18} {'PASS' if ok else 'FAIL'} "
                  f"{secs:5.1f}s {toks:5d} tok  {err}", flush=True)

print("\nSummary")
for model in MODELS:
    for think in [{"0": False, "1": True}[x] for x in os.environ.get("THINK", "01")]:
        rs = [r for r in results if r[0] == model and r[1] == think]
        print(f"{model:15} think={str(think):5} {sum(r[3] for r in rs)}/{len(rs)} passed, "
              f"{sum(r[4] for r in rs):6.1f}s total")
