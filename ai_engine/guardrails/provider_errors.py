"""Fixed public error codes; never carry upstream exception text or response."""
CODES = frozenset({"provider_disabled", "provider_configuration", "provider_timeout", "provider_auth",
                   "provider_rate_limit", "provider_http", "provider_network", "provider_invalid_output", "provider_limit"})


class SafeProviderError(Exception):
    def __init__(self, code):
        self.code = code if code in CODES else "provider_http"
        super().__init__(self.code)
