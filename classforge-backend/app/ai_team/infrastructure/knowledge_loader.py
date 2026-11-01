"""
KnowledgeLoader: Loads, measures, slices and caches ClassForge domain knowledge.

Provides deterministic, byte-identical static knowledge blocks for Gemini implicit caching
(Gemini 3.8 Flash requires >= 4,096 prefix tokens to trigger implicit cache hits).
"""
from __future__ import annotations
import os
import re
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent / "knowledge"
MAX_KNOWLEDGE_TOKENS_PER_CALL = 6000
GEMINI_38_FLASH_CACHE_THRESHOLD = 4096


def estimate_tokens(text: str) -> int:
    """Estimates token count for Spanish/Markdown text (~3.8 - 4 chars per token).
    
    Averages character count // 4 and word count * 1.3 for high accuracy across
    both natural language and JSON/code samples.
    """
    if not text:
        return 0
    char_est = len(text) / 4.0
    word_est = len(text.split()) * 1.3
    return max(1, int(round((char_est + word_est) / 2.0)))


@dataclass(frozen=True)
class KnowledgeDoc:
    filename: str
    title: str
    path: str
    content: str
    byte_size: int
    token_count: int


class KnowledgeLoader:
    """Singleton repository for ClassForge knowledge base documents."""

    def __init__(self, knowledge_dir: Optional[Path] = None):
        self.knowledge_dir = knowledge_dir or KNOWLEDGE_DIR
        self._docs: Dict[str, KnowledgeDoc] = {}
        self._load_all()

    def _extract_title(self, content: str, default: str) -> str:
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("# "):
                return line.lstrip("# ").strip()
        return default

    def _load_all(self) -> None:
        if not self.knowledge_dir.exists():
            logger.warning(f"[KnowledgeLoader] Directory {self.knowledge_dir} does not exist.")
            return

        for entry in sorted(self.knowledge_dir.glob("*.md")):
            try:
                content = entry.read_text(encoding="utf-8")
                byte_size = len(content.encode("utf-8"))
                tokens = estimate_tokens(content)
                title = self._extract_title(content, entry.stem)
                
                # Relative path from project root for clean referencing
                rel_path = f"app/ai_team/knowledge/{entry.name}"

                doc = KnowledgeDoc(
                    filename=entry.name,
                    title=title,
                    path=rel_path,
                    content=content,
                    byte_size=byte_size,
                    token_count=tokens,
                )
                self._docs[entry.name] = doc
            except Exception as e:
                logger.error(f"[KnowledgeLoader] Failed to read {entry.name}: {e}")

        logger.info(f"[KnowledgeLoader] Loaded {len(self._docs)} knowledge files ({self.total_tokens} approx tokens).")

    @property
    def total_tokens(self) -> int:
        return sum(d.token_count for d in self._docs.values())

    @property
    def total_bytes(self) -> int:
        return sum(d.byte_size for d in self._docs.values())

    def get_document(self, filename: str) -> Optional[KnowledgeDoc]:
        return self._docs.get(filename)

    def get_manifest(self) -> Dict[str, Any]:
        """Returns metadata manifest of all loaded knowledge files for admin inspection."""
        docs_list = [
            {
                "filename": doc.filename,
                "title": doc.title,
                "path": doc.path,
                "byte_size": doc.byte_size,
                "token_count": doc.token_count,
            }
            for doc in sorted(self._docs.values(), key=lambda d: d.filename)
        ]
        return {
            "total_documents": len(docs_list),
            "total_bytes": self.total_bytes,
            "total_tokens": self.total_tokens,
            "gemini_cache_threshold_tokens": GEMINI_38_FLASH_CACHE_THRESHOLD,
            "implicit_caching_eligible": self.total_tokens >= GEMINI_38_FLASH_CACHE_THRESHOLD,
            "documents": docs_list,
        }

    def get_slice_for_role(
        self,
        role_id: str,
        max_budget_tokens: int = MAX_KNOWLEDGE_TOKENS_PER_CALL,
    ) -> str:
        """Returns a deterministic, formatted slice of knowledge markdown files suited for the role.
        
        The slice is ordered deterministically so that identical roles produce byte-identical prefixes.
        """
        role_mapping: Dict[str, List[str]] = {
            "architect": [
                "00_producto.md",
                "10_modelo_uml.md",
                "20_comandos_uml.md",
                "70_buenas_practicas_uml.md",
                "30_codegen.md",
            ],
            "qa": [
                "00_producto.md",
                "10_modelo_uml.md",
                "70_buenas_practicas_uml.md",
                "20_comandos_uml.md",
                "60_glosario_es.md",
            ],
            "tech_lead": [
                "00_producto.md",
                "10_modelo_uml.md",
                "30_codegen.md",
                "70_buenas_practicas_uml.md",
                "40_colaboracion.md",
            ],
            "mentor": [
                "00_producto.md",
                "10_modelo_uml.md",
                "60_glosario_es.md",
                "70_buenas_practicas_uml.md",
                "20_comandos_uml.md",
            ],
            "dba": [
                "10_modelo_uml.md",
                "30_codegen.md",
                "70_buenas_practicas_uml.md",
                "20_comandos_uml.md",
                "00_producto.md",
            ],
            "security": [
                "00_producto.md",
                "50_roles_permisos.md",
                "40_colaboracion.md",
                "70_buenas_practicas_uml.md",
            ],
            "analyst": [
                "00_producto.md",
                "10_modelo_uml.md",
                "60_glosario_es.md",
                "20_comandos_uml.md",
                "50_roles_permisos.md",
            ],
        }

        requested_files = role_mapping.get(
            role_id,
            ["00_producto.md", "10_modelo_uml.md", "70_buenas_practicas_uml.md", "20_comandos_uml.md"]
        )

        accumulated_tokens = 0
        chunks: List[str] = []

        for filename in requested_files:
            doc = self._docs.get(filename)
            if not doc:
                continue
            if accumulated_tokens + doc.token_count > max_budget_tokens:
                # Stop if adding this file exceeds the budget
                break
            chunks.append(f"<!-- KNOWLEDGE:{doc.filename} -->\n{doc.content.strip()}\n")
            accumulated_tokens += doc.token_count

        return "\n\n".join(chunks)


# Global singleton instance
knowledge_loader = KnowledgeLoader()
