from __future__ import annotations

import os
import sys
import hashlib
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

load_dotenv(REPO_ROOT / ".env")
os.environ["LANGFUSE_PROMPT_CACHE_TTL_SECONDS"] = "0"

from app.agent import LabAgent
from app.prompt_management import DEFAULT_PROMPT_TEMPLATE
from app.tracing import get_langfuse_client


PROMPT_NAME = os.getenv("LANGFUSE_PROMPT_NAME", "day13-chat")
CANDIDATE_TEMPLATE = (
    "Answer concisely using the retrieved context.\n"
    "Feature={{feature}}\nDocs={{docs}}\nQuestion={{message}}"
)
QUESTION = "How do metrics, logs, and traces help investigate an incident?"


def _run_trace(client, *, label: str, session_id: str) -> None:
    os.environ["LANGFUSE_PROMPT_LABEL"] = label
    LabAgent().run(
        user_id="cp2-prompt-evaluation",
        feature="monitoring",
        session_id=session_id,
        message=QUESTION,
        correlation_id=f"req-{hashlib.sha256(session_id.encode()).hexdigest()[:8]}",
    )
    client.flush()


def _latest_trace_id(client, session_id: str) -> str:
    observations = client.api.observations.get_many(
        session_id=session_id,
        is_root_observation=True,
        limit=10,
    ).data
    return observations[0].trace_id if observations else "not-found"


def main() -> int:
    client = get_langfuse_client()
    prompt_meta = client.api.prompts.list(name=PROMPT_NAME, limit=50).data
    if not prompt_meta:
        client.create_prompt(
            name=PROMPT_NAME,
            prompt=DEFAULT_PROMPT_TEMPLATE,
            labels=["baseline", "production"],
            type="text",
            commit_message="Day13 baseline prompt",
        )
        versions = [1]
    else:
        versions = sorted(prompt_meta[0].versions)
        client.update_prompt(
            name=PROMPT_NAME,
            version=1,
            new_labels=["baseline", "production"],
        )

    if 2 not in versions:
        client.create_prompt(
            name=PROMPT_NAME,
            prompt=CANDIDATE_TEMPLATE,
            labels=["candidate"],
            type="text",
            commit_message="Day13 concise candidate prompt",
        )

    # Same input against the two immutable versions.
    _run_trace(client, label="baseline", session_id="cp2-baseline-v1")
    _run_trace(client, label="candidate", session_id="cp2-candidate-v2")

    # Promote v2 to production and record a trace.
    client.update_prompt(name=PROMPT_NAME, version=1, new_labels=["baseline"])
    client.update_prompt(
        name=PROMPT_NAME,
        version=2,
        new_labels=["candidate", "production"],
    )
    _run_trace(client, label="production", session_id="cp2-promoted-v2")

    # Roll production back to v1; leave the project in the safe baseline state.
    client.update_prompt(name=PROMPT_NAME, version=2, new_labels=["candidate"])
    client.update_prompt(
        name=PROMPT_NAME,
        version=1,
        new_labels=["baseline", "production"],
    )
    _run_trace(client, label="production", session_id="cp2-rollback-v1")

    print(f"Prompt: {PROMPT_NAME}")
    for label, session_id in (
        ("baseline/v1", "cp2-baseline-v1"),
        ("candidate/v2", "cp2-candidate-v2"),
        ("promoted production/v2", "cp2-promoted-v2"),
        ("rollback production/v1", "cp2-rollback-v1"),
    ):
        print(f"{label}: {_latest_trace_id(client, session_id)}")
    print("Final labels: v1=[baseline, production], v2=[candidate]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
