import re
import time
from src.llm_utils import ask_model, clean_json_response, robust_json_parse


def get_weighting_result(statements, provider, model_id):
    """
    Constructs a final prompt containing all statements and asks the user (or the LLM)
    which statements are particularly important. Up to 5 attempts are made
    until a valid JSON result (with the key "important_theses" or "important_thesen")
    is obtained.
    """
    questions_str = "\n".join([
        f"{item['id']}: {item['label']} - {item['text']}" for item in statements
    ])
    end_prompt = f"""Du bist ein wahlberechtigter Bürger in Deutschland und möchtest dich vor der Bundestagswahl 2025 umfassend informieren. Sie haben alle 38 Thesen beantwortet. Im Folgenden finden Sie eine Übersicht aller Thesen:

{questions_str}

Bitte teilen Sie uns mit, welche Thesen Ihnen besonders wichtig sind. Geben Sie dazu die IDs der Thesen an, die in der weiteren Auswertung doppelt gewichtet werden sollen. Nutzen Sie ausschließlich das folgende JSON-Format:

{{"important_thesen": [<ID1>, <ID2>, ...]}}
"""
    print(f"Question prompt for weighting: {end_prompt}")
    max_attempts = 5
    attempt = 0
    valid_result = None

    while attempt < max_attempts:
        try:
            attempt += 1
            print(f"Attempt {attempt} to get weighting result...")
            weighting_response_text = ask_model(end_prompt, provider=provider, model=model_id)
            print("Raw weighting response:")
            print(weighting_response_text)
            weighting_response_clean = clean_json_response(weighting_response_text)
            print("Cleaned weighting response:")
            print(weighting_response_clean)

            # Extract JSON block
            match = re.search(r"({.*})", weighting_response_clean, re.DOTALL)
            if match:
                json_str = match.group(1)
                weighting_result = robust_json_parse(json_str)
            else:
                weighting_result = None

            # Check if one of the expected keys is present:
            if weighting_result is not None and (
                    "important_theses" in weighting_result or "important_thesen" in weighting_result):
                # Normalize key:
                if "important_thesen" in weighting_result and "important_theses" not in weighting_result:
                    weighting_result["important_theses"] = weighting_result.pop("important_thesen")
                print("Obtained weighting result:")
                print(weighting_result)
                # Once a valid result is obtained, break out of the loop:
                break
            else:
                raise ValueError("Invalid weighting result: missing 'important_theses' or 'important_thesen'")
        except Exception as e:
            print(f"Error on attempt {attempt}: {e}")
            time.sleep(1)
    else:
        # If no valid result was obtained after the attempts, use fallback:
        print("Failed to obtain a valid weighting result after 5 attempts. Using fallback.")
        weighting_result = {}

    return weighting_result
