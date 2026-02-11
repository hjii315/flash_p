import json
import os
from dataclasses import asdict
from datetime import datetime

from flash_proto.storage import Storage
from flash_proto.types import Requirements
from dotenv import load_dotenv


def _prompt(label: str) -> str:
    print(f"\n[{label}]")
    return input("> ").strip()


def main() -> int:
    print("flash_proto")
    load_dotenv()

    os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")
    os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
    os.environ.setdefault("OTEL_SDK_DISABLED", "true")

    from flash_proto.pipeline import run_workflow

    data_name = _prompt("데이터명")
    run_stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    req = Requirements(
        input_spec=_prompt("입력 (사용자 제공)"),
        output_spec=_prompt("출력 (시스템 제공)"),
        success_criteria=_prompt("성공 기준"),
        constraints=_prompt("제약 조건"),
    )

    db_path = os.environ.get("FLASH_PROTO_DB", "flash_proto.sqlite3")
    runs_dir = os.environ.get("FLASH_PROTO_RUNS_DIR", "runs")

    storage = Storage(db_path=db_path, runs_dir=runs_dir)
    session_id = storage.create_session(requirements=req)

    artifacts = run_workflow(requirements=req)

    for kind, content, filename in artifacts:
        storage.save_artifact(
            session_id=session_id,
            kind=kind,
            content=content,
            filename=filename,
            data_name=data_name,
            run_stamp=run_stamp,
        )

    print("\nSaved")
    print(f"- session_id: {session_id}")
    print(f"- db: {db_path}")
    print(f"- runs_dir: {runs_dir}")
    print("\nRequirements:")
    print(json.dumps(asdict(req), ensure_ascii=False, indent=2))

    return 0
