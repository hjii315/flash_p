from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Requirements:
    input_spec: str
    output_spec: str
    success_criteria: str
    constraints: str


Artifact = tuple[str, str, str]
