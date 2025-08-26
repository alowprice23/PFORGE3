from __future__ import annotations
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import httpx
import logging

logger = logging.getLogger(__name__)

# Define the types of errors that are typically transient and worth retrying.
# This includes network errors and common HTTP status codes for rate limits
# or server-side issues.
TRANSIENT_ERRORS = (
    httpx.TimeoutException,
    httpx.NetworkError,
)

def is_retryable_http_status(e: BaseException) -> bool:
    """
    Determines if an httpx.HTTPStatusError is retryable.
    We retry on 5xx server errors and 429 Too Many Requests.
    """
    return (
        isinstance(e, httpx.HTTPStatusError) and
        (e.response.status_code >= 500 or e.response.status_code == 429)
    )

# The combined condition for retrying
retry_condition = retry_if_exception_type(TRANSIENT_ERRORS) | is_retryable_http_status

def retry_llm(
    max_tries: int = 3,
    initial_wait_s: float = 1.0,
    max_wait_s: float = 10.0
):
    """
    A decorator that adds exponential backoff retry logic to LLM API calls.

    It is configured to retry on specific, transient network and HTTP errors.

    Args:
        max_tries: The maximum number of times to attempt the call.
        initial_wait_s: The initial wait time in seconds for the backoff.
        max_wait_s: The maximum wait time between retries.

    Returns:
        A decorator that can be applied to an async function.
    """
    return retry(
        stop=stop_after_attempt(max_tries),
        wait=wait_exponential(multiplier=initial_wait_s, max=max_wait_s),
        retry=retry_condition,
        before_sleep=lambda retry_state: logger.warning(
            f"Retrying LLM call (attempt {retry_state.attempt_number}) after error: {retry_state.outcome.exception()}"
        )
    )
