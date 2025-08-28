from __future__ import annotations
import asyncio
import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Set

from pforge.orchestrator.state_bus import PuzzleState
from .base_agent import BaseAgent

SANDBOX_ROOT = Path(os.getenv("SANDBOX_ROOT", "sandbox_test"))
DOC_DIRS: List[Path] = [SANDBOX_ROOT, SANDBOX_ROOT / "docs"]

logger = logging.getLogger("agent.spec_oracle")

class SpecOracleAgent(BaseAgent):
    name = "spec_oracle"
    weight = 0.8
    spawn_threshold = 0.15
    retire_threshold = -0.05
    max_tokens_tick = 8_000
    tick_interval = 15.0

    _hash_cache: str | None = None
    _tg_nodes: Set[str] = set()

    async def on_startup(self) -> None:
        logger.info("SpecOracleAgent initial spec ingest")
        await self._ingest_spec()

    async def on_tick(self, state: PuzzleState) -> None:
        if self._docs_changed():
            await self._ingest_spec()

        manifest_msg = await self._latest_manifest()
        if manifest_msg:
            code_files = set(manifest_msg["payload"]["files"])
            missing = {n for n in self._tg_nodes if not self._node_realised(n, code_files)}
            if missing:
                await self.dE(len(missing))
                await self.send_amp(
                    action="spec_gaps",
                    payload={"missing_nodes": list(missing)},
                    broadcast=True,
                )

    async def _ingest_spec(self) -> None:
        nodes = set()
        for doc_dir in DOC_DIRS:
            if not doc_dir.exists():
                continue
            for file in doc_dir.rglob("*"):
                if file.suffix.lower() in {".md", ".markdown", ".rst"}:
                    nodes.update(self._parse_markdown(file))
                elif file.name.startswith(("openapi", "swagger")):
                    nodes.update(self._parse_openapi(file))

        self._tg_nodes = nodes
        await self._save_to_neo4j(nodes)
        await self.send_amp(action="tg_update", payload={"nodes": list(nodes)}, broadcast=True)
        self._hash_cache = self._current_hash()
        logger.info("SpecOracleAgent ingested %d TG nodes", len(nodes))

    def _parse_markdown(self, path: Path) -> Set[str]:
        content = path.read_text(encoding="utf-8", errors="ignore")
        nodes: Set[str] = set()
        for line in content.splitlines():
            if line.startswith("#"):
                title = line.lstrip("# ").strip()
                if title:
                    nodes.add(title.lower())
            if line.strip().startswith("- [ ]"):
                task = line.split("]")[-1].strip()
                nodes.add(task.lower())
        return nodes

    def _parse_openapi(self, path: Path) -> Set[str]:
        try:
            import yaml
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            nodes = {f"{method.upper()} {route}" for route, item in data["paths"].items() for method in item}
            return nodes
        except Exception as exc:
            logger.warning("Failed to parse OpenAPI: %s: %s", path, exc)
            return set()

    async def _save_to_neo4j(self, nodes: Set[str]) -> None:
        logger.warning("Neo4j is not available in local-only mode. Skipping TG persistence.")

    def _current_hash(self) -> str:
        md5 = hashlib.md5()
        for doc_dir in DOC_DIRS:
            if doc_dir.exists():
                for file in doc_dir.rglob("*"):
                    if file.is_file():
                        md5.update(str(file.relative_to(SANDBOX_ROOT)).encode())
                        md5.update(str(int(file.stat().st_mtime)).encode())
        return md5.hexdigest()

    def _docs_changed(self) -> bool:
        new_hash = self._current_hash()
        if new_hash != self._hash_cache:
            return True
        return False

    async def _latest_manifest(self) -> Dict | None:
        msgs = await self.read_amp()
        for msg in reversed(msgs):
            if msg.get("action") == "file_manifest":
                return msg
        return None

    def _node_realised(self, node_name: str, code_files: Set[str]) -> bool:
        slug = (
            node_name.replace(" ", "_")
            .replace("/", "_")
            .replace("-", "_")
            .lower()
        )
        return any(slug in f.lower() for f in code_files)
