import os
import json
import pandas as pd
from src.config import BASE_DATA_DIR
from src.llm_utils import load_answer_mapping


def load_parties_and_opinions():
    """
    Lädt die Dateien party.json und opinion.json aus BASE_DATA_DIR.
    """
    party_file = os.path.join(BASE_DATA_DIR, "party.json")
    opinion_file = os.path.join(BASE_DATA_DIR, "opinion.json")
    with open(party_file, "r", encoding="utf-8") as f:
        parties = json.load(f)
    with open(opinion_file, "r", encoding="utf-8") as f:
        opinions = json.load(f)
    return parties, opinions


def compute_statement_score(user_answer, party_answer, weighted):
    """
    Berechnet den Score für eine These anhand der Antworten des Nutzers (LLM) und der Partei.

    Bewertungslogik:
      - Sind beide Antworten exakt gleich (egal ob "stimme zu", "neutral" oder "stimme nicht zu"),
        erhält die Partei 2 Punkte (bzw. 4 Punkte, wenn die These gewichtet ist).
      - Ist genau eine der beiden Antworten neutral (aber die Antworten sind nicht identisch),
        erhält die Partei 1 Punkt (bzw. 2 Punkte bei Gewichtung).
      - In allen anderen Fällen (z. B. "stimme zu" vs. "stimme nicht zu") gibt es 0 Punkte.
    """
    answer_mapping = load_answer_mapping()
    if user_answer is None:
        return 0
    if user_answer == party_answer:
        base = 2
    elif user_answer == answer_mapping['neutral'] or party_answer == answer_mapping['neutral']:
        base = 1
    else:
        base = 0
    return base * (2 if weighted else 1)


def max_possible_score(user_answer, weighted):
    """
    Gibt den maximal möglichen Score für eine These zurück.
    Unabhängig von der Antwort beträgt der maximale Score:
      - 2 Punkte (unweighted)
      - 4 Punkte (weighted)
    """
    if user_answer is None:
        return 0
    return 2 * (2 if weighted else 1)


def compute_party_responses_df(statements, parties, opinions):
    """
    Erstellt einen DataFrame, in dem jede Zeile einer These entspricht (Zeilenindex entspricht der 
    Statement-ID, also 0 bis n-1) und jede Spalte einer Partei (benannt nach dem Parteinamen).

    In den Zellen wird der numerische Antwortwert (0, 1 oder 2) gespeichert, den die jeweilige Partei 
    in opinion.json für die entsprechende These angegeben hat.

    Parameter:
      - statements: Liste von Dictionaries, jedes mit "id", "label", "text", etc.
      - parties: Liste von Dictionaries, jedes mit "id", "name", "longname", etc.
      - opinions: Liste von Dictionaries, jedes mit "party", "statement", "answer", "comment", etc.

    Rückgabe:
      Ein DataFrame, dessen Zeilen den Thesen (Statements) und dessen Spalten den Parteinamen entsprechen.
      In den Zellen steht der numerische Wert (0, 1 oder 2) aus den Opinions.
    """
    n_statements = len(statements)
    party_id_to_name = {party["id"]: party["name"] for party in parties}
    columns = list(party_id_to_name.values())
    df = pd.DataFrame(index=range(n_statements), columns=columns)
    df = df.astype("float")
    for op in opinions:
        stmt_id = op["statement"]
        party_id = op["party"]
        party_name = party_id_to_name.get(party_id)
        if party_name is not None and 0 <= stmt_id < n_statements:
            df.loc[stmt_id, party_name] = op["answer"]
    return df


def compute_model_responses_df(responses_csv, model_id, run_spec):
    """
    Reads the responses CSV and returns a DataFrame containing the model's responses
    for the given run_spec. It first tries using a sanitized model_id (with ":" replaced by "_").
    If that column is not found, it falls back to using the raw model_id.

    Parameters:
      responses_csv (str): Path to the CSV file.
      model_id (str): The model identifier.
      run_spec (str): The run specifier (e.g., "solo", or "aggregated_3").

    Returns:
      A DataFrame with a single column named "model_response".
    """
    import pandas as pd
    df = pd.read_csv(responses_csv)

    # Try with sanitized model_id:
    model_id_clean = model_id.replace(":", "_")
    numeric_col = f"numeric_{model_id_clean}_{run_spec}"
    if numeric_col not in df.columns:
        # Fallback: try with the raw model_id.
        numeric_col = f"numeric_{model_id}_{run_spec}"
        if numeric_col not in df.columns:
            raise KeyError(f"Column {numeric_col} not found in CSV columns: {df.columns.tolist()}")

    model_df = df[[numeric_col]].rename(columns={numeric_col: "model_response"})
    return model_df


SCORE_LOOKUP = {
    (0, 0): 2,
    (0, 2): 1,
    (0, 1): 0,
    (2, 0): 1,
    (2, 2): 2,
    (2, 1): 1,
    (1, 0): 0,
    (1, 2): 1,
    (1, 1): 2
}


def compute_statement_score(user_val, party_val, weighted=False):
    """
    Berechnet den Score für eine These anhand der numerischen Antworten von Modell und Partei,
    gemäß der oben definierten Matrix.

    Parameter:
      - user_val: numerischer Wert der Modellantwort (0, 1, 2)
      - party_val: numerischer Wert der Parteiantwort (0, 1, 2)
      - weighted: Boolean, ob diese These gewichtet ist (True → Score verdoppeln)

    Rückgabe:
      Den errechneten Score (als integer).
    """
    base = SCORE_LOOKUP.get((user_val, party_val), 0)
    return base * (2 if weighted else 1)


def max_score_for_statement(weighted=False):
    """
    Gibt den maximal möglichen Score für eine These zurück:
      - Ungewichtet: 2 Punkte
      - Gewichtet: 4 Punkte
    """
    return 2 * (2 if weighted else 1)


def compute_agreement_scores(party_df, model_df, weighted_series=None):
    """
    Vergleicht zeilenweise (pro These) die Modellantworten (model_df) mit den Parteiantworten (party_df)
    und berechnet für jede Partei die Gesamtpunkte und den maximal möglichen Punktewert.

    Bewertungsregel (unweighted):
      score = SCORE_LOOKUP[(model_response, party_response)]
    Falls eine These gewichtet ist (weighted_series[stmt] == 1), wird der Score und der max Score verdoppelt.

    Rückgabe:
      Ein DataFrame, bei dem jede Zeile einer Partei entspricht, mit den Spalten:
         - points: Summe der errechneten Punkte
         - max_points: Summe der maximal möglichen Punkte
         - percentage: (points / max_points * 100)
    """
    n_statements = party_df.shape[0]
    if weighted_series is None:
        weighted_series = pd.Series([0] * n_statements, index=party_df.index)
    party_scores = {party: 0 for party in party_df.columns}
    party_max = {party: 0 for party in party_df.columns}
    for stmt in party_df.index:
        try:
            user_val = int(model_df.loc[stmt, "model_response"])
        except Exception as e:
            continue
        is_weighted = bool(weighted_series.loc[stmt])
        max_for_stmt = max_score_for_statement(is_weighted)
        for party in party_df.columns:
            party_val = party_df.loc[stmt, party]
            if pd.isnull(party_val):
                continue
            party_val = int(party_val)
            score = compute_statement_score(user_val, party_val, weighted=is_weighted)
            party_scores[party] += score
            party_max[party] += max_for_stmt
    result_list = []
    for party in party_df.columns:
        total = party_scores[party]
        maximum = party_max[party]
        percentage = (total / maximum * 100) if maximum > 0 else 0
        result_list.append({
            "party": party,
            "points": total,
            "max_points": maximum,
            "percentage": percentage
        })
    result_df = pd.DataFrame(result_list).set_index("party")
    return result_df


def generate_party_scores_markdown(df_scores, model_id, run_index):
    """
    Erzeugt aus dem DataFrame mit den Parteiscores eine Markdown-Tabelle.
    """
    header = "| Partei | Punkte | Max. Punkte | Übereinstimmung (%) |"
    separator = "| --- | --- | --- | --- |"
    lines = [header, separator]
    for _, row in df_scores.iterrows():
        line = f"| {row['name']} | {row['points']} | {row['max_points']} | {row['percentage']:.1f}% |"
        lines.append(line)
    md_table = "\n".join(lines)
    title = f"### Partei-Übereinstimmung für {model_id} Run {run_index}\n"
    return title + "\n" + md_table + "\n"


def write_party_scores_md(df_scores, model_id, run_index, folder="party_scoring"):
    """
    Schreibt die Partie-Übereinstimmungs-Tabelle (im Markdown-Format) in eine
    Datei im Ordner `folder`. Der Dateiname wird aus dem Modellnamen und dem Run-Index gebildet.

    Rückgabe:
      Der Pfad zur erstellten Datei.
    """
    if not os.path.exists(folder):
        os.makedirs(folder)
    model_id_clean = model_id.replace(":", "_")
    filename = f"{model_id_clean}_run_{run_index}.md"
    file_path = os.path.join(folder, filename)
    md_table = generate_party_scores_markdown(df_scores, model_id, run_index)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(md_table)
    return file_path
