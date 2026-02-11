from __future__ import annotations

import os

from crewai import Agent, Crew, Process, Task
from pydantic import BaseModel

from flash_proto.types import Artifact, Requirements


class CritiqueResult(BaseModel):
    needs_changes: bool
    corrections: str


def _extract_critique(output: object) -> tuple[bool, str, str]:
    text = "" if output is None else str(output)

    data = None
    pyd = getattr(output, "pydantic", None)
    if pyd is not None:
        data = getattr(pyd, "model_dump", lambda: None)()

    if data is None:
        as_dict = getattr(output, "to_dict", None)
        if callable(as_dict):
            try:
                data = as_dict()
            except Exception:
                data = None

    if data is None and isinstance(output, dict):
        data = output

    if data is None:
        try:
            import json

            data = json.loads(text)
        except Exception:
            data = {}

    needs_changes = bool(getattr(data, "get", lambda _k, _d=None: _d)("needs_changes", False))
    corrections = str(getattr(data, "get", lambda _k, _d=None: _d)("corrections", "") or "")
    return needs_changes, corrections, text


def _req_block(requirements: Requirements) -> str:
    return (
        f"Input: {requirements.input_spec}\n"
        f"Output: {requirements.output_spec}\n"
        f"Success criteria: {requirements.success_criteria}\n"
        f"Constraints: {requirements.constraints}\n"
    )


def _build_crew(requirements: Requirements, *, previous_code: str | None = None, corrections: str | None = None) -> Crew:
    model = os.environ.get("FLASH_PROTO_MODEL", "gpt-4o-mini")
    req_block = _req_block(requirements)

    coder = Agent(
        role="Senior Python Developer",
        goal="Generate minimal, runnable Python code that satisfies the requirements.",
        backstory="You write correct, concise code and respect constraints.",
        llm=model,
        allow_delegation=False,
        verbose=False,
    )
    architect = Agent(
        role="Software Architect",
        goal="Reverse-engineer documentation and structure from code in Korean.",
        backstory="You document module structure and behaviors precisely.",
        llm=model,
        allow_delegation=False,
        verbose=False,
    )
    teacher = Agent(
        role="Beginner-Friendly Explainer",
        goal="Explain the code with accurate real-world analogies in Korean.",
        backstory="You teach without inventing details not supported by the code.",
        llm=model,
        allow_delegation=False,
        verbose=False,
    )
    reviewer = Agent(
        role="Strict Reviewer",
        goal="Detect errors, omissions, and assumptions; request corrections if needed in Korean.",
        backstory="You are skeptical and focus on correctness.",
        llm=model,
        allow_delegation=False,
        verbose=False,
    )
    quizmaster = Agent(
        role="Quiz Generator",
        goal="Create quizzes that verify understanding with an answer key in Korean.",
        backstory="You generate concise and unambiguous questions in Korean.",
        llm=model,
        allow_delegation=False,
        verbose=False,
    )

    code_prompt = (
        "Generate a minimal, runnable Python solution that satisfies the requirements. "
        "Return only Python code in a single fenced code block. Do not include any explanation."\
        "\n\n" + req_block
    )
    if previous_code and corrections:
        code_prompt = (
            "Update the existing code to address the reviewer corrections while keeping it minimal and runnable. "
            "Return only Python code in a single fenced code block. Do not include any explanation."\
            "\n\nRequirements:\n" + req_block + "\n\nExisting code:\n" + previous_code + "\n\nCorrections:\n" + corrections
        )

    code_task = Task(
        description=code_prompt,
        expected_output="A single fenced code block containing the complete solution.",
        agent=coder,
    )

    docs_task = Task(
        description=(
            "아래 요구사항을 만족하는 코드에 대해 역설계 문서를 한국어로 작성하세요. "
            "반드시 포함: Module map / Data flow / Invariants / Failure modes."\
            "\n\n요구사항:\n" + req_block
        ),
        expected_output="Markdown documentation (no need to include code).",
        agent=architect,
        context=[code_task],
        markdown=True,
    )

    analogy_task = Task(
        description=(
            "초보자를 위한 비유 설명을 한국어로 작성하세요. 반드시 포함: "
            "현실 비유 / 코드 매핑 / 왜 필요한가 / 한계."\
            "\n\n요구사항:\n" + req_block
        ),
        expected_output="A clear explanation in markdown.",
        agent=teacher,
        context=[code_task],
        markdown=True,
    )

    critique_task = Task(
        description=(
            "설명(비유 설명)을 검증하고 반박하세요. 오류/누락/가정을 탐지하세요. "
            "출력은 반드시 JSON 하나로만 반환하세요. 키는 영문으로 고정: "
            "needs_changes (boolean), corrections (string). "
            "corrections는 한국어로, 가능한 한 구체적이고 실행 가능한 수정 지시로 작성하세요."\
            "\n\n요구사항:\n" + req_block
        ),
        expected_output="A JSON object with needs_changes and corrections.",
        agent=reviewer,
        context=[code_task, analogy_task],
        output_json=CritiqueResult,
    )

    quiz_task = Task(
        description=(
            "이해도를 확인하는 짧은 퀴즈를 한국어로 작성하세요. "
            "문항 5개와 정답(해설은 선택)을 포함하세요."\
            "\n\n요구사항:\n" + req_block
        ),
        expected_output="A quiz with an answer key in markdown.",
        agent=quizmaster,
        context=[code_task, docs_task],
        markdown=True,
    )

    return Crew(
        agents=[coder, architect, teacher, reviewer, quizmaster],
        tasks=[code_task, docs_task, analogy_task, critique_task, quiz_task],
        process=Process.sequential,
        verbose=False,
    )


def run_workflow(requirements: Requirements) -> list[Artifact]:
    crew = _build_crew(requirements=requirements)
    crew.kickoff(inputs={})

    code = str(crew.tasks[0].output)
    module_map = str(crew.tasks[1].output)
    analogy = str(crew.tasks[2].output)

    needs_changes, corrections, critique = _extract_critique(crew.tasks[3].output)
    quiz = str(crew.tasks[4].output)

    if needs_changes and corrections.strip():
        crew2 = _build_crew(requirements=requirements, previous_code=code, corrections=corrections)
        crew2.kickoff(inputs={})

        code = str(crew2.tasks[0].output)
        module_map = str(crew2.tasks[1].output)
        analogy = str(crew2.tasks[2].output)
        critique = str(crew2.tasks[3].output)
        quiz = str(crew2.tasks[4].output)

    return [
        ("code", code, "generated_code.md"),
        ("reverse_docs", module_map, "reverse_docs.md"),
        ("analogy", analogy, "analogy.md"),
        ("critique", critique, "critique.md"),
        ("quiz", quiz, "quiz.md"),
    ]
