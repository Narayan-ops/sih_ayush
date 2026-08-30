"""
One-off script: ingest data/corpus/section_3_patents_act.json into the running
ingestion service (http://localhost:8002/ingest).

Run from the ingestion/ directory with its venv activated:
    python ingest_section3.py
"""
import json
import requests

with open("../data/corpus/section_3_patents_act.json", "r", encoding="utf-8") as f:
    corpus = json.load(f)

data = [
    {
        "text": clause["text"],
        "section": corpus["section"],
        "clause_id": clause["clause_id"],
    }
    for clause in corpus["clauses"]
]

payload = {
    "data_source": "json",
    "data": data,
    "metadata": {
        "title": corpus["source"],
        "chapter": corpus["chapter"],
        "chapter_title": corpus["chapter_title"],
        "source_url": corpus["source_url"],
        "version": "1.0",
    },
    "jurisdiction": "in",
    "domain": "patents",
}

resp = requests.post("http://localhost:8002/ingest", json=payload, timeout=120)
print("Status code:", resp.status_code)
print(json.dumps(resp.json(), indent=2))
