import os

# Must be set before `app.config.get_settings()` is first called by any import below.
os.environ.setdefault("APP_ENV", "local")
os.environ.setdefault("DISABLE_AUTH", "true")
os.environ.setdefault("AZURE_OPENAI_ENDPOINT", "https://example-test.openai.azure.com/")
os.environ.setdefault("AZURE_SEARCH_ENDPOINT", "https://example-test.search.windows.net")
os.environ.setdefault("AZURE_STORAGE_ACCOUNT_URL", "https://exampletest.blob.core.windows.net")
