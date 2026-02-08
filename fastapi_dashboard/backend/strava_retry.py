"""
Retry logic with exponential backoff for Strava API calls.
"""

import asyncio
import httpx
from typing import Callable, Optional, TypeVar, Any
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')

# Default retry configuration
MAX_RETRIES = 3
INITIAL_BACKOFF = 1  # seconds
MAX_BACKOFF = 60  # seconds
BACKOFF_MULTIPLIER = 2

# HTTP status codes that should trigger retry
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


async def retry_with_backoff(
    func: Callable[[], Any],
    max_retries: int = MAX_RETRIES,
    initial_backoff: float = INITIAL_BACKOFF,
    max_backoff: float = MAX_BACKOFF,
    backoff_multiplier: float = BACKOFF_MULTIPLIER,
    retryable_status_codes: set = RETRYABLE_STATUS_CODES,
    description: str = "API call"
) -> T:
    """
    Retry a function with exponential backoff.
    
    Args:
        func: Async function to retry (should return a response object)
        max_retries: Maximum number of retry attempts
        initial_backoff: Initial backoff time in seconds
        max_backoff: Maximum backoff time in seconds
        backoff_multiplier: Multiplier for exponential backoff
        retryable_status_codes: Set of HTTP status codes that should trigger retry
        description: Description of the operation for logging
        
    Returns:
        Result of the function call
        
    Raises:
        httpx.HTTPStatusError: If all retries fail
        Exception: Other exceptions from the function
    """
    backoff = initial_backoff
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            result = await func()
            
            # If result is an httpx response, check status code
            if hasattr(result, 'status_code'):
                status_code = result.status_code
                
                # If status is retryable and not the last attempt, retry
                if status_code in retryable_status_codes and attempt < max_retries:
                    logger.warning(
                        f"{description} failed with status {status_code} (attempt {attempt + 1}/{max_retries + 1}). "
                        f"Retrying in {backoff:.1f} seconds..."
                    )
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * backoff_multiplier, max_backoff)
                    last_exception = httpx.HTTPStatusError(
                        f"Status {status_code}",
                        request=result.request,
                        response=result
                    )
                    continue
                
                # If status is not OK and not retryable, raise immediately
                if status_code >= 400:
                    result.raise_for_status()
            
            # Success - reset backoff for logging
            if attempt > 0:
                logger.info(f"{description} succeeded after {attempt + 1} attempts")
            
            return result
            
        except httpx.HTTPStatusError as e:
            # Check if status code is retryable
            if e.response.status_code in retryable_status_codes and attempt < max_retries:
                logger.warning(
                    f"{description} failed with status {e.response.status_code} (attempt {attempt + 1}/{max_retries + 1}). "
                    f"Retrying in {backoff:.1f} seconds..."
                )
                await asyncio.sleep(backoff)
                backoff = min(backoff * backoff_multiplier, max_backoff)
                last_exception = e
                continue
            else:
                # Non-retryable error or last attempt
                raise
                
        except (httpx.NetworkError, httpx.TimeoutException) as e:
            # Network errors are always retryable
            if attempt < max_retries:
                logger.warning(
                    f"{description} failed with network error: {str(e)} (attempt {attempt + 1}/{max_retries + 1}). "
                    f"Retrying in {backoff:.1f} seconds..."
                )
                await asyncio.sleep(backoff)
                backoff = min(backoff * backoff_multiplier, max_backoff)
                last_exception = e
                continue
            else:
                raise
                
        except Exception as e:
            # Other exceptions are not retryable
            logger.error(f"{description} failed with non-retryable error: {str(e)}")
            raise
    
    # If we get here, all retries failed
    if last_exception:
        raise last_exception
    else:
        raise Exception(f"{description} failed after {max_retries + 1} attempts")
