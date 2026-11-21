"""Prompt systemowy z definicji agenta (agent/).

Kolejność: agent/prawdowid.md, potem skille agent/skills/<nazwa>/SKILL.md (alfabetycznie),
na końcu agent/response_format.md - format JSON, który czyta src/prawdowid/api/report.py.
"""

from pathlib import Path

from prawdowid.api.settings import AGENT_DIR

AGENT_FILE = "prawdowid.md"
FORMAT_FILE = "response_format.md"


def agent_files(agent_dir: Path = AGENT_DIR) -> list[Path]:
    skills = sorted(agent_dir.glob("skills/*/SKILL.md"))
    return [p for p in [agent_dir / AGENT_FILE, *skills, agent_dir / FORMAT_FILE] if p.exists()]


def system_prompt(agent_dir: Path = AGENT_DIR) -> str:
    return "\n\n".join(
        f"<!-- {p.relative_to(agent_dir)} -->\n{p.read_text(encoding='utf-8')}" for p in agent_files(agent_dir)
    )
