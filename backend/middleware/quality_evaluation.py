"""
Quality Evaluation Middleware for Progressive Analysis

This middleware follows Microsoft Agent Framework patterns to detect
confidence scores and terminate execution when threshold is met.
"""

import os
import re
from typing import Awaitable, Callable
from agent_framework import AgentMiddleware, AgentRunContext


class ConfidenceTerminationMiddleware(AgentMiddleware):
    """Middleware that terminates execution when confidence threshold is met"""

    def __init__(self):
        # Get quality threshold from environment variable
        self.quality_threshold = int(os.getenv("QUALITY_THRESHOLD", "80"))
        # Track if we should terminate future requests
        self.should_terminate = False
        self.last_confidence_score = 0

    async def process(
        self,
        context: AgentRunContext,
        next: Callable[[AgentRunContext], Awaitable[None]],
    ) -> None:
        print(
            f"[ConfidenceMiddleware] Processing request with threshold: {self.quality_threshold}"
        )

        # Check if we should terminate BEFORE processing (like Microsoft's example)
        if self.should_terminate:
            print(
                f"[ConfidenceMiddleware] Terminating request due to previous high confidence ({self.last_confidence_score} >= {self.quality_threshold})"
            )
            context.terminate = True
            return  # Don't call next() at all

        # Process the agent normally first
        await next(context)

        # After agent processing, check confidence in response
        if context.result:
            # For streaming responses, we need to check the accumulated response
            # This is a simplified approach - in practice, streaming detection would need
            # special handling in the agent framework level
            response_text = self._extract_response_text(context.result)
            if response_text:
                confidence_score = self._extract_confidence_score(response_text)
                if confidence_score > 0:
                    print(
                        f"[ConfidenceMiddleware] Confidence detected: {confidence_score}/100"
                    )
                    self.last_confidence_score = confidence_score

                    # Mark for termination if confidence meets threshold
                    if confidence_score >= self.quality_threshold:
                        print(
                            f"[ConfidenceMiddleware] High confidence ({confidence_score} >= {self.quality_threshold}) detected! Will terminate future requests."
                        )
                        self.should_terminate = True
                        context.terminate = True

        print("[ConfidenceMiddleware] Request processed")

    def _extract_response_text(self, result) -> str:
        """Extract text from agent response result"""
        try:
            # Handle different result types
            if hasattr(result, "text"):
                return result.text or ""
            elif hasattr(result, "messages"):
                # Extract text from messages
                for message in result.messages:
                    if hasattr(message, "text") and message.text:
                        return message.text
            return ""
        except Exception:
            return ""

    def _extract_confidence_score(self, text: str) -> int:
        """Extract confidence score from agent response"""
        confidence_match = re.search(r"\[CONFIDENCE:\s*(\d+)\]", text, re.IGNORECASE)
        if confidence_match:
            return int(confidence_match.group(1))
        return 0
