# revision-grounding-eval

Asked "may I fly a small drone at night?", a retrieval pipeline over 14 CFR Part 107
answers "no" and cites § 107.29 verbatim. The citation is real. The regulation changed
in 2021 and the answer is now yes, under conditions.

Retrieval quality is not the problem. Both passages are topically correct, and the
prohibition sentence is nearly identical in both revisions: the entire difference is
the word "unless". Nothing in the pipeline knows which revision is in force.

This is a small harness for measuring that, on public documents. Work in progress.

## What this tests, and why

The question this project asks: when you embed regulatory text and search it with
plain semantic similarity, what fails when the underlying rules have changed between
versions? Embeddings capture meaning, not validity over time, so a retrieval pipeline
can return a passage that is topically correct and still be wrong, outdated, or citing
the wrong regulation under a reused number.

Two point-in-time snapshots of the same regulation give a controlled way to observe
that: identical retrieval code, same query, same embedding model, only the date of the
underlying text changes. Whatever breaks, breaks because of the revision, not because
of a bad query or a weak embedding model.

## Where the data comes from

The eCFR API serves any CFR title as XML as it stood on a given date, back to
January 2017. Two snapshots of 14 CFR Part 107, small unmanned aircraft systems:

    curl --compressed \
      "https://www.ecfr.gov/api/versioner/v1/full/2017-01-01/title-14.xml?part=107" \
      -o data/raw/part107-2017-01-01.xml

    curl --compressed \
      "https://www.ecfr.gov/api/versioner/v1/full/2021-04-21/title-14.xml?part=107" \
      -o data/raw/part107-2021-04-21.xml

44 sections in the 2017 snapshot, 61 in the 2021 one. Of the 44 in common, 16 changed
and 17 sections were added, including the whole of Subpart D on operations over people.

The raw XML, the parsed sections and the embedded vectors are all committed, so this
is provenance rather than a build step: the pipeline runs offline with no API keys and
no model.

Two things worth knowing if you do re-fetch. The endpoint returns an error string
instead of XML unless the request permits compression, and point-in-time coverage
starts at 2017-01-01, so earlier amendment dates appear in the versions listing but
cannot be retrieved.

## How it works

Sections are chunked whole, since a section is what a person cites. Each one is
embedded with nomic-embed-text and normalised at index time, so a search is a plain
dot product rather than a cosine calculation. Every chunk carries the revision date it
came from, and each hit is checked against a per-section revision status derived by
comparing the two snapshots.

No frameworks. Cosine similarity is fifteen lines of plain Python, because the point of
this repo is what happens underneath, not which library was imported.

`search.py` embeds the query with the same `search_query:` prefix and normalisation
used for documents, ranks sections by dot product for a given revision date, and joins
each hit against the revision status so a result can be flagged `changed` at query
time. `compare_revisions()` runs the same query against both snapshots and prints the
two ranked lists side by side, so a citation's drift across revisions is visible by eye
rather than asserted.

## Running it

Nothing is needed to read the results. The parsed sections, the per-section revision
status and the embedded vectors are all in `data/`.

    python search.py "night flying rules"

To re-embed, for instance to try a different embedding model or add another snapshot,
you need Ollama running locally with `nomic-embed-text`:

    ollama pull nomic-embed-text
    python embed.py

`requests` is the only Python dependency.

## Findings

Manual query testing against both snapshots surfaced three distinct ways a revision
flag on its own is not enough, each pointing at a different gap:

**Section numbers get reused for unrelated content.** Querying "waiver for night
operations" returns § 107.53 in both years, flagged `changed`. In 2017 that number was
the applicability clause opening the certification subpart; in 2021 it's the ADS-B Out
prohibition, an unrelated rule added when Subpart D was inserted (the old content moved
to § 107.56). `diff.py` correctly detects the text differs, but "changed" understates
what happened: it isn't an edit, it's a different regulation under the same citation.
Citing "§ 107.53" without a revision date here doesn't give a stale answer. It gives a
wrong one.

**The changed section doesn't always make the cut.** Querying "do I need to retake the
knowledge test" does not surface the sections that actually changed, § 107.65 and
§ 107.73, in the top 3 results in either year. They rank 4th and 5th, behind three
unrelated but topically closer sections that didn't change at all. A revision gate
only protects a result set that the changed section is actually part of; nothing here
guarantees that.

**"Changed" is a section-level fact, not a clause-level one.** Querying "remote pilot
certificate age requirement" ranks § 107.61 top in both years, flagged `changed` in
both. The clause the query is actually about, the 16-year minimum, is worded
identically in both revisions. What changed in that section was the knowledge-test
clause. The flag is true and also not informative about what the person asked.

None of these are argued away by a better retriever. They follow from checking "did
this section's text change" instead of "did the thing the person asked about change",
and from top-k cutting a result set before revision status gets a say in what's in it.

## Status

- `parse.py`: eCFR XML to sections as JSON. Done.
- `diff.py`: per-section revision status, added, changed, unchanged or removed. Done.
- `embed.py`: embeddings via Ollama, normalised and rounded at index time. Done.
- `search.py`: dot product, top-k, revision gate, side-by-side revision comparison. Done.
- `evaluate.py`: recall@k and groundedness against a labelled question set. Next.