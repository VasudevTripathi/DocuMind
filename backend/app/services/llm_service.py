import os
import json
import re
from typing import Dict, List, Any, Optional
from openai import OpenAI
from app.core.config import settings

# Cost control: Limit maximum words sent to LLM for cost-efficient analysis
MAX_LLM_INPUT_WORDS = 2500

class LLMServiceError(Exception):
    """Raised when LLM analysis fails."""
    pass

class LLMService:
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.OPENAI_API_KEY or os.environ.get("OPENAI_API_KEY")
        self.model = model or settings.LLM_MODEL or "gpt-4o-mini"
        self._client: Optional[OpenAI] = None

    @property
    def client(self) -> Optional[OpenAI]:
        if self._client is None and self.api_key:
            self._client = OpenAI(api_key=self.api_key)
        return self._client

    def prepare_representative_text(self, text: str, max_words: int = MAX_LLM_INPUT_WORDS) -> str:
        """
        Implements budget-conscious cost control by taking representative sections:
        - Opening sections / introduction
        - Middle context
        - Concluding section
        Without sending entire massive 200+ page documents to the API.
        """
        words = text.split()
        if len(words) <= max_words:
            return text

        # Budget allocation: 60% beginning, 20% middle, 20% end
        head_count = int(max_words * 0.6)
        mid_count = int(max_words * 0.2)
        tail_count = int(max_words * 0.2)

        mid_start = (len(words) // 2) - (mid_count // 2)
        mid_end = mid_start + mid_count

        head_part = " ".join(words[:head_count])
        mid_part = " ".join(words[mid_start:mid_end])
        tail_part = " ".join(words[-tail_count:])

        return f"{head_part}\n\n[... content truncated for cost efficiency ...]\n\n{mid_part}\n\n[... content truncated for cost efficiency ...]\n\n{tail_part}"

    def analyze_document(self, text: str) -> Dict[str, Any]:
        """
        Extracts summary, key findings, and named entities using OpenAI.
        If API key is missing or calls fail, falls back to rule-based heuristic extraction.
        """
        sample_text = self.prepare_representative_text(text)

        if not self.api_key:
            print("[LLMService] OPENAI_API_KEY not configured. Falling back to heuristic text extraction.")
            return self._heuristic_fallback(sample_text)

        try:
            client = self.client
            if not client:
                return self._heuristic_fallback(sample_text)

            prompt = (
                "You are an expert document analyst. Analyze the following document text and return ONLY a valid JSON object "
                "with this exact structure:\n"
                "{\n"
                '  "summary": "Concise 2-4 sentence executive summary of the document.",\n'
                '  "key_findings": [\n'
                '    {"text": "Key insight or critical takeaway 1", "priority": "high"},\n'
                '    {"text": "Key insight or critical takeaway 2", "priority": "medium"}\n'
                "  ],\n"
                '  "entities": [\n'
                '    {"name": "Entity Name", "type": "ORGANIZATION | PERSON | TECHNOLOGY | CONCEPT | LOCATION"}\n'
                "  ]\n"
                "}\n\n"
                "Do NOT include Markdown code fences or extra text, just raw JSON.\n\n"
                f"DOCUMENT TEXT:\n{sample_text}"
            )

            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a professional document analysis intelligence system. Output strictly valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=1000
            )

            raw_content = response.choices[0].message.content or ""
            parsed = self._clean_and_parse_json(raw_content)
            validated = self._validate_structure(parsed)
            return validated

        except Exception as e:
            print(f"[LLMService] OpenAI request failed ({e}). Employing fallback extraction.")
            return self._heuristic_fallback(sample_text)

    def _clean_and_parse_json(self, raw_content: str) -> Dict[str, Any]:
        """Cleans possible code fences and parses JSON safely."""
        cleaned = raw_content.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as err:
            # Try to match first { ... } block
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except Exception:
                    pass
            raise LLMServiceError(f"Failed to decode LLM JSON response: {err}")

    def _validate_structure(self, data: Any) -> Dict[str, Any]:
        """Ensures the returned JSON adheres to required schema."""
        if not isinstance(data, dict):
            raise LLMServiceError("LLM response root is not an object.")

        summary = str(data.get("summary", "")).strip()
        if not summary:
            summary = "Summary could not be generated."

        key_findings: List[Dict[str, str]] = []
        for item in data.get("key_findings", []):
            if isinstance(item, dict) and "text" in item:
                text_val = str(item.get("text", "")).strip()
                priority_val = str(item.get("priority", "medium")).lower()
                if priority_val not in ["high", "medium", "low"]:
                    priority_val = "medium"
                if text_val:
                    key_findings.append({
                        "text": text_val,
                        "priority": priority_val
                    })

        entities: List[Dict[str, str]] = []
        seen_entities = set()
        for item in data.get("entities", []):
            if isinstance(item, dict) and "name" in item:
                name_val = str(item.get("name", "")).strip()
                type_val = str(item.get("type", "CONCEPT")).strip().upper()
                if name_val and name_val.lower() not in seen_entities:
                    seen_entities.add(name_val.lower())
                    entities.append({
                        "name": name_val,
                        "type": type_val
                    })

        return {
            "summary": summary,
            "key_findings": key_findings,
            "entities": entities
        }

    def _heuristic_fallback(self, text: str) -> Dict[str, Any]:
        """
        Deterministic, rule-based fallback when LLM API is unavailable.
        Extracts lead sentences for summary, detects salient points, and extracts entities via regex.
        """
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        
        # Summary: First 2-3 substantive sentences
        lead_text = " ".join(paragraphs[:2]) if paragraphs else text
        sentences = re.split(r"(?<=[.!?])\s+", lead_text)
        summary = " ".join(sentences[:3]).strip() or "No summary available."

        # Key Findings: Look for bullet points or informative statements
        findings = []
        bullet_matches = re.findall(r"(?:^|\n)(?:[-*•]|\d+\.)\s*(.+)", text)
        for b in bullet_matches[:4]:
            cleaned_b = b.strip()
            if len(cleaned_b) > 15:
                findings.append({
                    "text": cleaned_b,
                    "priority": "high" if len(findings) == 0 else "medium"
                })

        if not findings and len(sentences) > 3:
            for s in sentences[3:7]:
                if len(s.strip()) > 20:
                    findings.append({
                        "text": s.strip(),
                        "priority": "medium"
                    })

        if not findings:
            findings.append({
                "text": "Document successfully ingested and indexed into system library.",
                "priority": "medium"
            })

        # Entities: Extract capitalized multi-word phrases and common technical/legal terms
        entity_patterns = re.findall(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b", text)
        entities = []
        seen = set()
        for ent in entity_patterns:
            ent_clean = ent.strip()
            if ent_clean.lower() not in seen and len(ent_clean) > 3:
                seen.add(ent_clean.lower())
                entities.append({
                    "name": ent_clean,
                    "type": "CONCEPT"
                })
            if len(entities) >= 6:
                break

        return {
            "summary": summary,
            "key_findings": findings,
            "entities": entities
        }

llm_service = LLMService()
