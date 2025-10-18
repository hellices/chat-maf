"""
Confidence Score Extraction Tool

Utility for extracting confidence scores from agent responses in real-time
during streaming or from completed responses.
"""

import re


def extract_confidence_score(text: str) -> int:
    """
    Extract confidence score from agent response text

    Args:
        text: Response text that may contain [CONFIDENCE: XX] pattern

    Returns:
        int: Confidence score (0-100), or 0 if not found
    """
    confidence_match = re.search(r"\[CONFIDENCE:\s*(\d+)\]", text, re.IGNORECASE)
    if confidence_match:
        score = int(confidence_match.group(1))
        return min(100, max(0, score))  # Ensure score is between 0-100
    return 0  # Default to 0 if no confidence found


def detect_confidence_in_stream(accumulated_text: str) -> tuple[bool, int]:
    """
    Check if confidence score is present in streaming text

    Args:
        accumulated_text: Text accumulated from streaming chunks

    Returns:
        tuple: (confidence_detected: bool, confidence_score: int)
    """
    if "[CONFIDENCE:" in accumulated_text.upper():
        score = extract_confidence_score(accumulated_text)
        return (score > 0, score)
    return (False, 0)
