"""Entra-backed auth for Azure-hosted OpenAI, injected into the tvt.ai modules."""

from tvt.azure import entra


def openai_auth_headers():
    """Bearer auth headers for the Azure OpenAI data plane."""
    return {"Authorization": f"Bearer {entra.bearer_token(entra.COGNITIVE_SCOPE)}"}
