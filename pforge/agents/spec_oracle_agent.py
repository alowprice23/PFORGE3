from __future__ import annotations
import logging
from pathlib import Path
from typing import Set, List, TYPE_CHECKING
import re

from .base_agent import BaseAgent
from pforge.orchestrator.signals import MsgType, Message

if TYPE_CHECKING:
    from pforge.messaging.in_memory_bus import InMemoryBus

logger = logging.getLogger(__name__)

class SpecOracleAgent(BaseAgent):
    """
    Ingests non-code artifacts to build a Target Graph (TG) of what the
    software *should* be, and reports on gaps between the spec and the code.
    """
    name: str = "spec_oracle"
    tick_interval: float = 10.0  # Re-scan for spec changes periodically

    def __init__(self, bus: InMemoryBus, source_root: str | Path = "."):
        super().__init__(bus)
        self.source_root = Path(source_root)
        self.doc_dirs: List[Path] = [self.source_root, self.source_root / "docs"]
        self.target_graph_nodes: Set[str] = set()
        self.code_manifest: Set[str] = set()

        # Subscribe to messages that might change the state of the code
        self.bus.subscribe(self.name, MsgType.FIX_PATCH_APPLIED.value)
        # For now, we'll also listen for the observer's manifest this way
        self.bus.subscribe(self.name, "file_manifest")

    async def on_startup(self):
        """On startup, perform an initial full scan of the specification."""
        self.logger.info("Performing initial spec ingest...")
        await self.on_tick()

    def _parse_markdown(self, path: Path) -> Set[str]:
        """A simple parser to extract spec nodes from Markdown files."""
        content = path.read_text(encoding="utf-8", errors="ignore")
        nodes: Set[str] = set()
        # Extract headings as nodes
        for line in content.splitlines():
            if line.startswith("#"):
                title = line.lstrip("# ").strip().lower()
                if title:
                    nodes.add(title)
            # Extract unchecked task list items as gap nodes
            if re.match(r'^\s*-\s*\[\s\]', line):
                task = line.split("]", 1)[-1].strip().lower()
                if task:
                    nodes.add(task)
        return nodes

    async def _ingest_spec_files(self):
        """Scans doc directories and parses files to build the Target Graph."""
        new_nodes: Set[str] = set()
        for doc_dir in self.doc_dirs:
            if not doc_dir.exists() or not doc_dir.is_dir():
                continue
            for file_path in doc_dir.rglob("*"):
                if file_path.suffix.lower() in {".md", ".markdown"}:
                    new_nodes.update(self._parse_markdown(file_path))
                # Add parsers for OpenAPI, etc. here in the future

        if new_nodes != self.target_graph_nodes:
            self.logger.info(f"Spec changed. Found {len(new_nodes)} target graph nodes.")
            self.target_graph_nodes = new_nodes

    async def on_tick(self):
        """
        Periodically re-scans the spec and compares it to the last known
        code manifest, publishing any gaps.
        """
        await self._ingest_spec_files()

        # Check for messages from other agents
        message = await self.bus.get(self.name, timeout=0.1)
        if message:
            if message.type == "file_manifest":
                self.code_manifest = set(message.payload.get("files", []))
                self.logger.info(f"Received code manifest with {len(self.code_manifest)} files.")
            elif message.type == MsgType.FIX_PATCH_APPLIED:
                # A fix was applied, which might have closed a gap.
                # We should re-compare the spec to the code.
                # The observer will send a new manifest soon.
                pass

        # Compare spec to code and find gaps
        if not self.target_graph_nodes or not self.code_manifest:
            return

        gaps = {node for node in self.target_graph_nodes if not self._node_realised(node, self.code_manifest)}

        if gaps:
            gap_message = Message(
                type=MsgType.TESTS_FAILED, # We can treat spec gaps as a type of test failure
                payload={"failed_tests": [{"nodeid": f"spec_gap::{g}", "traceback": f"Specification node '{g}' is not implemented."} for g in gaps]}
            )
            await self.publish(MsgType.TESTS_FAILED.value, gap_message)
            self.logger.info(f"Published {len(gaps)} specification gaps as test failures.")

    def _node_realised(self, node_name: str, code_files: Set[str]) -> bool:
        """
        A crude heuristic to check if a spec node is "realised" in the code.
        It checks if a slugified version of the node name appears in any file path.
        """
        # A real implementation would be much more sophisticated, using code parsing,
        # embeddings, or a formal mapping from spec to code.
        slug = re.sub(r'[^a-z0-9]+', '_', node_name.lower()).strip('_')
        if not slug:
            return False
        return any(slug in f.lower() for f in code_files)
