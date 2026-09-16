import json
import logging
import os
import re
from pathlib import Path
from typing import Dict, List, Optional

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter


LOG = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANUAL_PATH = ROOT / "rules" / "safety_manual.pdf"
DEFAULT_INDEX_DIR = ROOT / "data" / "faiss_index"
FALLBACK_RULES_PATH = ROOT / "rules" / "ppe_rules.json"


TASK_BLOCK = re.compile(
    r"Task\s*:\s*(?P<task>[A-Za-z0-9_\- ]+?)"
    r"\s+Required\s*PPE\s*:\s*(?P<required>[^\n]+?)"
    r"\s+Recommended\s*PPE\s*:\s*(?P<recommended>[^\n]+)",
    re.IGNORECASE,
)

MD_FENCE = re.compile(
    r"^```(?:json)?\s*(.*?)\s*```\s*$",
    re.DOTALL | re.IGNORECASE,
)


EXTRACTION_PROMPT = """You extract PPE requirements from a factory safety manual.

TASK: {task}

MANUAL EXCERPT:
{context}

Return ONLY valid JSON matching this schema:
{{
  "critical_ppe": ["item1", "item2"],
  "recommended_ppe": ["item3"],
  "citation": "verbatim short quote from the excerpt supporting this rule",
  "confidence": 0.0
}}

Rules:
- critical_ppe = mandatory; absence triggers CRITICAL severity.
- recommended_ppe = advisory; absence triggers WARNING.
- Use canonical short names (Helmet, Gloves, Face Shield, Safety Shoes, Safety Glasses, Coverall, Safety Harness, Safety Vest, Ear Protectors).
- If the excerpt does not specify PPE for the task, return empty lists and confidence 0.0.
- Do not invent items not present in the excerpt.
"""


KNOWN_PPE = (
    "Helmet",
    "Gloves",
    "Face Shield",
    "Safety Shoes",
    "Safety Glasses",
    "Coverall",
    "Safety Harness",
    "Safety Vest",
    "Ear Protectors",
)

BASE_MINIMUM_CRITICAL = (
    "Helmet",
    "Safety Shoes",
    "Safety Vest",
)

CACHEABLE_SOURCES = {
    "structured_parser",
    "llm_extraction",
}

CONFIDENCE_FLOOR = 0.5
MAX_CACHE_ENTRIES = 200


class ManualRAGError(Exception):
    pass


def normalize_task(task: str) -> str:
    return re.sub(
        r"[\s\-]+",
        "_",
        (task or "").strip().lower(),
    ).strip("_")


class ManualRAG:
    def __init__(
        self,
        manual_path: Path = DEFAULT_MANUAL_PATH,
        index_dir: Path = DEFAULT_INDEX_DIR,
        embeddings_model: str = "models/text-embedding-004",
        api_key: Optional[str] = None,
        llm_model: Optional[str] = None,
        gemini_client=None,
        chunk_size: int = 800,
        chunk_overlap: int = 150,
    ):
        self.manual_path = Path(manual_path)
        self.index_dir = Path(index_dir)
        self.api_key = api_key
        self.llm_model = llm_model or os.getenv("GEMINI_MODEL")
        self.gemini_client = gemini_client
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        self.embeddings = None
        self.vector_store = None
        self.structured_rules: Dict[str, dict] = {}
        self.raw_text = ""
        self.fallback_rules: Dict[str, dict] = {}
        self._extraction_cache: Dict[str, dict] = {}

        self._init_embeddings(embeddings_model)
        self._load_manual()
        self._build_or_load_index()
        self._load_fallback_rules()
        self._log_health()

    def _load_fallback_rules(self) -> None:
        if FALLBACK_RULES_PATH.is_file():
            try:
                raw = json.loads(
                    FALLBACK_RULES_PATH.read_text(
                        encoding="utf-8"
                    )
                )
                if isinstance(raw, dict):
                    self.fallback_rules = {
                        normalize_task(k): v
                        for k, v in raw.items()
                        if isinstance(v, dict)
                    }
                else:
                    self.fallback_rules = {}
            except Exception as exc:
                LOG.error(
                    "Failed to load fallback rules: %s",
                    exc,
                )
                self.fallback_rules = {}
        else:
            self.fallback_rules = {}

    def _log_health(self) -> None:
        LOG.info(
            "ManualRAG ready: structured=%d, faiss=%s, chars=%d, llm=%s",
            len(self.structured_rules),
            "yes" if self.vector_store is not None else "no",
            len(self.raw_text),
            self.llm_model or "<unset>",
        )

        if not self.llm_model:
            LOG.warning(
                "llm_model is unset; LLM extraction disabled."
            )

        if not self.structured_rules and self.vector_store is None:
            LOG.warning(
                "ManualRAG degraded: only fallback/conservative paths active."
            )

    def _init_embeddings(self, model: str) -> None:
        try:
            self.embeddings = GoogleGenerativeAIEmbeddings(
                model=model,
                google_api_key=self.api_key,
            )
        except Exception as exc:
            LOG.error(
                "Embeddings init failed: %s",
                exc,
            )
            self.embeddings = None

    def _load_manual(self) -> None:
        if not self.manual_path.is_file():
            LOG.warning(
                "Manual not found: %s",
                self.manual_path,
            )
            return

        try:
            if self.manual_path.suffix.lower() == ".pdf":
                docs = PyPDFLoader(
                    str(self.manual_path)
                ).load()
            else:
                docs = TextLoader(
                    str(self.manual_path),
                    encoding="utf-8",
                ).load()
        except Exception as exc:
            LOG.error(
                "Failed to load manual: %s",
                exc,
            )
            return

        self.raw_text = "\n\n".join(
            d.page_content
            for d in docs
        )
        self._parse_structured()

    def _parse_structured(self) -> None:
        for match in TASK_BLOCK.finditer(self.raw_text):
            task = normalize_task(
                match.group("task")
            )

            if not task:
                continue

            self.structured_rules[task] = {
                "critical_ppe": self._split_list(
                    match.group("required")
                ),
                "recommended_ppe": self._split_list(
                    match.group("recommended")
                ),
                "citation": match.group(0).strip(),
            }

        LOG.info(
            "Structured rules parsed: %d tasks -> %s",
            len(self.structured_rules),
            sorted(self.structured_rules),
        )

    @staticmethod
    def _split_list(value: str) -> List[str]:
        return [
            p.strip()
            for p in re.split(r"[,;]", value)
            if p.strip()
        ]

    def _manifest_path(self) -> Path:
        return self.index_dir / "_manifest.json"

    def _manual_fingerprint(self) -> Optional[dict]:
        if not self.manual_path.is_file():
            return None

        stat = self.manual_path.stat()

        return {
            "path": str(self.manual_path),
            "mtime": stat.st_mtime,
            "size": stat.st_size,
        }

    def _index_is_fresh(self) -> bool:
        manifest_path = self._manifest_path()

        if not manifest_path.is_file():
            return False

        try:
            stored = json.loads(
                manifest_path.read_text(
                    encoding="utf-8"
                )
            )
        except Exception:
            return False

        return stored == self._manual_fingerprint()

    def _write_manifest(self) -> None:
        fp = self._manual_fingerprint()

        if fp is None:
            return

        try:
            self.index_dir.mkdir(
                parents=True,
                exist_ok=True,
            )

            self._manifest_path().write_text(
                json.dumps(fp, indent=2),
                encoding="utf-8",
            )
        except Exception as exc:
            LOG.warning(
                "Could not write index manifest: %s",
                exc,
            )

    def _build_or_load_index(self) -> None:
        if self.embeddings is None or not self.raw_text:
            return

        index_present = (
            self.index_dir.exists()
            and any(self.index_dir.iterdir())
        )

        if index_present and self._index_is_fresh():
            try:
                self.vector_store = FAISS.load_local(
                    str(self.index_dir),
                    self.embeddings,
                    allow_dangerous_deserialization=True,
                )

                LOG.info(
                    "Loaded FAISS index from %s",
                    self.index_dir,
                )
                return

            except Exception as exc:
                LOG.warning(
                    "Index load failed: %s",
                    exc,
                )

        elif index_present:
            LOG.warning(
                "FAISS index is stale (manual changed); rebuilding."
            )

        try:
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                separators=[
                    "\n\n",
                    "\nTask:",
                    "\n",
                    ". ",
                    " ",
                    "",
                ],
            )

            chunks = splitter.split_documents(
                [
                    Document(
                        page_content=self.raw_text,
                        metadata={
                            "source": str(
                                self.manual_path
                            )
                        },
                    )
                ]
            )

            self.vector_store = FAISS.from_documents(
                chunks,
                self.embeddings,
            )

            self.index_dir.mkdir(
                parents=True,
                exist_ok=True,
            )

            self.vector_store.save_local(
                str(self.index_dir)
            )

            self._write_manifest()

            LOG.info(
                "Built FAISS index with %d chunks",
                len(chunks),
            )

        except Exception as exc:
            LOG.error(
                "Index build failed: %s",
                exc,
            )
            self.vector_store = None

    def get_required_ppe(self, task: str) -> dict:
        task_clean = normalize_task(task) or "unknown"

        if task_clean in self._extraction_cache:
            return self._extraction_cache[task_clean]

        result = self._do_lookup(task_clean)

        if result.get("source") in CACHEABLE_SOURCES:
            if len(self._extraction_cache) >= MAX_CACHE_ENTRIES:
                self._extraction_cache.pop(
                    next(iter(self._extraction_cache))
                )

            self._extraction_cache[task_clean] = result
        else:
            LOG.info(
                "Not caching '%s' (source=%s)",
                task_clean,
                result.get("source"),
            )

        return result

    def _do_lookup(self, task_clean: str) -> dict:
        if task_clean in self.structured_rules:
            rule = self.structured_rules[task_clean]

            return {
                "critical_ppe": rule["critical_ppe"],
                "recommended_ppe": rule["recommended_ppe"],
                "source": "structured_parser",
                "citations": [
                    {
                        "type": "manual_block",
                        "text": rule["citation"],
                    }
                ],
                "confidence": 1.0,
                "requires_manual_review": False,
            }

        retrieval = self._retrieve(task_clean)

        if retrieval["status"] == "error":
            return self._retrieval_error_result()

        chunks = retrieval["chunks"]

        if retrieval["status"] == "ok":
            try:
                extracted = self._llm_extract(
                    task_clean,
                    chunks,
                )

            except ManualRAGError as exc:
                LOG.warning(
                    "Transient LLM failure for '%s' (%s)",
                    task_clean,
                    exc,
                )

                return self._degraded_result(
                    task_clean,
                    chunks,
                    reason="llm_transient",
                )

            except Exception as exc:
                LOG.error(
                    "Unexpected LLM failure for '%s': %s",
                    task_clean,
                    exc,
                )

                return self._degraded_result(
                    task_clean,
                    chunks,
                    reason="llm_unexpected",
                )

            if self._is_trustworthy(extracted):
                return {
                    "critical_ppe": extracted.get(
                        "critical_ppe",
                        [],
                    ),
                    "recommended_ppe": extracted.get(
                        "recommended_ppe",
                        [],
                    ),
                    "source": "llm_extraction",
                    "citations": [
                        {
                            "type": "chunk_quote",
                            "text": extracted.get(
                                "citation",
                                "",
                            ),
                        }
                    ],
                    "confidence": float(
                        extracted.get(
                            "confidence",
                            0.5,
                        )
                    ),
                    "requires_manual_review": False,
                }

            LOG.info(
                "LLM low-confidence for '%s'; using safe fallback chain",
                task_clean,
            )

            return self._safe_fallback(
                task_clean,
                chunks,
                reason="llm_low_confidence",
            )

        return self._safe_fallback(
            task_clean,
            [],
            reason="no_retrieval",
        )

    def _retrieve(self, task_clean: str) -> dict:
        if self.vector_store is None:
            return {
                "status": "unavailable",
                "chunks": [],
            }

        query = (
            f"PPE required for "
            f"{task_clean.replace('_', ' ')} task"
        )

        try:
            chunks = self.vector_store.similarity_search(
                query,
                k=4,
            )
        except Exception as exc:
            LOG.error(
                "FAISS query failed for '%s': %s",
                task_clean,
                exc,
            )

            return {
                "status": "error",
                "chunks": [],
            }

        if not chunks:
            return {
                "status": "empty",
                "chunks": [],
            }

        return {
            "status": "ok",
            "chunks": chunks,
        }

    def _is_trustworthy(
        self,
        extracted: Optional[dict],
    ) -> bool:
        if not isinstance(extracted, dict):
            return False

        try:
            conf = float(
                extracted.get(
                    "confidence",
                    0.0,
                )
            )
        except (TypeError, ValueError):
            return False

        if conf < CONFIDENCE_FLOOR:
            return False

        crit = extracted.get(
            "critical_ppe"
        ) or []

        rec = extracted.get(
            "recommended_ppe"
        ) or []

        if not isinstance(crit, list):
            return False

        if not isinstance(rec, list):
            return False

        if not crit and not rec:
            return False

        return True

    def _safe_fallback(
        self,
        task_clean: str,
        chunks: List[Document],
        reason: str,
    ) -> dict:
        rule = self.fallback_rules.get(task_clean)

        if rule:
            return {
                "critical_ppe": rule.get(
                    "critical_ppe",
                    [],
                ),
                "recommended_ppe": rule.get(
                    "recommended_ppe",
                    [],
                ),
                "source": "fallback_json",
                "citations": [],
                "confidence": 0.4,
                "requires_manual_review": False,
                "reason": reason,
            }

        LOG.warning(
            "No fallback rule for '%s' (%s); "
            "applying base minimum + review flag",
            task_clean,
            reason,
        )

        return {
            "critical_ppe": list(
                BASE_MINIMUM_CRITICAL
            ),
            "recommended_ppe": [
                p
                for p in KNOWN_PPE
                if p not in BASE_MINIMUM_CRITICAL
            ],
            "source": "conservative_default",
            "citations": [
                {
                    "type": "chunk",
                    "text": c.page_content[:200],
                }
                for c in chunks
            ],
            "confidence": 0.2,
            "requires_manual_review": True,
            "reason": reason,
        }

    def _degraded_result(
        self,
        task_clean: str,
        chunks: List[Document],
        reason: str,
    ) -> dict:
        rule = self.fallback_rules.get(task_clean)

        if rule:
            return {
                "critical_ppe": rule.get(
                    "critical_ppe",
                    [],
                ),
                "recommended_ppe": rule.get(
                    "recommended_ppe",
                    [],
                ),
                "source": "fallback_json_after_llm_failure",
                "citations": [],
                "confidence": 0.3,
                "requires_manual_review": False,
                "reason": reason,
            }

        return {
            "critical_ppe": list(
                BASE_MINIMUM_CRITICAL
            ),
            "recommended_ppe": [
                p
                for p in KNOWN_PPE
                if p not in BASE_MINIMUM_CRITICAL
            ],
            "source": "conservative_default_after_llm_failure",
            "citations": [
                {
                    "type": "chunk",
                    "text": c.page_content[:200],
                }
                for c in chunks
            ],
            "confidence": 0.1,
            "requires_manual_review": True,
            "reason": reason,
        }

    @staticmethod
    def _retrieval_error_result() -> dict:
        return {
            "critical_ppe": list(
                BASE_MINIMUM_CRITICAL
            ),
            "recommended_ppe": [
                p
                for p in KNOWN_PPE
                if p not in BASE_MINIMUM_CRITICAL
            ],
            "source": "conservative_default_after_retrieval_error",
            "citations": [],
            "confidence": 0.1,
            "requires_manual_review": True,
            "reason": "retrieval_failed",
        }

    def _get_client(self):
        if self.gemini_client is not None:
            return self.gemini_client

        try:
            from google import genai

            self.gemini_client = genai.Client(
                api_key=self.api_key
            )

            return self.gemini_client

        except Exception as exc:
            raise ManualRAGError(
                f"client init failed: {exc}"
            ) from exc

    @staticmethod
    def _parse_json_response(
        text: Optional[str],
    ) -> dict:
        if text is None:
            raise ManualRAGError(
                "empty response from Gemini"
            )

        cleaned = text.strip()

        match = MD_FENCE.match(cleaned)

        if match:
            cleaned = match.group(1).strip()

        try:
            data = json.loads(cleaned)

        except json.JSONDecodeError as exc:
            raise ManualRAGError(
                f"non-JSON response: {exc}"
            ) from exc

        if not isinstance(data, dict):
            raise ManualRAGError(
                "response is not a JSON object"
            )

        return data

    @staticmethod
    def _validate_citation(
        citation: str,
        chunks: List[Document],
    ) -> bool:
        if not citation:
            return False

        needle = citation.strip().lower()

        if len(needle) < 15:
            return False

        for chunk in chunks:
            if needle in chunk.page_content.lower():
                return True

        return False

    @staticmethod
    def _canonical_ratio(
        items: List[str],
    ) -> float:
        if not items:
            return 0.0

        canon = {
            p.lower()
            for p in KNOWN_PPE
        }

        return (
            sum(
                1
                for item in items
                if isinstance(item, str)
                and item.strip().lower() in canon
            )
            / len(items)
        )

    @staticmethod
    def _ppe_supported_by_chunks(
        items: List[str],
        chunks: List[Document],
    ) -> float:
        if not items or not chunks:
            return 0.0

        context = " ".join(
            c.page_content.lower()
            for c in chunks
        )

        supported = 0

        aliases = {
            "helmet": ["helmet", "hard hat"],
            "gloves": ["gloves", "glove"],
            "face shield": ["face shield"],
            "safety shoes": [
                "safety shoes",
                "safety shoe",
            ],
            "safety glasses": [
                "safety glasses",
                "safety glass",
            ],
            "coverall": [
                "coverall",
                "coveralls",
            ],
            "safety harness": [
                "safety harness",
                "harness",
            ],
            "safety vest": [
                "safety vest",
                "vest",
            ],
            "ear protectors": [
                "ear protectors",
                "ear protection",
                "hearing protection",
            ],
        }

        for item in items:
            if not isinstance(item, str):
                continue

            key = item.strip().lower()

            candidates = aliases.get(
                key,
                [key],
            )

            if any(
                candidate in context
                for candidate in candidates
            ):
                supported += 1

        return supported / len(items)

    @staticmethod
    def _computed_confidence(
        llm_reported: float,
        citation_verified: bool,
        task_in_manual: bool,
        canonical_ratio: float,
        ppe_supported_ratio: float,
        has_chunks: bool,
    ) -> float:
        signals = {
            "llm_reported": max(
                0.0,
                min(1.0, llm_reported),
            ),
            "citation_verified": (
                1.0
                if citation_verified
                else 0.0
            ),
            "task_in_manual": (
                1.0
                if task_in_manual
                else 0.0
            ),
            "canonical_ratio": canonical_ratio,
            "ppe_supported_ratio": ppe_supported_ratio,
            "chunks_present": (
                1.0
                if has_chunks
                else 0.0
            ),
        }

        weights = {
            "llm_reported": 0.10,
            "citation_verified": 0.25,
            "task_in_manual": 0.15,
            "canonical_ratio": 0.15,
            "ppe_supported_ratio": 0.25,
            "chunks_present": 0.10,
        }

        score = sum(
            signals[key] * weights[key]
            for key in signals
        )

        return round(
            max(0.0, min(1.0, score)),
            3,
        )

    def _llm_extract(
        self,
        task: str,
        chunks: List[Document],
    ) -> dict:
        if not self.llm_model:
            raise ManualRAGError(
                "llm_model not configured"
            )

        client = self._get_client()

        try:
            from google.genai import types
        except Exception as exc:
            raise ManualRAGError(
                f"google.genai unavailable: {exc}"
            ) from exc

        context = "\n\n---\n\n".join(
            c.page_content
            for c in chunks
        )

        prompt = EXTRACTION_PROMPT.format(
            task=task,
            context=context,
        )

        try:
            response = client.models.generate_content(
                model=self.llm_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0,
                ),
            )

        except Exception as exc:
            raise ManualRAGError(
                f"generate_content failed: {exc}"
            ) from exc

        data = self._parse_json_response(
            response.text
        )

        citation = data.get("citation") or ""

        citation_valid = self._validate_citation(
            citation,
            chunks,
        )

        crit = data.get(
            "critical_ppe"
        ) or []

        rec = data.get(
            "recommended_ppe"
        ) or []

        if not isinstance(crit, list):
            crit = []

        if not isinstance(rec, list):
            rec = []

        combined_items = crit + rec

        canonical_ratio = self._canonical_ratio(
            combined_items
        )

        ppe_supported_ratio = (
            self._ppe_supported_by_chunks(
                combined_items,
                chunks,
            )
        )

        task_in_manual = (
            task in self.structured_rules
            or self._task_appears_in_manual(task)
        )

        try:
            llm_reported = float(
                data.get(
                    "confidence",
                    0.0,
                )
            )
        except (TypeError, ValueError):
            llm_reported = 0.0

        data["confidence"] = self._computed_confidence(
            llm_reported=llm_reported,
            citation_verified=citation_valid,
            task_in_manual=task_in_manual,
            canonical_ratio=canonical_ratio,
            ppe_supported_ratio=ppe_supported_ratio,
            has_chunks=bool(chunks),
        )

        if not citation_valid:
            data["citation"] = ""

        data["critical_ppe"] = crit
        data["recommended_ppe"] = rec

        LOG.info(
            "LLM extracted PPE for '%s' "
            "(computed confidence=%.2f)",
            task,
            data["confidence"],
        )

        return data

    def _task_appears_in_manual(
        self,
        task: str,
    ) -> bool:
        if not self.raw_text:
            return False

        normalized_task = task.replace(
            "_",
            " ",
        ).strip().lower()

        if not normalized_task:
            return False

        normalized_manual = re.sub(
            r"[\s\-_]+",
            " ",
            self.raw_text.lower(),
        )

        return normalized_task in normalized_manual