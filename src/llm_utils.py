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
    Sends a prompt to Ollama and returns the response text.
    """
    try:
        response = ollama.generate(model=model, prompt=prompt)
        return response.get('response')
    except Exception as e:
        print(f"Error in ask_ollama: {e}")
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



def ask_model(prompt, provider="ollama", model="phi4:14b"):
    """
    Calls the appropriate API based on the provider.
    """
    if provider.lower() == "ollama":
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
        if not cleaned.rstrip().endswith("}"):
            cleaned_fixed = cleaned.rstrip() + "}"
            try:
                return json.loads(cleaned_fixed)
            except json.JSONDecodeError as e2:
                print(f"Second attempt JSON parsing error: {e2}")
                return None
        else:
            print("JSON parsing error")
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

    Example result:
      {
         "stimme zu": 0,
         "stimme nicht zu": 1,
         "neutral": 2
      }
    """
    with open(mapping_filename, "r", encoding="utf-8") as f:
        mapping_data = json.load(f)
    mapping = {entry["message"].lower().strip(): entry["id"] for entry in mapping_data}
    return mapping
