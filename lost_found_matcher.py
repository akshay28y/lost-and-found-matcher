
import csv
import json
import re
import time
from datetime import datetime
from google import genai

# Connect to Gemini without storing the API key in this file
from google.colab import userdata
client = genai.Client(api_key=userdata.get("GEMINI_API_KEY"))

# Read the AI instructions
with open("system_prompt.txt", "r") as file:
    system_prompt = file.read()


def read_report(report):
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model="gemini-3.5-flash-lite",
                contents=system_prompt + "\n\nREPORT:\n" + report
            )

            result = response.text.strip()
            result = re.sub(r"^```json\s*", "", result)
            result = re.sub(r"^```\s*", "", result)
            result = re.sub(r"\s*```$", "", result)

            return json.loads(result)

        except Exception as error:
            print("Extraction attempt failed:", error)
            if attempt < 2:
                time.sleep(2 ** attempt)

    return None


allowed_items = {
    "phone", "wallet", "id_card", "bottle", "bag",
    "earphones", "keys", "umbrella", "calculator",
    "watch", "spectacles", "other"
}

allowed_colours = {
    "black", "white", "red", "blue", "green",
    "yellow", "brown", "silver", "grey", "pink"
}


def is_valid(data):
    if not isinstance(data, dict):
        return False

    required = ["item", "colour", "brand", "place", "summary"]

    if not all(key in data for key in required):
        return False

    if data["item"] not in allowed_items:
        return False

    if data["colour"] is not None and data["colour"] not in allowed_colours:
        return False

    return True


def check_facts(data, report):
    if not is_valid(data):
        return None

    for field in ["colour", "brand", "place"]:
        value = data[field]

        if value is not None and value.lower() not in report.lower():
            data[field] = None

    return data


def score_pair(lost, found):
    score = 0
    reasons = []

    if lost["item"] != found["item"]:
        return 0, ["Different item types"]

    if lost["item"] == "other":
        return 0, ["Other items cannot be automatically matched"]

    for field, points in [
        ("colour", 2), ("brand", 2), ("place", 1)
    ]:
        value1 = lost[field]
        value2 = found[field]

        if value1 is not None and value2 is not None:
            if value1.lower() != value2.lower():
                return 0, [f"Different {field}"]

            score += points
            reasons.append(f"Same {field}: {value1}")

    return score, reasons


def find_matches(lost_list, found_list):
    matches = []
    no_match = []
    unclaimed = []
    suggestions = {}

    for lost in lost_list:
        for found in found_list:
            d1 = datetime.strptime(lost["date"], "%Y-%m-%d")
            d2 = datetime.strptime(found["date"], "%Y-%m-%d")

            if abs((d1 - d2).days) > 30:
                continue

            score, reasons = score_pair(
                lost["details"], found["details"]
            )

            if score >= 3:
                status = "Likely"
            elif score >= 1:
                status = "Possible"
            else:
                continue

            matches.append({
                "lost_id": lost["id"],
                "found_id": found["id"],
                "score": score,
                "status": status,
                "reasons": "; ".join(reasons)
            })

            suggestions.setdefault(found["id"], set()).add(lost["id"])

    matched_lost = {m["lost_id"] for m in matches}
    matched_found = {m["found_id"] for m in matches}

    for lost in lost_list:
        if lost["id"] not in matched_lost:
            no_match.append(lost)

    for found in found_list:
        if found["id"] not in matched_found:
            unclaimed.append(found)

    for match in matches:
        match["double_claim"] = (
            "Yes" if len(suggestions[match["found_id"]]) > 1
            else "No"
        )

    matches.sort(key=lambda x: x["score"], reverse=True)

    return matches, no_match, unclaimed


def write_reports(matches, no_match, unclaimed):
    columns = [
        "lost_id", "found_id", "score",
        "status", "reasons", "double_claim"
    ]

    with open("matches.csv", "w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(matches)

    for filename, records in [
        ("no_match.csv", no_match),
        ("unclaimed.csv", unclaimed)
    ]:
        with open(filename, "w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["id", "date", "report"])

            for item in records:
                writer.writerow([
                    item["id"], item["date"], item["report"]
                ])


    likely = sum(1 for m in matches if m["status"] == "Likely")
    possible = sum(1 for m in matches if m["status"] == "Possible")
    double_claim_items = {
        m["found_id"] for m in matches if m["double_claim"] == "Yes"
    }

    with open("summary.txt", "w", encoding="utf-8") as file:
        file.write("LOST AND FOUND MATCHER - SUMMARY\n")
        file.write("--------------------------------\n")
        file.write(f"Lost reports processed: {len(no_match) + len({m['lost_id'] for m in matches})}\n")
        file.write(f"Found reports processed: {len(unclaimed) + len({m['found_id'] for m in matches})}\n")
        file.write(f"Total candidate pairs: {len(matches)}\n")
        file.write(f"Likely matches: {likely}\n")
        file.write(f"Possible matches: {possible}\n")
        file.write(f"No-match lost reports: {len(no_match)}\n")
        file.write(f"Unclaimed found items: {len(unclaimed)}\n")
        file.write(f"Found items with double claims: {len(double_claim_items)}\n")
        file.write("\nIMPORTANT:\n")
        file.write("AI suggestions are not proof of ownership.\n")
        file.write("The help desk must verify ownership using a private detail.\n")


# Main program
def main():
    lost_list = []
    found_list = []

    for filename, destination in [
        ("lost.csv", lost_list),
        ("found.csv", found_list)
    ]:
        with open(filename, newline="") as file:
            for row in csv.DictReader(file):
                details = read_report(row["report"])

                if details is None:
                    raise RuntimeError(
                        f"Extraction failed for {row['id']}"
                    )

                details = check_facts(details, row["report"])

                if details is None:
                    raise ValueError(
                        f"Invalid AI output for {row['id']}"
                    )

                destination.append({
                    "id": row["id"],
                    "date": row["date"],
                    "report": row["report"],
                    "details": details
                })

    matches, no_match, unclaimed = find_matches(
        lost_list, found_list
    )

    write_reports(matches, no_match, unclaimed)

    print("Matching completed!")
    print("Candidate pairs:", len(matches))
    print("Unmatched lost reports:", len(no_match))
    print("Unclaimed found items:", len(unclaimed))


if __name__ == "__main__":
    main()
