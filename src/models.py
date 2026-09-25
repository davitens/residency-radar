from __future__ import annotations

import dataclasses
import hashlib
import json
from dataclasses import dataclass


@dataclass
class Program:
    org: str
    title: str
    url: str
    text: str = ""
    location: str = ""
    deadline: str = ""
    posted: str = ""
    eligibility: str = ""
    stipend: str = ""
    source: str = "curated"
    parent: str = ""
    kind: str = "offer"
    status: str = "unknown"
    status_evidence: str = ""
    id: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            self.id = hashlib.sha1(self.url.encode("utf-8")).hexdigest()[:16]

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Program":
        names = {f.name for f in dataclasses.fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in names})


def load_programs(path: str) -> list[Program]:
    with open(path, encoding="utf-8") as fh:
        return [Program.from_dict(d) for d in json.load(fh)]


def save_programs(programs: list[Program], path: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump([p.to_dict() for p in programs], fh, indent=2, ensure_ascii=False)
