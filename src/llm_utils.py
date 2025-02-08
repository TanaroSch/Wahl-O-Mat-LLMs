# llm_utils.py
import re
import json
import time
import openai
import ollama
import anthropic

from src.config import OPENAI_API_KEY, ANTHROPIC_API_KEY

openai.api_key = OPENAI_API_KEY
anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def ask_ollama(prompt, model="phi4:14b"):
    """
    Sends a prompt to Ollama (non-streaming) and returns the response text.
    """
    try:
        response = ollama.generate(model=model, prompt=prompt)
        return response.get('response')
    except Exception as e:
        print(f"Error in ask_ollama: {e}")
        return None


def ask_ollama_stream(prompt, model="phi4:14b", max_tokens=None):
    """
    Streams tokens from Ollama and prints them as they are received.
    The function accumulates tokens and, on each iteration, checks if the
    collected text contains a complete JSON block.

    - If a valid JSON with the keys "answer" and "reason" is found, the stream is terminated early.
    - If the token limit is reached and no complete JSON is found but the text starts with '{',
      a fallback is used: we extract the answer and reason with regex and return a JSON string
      with whatever content was received (even if truncated).

    Parameters:
      prompt (str): The prompt text.
      model (str): The model identifier.
      max_tokens (int or None): The maximum number of tokens to collect before terminating.

    Returns:
      A JSON string (either complete or a fallback using the available text) or the full accumulated text.
    """
    collected_tokens = []
    token_count = 0
    candidate_json = None

    try:
        # Call the API with stream=True so that we get an iterator of token objects.
        response_stream = ollama.generate(model=model, prompt=prompt, stream=True)

        for token_obj in response_stream:
            # Extract text from the token object (adjust attribute name if needed).
            token_str = token_obj.response if hasattr(token_obj, "response") else str(token_obj)
            print(token_str, end='', flush=True)
            collected_tokens.append(token_str)
            token_count += 1

            full_text = ''.join(collected_tokens)
            candidate = extract_first_json(full_text)
            if candidate is not None:
                parsed = robust_json_parse(candidate)
                if parsed is not None and "answer" in parsed and "reason" in parsed:
                    candidate_json = candidate
                    print("\n[Debug] Found valid JSON with required keys, terminating stream early...")
                    break

            if max_tokens is not None and token_count >= max_tokens:
                print("\n[Debug] Token limit reached. Terminating stream early...")
                break

        print()  # Newline for formatting after streaming is complete.

        # If we have a complete JSON candidate, return it.
        if candidate_json:
            return candidate_json

        # Fallback: if no complete JSON block was extracted but the text starts with '{',
        # try to extract answer and reason using regex.
        full_text = ''.join(collected_tokens).strip()
        if full_text.startswith("{"):
            print("[Debug] Incomplete JSON detected; using fallback extraction.")
            answer_match = re.search(r'"answer"\s*:\s*"(?P<answer>[^"]*)', full_text, re.DOTALL)
            reason_match = re.search(r'"reason"\s*:\s*"(?P<reason>.*)', full_text, re.DOTALL)
            answer_val = answer_match.group("answer") if answer_match else ""
            reason_val = reason_match.group("reason").strip() if reason_match else ""
            # Optionally, if the reason seems truncated (e.g. missing a closing quote), you could trim it further.
            fallback_dict = {"answer": answer_val, "reason": reason_val}
            return json.dumps(fallback_dict, ensure_ascii=False)

        # If nothing looks like JSON, return the raw accumulated text.
        return full_text

    except Exception as e:
        print(f"Error in ask_ollama_stream: {e}")
        return None


def ask_openai(prompt, model="gpt-3.5-turbo"):
    """
    Sends a prompt to OpenAI using the new client interface and returns the answer text.
    """
    try:
        client = openai.OpenAI()
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            model=model,
            temperature=0.7,
            max_tokens=1000
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error calling OpenAI: {e}")
        return None


def ask_anthropic(prompt, model="claude-3-5-sonnet-20241022"):
    """
    Updated implementation for Claude 3 models using Messages API
    """
    try:
        response = anthropic_client.messages.create(
            model=model,
            max_tokens=1000,
            temperature=0.7,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return response.content[0].text
    except Exception as e:
        print(f"Error calling Anthropic: {e}")
        return None


def ask_model(prompt, provider="ollama", model="phi4:14b", stream=False, max_tokens=None):
    """
    Calls the appropriate API based on the provider.
    If `stream` is True and the provider supports streaming (e.g. Ollama),
    then the streaming function is used.
    """
    if provider.lower() == "ollama":
        if stream:
            return ask_ollama_stream(prompt, model=model, max_tokens=max_tokens)
        else:
            return ask_ollama(prompt, model=model)
    elif provider.lower() == "openai":
        return ask_openai(prompt, model=model)
    elif provider.lower() == "anthropic":
        return ask_anthropic(prompt, model=model)
    else:
        print("Unknown provider specified!")
        return None


def clean_json_response(response_text):
    """
    Removes Markdown code block markers (like ``` or ```json) from a response.
    """
    cleaned = response_text.strip()
    cleaned = re.sub(r"^```(json)?\n", "", cleaned)
    cleaned = re.sub(r"\n```$", "", cleaned)
    return cleaned


def robust_json_parse(response_text):
    """
    Attempts to parse a JSON string in a robust way by cleaning and,
    if necessary, appending a closing brace.
    """
    cleaned = clean_json_response(response_text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # If the text doesn't end with a "}", try adding one.
        if not cleaned.rstrip().endswith("}"):
            cleaned_fixed = cleaned.rstrip() + "}"
            try:
                return json.loads(cleaned_fixed)
            except json.JSONDecodeError:
                return None
        else:
            return None


def extract_first_json(text):
    """
    Attempts to extract the first complete JSON substring from text.
    This function scans from the first "{" and counts braces until the matching "}" is found.
    It is aware of quoted strings so that braces inside strings are ignored.
    Returns the substring from the first "{" to the matching "}" (inclusive)
    or None if no complete JSON object is found.
    """
    start_index = text.find("{")
    if start_index == -1:
        return None

    count = 0
    end_index = -1
    in_string = False
    escape = False

    for i, ch in enumerate(text[start_index:], start=start_index):
        if ch == '"' and not escape:
            in_string = not in_string
        if not in_string:
            if ch == "{":
                count += 1
            elif ch == "}":
                count -= 1
                if count == 0:
                    end_index = i
                    break
        if ch == "\\" and not escape:
            escape = True
        else:
            escape = False

    if end_index != -1:
        return text[start_index:end_index + 1]
    return None


def map_answer_to_numeric(answer_text, mapping):
    """
    Converts the answer text to a numeric value
    according to answer.json.
    """
    answer_lower = answer_text.lower().strip()
    for key, value in mapping.items():
        if key in answer_lower:
            return value
    return None


def load_answer_mapping(mapping_filename="../data/answer.json"):
    """
    Loads the file answer.json and creates a dictionary that maps
    the answer text (normalized to lowercase) to the corresponding numeric value.
    """
    with open(mapping_filename, "r", encoding="utf-8") as f:
        mapping_data = json.load(f)
    mapping = {entry["message"].lower().strip(): entry["id"] for entry in mapping_data}
    return mapping
