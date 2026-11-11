# Lost and Found Matcher

## Project Overview
A Python-based campus Lost and Found Matcher that uses Gemini AI to extract details from lost and found reports and suggests possible matches.

## Features
- Reads lost.csv and found.csv.
- Uses Gemini AI to extract item, colour, brand, place and summary.
- Validates extracted details using Python.
- Compares reports using a scoring system.
- Detects possible double claims.
- Generates matches.csv, no_match.csv, unclaimed.csv and summary.txt.

## Technology Used
- Python
- Google Gemini API
- Google Colab
- CSV files

## Scoring
- Same colour: 2 points
- Same brand: 2 points
- Same place: 1 point
- Score 3 or above: Likely
- Score 1 or 2: Possible
- Score 0: Not listed

## How to Run
1. Open the notebook in Google Colab.
2. Install the google-genai package.
3. Add your Gemini API key to Colab Secrets as GEMINI_API_KEY.
4. Upload lost.csv, found.csv and system_prompt.txt.
5. Run the Python program.
6. Check the generated output files.

## Important Safety Rule
AI suggestions are not proof of ownership. The campus help desk must verify ownership using a private detail that is not included in either report.

## Test Results
- Evaluation tests: 5/5 passed.
- Red-team tests: 3/3 passed.

## Security
Never upload your API key to GitHub.