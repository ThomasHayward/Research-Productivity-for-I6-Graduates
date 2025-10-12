import logging
import re
import time
from typing import Any, List, Tuple

import requests

# Configure logging for this module
logger = logging.getLogger(__name__)


class PubMedQueryError(Exception):
    """Custom exception for PubMed query errors."""
    pass


def sanitize_query(query: str) -> str:
    """
    Sanitize a PubMed query string by removing control characters and normalizing whitespace.
    
    Args:
        query: Raw query string
        
    Returns:
        Sanitized query string
        
    Raises:
        ValueError: If query becomes empty after sanitization
    """
    if not query or not isinstance(query, str):
        raise ValueError("Query must be a non-empty string")
    
    # Remove control characters (including newlines, tabs, etc.)
    query = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', query)
    
    # Replace multiple spaces with single space
    query = re.sub(r'\s+', ' ', query)
    
    # Strip leading/trailing whitespace
    query = query.strip()
    
    # Ensure proper encoding
    try:
        query = query.encode('utf-8').decode('utf-8')
    except UnicodeError:
        # If encoding fails, try to fix common issues
        query = query.encode('utf-8', errors='ignore').decode('utf-8')
    
    if not query:
        raise ValueError("Query became empty after sanitization")
    
    return query


def test_query_validity(query: str) -> Tuple[bool, List[str]]:
    """
    Test if a query string contains potentially problematic characters.
    
    Args:
        query: Query string to test
    
    Returns:
        Tuple of (is_valid, issues_found)
    """
    issues = []
    
    # Check for control characters
    if re.search(r'[\x00-\x1F\x7F-\x9F]', query):
        control_chars = re.findall(r'[\x00-\x1F\x7F-\x9F]', query)
        issues.append(f"Control characters found: {[hex(ord(c)) for c in control_chars]}")
    
    # Check for encoding issues
    try:
        query.encode('utf-8').decode('utf-8')
    except UnicodeError as e:
        issues.append(f"Encoding issue: {str(e)}")
    
    # Check for extremely long queries
    if len(query) > 2000:
        issues.append(f"Query very long: {len(query)} characters")
    
    return len(issues) == 0, issues


def retry_pubmed_query(pubmed, query: str, full_name: str = None, max_retries: int = 3, base_delay: int = 5) -> Any:
    """
    Retry PubMed query with exponential backoff and enhanced error handling.
    If complex query fails, tries fallback to simple full name search.
    
    Args:
        pubmed: PubMed API object
        query: Search query string
        full_name: Full name for fallback query (optional)
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds for exponential backoff
    
    Returns:
        Query results
        
    Raises:
        PubMedQueryError: If all retries fail
        ValueError: If query validation fails
    """
    
    # Validate and sanitize query
    original_query = query
    sanitized_query = sanitize_query(query)
    
    # Log the original and sanitized queries for debugging
    if query != sanitized_query:
        logger.info(f"Query sanitized from: {repr(query)}")
        logger.info(f"Query sanitized to: {repr(sanitized_query)}")
    
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            # Exponential backoff delay (only after first attempt)
            if attempt > 0:
                delay = base_delay * (2 ** (attempt - 1))
                logger.info(f"Waiting {delay} seconds before retry {attempt + 1}/{max_retries}")
                time.sleep(delay)
            
            logger.info(f"Attempting PubMed query (attempt {attempt + 1}/{max_retries}): {sanitized_query}")
            
            # Execute the query
            result = pubmed.query(sanitized_query, max_results=10000)
            
            # Log successful query
            logger.info(f"PubMed query successful on attempt {attempt + 1}")
            return result
            
        except requests.exceptions.HTTPError as e:
            last_exception = e
            if hasattr(e, 'response') and e.response.status_code == 429:
                logger.warning(f"Rate limit hit (429), attempt {attempt + 1}/{max_retries}")
                if attempt == max_retries - 1:
                    logger.error("Max retries reached for rate limit")
                    break  # Try fallback instead of raising
                continue
            elif hasattr(e, 'response'):
                logger.error(f"HTTP Error {e.response.status_code}: {str(e)}")
                # For non-429 HTTP errors, try fallback
                break
            else:
                logger.error(f"HTTP Error without response: {str(e)}")
                break
                
        except requests.exceptions.RequestException as e:
            last_exception = e
            logger.warning(f"Request exception on attempt {attempt + 1}/{max_retries}: {str(e)}")
            if attempt == max_retries - 1:
                logger.error("Max retries reached for request exception")
                break  # Try fallback instead of raising
            continue
            
        except ValueError as e:
            # Don't retry for validation errors
            logger.error(f"Query validation error: {str(e)}")
            raise
            
        except Exception as e:
            last_exception = e
            logger.error(f"Unexpected error querying PubMed (attempt {attempt + 1}/{max_retries}): {str(e)}")
            logger.error(f"Query used: {repr(sanitized_query)}")
            
            if attempt == max_retries - 1:
                logger.error("Max retries reached for unexpected error")
                break  # Try fallback instead of raising
            continue
    
    # If we get here, all retries failed - try fallback with full name
    if full_name:
        logger.info(f"Trying fallback query with full name: {full_name}")
        try:
            # Create simple fallback query using the same format as your original
            # Hardcoded format matching: f"{name}[AUTHOR]"
            fallback_query = f"{full_name}[AUTHOR]"
            sanitized_fallback = sanitize_query(fallback_query)
            
            logger.info(f"Attempting fallback PubMed query: {sanitized_fallback}")
            result = pubmed.query(sanitized_fallback, max_results=10000)
            
            logger.info(f"Fallback query successful for {full_name}")
            return result
            
        except Exception as fallback_e:
            logger.error(f"Fallback query also failed: {str(fallback_e)}")
            raise PubMedQueryError(f"Both original and fallback queries failed. Original: {str(last_exception)}, Fallback: {str(fallback_e)}")
    
    # No fallback name provided or fallback failed
    logger.error(f"All {max_retries} attempts failed")
    if last_exception:
        raise PubMedQueryError(f"All retry attempts failed: {str(last_exception)}")
    else:
        raise PubMedQueryError("All retry attempts failed with unknown error")


def debug_pubmed_query(pubmed, query: str) -> Any:
    """
    Debug version that provides detailed information about query issues.
    
    Args:
        pubmed: PubMed API object
        query: Query string to debug
        
    Returns:
        Query results if successful
    """
    print(f"Original query: {repr(query)}")
    
    is_valid, issues = test_query_validity(query)
    if not is_valid:
        print("Query issues found:")
        for issue in issues:
            print(f"  - {issue}")
    
    try:
        result = retry_pubmed_query(pubmed, query)
        print(f"Query successful, returned {len(result) if hasattr(result, '__len__') else 'unknown number of'} results")
        return result
    except Exception as e:
        print(f"Query failed: {str(e)}")
        raise