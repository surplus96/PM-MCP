from __future__ import annotations
import os
from typing import Dict, Optional


def _dump_yaml(front_matter: Dict) -> str:
    try:
        import yaml  # type: ignore
        return yaml.safe_dump(front_matter, allow_unicode=True, sort_keys=False).strip()
    except Exception:
        # 매우 단순한 YAML 직렬화 대체(중첩 최소 가정)
        lines = []
        for k, v in front_matter.items():
            if isinstance(v, (int, float)):
                lines.append(f"{k}: {v}")
            elif isinstance(v, (list, tuple)):
                lines.append(f"{k}:")
                for item in v:
                    lines.append(f"  - {item}")
            elif isinstance(v, dict):
                lines.append(f"{k}:")
                for sk, sv in v.items():
                    lines.append(f"  {sk}: {sv}")
            else:
                s = str(v).replace('\n', ' ')
                lines.append(f"{k}: {s}")
        return "\n".join(lines)


def write_markdown(note_path: str, front_matter: Optional[Dict] = None, body: str = "") -> str:
    root = os.getenv("OBSIDIAN_VAULT_PATH", "./obsidian_vault")
    abs_path = os.path.join(root, note_path)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    fm = ""
    if front_matter:
        fm = "---\n" + _dump_yaml(front_matter) + "\n---\n\n"
    with open(abs_path, "w", encoding="utf-8") as f:
        f.write(fm + body)
    return abs_path
