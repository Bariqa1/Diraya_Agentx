import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

LOG = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANUAL_PATH = ROOT / "rules" / "safety_manual.txt"
DEFAULT_CACHE_PATH = ROOT / "data" / "manual_rules.json"

TASK_BLOCK = re.compile(
    r"Task\s*:\s*(?P<task>[A-Za-z0-9_\- ]+?)"
    r"\s+Required\s*PPE\s*:\s*(?P<required>[^\n]+?)"
    r"\s+Recommended\s*PPE\s*:\s*(?P<recommended>[^\n]+)",
    re.IGNORECASE,
)

TASK_HEADER = re.compile(r"\bTask\s*:\s*([A-Za-z0-9_\- ]+)", re.IGNORECASE)

MD_FENCE = re.compile(r"^```(?:json)?\s*(.*?)\s*```\s*$", re.DOTALL | re.IGNORECASE)

EXTRACTION_PROMPT = """Extract PPE requirements and aliases from the safety manual excerpts below.

EXCERPTS:
{excerpts}

Return ONLY valid JSON in this exact schema:
{{
  "tasks": {{
    "task_name_snake_case": {{
      "critical_ppe": ["item1"],
      "recommended_ppe": ["item2"],
      "citation": "verbatim short quote from the excerpt"
    }}
  }},
  "aliases": {{
    "task_name_snake_case": ["synonym1", "synonym2"]
  }}
}}

Rules:
- Use canonical names: Helmet, Gloves, Face Shield, Safety Shoes, Safety Glasses, Coverall, Safety Harness, Safety Vest, Ear Protectors, Mask.
- Only include tasks present in the excerpts.
- Do not invent items.
- citation: exact short substring from the excerpt (10-120 chars).
- aliases: at most 3 common alternates per task.
"""

KNOWN_PPE = (
    "Helmet", "Gloves", "Face Shield", "Safety Shoes", "Safety Glasses",
    "Coverall", "Safety Harness", "Safety Vest", "Ear Protectors", "Mask",
)

BASE_MINIMUM_CRITICAL = ("Helmet", "Safety Shoes", "Safety Vest")

STOPWORDS = {"task", "the", "and", "of", "in", "on", "at", "a", "an", "with"}

MAX_LLM_EXCERPT_CHARS = 8000


def normalize_task(task: str) -> str:
    return re.sub(r"[\s\-]+", "_", (task or "").strip().lower()).strip("_")


def _tokens(name: str) -> set:
    return {
        t for t in re.split(r"[_\s\-]+", name.lower())
        if t and t not in STOPWORDS
    }


class ManualRAGError(Exception):
    pass


class ManualRules:
    def __init__(
        self,
        manual_path: Path = DEFAULT_MANUAL_PATH,
        cache_path: Path = DEFAULT_CACHE_PATH,
        api_key: Optional[str] = None,
        llm_model: Optional[str] = None,
        gemini_client=None,
    ):
        self.manual_path = Path(manual_path)
        self.cache_path = Path(cache_path)
        self.api_key = api_key
        self.llm_model = llm_model or os.getenv("GEMINI_MODEL")
        self.gemini_client = gemini_client
        self.rules: Dict[str, dict] = {}
        self.aliases: Dict[str, str] = {}

        self._load_or_build()
        self._rebuild_alias_index()
        self._log_health()

    def _load_or_build(self) -> None:
        if self._cache_is_fresh() and self._load_cache():
            return

        if not self.manual_path.is_file():
            LOG.warning("Manual not found: %s", self.manual_path)
            return

        text = self.manual_path.read_text(encoding="utf-8")

        parsed = self._parse_structured(text)
        LOG.info("Parser extracted %d tasks", len(parsed))

        missing_tasks = self._find_missing_tasks(text, parsed)
        excerpts = self._select_excerpts(text, missing_tasks)

        LOG.info("LLM pass: %d missing tasks, %d chars",
                 len(missing_tasks), len(excerpts))
        llm_rules, aliases_from_llm = self._llm_extract(excerpts)

        for task, rule in llm_rules.items():
            parsed.setdefault(task, rule)

        self.rules = parsed
        self._apply_llm_aliases(aliases_from_llm)

        if self.rules:
            self._write_cache()

    def _select_excerpts(self, text: str, missing_tasks: List[str]) -> str:
        if missing_tasks:
            excerpts = self._excerpts_for(text, missing_tasks)
            if excerpts:
                return excerpts
        return text[:MAX_LLM_EXCERPT_CHARS]

    def _load_cache(self) -> bool:
        try:
            raw = json.loads(self.cache_path.read_text(encoding="utf-8"))
        except Exception as exc:
            LOG.warning("Cache load failed: %s", exc)
            return False

        if isinstance(raw, dict) and "tasks" in raw:
            tasks = raw.get("tasks", {})
            self.aliases = {
                normalize_task(k): normalize_task(v)
                for k, v in raw.get("aliases", {}).items()
            }
        else:
            tasks = raw

        self.rules = {
            normalize_task(k): self._normalize_rule(v)
            for k, v in tasks.items() if isinstance(v, dict)
        }
        LOG.info("Loaded %d rules, %d aliases from cache",
                 len(self.rules), len(self.aliases))
        return True

    @staticmethod
    def _normalize_rule(rule: dict) -> dict:
        normalized = dict(rule)
        normalized.setdefault("critical_ppe", [])
        normalized.setdefault("recommended_ppe", [])
        normalized.setdefault("citation", "")
        normalized.setdefault("source", "unknown")
        normalized.setdefault("confidence", 0.0)
        normalized.setdefault("requires_manual_review", True)
        normalized.setdefault("approved_by", None)
        normalized.setdefault("approved_at", None)
        return normalized

    def _cache_is_fresh(self) -> bool:
        if not self.manual_path.is_file() or not self.cache_path.is_file():
            return False
        try:
            return self.cache_path.stat().st_mtime >= self.manual_path.stat().st_mtime
        except Exception:
            return False

    def _write_cache(self) -> None:
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {"tasks": self.rules, "aliases": self.aliases}
            self.cache_path.write_text(
                json.dumps(payload, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            LOG.info("Cache written: %s", self.cache_path)
        except Exception as exc:
            LOG.warning("Cache write failed: %s", exc)

    @staticmethod
    def _parse_structured(text: str) -> Dict[str, dict]:
        rules = {}
        for match in TASK_BLOCK.finditer(text):
            task = normalize_task(match.group("task"))
            if not task:
                continue
            rules[task] = {
                "critical_ppe": ManualRules._split_list(match.group("required")),
                "recommended_ppe": ManualRules._split_list(match.group("recommended")),
                "citation": match.group(0).strip(),
                "source": "structured_parser",
                "confidence": 1.0,
                "requires_manual_review": False,
                "approved_by": "system_parser",
                "approved_at": time.time(),
            }
        return rules

    @staticmethod
    def _split_list(value: str) -> List[str]:
        return [p.strip() for p in re.split(r"[,;]", value) if p.strip()]

    @staticmethod
    def _find_missing_tasks(text: str, parsed: Dict[str, dict]) -> List[str]:
        seen = {normalize_task(m) for m in TASK_HEADER.findall(text)}
        return sorted(seen - set(parsed.keys()))

    @staticmethod
    def _excerpts_for(text: str, tasks: List[str]) -> str:
        if not tasks:
            return ""
        excerpts = []
        for task in tasks:
            for match in TASK_HEADER.finditer(text):
                if normalize_task(match.group(1)) != task:
                    continue
                start = match.start()
                end = min(start + 800, len(text))
                excerpts.append(text[start:end])
                break
        return "\n\n---\n\n".join(excerpts)

    def _get_client(self):
        if self.gemini_client is not None:
            return self.gemini_client
        try:
            from google import genai
            self.gemini_client = genai.Client(api_key=self.api_key)
            return self.gemini_client
        except Exception as exc:
            LOG.error("Client init failed: %s", exc)
            return None

    @staticmethod
    def _parse_json_response(text: Optional[str]) -> dict:
        if text is None:
            raise ManualRAGError("empty response from Gemini")
        cleaned = text.strip()
        match = MD_FENCE.match(cleaned)
        if match:
            cleaned = match.group(1).strip()
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise ManualRAGError(f"non-JSON response: {exc}") from exc
        if not isinstance(data, dict):
            raise ManualRAGError("response is not a JSON object")
        return data

    def _llm_extract(self, excerpts: str) -> Tuple[Dict[str, dict], Dict[str, List[str]]]:
        if not self.llm_model or not excerpts:
            return {}, {}

        client = self._get_client()
        if client is None:
            return {}, {}

        try:
            from google.genai import types
        except Exception as exc:
            LOG.warning("google.genai unavailable: %s", exc)
            return {}, {}

        prompt = EXTRACTION_PROMPT.format(excerpts=excerpts)
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
            LOG.error("LLM extraction failed: %s", exc)
            return {}, {}

        try:
            data = self._parse_json_response(response.text)
        except ManualRAGError as exc:
            LOG.error("LLM returned invalid JSON: %s", exc)
            return {}, {}

        tasks = data.get("tasks", {})
        aliases_raw = data.get("aliases", {})

        rules: Dict[str, dict] = {}
        if isinstance(tasks, dict):
            for raw_task, rule in tasks.items():
                if not isinstance(rule, dict):
                    continue
                task = normalize_task(raw_task)
                crit = [p for p in rule.get("critical_ppe", []) if isinstance(p, str)]
                rec = [p for p in rule.get("recommended_ppe", []) if isinstance(p, str)]
                if not crit and not rec:
                    continue
                citation = rule.get("citation", "")
                if not isinstance(citation, str):
                    citation = ""
                rules[task] = {
                    "critical_ppe": crit,
                    "recommended_ppe": rec,
                    "citation": citation.strip(),
                    "source": "llm_extraction",
                    "confidence": 0.75,
                    "requires_manual_review": True,
                    "approved_by": None,
                    "approved_at": None,
                }

        aliases: Dict[str, List[str]] = {}
        if isinstance(aliases_raw, dict):
            for raw_task, syns in aliases_raw.items():
                task = normalize_task(raw_task)
                if not isinstance(syns, list):
                    continue
                clean = [normalize_task(s) for s in syns if isinstance(s, str)]
                clean = [s for s in clean if s and s != task][:5]
                if clean:
                    aliases[task] = clean

        return rules, aliases

    def _apply_llm_aliases(self, aliases: Dict[str, List[str]]) -> None:
        for canonical, syns in aliases.items():
            if canonical not in self.rules:
                continue
            for syn in syns:
                self.aliases[syn] = canonical

    def _rebuild_alias_index(self) -> None:
        for canonical in self.rules:
            self.aliases.setdefault(canonical, canonical)

    def _log_health(self) -> None:
        sources = {}
        pending = 0
        for rule in self.rules.values():
            src = rule.get("source", "unknown")
            sources[src] = sources.get(src, 0) + 1
            if rule.get("requires_manual_review") and not rule.get("approved_by"):
                pending += 1
        LOG.info("ManualRules ready: tasks=%d, aliases=%d, pending=%d, sources=%s",
                 len(self.rules), len(self.aliases), pending, sources)
        if not self.rules:
            LOG.warning("No rules loaded; conservative default will be used")

    def _resolve_task(self, task: str) -> Optional[str]:
        task_clean = normalize_task(task) or "unknown"

        if task_clean in self.rules:
            return task_clean

        if task_clean in self.aliases:
            return self.aliases[task_clean]

        query_tokens = _tokens(task_clean)
        if not query_tokens:
            return None

        best_key: Optional[str] = None
        best_score = 0.0
        for key in self.rules:
            key_tokens = _tokens(key)
            if not key_tokens:
                continue
            overlap = len(query_tokens & key_tokens)
            if overlap == 0:
                continue
            if key_tokens.issubset(query_tokens):
                score = 1.0
            else:
                score = overlap / len(key_tokens)
            if score > best_score:
                best_score = score
                best_key = key

        if best_key and best_score >= 0.5:
            LOG.info("Token-matched '%s' -> '%s' (score=%.2f)",
                     task_clean, best_key, best_score)
            return best_key

        return None

    def get_required_ppe(self, task: str) -> dict:
        resolved = self._resolve_task(task)

        if resolved:
            return self.rules[resolved]

        LOG.info("Task '%s' not resolvable; conservative default",
                 normalize_task(task))
        return {
            "critical_ppe": list(BASE_MINIMUM_CRITICAL),
            "recommended_ppe": [p for p in KNOWN_PPE if p not in BASE_MINIMUM_CRITICAL],
            "citation": "",
            "source": "conservative_default",
            "confidence": 0.2,
            "requires_manual_review": True,
            "approved_by": None,
            "approved_at": None,
        }

    def pending_review(self) -> List[str]:
        return [
            task for task, rule in self.rules.items()
            if rule.get("requires_manual_review") and not rule.get("approved_by")
        ]

    def approve(self, task: str, reviewer: str = "operator") -> bool:
        task_clean = normalize_task(task)
        if task_clean not in self.rules:
            LOG.warning("approve: unknown task '%s'", task_clean)
            return False
        rule = self.rules[task_clean]
        rule["requires_manual_review"] = False
        rule["approved_by"] = reviewer
        rule["approved_at"] = time.time()
        if rule.get("source", "").startswith("llm_"):
            rule["source"] = "llm_extraction_approved"
        self._write_cache()
        LOG.info("Approved '%s' by %s", task_clean, reviewer)
        return True

    def update(
        self,
        task: str,
        critical_ppe: List[str],
        recommended_ppe: List[str],
        citation: Optional[str] = None,
        reviewer: str = "operator",
    ) -> bool:
        task_clean = normalize_task(task)
        if task_clean not in self.rules:
            LOG.warning("update: unknown task '%s'", task_clean)
            return False

        rule = self.rules[task_clean]
        original_source = rule.get("source", "unknown")

        rule["critical_ppe"] = [p.strip() for p in critical_ppe if p and p.strip()]
        rule["recommended_ppe"] = [p.strip() for p in recommended_ppe if p and p.strip()]
        if citation is not None:
            rule["citation"] = citation.strip()
        rule["source"] = f"human_edited_from_{original_source}"
        rule["confidence"] = 1.0
        rule["requires_manual_review"] = False
        rule["approved_by"] = reviewer
        rule["approved_at"] = time.time()

        self._write_cache()
        LOG.info("Updated '%s' by %s", task_clean, reviewer)
        return True

    def add(
        self,
        task: str,
        critical_ppe: List[str],
        recommended_ppe: List[str],
        reviewer: str = "operator",
    ) -> bool:
        task_clean = normalize_task(task)
        if not task_clean:
            return False
        if task_clean in self.rules:
            LOG.warning("add: task '%s' already exists; use update", task_clean)
            return False

        self.rules[task_clean] = {
            "critical_ppe": [p.strip() for p in critical_ppe if p and p.strip()],
            "recommended_ppe": [p.strip() for p in recommended_ppe if p and p.strip()],
            "citation": "",
            "source": "human_created",
            "confidence": 1.0,
            "requires_manual_review": False,
            "approved_by": reviewer,
            "approved_at": time.time(),
        }
        self.aliases.setdefault(task_clean, task_clean)
        self._write_cache()
        LOG.info("Added '%s' by %s", task_clean, reviewer)
        return True

    def approve_all(self, reviewer: str = "operator") -> int:
        count = 0
        for task in list(self.rules.keys()):
            if self.approve(task, reviewer):
                count += 1
        return count