"""Talking to the LLM provider. Implemented once the provider is chosen (Phase 6)."""
from app import config


def complete_json(system: str, user: str) -> dict:
    """Send a system + user prompt and return the model's reply parsed as a JSON object."""
    raise RuntimeError(f"LLM_PROVIDER={config.LLM_PROVIDER} is not implemented yet.")
