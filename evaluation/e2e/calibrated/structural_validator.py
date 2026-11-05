"""Layer A: Deterministic Structural & Evidence-Reference Validator (Revision 2.4)."""

import json
import re
import unicodedata
from typing import Dict, List, Optional, Tuple, Any
from pydantic import ValidationError
from .models import AnchorState, RawJudgeStatementVerdict, EvaluatorExecutionTrace, RetryEvent

class StructuralValidator:
    """Deterministic structural and citation integrity validator with audit trajectory preservation."""

    @staticmethod
    def normalize_chunk_id(cid: Optional[str]) -> str:
        if not cid:
            return ""
        cid = str(cid).strip()
        # Strip brackets: [E1] -> E1
        if cid.startswith("[") and cid.endswith("]"):
            cid = cid[1:-1].strip()
        # Handle "e.g. E7", "e.g., E7", or "Chunk E7"
        if "e.g." in cid.lower() or "chunk" in cid.lower():
            match = re.search(r"\b(E\d+|disease_chunk_\d+|drug_chunk_\d+|\d{4,6})\b", cid, re.IGNORECASE)
            if match:
                res = match.group(1)
                return res.upper() if res.lower().startswith("e") else res
        return cid

    @classmethod
    def validate_raw_json(cls, raw_text: str) -> Tuple[Optional[RawJudgeStatementVerdict], Optional[str]]:
        """Parses and validates raw LLM text into RawJudgeStatementVerdict envelope."""
        if not raw_text or not raw_text.strip():
            return None, "Empty response from judge"
        
        text = raw_text.strip()
        # Extract markdown json block if present
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            if end != -1:
                text = text[start:end].strip()
        elif "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            if end != -1:
                text = text[start:end].strip()

        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            # Fallback regex search for json object
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(0))
                except Exception:
                    return None, f"JSONDecodeError: {str(e)}"
            else:
                return None, f"JSONDecodeError: {str(e)}"

        try:
            envelope = RawJudgeStatementVerdict.model_validate(data)
            return envelope, None
        except ValidationError as e:
            return None, f"ValidationError: {str(e)}"

    @classmethod
    def parse_context_chunks(cls, evidence_blocks: str) -> List[Dict[str, str]]:
        """Robustly parses evidence blocks into a list of chunk dicts without merging or truncation."""
        if not evidence_blocks or not evidence_blocks.strip():
            return []
        
        # Pattern to match chunk boundary at start of string or on a new line
        pattern = re.compile(r"(?:^|\n)\s*(\[([A-Za-z0-9_.-]+)\][^\n]*)")
        matches = list(pattern.finditer(evidence_blocks))
        if not matches:
            # Fallback if no bracketed chunk headers: split by double-newline or whole text
            chunks = [c.strip() for c in evidence_blocks.split("\n\n") if c.strip()]
            if not chunks:
                chunks = [evidence_blocks.strip()]
            return [{"chunk_id": f"E{i+1}", "text": c} for i, c in enumerate(chunks)]
        
        chunks = []
        for i, match in enumerate(matches):
            start = match.start()
            end = matches[i+1].start() if i + 1 < len(matches) else len(evidence_blocks)
            raw_chunk_text = evidence_blocks[start:end].strip()
            chunk_id = match.group(2).strip()
            chunks.append({
                "chunk_id": chunk_id,
                "text": raw_chunk_text
            })
        return chunks

    @classmethod
    def extract_verifiable_source_span(cls, chunk_text: str, cited_quote: str) -> Tuple[bool, Optional[str]]:
        """Identifies exact verifiable source span from chunk text, resolving formatting/punctuation/ellipsis artifacts.
        
        Strict provenance rules:
        - Rejects unsupported or fabricated spans (no fuzzy semantic matching).
        - Unicode NFKC normalization.
        - Strips surrounding quotes, backticks, brackets, and leading/trailing ellipsis (... or …).
        - Resolves harmless intra-chunk newline/whitespace breaks.
        - For compound pipe-delimited segment extractions (e.g. structured FDA field exports),
          verifies all segments exist verbatim in chunk text.
        """
        if not cited_quote or not chunk_text:
            return False, None

        q_norm = unicodedata.normalize("NFKC", str(cited_quote)).strip()
        c_norm = unicodedata.normalize("NFKC", str(chunk_text))

        # Strip surrounding quotes, backticks, brackets, guillemets
        q_clean = q_norm.strip(" \t\n\r\f\v\"'“”‘’`«»[]")
        # Strip leading and trailing ellipsis
        q_clean = re.sub(r"^[\.\u2026\s]{2,}\s*", "", q_clean)
        q_clean = re.sub(r"\s*[\.\u2026\s]{2,}$", "", q_clean)
        q_clean = q_clean.strip(" \t\n\r\f\v\"'“”‘’`«»[]")

        if not q_clean or len(q_clean) < 3:
            return False, None

        # 1. Exact verbatim match in chunk
        if q_clean in c_norm:
            return True, q_clean

        # 2. Whitespace-collapsed match
        q_ws = " ".join(q_clean.split())
        c_ws = " ".join(c_norm.split())
        if q_ws in c_ws:
            tokens = [re.escape(t) for t in q_ws.split()]
            pattern = r"\s+".join(tokens)
            match = re.search(pattern, c_norm, re.IGNORECASE)
            if match:
                return True, match.group(0)
            return True, q_ws

        # 3. Pipe-delimited segment extractions (e.g. [ACETAMINOPHEN; ...] | Active ingredients: ACETAMINOPHEN;)
        if "|" in q_clean:
            raw_segments = [s.strip(" \t\n\r\f\v\"';,") for s in q_clean.split("|")]
            cleaned_segments = []
            for s in raw_segments:
                s_clean = re.sub(r"^[\.\u2026\s]{2,}\s*", "", s)
                s_clean = re.sub(r"\s*[\.\u2026\s]{2,}$", "", s_clean).strip(" \t\n\r\f\v\"'“”‘’`«»[];,")
                if len(s_clean) >= 3:
                    cleaned_segments.append(s_clean)
            if cleaned_segments:
                matching_segments = []
                for s in cleaned_segments:
                    s_ws = " ".join(s.split())
                    if s in c_norm or s_ws in c_ws:
                        matching_segments.append(s)
                if len(matching_segments) == len(cleaned_segments):
                    return True, " | ".join(matching_segments)

        # 4. Trailing punctuation normalization (if quote ended with period/semicolon absent in header)
        q_stripped_punct = q_clean.rstrip(".,;:")
        if len(q_stripped_punct) >= 5:
            if q_stripped_punct in c_norm:
                return True, q_stripped_punct
            q_sp_ws = " ".join(q_stripped_punct.split())
            if q_sp_ws in c_ws:
                return True, q_sp_ws

        return False, None

    @classmethod
    def check_exception_consistency(cls, statement: str, cited_text: str) -> Tuple[bool, Optional[str]]:
        """Verifies clinical exception consistency between candidate statement and cited evidence text.
        
        Rules:
        - If cited text has an explicit limiting exception clause (except, excluding, unless, etc.):
          1. Statement preserving exception -> Valid.
          2. Statement dropping exception and overstating indication -> Contradiction / Unsupported.
          3. Statement altering the scope/condition of the exception -> Contradiction / Unsupported.
          4. Statement treating narrow exception as universal prohibition -> Contradiction / Unsupported.
        """
        exception_patterns = [
            r"\b(?:except|with the exception of|excluding|other than|unless|not including)\s+([^,.;\n]+)",
        ]
        found_exceptions = []
        for pat in exception_patterns:
            for match in re.finditer(pat, cited_text, re.IGNORECASE):
                found_exceptions.append((match.group(0).strip(), match.group(1).strip()))

        if not found_exceptions:
            return False, None

        for full_clause, target in found_exceptions:
            stop_words = {"the", "a", "an", "in", "of", "during", "phase", "patients", "with", "and", "or"}
            target_tokens = [w.lower() for w in re.findall(r"\b[A-Za-z0-9_-]+\b", target) if w.lower() not in stop_words and len(w) > 3]
            stmt_lower = statement.lower()
            has_exception_marker = any(m in stmt_lower for m in ["except", "excluding", "with the exception", "other than", "unless", "not including"])
            is_prohibition = any(p in stmt_lower for p in ["contraindicated for all", "not indicated for all", "is contraindicated for", "not indicated for", "not suitable for"])

            if is_prohibition:
                matching_tokens = [t for t in target_tokens if t in stmt_lower]
                if len(matching_tokens) >= max(1, len(target_tokens) // 2):
                    # Statement accurately asserts that the excepted condition is excluded/not indicated
                    continue
                else:
                    return True, f"Statement treats narrow exception as universal prohibition: {statement}"

            if not has_exception_marker:
                return True, f"Evidence contains explicit exception \"{full_clause}\" which is omitted in statement, overstating evidence."
            else:
                matching_tokens = [t for t in target_tokens if t in stmt_lower]
                if len(matching_tokens) < max(1, len(target_tokens) // 2):
                    return True, f"Statement changes scope of exception from \"{target}\"."

        return False, None

    @classmethod
    def verify_citations(
        cls,
        envelope: RawJudgeStatementVerdict,
        context_chunks: List[Dict[str, str]],
        statement_text: Optional[str] = None
    ) -> Tuple[AnchorState, Optional[str]]:
        """Verifies chunk existence, context-aware absence consistency, and verbatim quotation authenticity."""
        # Index chunks by raw id, normalized id, E{idx+1}, and embedded id=...
        chunk_map: Dict[str, str] = {}
        for idx, chunk in enumerate(context_chunks):
            raw_id = chunk.get("chunk_id", f"E{idx+1}").strip()
            norm_id = cls.normalize_chunk_id(raw_id)
            text = chunk.get("text", chunk.get("content", ""))
            chunk_map[raw_id] = text
            chunk_map[norm_id] = text
            chunk_map[f"[{norm_id}]"] = text
            chunk_map[f"E{idx+1}"] = text
            chunk_map[f"[E{idx+1}]"] = text

            # Extract embedded id=... from the first line (e.g. id=disease_chunk_416 or id=29609)
            first_line = text.splitlines()[0] if text else ""
            id_match = re.search(r"\bid=([A-Za-z0-9_-]+)", first_line)
            if id_match:
                emb_id = id_match.group(1).strip()
                chunk_map[emb_id] = text
                chunk_map[f"[{emb_id}]"] = text
                chunk_map[f"id={emb_id}"] = text

        cited_id = envelope.cited_chunk_id
        cited_quote = envelope.cited_quote

        if not cited_id and envelope.verdict == 0:
            return AnchorState.VALID_BUT_IRRELEVANT_ANCHOR, None

        if envelope.verdict == 1 and not envelope.is_absence_statement:
            if not cited_id or not cited_id.strip():
                return AnchorState.MISSING_REQUIRED_ANCHOR, "Verdict 1 requires a cited_chunk_id anchor"
            if not cited_quote or not cited_quote.strip():
                return AnchorState.MISSING_REQUIRED_ANCHOR, "Verdict 1 requires a cited_quote anchor"

        # Resolve chunk text
        matching_text = None
        if cited_id:
            norm_cited_id = cls.normalize_chunk_id(cited_id)
            matching_text = chunk_map.get(norm_cited_id, chunk_map.get(cited_id))

            # Fallback search for chunk identifiers in cited_id e.g. "e.g. E7", "[E4], [E5]"
            if not matching_text:
                extracted_ids = re.findall(r"E\d+|disease_chunk_\d+|drug_chunk_\d+|\b\d{4,6}\b", cited_id, re.IGNORECASE)
                valid_extracted = [cid for cid in extracted_ids if cid in chunk_map or cid.upper() in chunk_map or f"[{cid}]" in chunk_map or cls.normalize_chunk_id(cid) in chunk_map]
                if valid_extracted:
                    primary_id = valid_extracted[0]
                    matching_text = chunk_map.get(cls.normalize_chunk_id(primary_id), chunk_map.get(primary_id, chunk_map.get(primary_id.upper())))

        # If matching chunk and quote are present, verify source span
        has_valid_quote = False
        valid_source_span = None
        if matching_text and cited_quote and cited_quote.strip():
            ok_span, span = cls.extract_verifiable_source_span(matching_text, cited_quote)
            if ok_span:
                has_valid_quote = True
                valid_source_span = span

        if has_valid_quote:
            if envelope.verdict == 1:
                # Check exception consistency if statement text is provided
                if statement_text:
                    is_exc_viol, exc_reason = cls.check_exception_consistency(statement_text, cited_quote)
                    if is_exc_viol:
                        return AnchorState.VALID_CONTRADICTING_ANCHOR, f"Exception inconsistency: {exc_reason}"
                return AnchorState.VALID_SUPPORTING_ANCHOR, None
            else:
                return AnchorState.VALID_CONTRADICTING_ANCHOR, None

        # Check for verified context absence
        if envelope.is_absence_statement and envelope.verdict == 1:
            from .absence_scanner import AbsenceScanner
            if statement_text:
                is_valid_absence, absence_err = AbsenceScanner.verify_evidence_absence(statement_text, context_chunks)
                if not is_valid_absence:
                    return AnchorState.MISSING_REQUIRED_ANCHOR, (
                        f"Verdict 1 marked as absence statement, but context absence verification failed: {absence_err}"
                    )
            return AnchorState.VERIFIED_CONTEXT_ABSENCE, None

        # If not verified, classify exact failure
        if not matching_text:
            return AnchorState.INVALID_CHUNK_ID, f"Cited chunk '{cited_id}' not found in retrieved context"
        if cited_quote and cited_quote.strip():
            return AnchorState.INVALID_QUOTATION, f"Cited quote '{cited_quote[:60]}...' not found verbatim in chunk '{cited_id}'"

        if envelope.verdict == 1:
            return AnchorState.MISSING_REQUIRED_ANCHOR, "Verdict 1 requires a valid cited_quote anchor"
        else:
            return AnchorState.VALID_BUT_IRRELEVANT_ANCHOR, None

    @classmethod
    def build_format_repair_prompt(cls, raw_output: str, error_msg: str) -> str:
        """Constructs targeted format repair prompt for retry."""
        return (
            f"Your previous response had a structural/citation validation failure:\n"
            f"ERROR: {error_msg}\n\n"
            f"PREVIOUS OUTPUT:\n{raw_output}\n\n"
            f"Please output a corrected, strictly conforming JSON response with keys:\n"
            f"- 'verdict': 1 (Supported) or 0 (Unsupported)\n"
            f"- 'reason': concise clinical rationale\n"
            f"- 'cited_chunk_id': existing chunk identifier\n"
            f"- 'cited_quote': verbatim quote matching chunk text exactly\n"
            f"- 'is_absence_statement': boolean\n"
            f"Output ONLY valid JSON."
        )
