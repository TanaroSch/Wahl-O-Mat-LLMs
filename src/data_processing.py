import json
from unicodedata import numeric
import pandas as pd
import os
import re
from src.llm_utils import map_answer_to_numeric, load_answer_mapping


def load_statements(json_path):
    """
    Loads the list of statements from a JSON file.
    """
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def merge_response_to_csv(responses, model_id, valid_result, csv_filename="responses.csv"):
    """
    Merges the new responses with existing ones (if any) and writes the result to a CSV.
    """
    model_id_clean = model_id.replace(":", "_")
    model_run_prefix = f"answer_{model_id_clean}"
    new_run = 1

    if os.path.exists(csv_filename):
        df_existing = pd.read_csv(csv_filename)
        existing_cols = [col for col in df_existing.columns if col.startswith(model_run_prefix)]
        max_run = 0
        for col in existing_cols:
            m = re.match(rf"^{model_run_prefix}(?:_(\d+))?$", col)
            if m:
                if m.group(1) is None:
                    max_run = max(max_run, 1)
                else:
                    max_run = max(max_run, int(m.group(1)))
        new_run = max_run + 1
    else:
        new_run = 1

    important_ids = valid_result.get("important_theses", [])
    data_for_df = []
    for r in responses:
        numeric_value = map_answer_to_numeric(r["answer"], load_answer_mapping())
        question_nr = r["id"]
        weighted_value = 1 if question_nr in important_ids else 0
        data_for_df.append({
            "question_nr": question_nr,
            "thesis": r["thesis"],
            f"answer_{model_id_clean}_{new_run}": r["answer"],
            f"reason_{model_id_clean}_{new_run}": r["reason"],
            f"numeric_{model_id_clean}_{new_run}": r["numeric"],
            f"weighted_{model_id_clean}_{new_run}": weighted_value
        })

    df_new = pd.DataFrame(data_for_df)
    df_new.sort_values("question_nr", inplace=True)

    if os.path.exists(csv_filename):
        df_existing = pd.read_csv(csv_filename)
        df_existing.set_index("question_nr", inplace=True)
        df_new.set_index("question_nr", inplace=True)
        if "thesis" in df_new.columns:
            df_new = df_new.drop(columns=["thesis"])
        df_merged = df_existing.join(df_new, how="outer")
        df_merged.reset_index(inplace=True)
    else:
        df_merged = df_new

    df_merged.to_csv(csv_filename, index=False)
    print(f"Saved responses to {csv_filename}")
    return df_merged


def update_readme(csv_filename="responses.csv", statements=None, readme_filename="README.md"):
    """
    Reads the CSV responses and creates a Markdown table with emoji representations
    of the answers. Then updates README.md with the new table.
    """
    if not os.path.exists(csv_filename):
        print(f"{csv_filename} not found.")
        return

    df = pd.read_csv(csv_filename)
    answer_cols = [col[len("answer_"):] for col in df.columns if col.startswith("answer_")]
    numeric_cols = ["numeric_" + identifier for identifier in answer_cols if "numeric_" + identifier in df.columns]
    # numeric_cols = [col for col in df.columns if col.startswith("numeric_")]

    id_to_label = {item["id"]: item["label"] for item in statements}

    header = ["id", "These"] + answer_cols
    table_lines = []
    table_lines.append("| " + " | ".join(header) + " |")
    table_lines.append("| " + " | ".join(["---"] * len(header)) + " |")

    def answer_to_emoji(ans):
        answer_mapping = load_answer_mapping()
        try:
            ans_int = int(ans)
        except (ValueError, TypeError):
            print(f"Unknown answer: {ans}")
            return "-"

        if ans_int == answer_mapping['stimme zu']:
            return "✅"
        elif ans_int == answer_mapping['stimme nicht zu']:
            return "❌"
        elif ans_int == answer_mapping['neutral']:
            return "⚪"

        print(f"Unknown answer: {ans}")
        return "⚪"

    for idx, row in df.iterrows():
        q = str(row.get("question_nr", idx + 1))
        q_id = int(row.get("question_nr", idx + 1))
        label = id_to_label.get(q_id, "")
        emojis = [answer_to_emoji(row.get(col, "")) for col in numeric_cols]
        table_line = "| " + " | ".join([q, label] + emojis) + " |"
        table_lines.append(table_line)

    md_table = "\n".join(table_lines)
    static_readme = """# Wahl-o-mat Vergleichsprojekt

Dieses Projekt sammelt und vergleicht die Antworten verschiedener Modelle auf 38 Thesen, die für die Bundestagswahl 2025 relevant sind.

## Projektübersicht

Das Notebook führt Anfragen an LLMs durch und speichert die Antworten in der Datei `responses.csv`.  
Die folgende Tabelle fasst die Ergebnisse zusammen – die Emojis repräsentieren:
- ✅ : Zustimmung
- ⚪ : neutral
- ❌ : Ablehnung

## Ergebnisse
"""
    final_readme = static_readme + "\n" + md_table
    with open(readme_filename, "w", encoding="utf-8") as f:
        f.write(final_readme)
    print(f"{readme_filename} has been updated.")


def write_party_scores_md(scores_df, model_id, run_index, folder="party_scoring"):
    """
    Writes the scores DataFrame to a Markdown file and returns the file path.

    The DataFrame is sorted in descending order by "percentage".

    Parameters:
      - scores_df: DataFrame containing the scores (columns: points, max_points, percentage)
      - model_id: Model name (e.g., "gpt-4o-mini")
      - run_index: Run index (e.g., 1)
      - folder: Folder where the Markdown file will be saved (default: "party_scoring")

    The file name is composed of the cleaned model name and the run index.
    """
    if not os.path.exists(folder):
        os.makedirs(folder)

    model_id_clean = model_id.replace(":", "_")
    filename = f"{model_id_clean}_run_{run_index}_scores.md"
    file_path = os.path.join(folder, filename)

    sorted_df = scores_df.sort_values(by="percentage", ascending=False)

    header = f"### Agreement Scores for {model_id} Run {run_index}\n\n"
    md_table = sorted_df.to_markdown(tablefmt="pipe", index=True)
    md_content = header + md_table

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    print(f"Scores Markdown file created: {file_path}")
    return file_path


def update_readme_with_score_links_replace(score_files, readme_filename="README.md"):
    """
    Updates the README.md by replacing the section "## Model Agreement Scores"
    with a new list of links specified in score_files.

    If the section exists, it is replaced; otherwise, it is appended to the end of the README.
    In the process, backslashes in the file paths are converted to forward slashes.
    Now that the README is one level up, the links will be prefixed with "notebooks/".
    """
    new_section = "## Model Agreement Scores\n\n"
    for file_path in score_files:
        # Convert backslashes to forward slashes
        file_path = file_path.replace("\\", "/")
        # Prepend the 'notebooks/' directory if not already present
        if not file_path.startswith("notebooks/"):
            file_path = "notebooks/" + file_path
        filename = os.path.basename(file_path)
        new_section += f"- [{filename}]({file_path})\n"

    if os.path.exists(readme_filename):
        with open(readme_filename, "r", encoding="utf-8") as f:
            content = f.read()
    else:
        content = ""

    pattern = r"(## Model Agreement Scores[\s\S]*?)(?=\n## |\Z)"

    if re.search(pattern, content):
        new_content = re.sub(pattern, new_section, content)
    else:
        new_content = content.rstrip() + "\n\n" + new_section

    with open(readme_filename, "w", encoding="utf-8") as f:
        f.write(new_content)

    print("README.md has been updated (section 'Model Agreement Scores' replaced).")
