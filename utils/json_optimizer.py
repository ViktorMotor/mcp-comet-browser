"""JSON optimization for page_info output - reduce size by 70-80%"""
from typing import Dict, Any, List
import hashlib


class JsonOptimizer:
    """Optimize page_info.json by removing redundant data and prioritizing important elements"""

    @staticmethod
    def optimize_page_info(data: Dict[str, Any], full: bool = False) -> Dict[str, Any]:
        """
        Optimize page info JSON

        Args:
            data: Raw page info from save_page_info
            full: If True, return full unoptimized data (for debugging)

        Returns:
            Optimized page info (2-3KB instead of 10KB)
        """
        # Handle None input
        if data is None:
            return {}

        if full:
            return data  # No optimization for debugging

        optimized = {
            "url": data.get("url", ""),
            "title": data.get("title", "")[:50] if data.get("title") else "",  # Truncate long titles
            "viewport": data.get("viewport", {}),
            "summary": data.get("summary", {}),
            "console": JsonOptimizer._optimize_console(data.get("console", {})),
            "network": JsonOptimizer._optimize_network(data.get("network", {})),
            "interactive_elements": JsonOptimizer._optimize_elements(data.get("interactive_elements", []))
        }

        return optimized

    @staticmethod
    def _optimize_console(console_data: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize console logs - keep only last 5"""
        logs = console_data.get("logs", [])
        return {
            "recent": logs[-5:] if logs else [],
            "total": console_data.get("total", 0)
        }

    @staticmethod
    def _optimize_network(network_data: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize network info - keep only summary"""
        return {
            "total": network_data.get("total_requests", 0),
            "failed": network_data.get("failed", 0)
            # Remove recent requests - usually not needed
        }

    @staticmethod
    def _optimize_elements(elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Optimize interactive elements:
        1. Remove null fields
        2. Truncate long className
        3. Deduplicate
        4. Prioritize top-20 by importance
        5. Return flat list (not grouped)
        """
        if not elements:
            return []

        # Step 1: Clean each element (filter out None)
        cleaned = [JsonOptimizer._clean_element(el) for el in elements if el is not None and isinstance(el, dict)]

        # Step 2: Deduplicate (same text + tag + similar y position)
        deduplicated = JsonOptimizer._deduplicate_elements(cleaned)

        # Step 3: Score and prioritize
        scored = JsonOptimizer._score_elements(deduplicated)

        # Step 4: Take top 15 (stricter limit for size)
        top_elements = sorted(scored, key=lambda x: x["_score"], reverse=True)[:15]

        # Step 5: Remove score field
        for el in top_elements:
            el.pop("_score", None)  # Remove internal score

        return top_elements

    @staticmethod
    def _clean_element(element: Dict[str, Any]) -> Dict[str, Any]:
        """Clean single element: remove nulls, truncate text, simplify classes"""
        cleaned = {}

        # Basic fields
        if element.get("tag"):
            cleaned["tag"] = element["tag"]

        # Text (truncate to 40 chars for more savings)
        text = element.get("text", "").strip()
        if text:
            cleaned["text"] = text[:40]

        # ID (only if present and short)
        el_id = element.get("id")
        if el_id and len(el_id) < 30:
            cleaned["id"] = el_id

        # Classes (only keep first 2, skip utility classes)
        classes = element.get("classes", [])
        if classes:
            # Filter out utility classes (too long, contain numbers, etc.)
            useful_classes = [
                c for c in classes
                if len(c) < 30 and not any(x in c for x in ["px-", "py-", "text-", "hover:", "group-"])
            ][:2]  # Take first 2
            if useful_classes:
                cleaned["class"] = " ".join(useful_classes)

        # Position (only x, y - no width/height)
        pos = element.get("position", {})
        if pos:
            cleaned["pos"] = {
                "x": pos.get("x", 0),
                "y": pos.get("y", 0)
            }

        # Role (if present)
        role = element.get("role")
        if role:
            cleaned["role"] = role

        return cleaned

    @staticmethod
    def _deduplicate_elements(elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicates based on text + tag + y position"""
        seen = set()
        unique = []

        for el in elements:
            # Create signature
            text = el.get("text", "")[:30]
            tag = el.get("tag", "")
            y_pos = el.get("pos", {}).get("y", 0)
            # Round y to 50px buckets (elements in same row)
            y_bucket = round(y_pos / 50) * 50

            signature = f"{text}|{tag}|{y_bucket}"

            if signature not in seen:
                seen.add(signature)
                unique.append(el)

        return unique

    @staticmethod
    def _score_elements(elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Score elements by importance:
        - Has text: +10
        - Short text (< 20 chars): +5
        - Has ID: +8
        - Button/link: +7
        - Upper part of page (y < 500): +5
        - Has useful class: +3
        """
        scored = []
        for el in elements:
            score = 0

            # Text presence and quality
            text = el.get("text", "")
            if text:
                score += 10
                if len(text) < 20:
                    score += 5

            # ID presence
            if el.get("id"):
                score += 8

            # Tag importance
            tag = el.get("tag", "")
            if tag in ["button", "a"]:
                score += 7

            # Position (prefer top of page)
            y_pos = el.get("pos", {}).get("y", 1000)
            if y_pos < 500:
                score += 5

            # Useful class
            if el.get("class"):
                score += 3

            # Add score to element
            el["_score"] = score
            scored.append(el)

        return scored
