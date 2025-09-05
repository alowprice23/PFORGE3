from __future__ import annotations
import logging
import re
from typing import Type, TypeVar, Optional
from pydantic import BaseModel, ValidationError
import orjson

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

def parse_llm_json_response(
    response_text: str,
    pydantic_model: Optional[Type[T]] = None
) -> Optional[T | dict]:
    """
    Parses a JSON response from an LLM, with resilience to common formatting issues.

    Args:
        response_text: The raw text response from the LLM.
        pydantic_model: An optional Pydantic model to validate the JSON against.

    Returns:
        An instance of the Pydantic model if provided and validation succeeds,
        a dictionary if no model is provided, or None if parsing fails.
    """
    if not response_text:
        return None

    # 1. Try to extract JSON from a markdown block
    match = re.search(r"```json\n(.*?)\n```", response_text, re.DOTALL)
    if match:
        json_str = match.group(1).strip()
    else:
        # If no markdown block, try to find a JSON object anywhere in the string
        match = re.search(r"\{.*\}", response_text, re.DOTALL)
        if match:
            json_str = match.group(0)
        else:
            json_str = response_text # Fallback to the whole string

    # 2. Parse the JSON string
    try:
        parsed_json = orjson.loads(json_str)
    except orjson.JSONDecodeError as e:
        logger.warning(f"Failed to parse JSON from LLM response: {e}\nResponse text: {response_text}")
        return None

    # 3. Validate with Pydantic model if provided
    if pydantic_model:
        try:
            return pydantic_model.parse_obj(parsed_json)
        except ValidationError as e:
            logger.warning(f"LLM response did not match Pydantic model {pydantic_model.__name__}: {e}\nParsed JSON: {parsed_json}")
            return None

    return parsed_json
