from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class ScreenerConfig:
    raw: dict[str, Any]

    @classmethod
    def load(cls, path: str | Path) -> "ScreenerConfig":
        with Path(path).open("r", encoding="utf-8") as file:
            return cls(yaml.safe_load(file))

    def get(self, *keys: str, default: Any = None) -> Any:
        node: Any = self.raw
        for key in keys:
            if not isinstance(node, dict) or key not in node:
                return default
            node = node[key]
        return node
