# NFL Team Analyzer — website starter

This is a simple Streamlit website for looking up NFL team offense and defense averages.

## Files
- `app.py` — the interactive website
- `requirements.txt` — Python dependencies
- `nfl_team_report.py` — your original command-line script (optional)

## Run locally on Windows

1. Install Python 3.11 or 3.12 if needed.
2. Open Command Prompt in this folder.
3. Install dependencies:

   ```bash
   py -m pip install -r requirements.txt
   ```

4. Start the website:

   ```bash
   py -m streamlit run app.py
   ```

5. Your browser should open to `http://localhost:8501`.

## Publish it free

1. Create a GitHub account if you don't already have one.
2. Create a new repository, for example `nfl-team-analyzer`.
3. Upload `app.py` and `requirements.txt` to the repository (you may also upload `README.md`).
4. Open Streamlit Community Cloud: https://share.streamlit.io/
5. Sign in with GitHub and choose **Create app**.
6. Select the repository, branch (`main`), and main file path (`app.py`), then deploy.

Streamlit Community Cloud offers free hosting for small apps; its free-tier limits and availability can change.

## Notes
- The first run requires internet access to fetch data.
- Current-season stats only include games published by the data provider.
- If a data schema changes, the app displays the available columns to help troubleshoot.
