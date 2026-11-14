import csv
import json
import math
from pathlib import Path
from urllib.request import Request, urlopen

DATA_DIR = Path("ml-service/data")
RESULT_FILE = DATA_DIR / "evaluation_results.csv"
CHRONOS_URL = "http://localhost:8000/api/v1/forecast"

CONTEXT_SIZE = 12
TEST_SIZE = 24


def calculate_metrics(actual, predicted):
    errors = [
        prediction - real
        for real, prediction in zip(actual, predicted)
    ]

    mae = sum(abs(error) for error in errors) / len(errors)
    rmse = math.sqrt(
        sum(error ** 2 for error in errors) / len(errors)
    )

    return mae, rmse


def predict_chronos(history):
    payload = json.dumps({
        "history": history,
        "prediction_length": 1,
    }).encode("utf-8")

    request = Request(
        CHRONOS_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urlopen(request, timeout=300) as response:
        result = json.loads(response.read().decode("utf-8"))

    return float(result["forecasts"]["q50"][0])


all_results = []

for fog in ("fog-a", "fog-b", "fog-c"):
    csv_path = DATA_DIR / f"{fog}.csv"

    with csv_path.open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))

    values = [float(row["busy"]) for row in rows]

    if len(values) < CONTEXT_SIZE + TEST_SIZE:
        raise ValueError(f"Not enough data for {fog}")

    actual_values = []
    chronos_values = []
    baseline_values = []

    start = len(values) - TEST_SIZE

    print(f"\nEvaluation de {fog}...")

    for index in range(start, len(values)):
        history = values[index - CONTEXT_SIZE:index]
        actual = values[index]

        chronos_prediction = predict_chronos(history)
        baseline_prediction = history[-1]

        actual_values.append(actual)
        chronos_values.append(chronos_prediction)
        baseline_values.append(baseline_prediction)

        all_results.append({
            "fog_id": fog,
            "time": rows[index]["time"],
            "actual": actual,
            "chronos_q50": chronos_prediction,
            "baseline": baseline_prediction,
        })

    chronos_mae, chronos_rmse = calculate_metrics(
        actual_values, chronos_values
    )
    baseline_mae, baseline_rmse = calculate_metrics(
        actual_values, baseline_values
    )

    print(f"Chronos-2 : MAE={chronos_mae:.2f} | RMSE={chronos_rmse:.2f}")
    print(f"Baseline  : MAE={baseline_mae:.2f} | RMSE={baseline_rmse:.2f}")

    if chronos_mae < baseline_mae:
        print("Resultat MAE : Chronos est meilleur.")
    else:
        print("Resultat MAE : La baseline est meilleure ou equivalente.")

with RESULT_FILE.open("w", newline="", encoding="utf-8") as file:
    writer = csv.DictWriter(
        file,
        fieldnames=[
            "fog_id", "time", "actual",
            "chronos_q50", "baseline",
        ],
    )
    writer.writeheader()
    writer.writerows(all_results)

print(f"\nResultats detailles sauvegardes dans : {RESULT_FILE}")
