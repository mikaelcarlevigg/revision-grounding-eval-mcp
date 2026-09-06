import json
import sys
from pathlib import Path

DATA_DIR = Path("data")


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def load_corpus(revision_date):
    """Load vectors + section text + revision status for one revision date."""
    vectors = load_json(DATA_DIR / f"vectors-{revision_date}.json")
    sections = {s["identifier"]: s for s in load_json(DATA_DIR / f"sections-{revision_date}.json")}
    status = load_json(DATA_DIR / "revision-status.json")
    return vectors, sections, status


def top_k(query_vector, vectors, k=5):
    scored = []
    for item in vectors:
        score = dot(query_vector, item["vector"])
        scored.append((score, item))

    scored.sort(reverse=True)
    return scored[:k]

def search(query_text, revision_date="2021-04-21", k=5):
    from embed import embed_text, normalize

    prefixed_query = "search_query: " + query_text
    query_vector = normalize(embed_text(prefixed_query))

    vectors, sections, status = load_corpus(revision_date)
    best_matches = top_k(query_vector, vectors, k)

    results = []
    for score, item in best_matches:
        sec_id = item["identifier"]

        heading = ""
        if sec_id in sections:
            heading = sections[sec_id]["heading"]

        rev_status = "unknown"
        if sec_id in status:
            rev_status = status[sec_id]["status"]

        result = {
            "identifier": sec_id,
            "heading": heading,
            "score": score,
            "revision_status": rev_status,
            "revision_gate_flag": rev_status == "changed",
        }
        results.append(result)

    return results


def print_results(results):
    for r in results:
        line = r["identifier"] + "  " + str(r["score"]) + "  " + r["heading"]
        if r["revision_gate_flag"]:
            line = line + "   VARNING: paragrafen har ändrats mellan versionerna"
        print(line)

def compare_revisions(query_text, k=5):
    print("=== 2017-01-01 ===")
    results_2017 = search(query_text, "2017-01-01", k)
    print_results(results_2017)

    print()
    print("=== 2021-04-21 ===")
    results_2021 = search(query_text, "2021-04-21", k)
    print_results(results_2021)


if __name__ == "__main__":
    query = "can I fly my drone at night"

    if len(sys.argv) > 1:
        query = sys.argv[1]

    compare_revisions(query)