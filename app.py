import datetime
import pandas as pd
import streamlit as st
import nflreadpy as nfl

st.set_page_config(page_title="NFL Team Analyzer", page_icon="🏈", layout="wide")

TEAM_NAMES = {
    "ARI": "Arizona Cardinals", "ATL": "Atlanta Falcons", "BAL": "Baltimore Ravens",
    "BUF": "Buffalo Bills", "CAR": "Carolina Panthers", "CHI": "Chicago Bears",
    "CIN": "Cincinnati Bengals", "CLE": "Cleveland Browns", "DAL": "Dallas Cowboys",
    "DEN": "Denver Broncos", "DET": "Detroit Lions", "GB": "Green Bay Packers",
    "HOU": "Houston Texans", "IND": "Indianapolis Colts", "JAX": "Jacksonville Jaguars",
    "KC": "Kansas City Chiefs", "LV": "Las Vegas Raiders", "LAC": "Los Angeles Chargers",
    "LA": "Los Angeles Rams", "MIA": "Miami Dolphins", "MIN": "Minnesota Vikings",
    "NE": "New England Patriots", "NO": "New Orleans Saints", "NYG": "New York Giants",
    "NYJ": "New York Jets", "PHI": "Philadelphia Eagles", "PIT": "Pittsburgh Steelers",
    "SF": "San Francisco 49ers", "SEA": "Seattle Seahawks", "TB": "Tampa Bay Buccaneers",
    "TEN": "Tennessee Titans", "WAS": "Washington Commanders",
}

st.markdown("""
<style>
.block-container {padding-top: 2rem; max-width: 1150px;}
</style>
""", unsafe_allow_html=True)

st.title("🏈 NFL Team Analyzer")
st.caption("Team offense and defense averages — regular-season games")

with st.sidebar:
    st.header("Choose a team")
    sorted_teams = sorted(TEAM_NAMES.keys(), key=lambda x: TEAM_NAMES[x])
    team_code = st.selectbox(
        "NFL team",
        options=sorted_teams,
        format_func=lambda x: f"{TEAM_NAMES[x]} ({x})",
        index=sorted_teams.index("CHI"),
    )
    current_year = datetime.date.today().year
    season = st.number_input("Season year", min_value=1999, max_value=current_year, value=current_year, step=1)
    if st.button("Load / refresh stats", type="primary", use_container_width=True):
        st.cache_data.clear()
    st.caption("Current-season averages include only completed games available from the data provider.")

@st.cache_data(ttl=3600, show_spinner=False)
def load_data(season_year: int):
    # Team stats contain rushing/passing yardage. Scores come from the schedule dataset.
    team_stats = nfl.load_team_stats(seasons=[season_year], summary_level="week")
    schedules = nfl.load_schedules(seasons=[season_year])
    if hasattr(team_stats, "to_pandas"):
        team_stats = team_stats.to_pandas()
    if hasattr(schedules, "to_pandas"):
        schedules = schedules.to_pandas()
    return team_stats, schedules

def fmt(value):
    return "N/A" if pd.isna(value) else f"{value:.1f}"

with st.spinner(f"Loading {season} season data..."):
    try:
        stats, schedule = load_data(int(season))
    except Exception as exc:
        st.error("I couldn't load NFL stats. The data provider may be temporarily unavailable.")
        st.exception(exc)
        st.stop()

if stats is None or stats.empty:
    st.warning(f"No team stats were returned for the {season} season.")
    st.stop()

# Normalize expected field names in the team statistics dataset.
stats.columns = [str(c).lower() for c in stats.columns]
schedule.columns = [str(c).lower() for c in schedule.columns]

required_stats = ["team", "opponent_team", "game_id", "passing_yards", "rushing_yards"]
missing_stats = [c for c in required_stats if c not in stats.columns]
if missing_stats:
    st.error("The team-stats data has an unexpected layout.")
    st.write("Missing fields:", ", ".join(missing_stats))
    st.write("Available columns:", list(stats.columns))
    st.stop()

# Score fields are in schedules, not in the weekly team_stats dataset.
required_schedule = ["game_id", "home_team", "away_team", "home_score", "away_score"]
missing_schedule = [c for c in required_schedule if c not in schedule.columns]
if missing_schedule:
    st.error("The schedule data has an unexpected layout.")
    st.write("Missing fields:", ", ".join(missing_schedule))
    st.write("Available schedule columns:", list(schedule.columns))
    st.stop()

if "season_type" in stats.columns:
    stats = stats[stats["season_type"].astype(str).str.upper().isin(["REG", "REGULAR", "REGULAR SEASON"])].copy()
if "game_type" in schedule.columns:
    schedule = schedule[schedule["game_type"].astype(str).str.upper().isin(["REG", "REGULAR"])].copy()
elif "season_type" in schedule.columns:
    schedule = schedule[schedule["season_type"].astype(str).str.upper().isin(["REG", "REGULAR", "REGULAR SEASON"])].copy()

# Only games with a final score are completed.
schedule["home_score"] = pd.to_numeric(schedule["home_score"], errors="coerce")
schedule["away_score"] = pd.to_numeric(schedule["away_score"], errors="coerce")
schedule = schedule[schedule["home_score"].notna() & schedule["away_score"].notna()].copy()

# Convert schedule results to one row per team/game with points scored and allowed.
home = schedule[["game_id", "home_team", "away_team", "home_score", "away_score"]].copy()
home.columns = ["game_id", "team", "opponent_team", "points_scored", "points_allowed"]
away = schedule[["game_id", "away_team", "home_team", "away_score", "home_score"]].copy()
away.columns = ["game_id", "team", "opponent_team", "points_scored", "points_allowed"]
scores = pd.concat([home, away], ignore_index=True)
scores["team"] = scores["team"].astype(str).str.upper()
scores["opponent_team"] = scores["opponent_team"].astype(str).str.upper()

stats["team"] = stats["team"].astype(str).str.upper()
stats["opponent_team"] = stats["opponent_team"].astype(str).str.upper()
stats["rushing_yards"] = pd.to_numeric(stats["rushing_yards"], errors="coerce")
stats["passing_yards"] = pd.to_numeric(stats["passing_yards"], errors="coerce")

# Join final game scores onto the team-game rows.
data = stats.merge(scores, on=["game_id", "team", "opponent_team"], how="inner")
if data.empty:
    st.warning(f"No completed regular-season games found for {season}. Try again later or choose another season.")
    st.stop()

selected_offense = data[data["team"] == team_code].copy()
selected_defense = data[data["opponent_team"] == team_code].copy()

if selected_offense.empty:
    st.warning(f"No completed regular-season games found for {TEAM_NAMES[team_code]} in {season}.")
    st.stop()

# One row per team-game, guarding against any duplicate data rows.
selected_offense = selected_offense.drop_duplicates(subset=["game_id", "team"])
selected_defense = selected_defense.drop_duplicates(subset=["game_id", "team"])

st.subheader(f"{TEAM_NAMES[team_code]} · {season} season")
left, right = st.columns(2, gap="large")

with left:
    st.markdown("### 🟢 Offense — per game")
    a, b, c = st.columns(3)
    a.metric("Rush yards", fmt(selected_offense["rushing_yards"].mean()))
    b.metric("Pass yards", fmt(selected_offense["passing_yards"].mean()))
    c.metric("Points scored", fmt(selected_offense["points_scored"].mean()))
    st.caption(f"Based on {len(selected_offense)} completed games.")

with right:
    st.markdown("### 🔴 Defense — allowed per game")
    a, b, c = st.columns(3)
    a.metric("Rush yards allowed", fmt(selected_defense["rushing_yards"].mean()))
    b.metric("Pass yards allowed", fmt(selected_defense["passing_yards"].mean()))
    c.metric("Points allowed", fmt(selected_defense["points_scored"].mean()))
    st.caption(f"Based on {len(selected_defense)} opponent team-game records.")

with st.expander("View game-by-game offensive data"):
    detail = selected_offense[["game_id", "week", "opponent_team", "rushing_yards", "passing_yards", "points_scored"]].copy() if "week" in selected_offense.columns else selected_offense[["game_id", "opponent_team", "rushing_yards", "passing_yards", "points_scored"]].copy()
    detail = detail.rename(columns={
        "game_id": "Game ID", "week": "Week", "opponent_team": "Opponent",
        "rushing_yards": "Rushing yards", "passing_yards": "Passing yards",
        "points_scored": "Points scored"
    })
    st.dataframe(detail, use_container_width=True, hide_index=True)
    st.download_button(
        "Download game data as CSV",
        data=detail.to_csv(index=False).encode("utf-8"),
        file_name=f"{team_code}_{season}_games.csv",
        mime="text/csv",
    )

st.divider()
st.caption("Source: nflverse via nflreadpy. Statistics describe completed regular-season games and are not predictions.")
