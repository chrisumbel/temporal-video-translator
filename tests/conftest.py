"""Test setup: repo root on sys.path and dummy env so modules import without
real credentials. Set before any module import; load_dotenv never overrides
existing env, so tests stay hermetic even with a real .env present."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DUMMY_ENV = {
    "AZURE_SUBSCRIPTION_ID": "test-sub",
    "AZURE_RESOURCE_GROUP": "test-rg",
    "AZURE_LOCATION": "testus",
    "STORAGE_ACCOUNT_NAME": "teststorage",
    "STORAGE_CONTAINER": "json",
    "STORAGE_VIDEO_CONTAINER": "videos",
    "SCRATCH_SCREENSHOT_CONTAINER": "scratchscreenshots",
    "SCREENSHOT_CONTAINER": "screenshots",
    "PDF_CONTAINER": "pdf",
    "VIDEO_INDEXER_ACCOUNT_NAME": "test-vi",
    "VIDEO_INDEXER_ACCOUNT_ID": "test-vi-id",
    "TRANSLATOR_ACCOUNT_NAME": "test-translator",
    "TRANSLATOR_ENDPOINT": "https://translator.invalid",
    "OPENAI_ACCOUNT_NAME": "test-openai",
    "OPENAI_ENDPOINT": "https://openai.invalid",
    "OPENAI_DEPLOYMENT": "test-deployment",
    "API_KEY": "test-api-key",
}

for key, value in DUMMY_ENV.items():
    os.environ[key] = value
