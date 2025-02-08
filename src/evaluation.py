import json
import re
from collections import Counter
import os
import pandas as pd

# Import your existing helper functions from llm_utils.
from src.llm_utils import (
    ask_model,
    clean_json_response,
    robust_json_parse,
    map_answer_to_numeric
)


def evaluate_statement_single(q, pre_prompt, provider, model, max_tokens, stream, answer_mapping):
    """
    Evaluates a single question (one run).
    Returns a dictionary with keys:
      "id", "answer", "numeric", "reason", "weighted"
    """
    full_prompt = pre_prompt + "\nThesis: " + q["text"] + "\n"
    response_text = ask_model(full_prompt, provider=provider, model=model, max_tokens=max_tokens, stream=stream)
    if response_text is None:
        return None
    cleaned_response = clean_json_response(response_text)
    response_json = robust_json_parse(cleaned_response)
    if response_json is None:
        return None
    numeric_value = map_answer_to_numeric(response_json.get("answer", ""), answer_mapping)
    return {
        "id": q["id"],
        "answer": response_json.get("answer", ""),
        "numeric": numeric_value,
        "reason": response_json.get("reason", ""),
        "weighted": ""  # placeholder; will be updated later
    }


def evaluate_statements(
        statements, pre_prompt, provider, model, max_tokens, stream, answer_mapping, repeat_count=1,
        weighting_result=None):
    """
    Evaluates a list of statements.

    For repeat_count == 1, each question is processed once.
    For repeat_count > 1, the model is run multiple times per question and then
    aggregated (using the mode of the numeric responses). One of the candidate responses
    (and its weighted value) is selected.

    The optional weighting_result (as returned by your weighting function) is used to set
    weighted = 2 for important questions and 1 otherwise.

    Returns a tuple (aggregated_results, raw_results) where:
      - aggregated_results: one dict per question with keys:
            "question_nr", "answer", "numeric", "reason", "weighted", "repeat_count"
      - raw_results: all individual responses with an extra key "run_index".
    """
    aggregated_results = []
    raw_results = []
    for q in statements:
        if repeat_count == 1:
            res = evaluate_statement_single(q, pre_prompt, provider, model, max_tokens, stream, answer_mapping)
            if res is not None:
                res["repeat_count"] = 1
                aggregated_results.append({
                    "question_nr": q["id"],
                    "answer": res["answer"],
                    "numeric": res["numeric"],
                    "reason": res["reason"],
                    "weighted": res["weighted"]
                })
                r = res.copy()
                r["run_index"] = 1
                r["question_nr"] = q["id"]
                raw_results.append(r)
        else:
            responses_for_question = []
            for i in range(repeat_count):
                res = evaluate_statement_single(q, pre_prompt, provider, model, max_tokens, stream, answer_mapping)
                if res is not None:
                    r = res.copy()
                    r["run_index"] = i + 1
                    r["question_nr"] = q["id"]
                    raw_results.append(r)
                    responses_for_question.append(res)
            if responses_for_question:
                numeric_values = [r["numeric"] for r in responses_for_question if r["numeric"] is not None]
                if numeric_values:
                    from collections import Counter
                    counter = Counter(numeric_values)
                    aggregated_numeric, _ = counter.most_common(1)[0]
                else:
                    aggregated_numeric = None
                candidate_responses = [r for r in responses_for_question if r["numeric"] == aggregated_numeric]
                aggregated_answer = candidate_responses[0]["answer"] if candidate_responses else ""
                aggregated_reason = candidate_responses[0]["reason"] if candidate_responses else ""
                aggregated_weighted = candidate_responses[0]["weighted"] if candidate_responses else ""
            else:
                aggregated_numeric = None
                aggregated_answer = ""
                aggregated_reason = ""
                aggregated_weighted = ""
            aggregated_results.append({
                "question_nr": q["id"],
                "answer": aggregated_answer,
                "numeric": aggregated_numeric,
                "reason": aggregated_reason,
                "weighted": aggregated_weighted,
                "repeat_count": repeat_count
            })
    # Update weighted values based on weighting_result.
    if weighting_result and ("important_theses" in weighting_result or "important_thesen" in weighting_result):
        if "important_thesen" in weighting_result and "important_theses" not in weighting_result:
            weighting_result["important_theses"] = weighting_result.pop("important_thesen")
        important_set = set(str(x) for x in weighting_result.get("important_theses", []))
        for res in aggregated_results:
            res["weighted"] = 2 if str(res["question_nr"]) in important_set else 1
        for r in raw_results:
            r["weighted"] = 2 if str(r["question_nr"]) in important_set else 1
    else:
        for res in aggregated_results:
            res["weighted"] = 1
        for r in raw_results:
            r["weighted"] = 1
    return aggregated_results, raw_results


def format_results_for_csv(results, model_tag, aggregated=False):
    """
    Reformats evaluation results so that the new columns are named as follows:
      - For solo runs: 
          "answer_{model_tag_clean}_solo", "reason_{model_tag_clean}_solo",
          "numeric_{model_tag_clean}_solo", "weighted_{model_tag_clean}_solo"
      - For aggregated runs:
          "answer_{model_tag_clean}_aggregated_{repeat_count}",
          "reason_{model_tag_clean}_aggregated_{repeat_count}",
          "numeric_{model_tag_clean}_aggregated_{repeat_count}",
          "weighted_{model_tag_clean}_aggregated_{repeat_count}"
    Here we sanitize the model tag by replacing ":" with "_" so that column names are safe.
    The output is a list of dictionaries keyed by "question_nr" and the new columns.
    """
    model_tag_clean = model_tag.replace(":", "_")
    formatted = []
    for res in results:
        row = {"question_nr": res["question_nr"]}
        if aggregated:
            suffix = f"aggregated_{res.get('repeat_count', 1)}"
        else:
            suffix = "solo"
        row[f"answer_{model_tag_clean}_{suffix}"] = res["answer"]
        row[f"reason_{model_tag_clean}_{suffix}"] = res["reason"]
        row[f"numeric_{model_tag_clean}_{suffix}"] = res["numeric"]
        row[f"weighted_{model_tag_clean}_{suffix}"] = res["weighted"]
        formatted.append(row)
    return formatted


def sanitize_filename(s):
    """Replace illegal filename characters with an underscore."""
    return re.sub(r'[<>:"/\\|?*]', "_", s)


def save_evaluation_to_csv(formatted_results, filename):
    """
    Merges new evaluation results with an existing CSV based on "question_nr".
    Only new columns are added so that the thesis is not duplicated.
    """
    df_new = pd.DataFrame(formatted_results)
    if os.path.exists(filename):
        df_existing = pd.read_csv(filename)
        df_merged = pd.merge(df_existing, df_new, on="question_nr", how="outer")
        df_merged.to_csv(filename, index=False)
        print(f"Updated existing CSV with new evaluation columns: {filename}")
    else:
        df_new.to_csv(filename, index=False)
        print(f"Created new CSV file: {filename}")


def save_raw_runs_csv(raw_results, model_tag, repeat_count, out_folder="notebooks/aggregated_runs"):
    """
    Saves all individual run responses to a dedicated CSV file.
    The filename is built from a sanitized model tag and the number of repeats.

    Returns the full path of the CSV file.
    """
    if not raw_results:
        print("[Debug] No raw results available to save!")
        return None
    if not os.path.exists(out_folder):
        os.makedirs(out_folder)
        print(f"[Debug] Created folder: {out_folder}")
    sanitized_model_tag = sanitize_filename(model_tag)
    filename = f"{sanitized_model_tag}_raw_runs_{repeat_count}.csv"
    full_path = os.path.join(out_folder, filename)
    df = pd.DataFrame(raw_results)
    print(f"[Debug] Raw results DataFrame shape: {df.shape}")
    df.to_csv(full_path, index=False)
    print(f"[Debug] Saved raw runs CSV to: {full_path}")
    return full_path
