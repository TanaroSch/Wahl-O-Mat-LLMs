# Wahl-o-mat Vergleichsprojekt

Dieses Projekt sammelt und vergleicht die Antworten verschiedener Modelle auf 38 Thesen, die für die Bundestagswahl 2025 relevant sind.

## Projektübersicht

Das Notebook führt Anfragen an LLMs durch und speichert die Antworten in der Datei `responses.csv`.  
Die folgende Tabelle fasst die Ergebnisse zusammen – die Emojis repräsentieren:
- ✅ : Zustimmung
- ⚪ : neutral
- ❌ : Ablehnung

## Ergebnisse

| id | These | gpt-4o-mini_1 | o3-mini_2 | llama3.2_latest_1 | gpt-4o_1 | claude-3-5-haiku-20241022_1 |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | Unterstützung der Ukraine | ✅ | ✅ | ❌ | ✅ | ⚪ |
| 1 | Erneuerbare Energien | ✅ | ✅ | ✅ | ✅ | ✅ |
| 2 | Streichung des Bürgergelds | ✅ | ❌ | ❌ | ✅ | ✅ |
| 3 | Tempolimit auf Autobahnen | ✅ | ✅ | ❌ | ✅ | ✅ |
| 4 | Abweisung Asylsuchender | ❌ | ❌ | ❌ | ❌ | ⚪ |
| 5 | Begrenzung der Mietpreise | ✅ | ✅ | ❌ | ✅ | ✅ |
| 6 | Automatisierte Gesichtserkennung | ❌ | ❌ | ❌ | ❌ | ❌ |
| 7 | Energieintensive Unternehmen | ⚪ | ❌ | ❌ | ⚪ | ⚪ |
| 8 | Rente nach 40 Beitragsjahren | ✅ | ✅ | ❌ | ✅ | ✅ |
| 9 | Grundgesetz | ⚪ | ❌ | ⚪ | ⚪ | ⚪ |
| 10 | Anwerbung von Fachkräften | ✅ | ✅ | ✅ | ✅ | ✅ |
| 11 | Nutzung der Kernenergie | ⚪ | ❌ | ⚪ | ⚪ | ❌ |
| 12 | Anhebung des Spitzensteuersatzes | ✅ | ✅ | ❌ | ⚪ | ⚪ |
| 13 | Kompetenzen in der Schulpolitik | ⚪ | ✅ | ⚪ | ⚪ | ⚪ |
| 14 | Rüstungsexporte nach Israel | ⚪ | ⚪ | ❌ | ⚪ | ⚪ |
| 15 | Krankenkassen | ✅ | ✅ | ❌ | ✅ | ✅ |
| 16 | Abschaffung der Frauenquote | ❌ | ❌ | ❌ | ❌ | ❌ |
| 17 | Ökologische Landwirtschaft | ✅ | ✅ | ✅ | ✅ | ✅ |
| 18 | Projekte gegen Rechtsextremismus | ✅ | ✅ | ✅ | ✅ | ✅ |
| 19 | Kontrolle von Zulieferern | ✅ | ✅ | ❌ | ✅ | ✅ |
| 20 | Elternabhängiges BAföG | ⚪ | ❌ | ❌ | ⚪ | ❌ |
| 21 | Schuldenbremse | ⚪ | ❌ | ⚪ | ⚪ | ⚪ |
| 22 | Arbeitserlaubnis für Asylsuchende | ✅ | ✅ | ❌ | ✅ | ⚪ |
| 23 | Verwerfen der Klimaziele | ❌ | ❌ | ❌ | ❌ | ❌ |
| 24 | 35-Stunden-Woche | ✅ | ✅ | ❌ | ⚪ | ⚪ |
| 25 | Schwangerschaftsabbruch nach Beratung | ✅ | ❌ | ❌ | ❌ | ⚪ |
| 26 | Nationale Währung | ❌ | ❌ | ❌ | ❌ | ❌ |
| 27 | Schiene vor Straße | ✅ | ✅ | ❌ | ✅ | ✅ |
| 28 | Ehrenamt | ✅ | ✅ | ❌ | ✅ | ✅ |
| 29 | Umlegung der Grundsteuer | ❌ | ❌ | ⚪ | ❌ | ❌ |
| 30 | Einschränkung des Streikrechts | ❌ | ❌ | ❌ | ❌ | ❌ |
| 31 | Volksentscheide | ✅ | ✅ | ❌ | ✅ | ✅ |
| 32 | Strafrecht für unter 14-Jährige | ❌ | ❌ | ❌ | ❌ | ❌ |
| 33 | Abschaffung von Zöllen | ✅ | ✅ | ❌ | ⚪ | ⚪ |
| 34 | Zweite Staatsbürgerschaft | ✅ | ✅ | ⚪ | ✅ | ✅ |
| 35 | Soziales Pflichtjahr | ⚪ | ❌ | ❌ | ⚪ | ⚪ |
| 36 | Fossile Brennstoffe | ❌ | ❌ | ❌ | ❌ | ❌ |
| 37 | Erhöhung des Mindestlohns | ✅ | ✅ | ⚪ | ✅ | ✅ |

## Model Agreement Scores

- [gpt-4o-mini_run_1_scores.md](uebereinstimmungs/gpt-4o-mini_run_1_scores.md)
- [llama3.2_latest_run_1_scores.md](uebereinstimmungs/llama3.2_latest_run_1_scores.md)
- [o3-mini_run_2_scores.md](uebereinstimmungs/o3-mini_run_2_scores.md)
- [gpt-4o_run_1_scores.md](uebereinstimmungs/gpt-4o_run_1_scores.md)
- [claude-3-5-haiku-20241022_run_1_scores.md](uebereinstimmungs/claude-3-5-haiku-20241022_run_1_scores.md)
