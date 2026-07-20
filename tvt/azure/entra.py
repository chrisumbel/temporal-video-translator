"""Shared Microsoft Entra ID auth: one credential, tokens per scope.

DefaultAzureCredential resolves to the service principal env vars in the
cluster and the az CLI login locally. Data-plane calls need the matching
RBAC role (Cognitive Services User, Storage Blob Data Contributor).
"""

import logging

from azure.identity import DefaultAzureCredential

COGNITIVE_SCOPE = "https://cognitiveservices.azure.com/.default"
ARM_SCOPE = "https://management.azure.com/.default"

logger = logging.getLogger(__name__)

shared_credential = None


def credential():
    """The process-wide DefaultAzureCredential instance."""
    global shared_credential
    if shared_credential is None:
        logger.info("Creating DefaultAzureCredential")
        shared_credential = DefaultAzureCredential()
    return shared_credential


def bearer_token(scope):
    """An Entra access token for scope; azure-identity handles caching/refresh."""
    return credential().get_token(scope).token
