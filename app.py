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
.metric-card {padding: 1rem; border: 1px solid #333; border-radius: 12px;}
</style>
""", unsafe_allow_html=True)

st.title("🏈 NFL Team Analyzer")
st.caption("Team offense and defense averages — regular-season games")

with st.sidebar:
    st.header("Choose a team")
    team_code = st.selectbox(
        "NFL team",
        options=sorted(TEAM_NAMES.keys(), key=lambda x: TEAM_NAMES[x]),
        format_func=lambda x: f"{TEAM_NAMES[x]} ({x})",
        index=sorted(TEAM_NAMES.keys(), key=lambda x: TEAM_NAMES[x]).index("CHI"),
    )
    current_year = datetime.date.today().year
    season = st.number_input("Season year", min_value=1999, max_value=current_year, value=current_year, step=1)
    refresh = st.button("Load / refresh stats", type="primary", use_container_width=True)
    st.caption("The current season only includes completed games available from the data provider.")

@st.cache_data(ttl=3600, show_spinner=False)
def load_stats(season_year: int):
    frame = nfl.load_team_stats(seasons=[season_year], summary_level="week")
    if hasattr(frame, "to_pandas"):
        frame = frame.to_pandas()
    return frame

def find_col(df, options):
    lower_map = {str(c).lower(): c for c in df.columns}
    for option in options:
        if option.lower() in lower_map:
            return lower_map[option.lower()]
    return None

def fmt_num(value):
    return "N/A" if pd.isna(value) else f"{value:.1f}"

if refresh:
    load_stats.clear()

with st.spinner(f"Loading {season} season data..."):
    try:
        df = load_stats(int(season))
    except Exception as exc:
        st.error("I couldn't load the NFL stats right now.")
        st.exception(exc)
        st.info("Try again in a moment. If this persists, check the app logs and the nflreadpy package version.")
        st.stop()

if df is None or df.empty:
    st.warning(f"No stats were returned for the {season} season.")
    st.stop()

team_col = find_col(df, ["team"])
opp_col = find_col(df, ["opponent_team", "opponent", "opp"])
points_col = find_col(df, ["points", "points_scored"])
pass_col = find_col(df, ["passing_yards", "pass_yards"])
rush_col = find_col(df, ["rushing_yards", "rush_yards"])
week_col = find_col(df, ["week"])
season_type_col = find_col(df, ["season_type"])

missing = [name for name, col in [
    ("team", team_col), ("opponent", opp_col), ("points", points_col),
    ("passing yards", pass_col), ("rushing yards", rush_col)
] if col is None]
if missing:
    st.error("The data provider returned an unexpected column layout.")
    st.write("Missing expected fields:", ", ".join(missing))
    st.write("Available columns:", list(df.columns))
    st.stop()

data = df.copy()
if season_type_col:
    data = data[data[season_type_col].astype(str).str.upper().isin(["REG", "REGULAR", "REGULAR SEASON"])]

for col in [points_col, pass_col, rush_col]:
    data[col] = pd.to_numeric(data[col], errors="coerce")

# Keep completed games. A populated points field is the available-data indicator.
data = data[data[points_col].notna()].copy()
data[team_col] = data[team_col].astype(str).str.upper()
data[opp_col] = data[opp_col].astype(str).str.upper()

offense = data[data[team_col] == team_code].copy()
# Each opponent's offense line is the production this team's defense allowed.
defense_allowed = data[data[opp_col] == team_code].copy()

if offense.empty:
    st.warning(f"No completed regular-season games found for {TEAM_NAMES[team_code]} in {season}.")
    st.info("If the season is underway, try again after game data has been published. Or choose a previous season.")
    st.stop()

# Prevent accidental duplicate weekly rows if the provider schema contains multiple records.
if week_col:
    offense = offense.drop_duplicates(subset=[week_col, team_col])
    defense_allowed = defense_allowed.drop_duplicates(subset=[week_col, team_col])

def mean_or_nan(frame, col):
    return frame[col].mean() if not frame.empty else float("nan")

st.subheader(f"{TEAM_NAMES[team_code]} · {season} season")
left, right = st.columns(2, gap="large")

with left:
    st.markdown("### 🟢 Offense — per game")
    a, b, c = st.columns(3)
    a.metric("Rush yards", fmt_num(mean_or_nan(offense, rush_col)))
    b.metric("Pass yards", fmt_num(mean_or_nan(offense, pass_col)))
    c.metric("Points scored", fmt_num(mean_or_nan(offense, points_col)))
    st.caption(f"Based on {len(offense)} completed team games.")

with right:
    st.markdown("### 🔴 Defense — allowed per game")
    a, b, c = st.columns(3)
    a.metric("Rush yards allowed", fmt_num(mean_or_nan(defense_allowed, rush_col)))
    b.metric("Pass yards allowed", fmt_num(mean_or_nan(defense_allowed, pass_col)))
    c.metric("Points allowed", fmt_num(mean_or_nan(defense_allowed, points_col)))
    st.caption(f"Based on {len(defense_allowed)} opponent team-game records.")

with st.expander("View game-by-game data"):
    show_cols = []
    if week_col:
        show_cols.append(week_col)
    show_cols += [team_col, opp_col, rush_col, pass_col, points_col]
    detail = offense[show_cols].copy()
    detail = detail.rename(columns={
        team_col: "Team", opp_col: "Opponent", rush_col: "Rushing yards",
        pass_col: "Passing yards", points_col: "Points"
    })
    st.dataframe(detail, use_container_width=True, hide_index=True)
    csv = detail.to_csv(index=False).encode("utf-8")
    st.download_button("Download game data as CSV", data=csv, file_name=f"{team_code}_{season}_games.csv", mime="text/csv")

st.divider()
st.caption("Source: nflverse data accessed through nflreadpy. Averages are descriptive and do not guarantee future performance.")
