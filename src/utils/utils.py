"""
utils.py
--------
Generic helper functions used by the chatbot:
  - Calling the Groq LLM API (single-turn and multi-turn)
  - Building request parameter dictionaries
  - Parsing (sometimes messy) JSON returned by the LLM
  - Formatting FAQ entries and product results into plain-text context blocks

FAQ entries and product data both live in Weaviate already, so there is no
local dataset loading here — chatbot.py reads them straight from the
"faq" and "products" collections.

These functions have no notebook-specific code (no display(), no widgets,
no Flask server, etc.) so they can run in any regular Python environment.
"""

import json
import os
import re
import requests

GROQ_BASE_URL = "https://api.groq.com/openai/v1/chat/completions"


# --------------------------------------------------------------------------- #
# Groq API key / credentials
# --------------------------------------------------------------------------- #
def get_groq_key() -> str:
    """
    Retrieve the Groq API key from the GROQ_API_KEY environment variable.

    Raises:
        RuntimeError: if the environment variable is not set.
    """
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        raise RuntimeError(
            "GROQ_API_KEY not set. Get a free key at https://console.groq.com/keys "
            "and set it with: export GROQ_API_KEY='your_key_here'"
        )
    return key


# --------------------------------------------------------------------------- #
# LLM call helpers
# --------------------------------------------------------------------------- #
def generate_params_dict(
    prompt: str,
    temperature: float = None,
    role: str = "user",
    top_p: float = None,
    max_tokens: int = 500,
    model: str = "llama-3.3-70b-versatile",
) -> dict:
    """
    Build a dictionary of parameters that can later be passed to
    `generate_with_single_input` / `generate_with_multiple_input` via **kwargs.
    """
    return {
        "prompt": prompt,
        "role": role,
        "temperature": temperature,
        "top_p": top_p,
        "max_tokens": max_tokens,
        "model": model,
    }


def generate_with_single_input(
    prompt: str,
    role: str = "user",
    top_p: float = None,
    temperature: float = None,
    max_tokens: int = 500,
    model: str = "llama-3.3-70b-versatile",
    groq_api_key: str = None,
    **kwargs,
) -> dict:
    """
    Send a single-turn prompt to the Groq chat completion API.

    Returns:
        dict: {"role": ..., "content": ...} taken from the model's reply.
    """
    payload = {
        "model": model,
        "messages": [{"role": role, "content": prompt}],
        "max_tokens": max_tokens,
        **kwargs,
    }
    if temperature is not None:
        payload["temperature"] = temperature
    if top_p is not None:
        payload["top_p"] = top_p

    headers = {
        "Authorization": f"Bearer {groq_api_key or get_groq_key()}",
        "Content-Type": "application/json",
    }

    response = requests.post(GROQ_BASE_URL, headers=headers, json=payload, timeout=60)
    response.raise_for_status()

    message = response.json()["choices"][-1]["message"]
    return {"role": message["role"], "content": message["content"]}


def generate_with_multiple_input(
    messages: list,
    top_p: float = None,
    temperature: float = None,
    max_tokens: int = 500,
    model: str = "llama-3.3-70b-versatile",
    groq_api_key: str = None,
    **kwargs,
) -> dict:
    """
    Send a full conversation (list of {"role", "content"} messages) to the
    Groq chat completion API. Used to keep multi-turn conversation history.
    """
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        **kwargs,
    }
    if temperature is not None:
        payload["temperature"] = temperature
    if top_p is not None:
        payload["top_p"] = top_p

    headers = {
        "Authorization": f"Bearer {groq_api_key or get_groq_key()}",
        "Content-Type": "application/json",
    }

    response = requests.post(GROQ_BASE_URL, headers=headers, json=payload, timeout=60)
    response.raise_for_status()

    message = response.json()["choices"][-1]["message"]
    return {"role": message["role"], "content": message["content"]}


def call_llm_with_context(prompt: str, context: list, role: str = "user", **kwargs) -> dict:
    """
    Append a new prompt to an existing conversation context, call the LLM
    with the full context, and append the response to the context too.

    Parameters:
        prompt (str): The new user/assistant input to add.
        context (list): Conversation history (mutated in place).
        role (str): Role of the new message ('user' or 'assistant').
        **kwargs: Extra parameters forwarded to generate_with_multiple_input.

    Returns:
        dict: The model's response message.
    """
    context.append({"role": role, "content": prompt})
    response = generate_with_multiple_input(context, **kwargs)
    context.append(response)
    return response


# --------------------------------------------------------------------------- #
# JSON parsing helper (handles messy LLM output)
# --------------------------------------------------------------------------- #
def parse_json_output(llm_output: str):
    """
    Parse a string returned by an LLM into a Python object (dict/list).

    Handles common LLM quirks:
      - JSON wrapped in ```json ... ``` code fences
      - Extra text before/after the JSON
      - Single quotes instead of double quotes
      - Trailing commas

    Returns:
        dict/list or None if parsing fails.
    """
    if not llm_output or not isinstance(llm_output, str):
        print("Error: Empty or invalid input")
        return None

    cleaned_output = llm_output.strip()

    try:
        # Try to extract JSON from a ```json ... ``` code block first.
        code_block_pattern = r"```(?:json)?\s*\n?(.*?)\n?```"
        match = re.search(code_block_pattern, cleaned_output, re.DOTALL)
        if match:
            cleaned_output = match.group(1).strip()
        else:
            # Otherwise, grab everything between the first { or [ and the last } or ]
            start = min(
                cleaned_output.find("{") if "{" in cleaned_output else float("inf"),
                cleaned_output.find("[") if "[" in cleaned_output else float("inf"),
            )
            end = max(
                cleaned_output.rfind("}") if "}" in cleaned_output else -1,
                cleaned_output.rfind("]") if "]" in cleaned_output else -1,
            )
            if start != float("inf") and end != -1:
                cleaned_output = cleaned_output[start:end + 1]

        if not cleaned_output:
            cleaned_output = llm_output.strip()

        # Fix single-quoted keys/values -> double quotes
        cleaned_output = re.sub(r"'([^']*)':", r'"\1":', cleaned_output)
        cleaned_output = re.sub(r":\s*'([^']*)'", r': "\1"', cleaned_output)

        # Remove trailing commas
        cleaned_output = re.sub(r",\s*}", "}", cleaned_output)
        cleaned_output = re.sub(r",\s*\]", "]", cleaned_output)

        return json.loads(cleaned_output)

    except json.JSONDecodeError as e:
        print(f"JSON parsing failed: {e}")
        print(f"Attempted to parse: {cleaned_output[:200]}...")
        return None
    except Exception as e:
        print(f"Unexpected error while parsing JSON: {e}")
        return None


# --------------------------------------------------------------------------- #
# Text formatting helpers
# --------------------------------------------------------------------------- #
def generate_faq_layout(faq_dict: list) -> str:
    """
    Build a plain-text layout of the FAQ entries, one per line, to be
    embedded in an LLM prompt.
    """
    layout = ""
    for f in faq_dict:
        layout += f"Question: {f['question']} Answer: {f['answer']} Type: {f['type']}\n"
    return layout


def generate_items_context(results: list) -> str:
    """
    Build a plain-text summary of retrieved product objects, one per line,
    to be embedded in an LLM prompt.

    Parameters:
        results (list): Weaviate query result objects, each with a
                         `.properties` dict.
    """
    layout = ""
    for item in results:
        props = item.properties
        layout += (
            f"Product ID: {props['product_id']}. "
            f"Product name: {props['productDisplayName']}. "
            f"Product Category: {props['masterCategory']}. "
            f"Product usage: {props['usage']}. "
            f"Product gender: {props['gender']}. "
            f"Product Type: {props['articleType']}. "
            f"Product Category: {props['subCategory']} "
            f"Product Color: {props['baseColour']}. "
            f"Product Season: {props['season']}. "
            f"Product Year: {props['year']}.\n"
        )
    return layout
