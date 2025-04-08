# This contains the data classes both modules need

# shared_models.py
from dataclasses import dataclass

@dataclass
class ClaudePromptInput:
    prompt: str
    model: str = "claude-3-7-sonnet-20250219"
    max_tokens: int = 1024


@dataclass
class ClaudeResponse:
    text: str
    request_id: str = ""