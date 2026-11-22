"""Lista dozwolonych źródeł - jedna dla agenta i backendu.

Źródłem prawdy są reguły webfetch w agent/opencode.jsonc: OpenCode pozwala agentowi pobierać
tylko te adresy, a backend tymi samymi wzorcami sprawdza źródła w raporcie.
"""

import json
import re
from fnmatch import fnmatchcase
from functools import lru_cache
from pathlib import Path

from prawdowid.api.settings import AGENT_DIR

CONFIG_FILE = "opencode.jsonc"


def _strip_jsonc(text: str) -> str:
    """Usuwa komentarze // i /* */ poza napisami oraz przecinki przed ] i }."""
    out, i, in_str = [], 0, False
    while i < len(text):
        ch = text[i]
        if in_str:
            out.append(ch)
            if ch == "\\":
                out.append(text[i + 1 : i + 2])
                i += 1
            elif ch == '"':
                in_str = False
        elif ch == '"':
            in_str = True
            out.append(ch)
        elif text.startswith("//", i):
            i = text.find("\n", i)
            if i == -1:
                break
            continue
        elif text.startswith("/*", i):
            i = text.find("*/", i) + 2
            continue
        else:
            out.append(ch)
        i += 1
    return re.sub(r",(\s*[\]}])", r"\1", "".join(out))


@lru_cache
def allowed_patterns(agent_dir: Path = AGENT_DIR) -> tuple[str, ...]:
    """Wzorce adresów, które agent może pobrać (reguły webfetch z effect=allow)."""
    config = json.loads(_strip_jsonc((agent_dir / CONFIG_FILE).read_text(encoding="utf-8")))
    return tuple(
        rule["resource"]
        for rule in config.get("permissions", [])
        if rule.get("action") == "webfetch" and rule.get("effect") == "allow"
    )


def is_allowed(url: str, patterns: tuple[str, ...] | None = None) -> bool:
    """Ta sama reguła co w OpenCode: cały adres musi pasować do wzorca (* obejmuje każdy znak)."""
    url = (url or "").strip()
    if not url.lower().startswith("https://"):
        return False
    if "/" not in url[len("https://") :]:
        url += "/"  # https://www.gov.pl -> https://www.gov.pl/
    return any(fnmatchcase(url, p) for p in (patterns if patterns is not None else allowed_patterns()))
