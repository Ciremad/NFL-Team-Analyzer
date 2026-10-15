import datetime
import numpy as np
import pandas as pd
import streamlit as st
import nflreadpy as nfl

# ============================================================
# NFL Team Analyzer — matchup research + player props dashboard
# Data: nflverse via nflreadpy
# ============================================================

st.set_page_config(page_title="NFL Matchup Lab", page_icon="🏈", layout="wide")

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
TEAM_CODES = sorted(TEAM_NAMES.keys(), key=lambda x: TEAM_NAMES[x])

# Sportsbook-inspired dark dashboard, using CSS only.
st.markdown("""
<style>
:root { color-scheme: dark; }
.stApp { background: #0b0e13; }
[data-testid="stSidebar"] { background: #171c25; }
.block-container { max-width: 1400px; padding-top: 1.3rem; padding-bottom: 3rem; }
h1, h2, h3 { letter-spacing: -0.025em; }
h1 { font-weight: 800; }
[data-testid="stMetric"] {
  background: linear-gradient(145deg, #171f2b, #10151d);
  border: 1px solid #2b394a;
  padding: 14px 16px;
  border-radius: 12px;
}
[data-testid="stMetricLabel"] { color: #a8b6c9; }
[data-testid="stMetricValue"] { color: #f4f7fb; }
[data-testid="stDataFrame"] { border: 1px solid #2b394a; border-radius: 10px; }
[data-testid="stExpander"] { border: 1px solid #2b394a; border-radius: 10px; background: #10151d; }
@media (max-width: 700px) {
  .block-container { padding-left: .7rem; padding-right: .7rem; padding-top: .7rem; }
  h1 { font-size: 1.65rem !important; }
  h2 { font-size: 1.25rem !important; }
  [data-testid="stMetric"] { padding: 8px 10px; }
  [data-testid="stMetricLabel"] { font-size: .75rem; }
  [data-testid="stMetricValue"] { font-size: 1.25rem; }
}
div.stButton > button[kind="primary"] {
  background: #d5ff3f; color: #10140a; border: 0; font-weight: 800;
}
.panel-title { color: #d5ff3f; font-size: 0.82rem; font-weight: 800; text-transform: uppercase; letter-spacing: .12em; }
.small-muted { color: #9ba8ba; font-size: .88rem; }
</style>
""", unsafe_allow_html=True)

st.title("🏈 NFL MATCHUP LAB")
st.caption("Team matchup research • Player prop trends • Recent-game splits")

with st.sidebar:
    st.markdown("## ⚙️ Controls")
    current_year = datetime.date.today().year
    season = int(st.number_input("NFL season", min_value=1999, max_value=current_year, value=current_year, step=1))
    st.caption("Current-season data depends on completed games published by nflverse.")
    if st.button("↻ Refresh data", type="primary", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.markdown("---")
    st.markdown("**Included tools**")
    st.markdown("• Team vs. team matchup\n\n• Player game logs & averages\n\n• Last 3 / 5 / 10 games\n\n• Dark, sportsbook-inspired layout")

@st.cache_data(ttl=3600, show_spinner=False)
def load_all_data(season_year: int):
    team_stats = nfl.load_team_stats(seasons=[season_year], summary_level="week")
    player_stats = nfl.load_player_stats(seasons=[season_year], summary_level="week")
    schedules = nfl.load_schedules(seasons=[season_year])
    def as_pandas(frame):
        return frame.to_pandas() if hasattr(frame, "to_pandas") else frame
    return as_pandas(team_stats), as_pandas(player_stats), as_pandas(schedules)

def safe_mean(series):
    numeric = pd.to_numeric(series, errors="coerce").dropna()
    return float(numeric.mean()) if len(numeric) else np.nan

def display_num(value, decimals=1):
    return "—" if pd.isna(value) else f"{value:,.{decimals}f}"

def require_columns(frame, cols, label):
    missing = [c for c in cols if c not in frame.columns]
    if missing:
        st.error(f"{label} data is missing expected fields: {', '.join(missing)}")
        st.caption("The upstream data schema may have changed. Available columns are shown below.")
        st.write(list(frame.columns))
        st.stop()

with st.spinner(f"Loading {season} NFL data..."):
    try:
        team_stats, player_stats, schedules = load_all_data(season)
    except Exception as exc:
        st.error("NFL data could not be loaded. Check the connection and try again.")
        st.exception(exc)
        st.stop()

team_stats.columns = [str(c).lower() for c in team_stats.columns]
player_stats.columns = [str(c).lower() for c in player_stats.columns]
schedules.columns = [str(c).lower() for c in schedules.columns]

require_columns(team_stats, ["team", "opponent_team", "game_id", "rushing_yards", "passing_yards"], "Team statistics")
require_columns(player_stats, ["team", "opponent_team", "game_id", "player_display_name", "position", "week"], "Player statistics")
require_columns(schedules, ["game_id", "home_team", "away_team", "home_score", "away_score"], "Schedule")

# Keep regular-season rows only.
if "season_type" in team_stats.columns:
    team_stats = team_stats[team_stats["season_type"].astype(str).str.upper() == "REG"].copy()
if "season_type" in player_stats.columns:
    player_stats = player_stats[player_stats["season_type"].astype(str).str.upper() == "REG"].copy()
if "game_type" in schedules.columns:
    schedules = schedules[schedules["game_type"].astype(str).str.upper().isin(["REG", "REGULAR"])].copy()
elif "season_type" in schedules.columns:
    schedules = schedules[schedules["season_type"].astype(str).str.upper() == "REG"].copy()

# Normalize team IDs and attach final scores to team-game rows.
for frame in (team_stats, player_stats):
    frame["team"] = frame["team"].astype(str).str.upper()
    frame["opponent_team"] = frame["opponent_team"].astype(str).str.upper()

all_schedules = schedules.copy()  # Preserve upcoming games for the betting matchup finder.
schedules["home_score"] = pd.to_numeric(schedules["home_score"], errors="coerce")
schedules["away_score"] = pd.to_numeric(schedules["away_score"], errors="coerce")
schedules = schedules[schedules["home_score"].notna() & schedules["away_score"].notna()].copy()

home = schedules[["game_id", "home_team", "away_team", "home_score", "away_score"]].copy()
home.columns = ["game_id", "team", "opponent_team", "points_scored", "points_allowed"]
away = schedules[["game_id", "away_team", "home_team", "away_score", "home_score"]].copy()
away.columns = ["game_id", "team", "opponent_team", "points_scored", "points_allowed"]
scores = pd.concat([home, away], ignore_index=True)
scores["team"] = scores["team"].astype(str).str.upper()
scores["opponent_team"] = scores["opponent_team"].astype(str).str.upper()

team_stats = team_stats.merge(scores, on=["game_id", "team", "opponent_team"], how="inner")
if team_stats.empty:
    st.warning(f"No completed regular-season team games are available for {season}.")
    st.stop()

team_stats = team_stats.drop_duplicates(subset=["game_id", "team"])
player_stats = player_stats[player_stats["game_id"].isin(set(team_stats["game_id"]))].copy()
player_stats["week"] = pd.to_numeric(player_stats["week"], errors="coerce")
NUMERIC_PLAYER_STATS = {
    "passing_yards", "rushing_yards", "receiving_yards", "receptions", "passing_tds",
    "rushing_tds", "receiving_tds", "attempts", "passing_attempts", "passing_completions",
    "completions", "carries", "targets", "air_yards", "target_share", "fantasy_points",
    "rushing_fumbles", "receiving_fumbles"
}
for c in player_stats.columns:
    if c in NUMERIC_PLAYER_STATS:
        player_stats[c] = pd.to_numeric(player_stats[c], errors="coerce")


# Position-specific stat definitions. TDs are combined for RBs as rushing + receiving TDs.
POSITION_METRICS = {
    "QB": {"Passing yards": "passing_yards", "Passing TDs": "passing_tds", "Rushing yards": "rushing_yards"},
    "RB": {"Rushing yards": "rushing_yards", "Receiving yards": "receiving_yards", "Receptions": "receptions", "Total TDs": "total_tds"},
    "WR": {"Receiving yards": "receiving_yards", "Receptions": "receptions", "Receiving TDs": "receiving_tds"},
    "TE": {"Receiving yards": "receiving_yards", "Receptions": "receptions", "Receiving TDs": "receiving_tds"},
}
# Optional opportunity stats; use only columns actually provided by the current data source.
OPPORTUNITY_METRICS = {
    "QB": {"Pass attempts": ["attempts", "passing_attempts"], "Completions": ["completions", "passing_completions"], "Rushing attempts": ["carries"]},
    "RB": {"Carries": ["carries"], "Targets": ["targets"], "Receptions": ["receptions"]},
    "WR": {"Targets": ["targets"], "Receptions": ["receptions"], "Air yards": ["air_yards"]},
    "TE": {"Targets": ["targets"], "Receptions": ["receptions"], "Air yards": ["air_yards"]},
}

# Standardize TD fields and identify completed games available in the loaded data.
for col in ["passing_tds", "rushing_tds", "receiving_tds"]:
    if col not in player_stats.columns:
        player_stats[col] = 0
    player_stats[col] = pd.to_numeric(player_stats[col], errors="coerce").fillna(0)
player_stats["total_tds"] = player_stats["rushing_tds"] + player_stats["receiving_tds"]
player_stats["position"] = player_stats["position"].astype(str).str.upper().str.strip()

# Make recent-game windows reflect most recent games available for the selected team/player.
def latest_n(frame, n):
    if "week" in frame.columns:
        return frame.sort_values(["week", "game_id"], ascending=[False, False]).head(n)
    return frame.tail(n)

def team_summary(team_code):
    offense = team_stats[team_stats["team"] == team_code]
    allowed = team_stats[team_stats["opponent_team"] == team_code]
    return {
        "games": offense["game_id"].nunique(),
        "rush_for": safe_mean(offense["rushing_yards"]),
        "pass_for": safe_mean(offense["passing_yards"]),
        "points_for": safe_mean(offense["points_scored"]),
        "rush_allowed": safe_mean(allowed["rushing_yards"]),
        "pass_allowed": safe_mean(allowed["passing_yards"]),
        "points_allowed": safe_mean(allowed["points_scored"]),
    }

tab_matchup, tab_players, tab_betting, tab_dashboard = st.tabs([
    "⚔️ Matchup Analyzer", "🎯 Player Research", "💸 Betting Matchups", "🏆 Team Rankings"
])

# ------------------------------------------------------------
# 2. MATCHUP ANALYZER — LEAGUE-AVERAGE BASED
# ------------------------------------------------------------
with tab_matchup:
    st.markdown('<div class="panel-title">Head-to-head matchup</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        team_a = st.selectbox("Offense", TEAM_CODES, index=TEAM_CODES.index("CHI"),
                              format_func=lambda x: f"{TEAM_NAMES[x]} ({x})", key="match_a")
    with c2:
        team_b = st.selectbox("Opponent defense", TEAM_CODES, index=TEAM_CODES.index("GB"),
                              format_func=lambda x: f"{TEAM_NAMES[x]} ({x})", key="match_b")

    if team_a == team_b:
        st.warning("Choose two different teams for a matchup.")
    else:
        def grade_vs_league(projected_value, league_avg):
            """Convert projected production vs. league average into a friendlier 1–10 grade.

            Benchmarks: near league average is yellow; +15% becomes green; +25% is a
            strong green; substantial underperformance trends red. Piecewise interpolation
            keeps the scale predictable rather than letting small differences crush grades.
            """
            if pd.isna(projected_value) or pd.isna(league_avg) or league_avg <= 0:
                return np.nan
            ratio = max(0.0, float(projected_value) / float(league_avg))
            ratios = [0.00, 0.70, 0.85, 1.00, 1.14, 1.15, 1.24, 1.25, 1.34, 1.35, 2.00]
            scores = [1.00, 4.00, 4.80, 5.80, 6.90, 7.00, 8.40, 8.50, 9.40, 9.50, 10.00]
            return float(np.clip(np.interp(ratio, ratios, scores), 1, 10))

        def simple_matchup_grade(offense_avg, defense_allowed, league_avg):
            values = [offense_avg, defense_allowed, league_avg]
            if any(pd.isna(v) for v in values) or league_avg <= 0:
                return np.nan, "Not enough data"
            projected = (offense_avg + defense_allowed) / 2
            grade = grade_vs_league(projected, league_avg)
            if grade >= 7:
                label = "Favorable"
            elif grade >= 4.9:
                label = "Average / mixed"
            else:
                label = "Difficult"
            return grade, label

        def render_team_matchup(offense_code, defense_code):
            offense = team_summary(offense_code)
            defense = team_summary(defense_code)
            metrics = [
                ("Rushing yards", "rush_for", "rush_allowed", "rushing_yards"),
                ("Passing yards", "pass_for", "pass_allowed", "passing_yards"),
                ("Points scored", "points_for", "points_allowed", "points_scored"),
            ]
            rows = []
            for label, off_key, def_key, raw_col in metrics:
                league_avg = safe_mean(team_stats[raw_col]) if raw_col in team_stats.columns else np.nan
                off_avg = offense[off_key]
                def_avg = defense[def_key]
                grade, assessment = simple_matchup_grade(off_avg, def_avg, league_avg)
                projected = (off_avg + def_avg) / 2 if pd.notna(off_avg) and pd.notna(def_avg) else np.nan
                rows.append({
                    "Category": label,
                    "Offense avg/game": display_num(off_avg),
                    "Defense allows/game": display_num(def_avg),
                    "League avg/game": display_num(league_avg),
                    "Estimated production": display_num(projected),
                    "Grade": f"{grade:.1f}/10" if pd.notna(grade) else "N/A",
                    "Matchup": assessment,
                })
            st.markdown(f"### {TEAM_NAMES[offense_code]} offense vs. {TEAM_NAMES[defense_code]} defense")
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            st.caption("Estimated production is the average of offense production and opponent allowance. The grade benchmarks that estimate against league average: Green 7.0–10.0, Yellow 4.9–6.9, Red below 4.9.")

        render_team_matchup(team_a, team_b)
        st.divider()
        render_team_matchup(team_b, team_a)

# ------------------------------------------------------------
# 3. PLAYER PROP RESEARCH
# ------------------------------------------------------------
with tab_players:
    st.markdown('<div class="panel-title">Offensive skill-player research</div>', unsafe_allow_html=True)
    st.caption("Only quarterbacks, running backs, wide receivers, and tight ends are included. Defensive players are excluded.")
    pc1, pc2 = st.columns([1, 1])
    with pc1:
        p_team = st.selectbox("Player's team", TEAM_CODES, index=TEAM_CODES.index("CHI"),
                              format_func=lambda x: f"{TEAM_NAMES[x]} ({x})", key="player_team")
    # Player Research is intentionally limited to offensive skill positions.
    # This keeps defensive players and non-skill roster entries out of the dropdown.
    skill_positions = ["QB", "RB", "WR", "TE"]
    team_players = player_stats[
        (player_stats["team"] == p_team)
        & (player_stats["position"].isin(skill_positions))
    ].copy()
    if team_players.empty:
        st.info(f"No QB, RB, WR, or TE player statistics found for {TEAM_NAMES[p_team]} in {season}.")
    else:
        name_col = "player_display_name"
        player_names = sorted(team_players[name_col].dropna().astype(str).unique())
        with pc2:
            chosen_player = st.selectbox("Player", player_names, key="chosen_player")
        selected = team_players[team_players[name_col].astype(str) == chosen_player].copy()
        if selected.empty:
            st.info("No game logs available for this player.")
        else:
            pos = str(selected["position"].dropna().iloc[0]) if selected["position"].notna().any() else "—"
            opps = sorted(selected["opponent_team"].dropna().astype(str).unique())
            prop_metrics = POSITION_METRICS.get(pos, POSITION_METRICS["WR"]).copy()
            available_metrics = [label for label, col in prop_metrics.items() if col in selected.columns]
            if not available_metrics:
                st.warning("No supported player prop statistics were found in this dataset.")
            else:
                pc3, pc4 = st.columns(2)
                with pc3:
                    metric_label = st.selectbox("Prop statistic", available_metrics, key="prop_metric")
                with pc4:
                    window = st.selectbox("Recent sample", [3, 5, 10], index=1, format_func=lambda n: f"Last {n} games", key="prop_window")
                metric_col = prop_metrics[metric_label]
                selected = selected.sort_values(["week", "game_id"], ascending=[False, False])
                season_avg = safe_mean(selected[metric_col])
                recent = selected.head(window)
                recent_avg = safe_mean(recent[metric_col])
                latest = selected.iloc[0]
                season_count = int(pd.to_numeric(selected[metric_col], errors="coerce").notna().sum())
                trend_delta = ((recent_avg - season_avg) / abs(season_avg) * 100) if pd.notna(season_avg) and season_avg != 0 and pd.notna(recent_avg) else np.nan
                k1, k2, k3, k4 = st.columns(4)
                k1.metric("Season average", display_num(season_avg), f"{season_count} game rows")
                k2.metric(f"Last {len(recent)} games", display_num(recent_avg),
                          (f"{trend_delta:+.1f}% vs season" if pd.notna(trend_delta) else None))
                k3.metric("Latest game", display_num(pd.to_numeric(pd.Series([latest.get(metric_col)]), errors="coerce").iloc[0]))
                k4.metric("Position", pos)

                with st.expander("📏 Compare with a sportsbook line", expanded=False):
                    line_col, direction_col = st.columns([1, 1])
                    with line_col:
                        prop_line = st.number_input("Enter prop line", min_value=0.0, value=0.0, step=0.5,
                                                    key=f"line_{p_team}_{chosen_player}_{metric_col}")
                    with direction_col:
                        line_direction = st.selectbox("Evaluate", ["Over", "Under"],
                                                      key=f"direction_{p_team}_{chosen_player}_{metric_col}")
                    valid_games = pd.to_numeric(selected[metric_col], errors="coerce").dropna()
                    recent_valid = pd.to_numeric(recent[metric_col], errors="coerce").dropna()
                    if prop_line > 0 and len(valid_games):
                        if line_direction == "Over":
                            season_hits = int((valid_games > prop_line).sum())
                            recent_hits = int((recent_valid > prop_line).sum())
                        else:
                            season_hits = int((valid_games < prop_line).sum())
                            recent_hits = int((recent_valid < prop_line).sum())
                        l1, l2, l3 = st.columns(3)
                        l1.metric("Season hit rate", f"{season_hits}/{len(valid_games)} ({season_hits / len(valid_games) * 100:.0f}%)")
                        l2.metric(f"Last {len(recent_valid)} hit rate", f"{recent_hits}/{len(recent_valid)} ({recent_hits / len(recent_valid) * 100:.0f}%)" if len(recent_valid) else "—")
                        l3.metric("Recent avg vs line", f"{recent_avg - prop_line:+.1f}" if pd.notna(recent_avg) else "—")
                        st.caption("Pushes are not counted as hits. Historical hit rates are descriptive, not a probability guarantee.")
                    else:
                        st.caption("Enter a line above 0 to see historical season and recent hit rates.")

                opportunity_metrics = OPPORTUNITY_METRICS.get(pos, {})
                opportunity_rows = []
                for label, candidates in opportunity_metrics.items():
                    col = next((candidate for candidate in candidates if candidate in selected.columns), None)
                    if col:
                        opportunity_rows.append({"Opportunity stat": label, "Season avg": safe_mean(selected[col]),
                                                 f"Last {len(recent)} avg": safe_mean(recent[col])})
                if opportunity_rows:
                    st.markdown("#### Opportunity & usage")
                    st.dataframe(pd.DataFrame(opportunity_rows).style.format(
                        {"Season avg": "{:.1f}", f"Last {len(recent)} avg": "{:.1f}"}, na_rep="—"),
                        use_container_width=True, hide_index=True)
                    st.caption("Carries, targets and attempts add context about opportunity. These appear only when available in the source data.")

                st.markdown("#### Game log")
                log_cols = [c for c in ["week", "opponent_team", "position", metric_col] if c in selected.columns]
                game_log = selected[log_cols].copy().rename(columns={
                    "week": "Week", "opponent_team": "Opponent", "position": "Position", metric_col: metric_label
                })
                st.dataframe(game_log, use_container_width=True, hide_index=True)
                st.download_button(
                    "Download player game log",
                    data=game_log.to_csv(index=False).encode("utf-8"),
                    file_name=f"{chosen_player.replace(' ', '_')}_{season}_game_log.csv",
                    mime="text/csv",
                )

                # Optional opponent defense context: compare the selected player's chosen stat to
                # the selected opponent's team-level yards/points allowed where relevant.
                prop_opp = st.selectbox("Compare against opponent defense", ["Select opponent…"] + TEAM_CODES,
                                        format_func=lambda x: x if x == "Select opponent…" else f"{TEAM_NAMES[x]} ({x})",
                                        key="prop_opp")
                if prop_opp != "Select opponent…":
                    def_frame = team_stats[team_stats["opponent_team"] == prop_opp]
                    allowed_lookup = {
                        "Passing yards": "passing_yards",
                        "Rushing yards": "rushing_yards",
                        "Receiving yards": "passing_yards",  # team passing yards is context, not WR-specific allowance
                        "Points scored": "points_scored",
                    }
                    if metric_label in allowed_lookup:
                        allowed_col = allowed_lookup[metric_label]
                        st.metric(f"{TEAM_NAMES[prop_opp]} opponent {allowed_col.replace('_', ' ')} allowed/game",
                                  display_num(safe_mean(def_frame[allowed_col])))
                        if metric_label == "Receiving yards":
                            st.caption("Team passing yards allowed is broad passing-defense context; it is not a position-specific receiving-yards-allowed statistic.")
                    else:
                        st.caption("The selected statistic doesn't have a directly comparable team-level defensive allowance metric in this dataset.")

                st.caption("Recent averages use the latest available player game rows. They are descriptive trends, not guaranteed outcomes.")

# ------------------------------------------------------------
# BETTING MATCHUP FINDER — DEFENSE-BASED POSITION GRADES
# ------------------------------------------------------------
with tab_betting:
    st.markdown('<div class="panel-title">Position matchup grades</div>', unsafe_allow_html=True)
    st.write("Compact game cards show QB, RB, WR, and TE grades for both offenses; expand a game to inspect the underlying statistics.")
    st.caption("Letter grades make matchups easy to scan. A/A+ = blue, B = green, C = yellow, D = orange, F = red. Expand a game for the supporting stats.")
    st.markdown("""
    <style>
    .grade-card {border:1px solid #2b394a;border-radius:12px;padding:12px;background:linear-gradient(145deg,#171f2b,#10151d);margin-bottom:8px;}
    .grade-head {display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:8px;}
    .grade-pos {font-size:1.05rem;font-weight:800;color:#f4f7fb;}
    .grade-score {font-size:1.5rem;font-weight:900;}
    .grade-sub {display:flex;justify-content:space-between;gap:8px;padding:5px 0;border-top:1px solid #2b394a;font-size:.88rem;color:#c4ceda;}
    .grade-blue {color:#60a5fa;} .grade-green {color:#4ade80;} .grade-yellow {color:#facc15;} .grade-orange {color:#fb923c;} .grade-red {color:#fb7185;}
    </style>
    """, unsafe_allow_html=True)

    if "week" not in schedules.columns:
        st.warning("The schedule data does not include a week field, so weekly matchups cannot be displayed.")
    else:
        schedule_view = all_schedules.copy()
        schedule_view["week"] = pd.to_numeric(schedule_view["week"], errors="coerce")
        schedule_view = schedule_view.dropna(subset=["week", "home_team", "away_team"]).copy()
        schedule_view["week"] = schedule_view["week"].astype(int)
        if "game_id" in schedule_view.columns:
            schedule_view = schedule_view.drop_duplicates(subset=["game_id"])
        available_weeks = sorted(schedule_view["week"].unique().tolist())
        if not available_weeks:
            st.info("No scheduled games are available for this season.")
        else:
            today = pd.Timestamp.today().normalize()
            future_games = schedule_view.copy()
            if "gameday" in future_games.columns:
                future_games["_date"] = pd.to_datetime(future_games["gameday"], errors="coerce")
                future_games = future_games[future_games["_date"].isna() | (future_games["_date"] >= today)]
            upcoming_weeks = sorted(future_games["week"].unique().tolist())
            default_week = upcoming_weeks[0] if upcoming_weeks else available_weeks[-1]
            week_index = available_weeks.index(default_week) if default_week in available_weeks else len(available_weeks)-1
            bc1, bc2 = st.columns(2)
            with bc1:
                betting_week = st.selectbox("NFL week", available_weeks, index=week_index, key="betting_week")
            with bc2:
                betting_window = st.selectbox("Defensive sample", ["Season", "Last 5 games", "Last 3 games"], key="betting_window")

            week_games = schedule_view[schedule_view["week"] == betting_week].copy()
            if week_games.empty:
                st.info(f"No games found for Week {betting_week}.")
            else:
                # These are the exact stats used for the matchup grades. TDs are deliberately
                # excluded from this grading model per the requested subgrade definitions.
                GRADE_METRICS = {
                    "QB": {"Passing yards": "passing_yards", "Rushing yards": "rushing_yards"},
                    "RB": {"Rushing yards": "rushing_yards", "Receiving yards": "receiving_yards", "Receptions": "receptions"},
                    "WR": {"Receiving yards": "receiving_yards", "Receptions": "receptions"},
                    "TE": {"Receiving yards": "receiving_yards", "Receptions": "receptions"},
                }
                metric_cols = sorted({col for spec in GRADE_METRICS.values() for col in spec.values() if col in player_stats.columns})
                pos_games = player_stats[player_stats["position"].isin(["QB", "RB", "WR", "TE"])].copy()
                group_cols = [c for c in ["game_id", "week", "team", "opponent_team", "position"] if c in pos_games.columns]
                if not group_cols or not metric_cols:
                    st.warning("The player statistics needed to calculate position grades are unavailable.")
                else:
                    # Aggregate every position's production within a game first. For WR/RB/TE,
                    # this means a defense is graded against the combined position output per game.
                    pos_game_totals = pos_games.groupby(group_cols, dropna=False)[metric_cols].sum(min_count=1).reset_index()
                    pos_game_totals["week"] = pd.to_numeric(pos_game_totals["week"], errors="coerce")
                    sort_cols = [c for c in ["week", "game_id"] if c in pos_game_totals.columns]
                    pos_game_totals = pos_game_totals.sort_values(sort_cols)
                    n_games = None if betting_window == "Season" else (5 if betting_window == "Last 5 games" else 3)

                    def defensive_allowed(def_code, position, metric_col, n=None):
                        rows = pos_game_totals[(pos_game_totals["opponent_team"] == def_code) & (pos_game_totals["position"] == position)].copy()
                        if "game_id" in rows.columns:
                            rows = rows.drop_duplicates("game_id")
                        rows = rows.sort_values(sort_cols, ascending=False)
                        if n is not None:
                            rows = rows.head(n)
                        return safe_mean(rows[metric_col]) if metric_col in rows.columns else np.nan

                    def league_allowed(position, metric_col, n=None):
                        rows = pos_game_totals[pos_game_totals["position"] == position].copy()
                        if "game_id" in rows.columns:
                            # One observation per defending team/game; each observation is the
                            # combined production allowed to this position in that game.
                            rows = rows.drop_duplicates(["opponent_team", "game_id"])
                        if n is not None:
                            rows = rows.sort_values(sort_cols, ascending=False).groupby("opponent_team", group_keys=False).head(n)
                        return safe_mean(rows[metric_col]) if metric_col in rows.columns else np.nan

                    def offense_position_average(off_code, position, metric_col, n=None):
                        rows = pos_game_totals[(pos_game_totals["team"] == off_code) &
                                               (pos_game_totals["position"] == position)].copy()
                        rows = rows.sort_values(sort_cols, ascending=False)
                        if n is not None:
                            rows = rows.drop_duplicates("game_id" if "game_id" in rows.columns else sort_cols).head(n)
                        return safe_mean(rows[metric_col]) if metric_col in rows.columns else np.nan

                    def letter_grade(score):
                        """Translate the existing internal 1–10 score to a simple letter grade."""
                        if pd.isna(score):
                            return "N/A"
                        if score >= 9.5:
                            return "A+"
                        if score >= 8.5:
                            return "A"
                        if score >= 7.0:
                            return "B"
                        if score >= 4.9:
                            return "C"
                        if score >= 3.0:
                            return "D"
                        return "F"

                    def grade_class(score):
                        grade = letter_grade(score)
                        if grade in {"A+", "A"}:
                            return "grade-blue", grade
                        if grade == "B":
                            return "grade-green", grade
                        if grade == "C":
                            return "grade-yellow", grade
                        if grade == "D":
                            return "grade-orange", grade
                        if grade == "F":
                            return "grade-red", grade
                        return "grade-yellow", "N/A"

                    # Position-specific weights. RB rushing remains important, but it cannot
                    # overwhelm two strong receiving subgrades; this avoids counterintuitive
                    # overall grades when a position has mixed results.
                    GRADE_WEIGHTS = {
                        "QB": {"Passing yards": 0.85, "Rushing yards": 0.15},
                        "RB": {"Rushing yards": 0.40, "Receiving yards": 0.35, "Receptions": 0.25},
                        "WR": {"Receiving yards": 0.65, "Receptions": 0.35},
                        "TE": {"Receiving yards": 0.65, "Receptions": 0.35},
                    }

                    def make_position_grade(offense, defense, position):
                        subgrades = []
                        for label, metric_col in GRADE_METRICS[position].items():
                            if metric_col not in pos_game_totals.columns:
                                continue
                            offense_avg = offense_position_average(offense, position, metric_col, n_games)
                            allowed = defensive_allowed(defense, position, metric_col, n_games)
                            league_avg = league_allowed(position, metric_col, n_games)
                            projected = (offense_avg + allowed) / 2 if pd.notna(offense_avg) and pd.notna(allowed) else np.nan
                            score = grade_vs_league(projected, league_avg)
                            subgrades.append({"label": label, "score": score, "offense": offense_avg,
                                              "allowed": allowed, "projected": projected, "league": league_avg})
                        # Normalize over available metrics so missing data does not count as zero.
                        weighted = [(item["score"], GRADE_WEIGHTS[position].get(item["label"], 0.0))
                                    for item in subgrades if pd.notna(item["score"])]
                        weight_total = sum(weight for _, weight in weighted)
                        overall = (sum(score * weight for score, weight in weighted) / weight_total
                                   if weight_total > 0 else np.nan)
                        return overall, subgrades

                    def render_grade_card(team_name, position, overall, subgrades):
                        css, tag = grade_class(overall)
                        score_text = letter_grade(overall)
                        rows_html = ""
                        for item in subgrades:
                            sub_css, _ = grade_class(item["score"])
                            sub_score = f"{item['score']:.1f}" if pd.notna(item["score"]) else "N/A"
                            rows_html += f'<div class="grade-sub"><span>{item["label"]}</span><strong class="{sub_css}">{sub_score}/10</strong></div>'
                        st.markdown(
                            f'<div class="grade-card"><div class="grade-head"><span class="grade-pos">{position}</span><span class="grade-score {css}">{score_text}</span></div><div style="font-size:.78rem;color:#9ba8ba;margin-bottom:8px">{team_name} vs. opposing defense · {tag}</div>{rows_html}</div>',
                            unsafe_allow_html=True,
                        )

                    st.markdown(f"### Week {betting_week} matchups")
                    st.caption("Grades compare projected position production with league averages. A+/A = elite or excellent (blue); B = favorable (green); C = average/mixed (yellow); D = difficult (orange); F = toughest (red). Numeric calculations remain behind the scenes. TDs are excluded from grading.")
                    filter_col, sort_col = st.columns([1, 1])
                    with filter_col:
                        matchup_filter = st.selectbox(
                            "Show matchups", ["All matchups", "At least one B-or-better grade", "Best matchups (average B-or-better)", "Only matchups with a D/F grade"],
                            key="betting_matchup_filter")
                    with sort_col:
                        sort_matchups = st.checkbox("Sort by strongest matchup first", value=True, key="betting_sort_matchups")

                    matchup_cards = []
                    export_rows = []
                    for _, game in week_games.iterrows():
                        home_team = str(game["home_team"]).upper()
                        away_team = str(game["away_team"]).upper()
                        if home_team not in TEAM_NAMES or away_team not in TEAM_NAMES:
                            continue
                        game_sides = []
                        grades_for_game = []
                        for offense_team, defense_team in [(away_team, home_team), (home_team, away_team)]:
                            position_results = {}
                            for pos in ["QB", "RB", "WR", "TE"]:
                                overall, subgrades = make_position_grade(offense_team, defense_team, pos)
                                position_results[pos] = {"overall": overall, "subgrades": subgrades}
                                if pd.notna(overall):
                                    grades_for_game.append(float(overall))
                                row = {"Week": betting_week, "Matchup": f"{TEAM_NAMES[away_team]} at {TEAM_NAMES[home_team]}",
                                       "Offensive team": TEAM_NAMES[offense_team], "Position": pos,
                                       "Opponent defense": TEAM_NAMES[defense_team],
                                       "Overall grade": round(overall, 1) if pd.notna(overall) else None,
                                       "Letter grade": letter_grade(overall)}
                                for sub in subgrades:
                                    row[sub["label"] + " grade"] = round(sub["score"], 1) if pd.notna(sub["score"]) else None
                                    row[sub["label"] + " offense avg/game"] = round(sub["offense"], 1) if pd.notna(sub["offense"]) else None
                                    row[sub["label"] + " allowed/game"] = round(sub["allowed"], 1) if pd.notna(sub["allowed"]) else None
                                    row[sub["label"] + " projected/game"] = round(sub["projected"], 1) if pd.notna(sub["projected"]) else None
                                    row[sub["label"] + " league avg/game"] = round(sub["league"], 1) if pd.notna(sub["league"]) else None
                                export_rows.append(row)
                            game_sides.append({"offense": offense_team, "defense": defense_team, "positions": position_results})
                        average_grade = float(np.mean(grades_for_game)) if grades_for_game else np.nan
                        has_green = any(g >= 7 for g in grades_for_game)
                        has_red = any(g < 4.9 for g in grades_for_game)
                        if matchup_filter == "At least one B-or-better grade" and not has_green:
                            continue
                        if matchup_filter == "Best matchups (average B-or-better)" and (pd.isna(average_grade) or average_grade < 7):
                            continue
                        if matchup_filter == "Only matchups with a D/F grade" and not has_red:
                            continue
                            # Rank all eight team/position combinations in this game and spotlight
                        # the three strongest. These are the model's best relative matchups,
                        # not guarantees of player performance.
                        ranked_positions = []
                        for side in game_sides:
                            for pos in ["QB", "RB", "WR", "TE"]:
                                result = side["positions"][pos]
                                score = result["overall"]
                                if pd.notna(score):
                                    ranked_positions.append({
                                        "offense": side["offense"], "defense": side["defense"],
                                        "position": pos, "score": float(score),
                                        "subgrades": result["subgrades"]
                                    })
                        ranked_positions.sort(key=lambda item: item["score"], reverse=True)
                        top_three = ranked_positions[:3]
                        matchup_cards.append({"away": away_team, "home": home_team, "sides": game_sides,
                                              "average": average_grade, "has_green": has_green, "has_red": has_red,
                                              "top_three": top_three})

                    if sort_matchups:
                        matchup_cards.sort(key=lambda x: (pd.isna(x["average"]), -(x["average"] if pd.notna(x["average"]) else -1)))
                    st.caption(f"Showing {len(matchup_cards)} of {len(week_games)} games · Defensive sample: {betting_window}")

                    def score_badge(score):
                        css, grade = grade_class(score)
                        return f'<span class="{css}" style="font-weight:900;font-size:1.05rem">{grade}</span>'

                    if not matchup_cards:
                        st.info("No matchups match that filter. Try All matchups or change the defensive sample.")
                    for card in matchup_cards:
                        away_team, home_team = card["away"], card["home"]
                        avg_label = f" · avg {card['average']:.1f}" if pd.notna(card["average"]) else ""
                        with st.expander(f"🏈 {TEAM_NAMES[away_team]} at {TEAM_NAMES[home_team]}{avg_label}", expanded=False):
                            st.markdown("#### 🎯 Top 3 positional matchups")
                            st.caption("Ranked by overall position grade across both offenses. Each card explains its strongest/weakest stat, projected production versus the league baseline, and the inputs behind the projection. Rankings are descriptive, not betting guarantees.")
                            if card["top_three"]:
                                top_cols = st.columns(3)
                                for rank, (col, pick) in enumerate(zip(top_cols, card["top_three"]), start=1):
                                    with col:
                                        css, tag = grade_class(pick["score"])
                                        st.markdown(
                                            f"<div class='grade-card' style='padding:12px;min-height:150px'>"
                                            f"<div style='font-size:.72rem;color:#d5ff3f;font-weight:800'>#{rank} BEST MATCHUP</div>"
                                            f"<div style='font-size:1rem;font-weight:800;margin:.35rem 0'>{TEAM_NAMES[pick['offense']]} {pick['position']}</div>"
                                            f"<div style='font-size:.76rem;color:#9ba8ba'>vs. {TEAM_NAMES[pick['defense']]}</div>"
                                            f"<div class='{css}' style='font-size:1.55rem;font-weight:900;margin-top:.35rem'>{letter_grade(pick['score'])}</div>"
                                            f"<div style='font-size:.68rem;color:#9ba8ba'>{tag}</div></div>",
                                            unsafe_allow_html=True,
                                        )
                                        valid_metrics = [item for item in pick["subgrades"] if pd.notna(item["score"])]
                                        if valid_metrics:
                                            best_metric = max(valid_metrics, key=lambda item: item["score"])
                                            weakest_metric = min(valid_metrics, key=lambda item: item["score"])
                                            st.caption(f"**Best component:** {best_metric['label']} · {letter_grade(best_metric['score'])}")
                                            if len(valid_metrics) > 1:
                                                st.caption(f"**Weakest component:** {weakest_metric['label']} · {letter_grade(weakest_metric['score'])}")

                                            # Explain the grade with the actual model inputs, not a betting promise.
                                            reference = next((item for item in valid_metrics if item is best_metric), valid_metrics[0])
                                            if pd.notna(reference["projected"]) and pd.notna(reference["league"]) and reference["league"] > 0:
                                                delta_pct = (reference["projected"] / reference["league"] - 1) * 100
                                                direction = "above" if delta_pct >= 0 else "below"
                                                st.caption(f"**{reference['label']} projection:** {reference['projected']:.1f}/game vs. league avg {reference['league']:.1f} ({abs(delta_pct):.0f}% {direction}).")
                                            if pd.notna(reference["offense"]) and pd.notna(reference["allowed"]):
                                                st.caption(f"Offense averages {reference['offense']:.1f}/game; opponent allows {reference['allowed']:.1f}/game.")

                                            if pick["score"] >= 8.5:
                                                takeaway = "Strong statistical matchup relative to the league baseline."
                                            elif pick["score"] >= 7:
                                                takeaway = "Favorable on the model's production baseline; check player usage and availability."
                                            elif pick["score"] >= 4.9:
                                                takeaway = "Mixed profile—look at the component grades to see what drives the score."
                                            else:
                                                takeaway = "Below-average statistical setup despite ranking among this game's top available grades."
                                            st.markdown(f"<div style='font-size:.78rem;color:#d5dce7;margin-top:.35rem'>{takeaway}</div>", unsafe_allow_html=True)

                                            # Add player-level context for the position's strongest component.
                                            # The team/position grade stays team-based; this section identifies
                                            # the players whose recent production may be driving that matchup.
                                            metric_col = GRADE_METRICS.get(pick["position"], {}).get(best_metric["label"])
                                            player_name_col = "player_display_name" if "player_display_name" in player_stats.columns else ("player_name" if "player_name" in player_stats.columns else None)
                                            if metric_col and metric_col in player_stats.columns and player_name_col:
                                                player_rows = player_stats[
                                                    (player_stats["team"] == pick["offense"])
                                                    & (player_stats["position"] == pick["position"])
                                                ].copy()
                                                if not player_rows.empty:
                                                    player_rows["week"] = pd.to_numeric(player_rows["week"], errors="coerce")
                                                    player_rows = player_rows.sort_values([c for c in ["week", "game_id"] if c in player_rows.columns], ascending=False)
                                                    recent_n = 5 if betting_window == "Season" else (5 if betting_window == "Last 5 games" else 3)
                                                    player_rows = player_rows.groupby(player_name_col, dropna=True, group_keys=False).head(recent_n)
                                                    player_rows[metric_col] = pd.to_numeric(player_rows[metric_col], errors="coerce")
                                                    leaders = (player_rows.groupby(player_name_col)[metric_col]
                                                               .agg(["mean", "count"]).reset_index()
                                                               .sort_values("mean", ascending=False).head(2))
                                                    if not leaders.empty:
                                                        st.markdown("**Players to research**")
                                                        for _, leader in leaders.iterrows():
                                                            player_name = str(leader[player_name_col])
                                                            # Show available opportunity indicators, never assume missing columns exist.
                                                            original_rows = player_rows[player_rows[player_name_col].astype(str) == player_name]
                                                            usage_bits = []
                                                            usage_candidates = [
                                                                ("Targets", "targets"), ("Carries", "carries"),
                                                                ("Receptions", "receptions"), ("Rushing attempts", "rushing_attempts"),
                                                            ]
                                                            for usage_label, usage_col in usage_candidates:
                                                                if usage_col in original_rows.columns:
                                                                    usage_avg = safe_mean(original_rows[usage_col])
                                                                    if pd.notna(usage_avg):
                                                                        usage_bits.append(f"{usage_label.lower()} {usage_avg:.1f}/game")
                                                            usage_text = " · ".join(usage_bits[:2])
                                                            st.caption(f"{player_name}: {safe_mean(original_rows[metric_col]):.1f} {best_metric['label'].lower()}/game over last {int(leader['count'])} games" + (f" · {usage_text}" if usage_text else ""))
                                                    else:
                                                        st.caption("No player-level recent averages available for this position yet.")
                                                else:
                                                    st.caption("No player game logs available for this team and position yet.")
                            else:
                                st.info("Not enough data to rank positional matchups for this game.")
                            st.markdown("---")
                            for side in card["sides"]:
                                offense_team, defense_team = side["offense"], side["defense"]
                                st.markdown(f"**{TEAM_NAMES[offense_team]} offense** <span class='small-muted'>vs. {TEAM_NAMES[defense_team]} defense</span>", unsafe_allow_html=True)
                                grade_cols = st.columns(4)
                                for col, pos in zip(grade_cols, ["QB", "RB", "WR", "TE"]):
                                    with col:
                                        score = side["positions"][pos]["overall"]
                                        css, tag = grade_class(score)
                                        score_text = letter_grade(score)
                                        st.markdown(f"<div class='grade-card' style='padding:9px;text-align:center;margin-bottom:8px'><div style='font-size:.8rem;color:#a8b6c9'>{pos}</div><div class='{css}' style='font-size:1.45rem;font-weight:900'>{score_text}</div></div>", unsafe_allow_html=True)
                                with st.expander(f"View {TEAM_NAMES[offense_team]} subgrades & stats", expanded=False):
                                    detail_rows = []
                                    for pos in ["QB", "RB", "WR", "TE"]:
                                        for item in side["positions"][pos]["subgrades"]:
                                            detail_rows.append({
                                                "Position": pos, "Metric": item["label"],
                                                "Grade": f"{item['score']:.1f}" if pd.notna(item["score"]) else "—",
                                                "Offense avg/game": display_num(item["offense"]),
                                                "Defense allows/game": display_num(item["allowed"]),
                                                "Projected/game": display_num(item["projected"]),
                                                "League avg/game": display_num(item["league"]),
                                            })
                                    if detail_rows:
                                        st.dataframe(pd.DataFrame(detail_rows), hide_index=True, use_container_width=True)
                            st.caption("Grades are descriptive matchup indicators, not predictions or guarantees. Smaller samples can be volatile.")

                    # CSV gives one row per team/position, including overall and component grades.
                    export_rows = []
                    for _, game in week_games.iterrows():
                        home_team = str(game["home_team"]).upper()
                        away_team = str(game["away_team"]).upper()
                        if home_team not in TEAM_NAMES or away_team not in TEAM_NAMES:
                            continue
                        game_export = []
                        for offense_team, defense_team in [(away_team, home_team), (home_team, away_team)]:
                            for pos in ["QB", "RB", "WR", "TE"]:
                                overall, subgrades = make_position_grade(offense_team, defense_team, pos)
                                row = {"Week": betting_week, "Matchup": f"{TEAM_NAMES[away_team]} at {TEAM_NAMES[home_team]}",
                                       "Offensive team": TEAM_NAMES[offense_team], "Position": pos,
                                       "Opponent defense": TEAM_NAMES[defense_team],
                                       "Overall grade": round(overall, 1) if pd.notna(overall) else None,
                                       "Letter grade": letter_grade(overall)}
                                for sub in subgrades:
                                    row[sub["label"] + " grade"] = round(sub["score"], 1) if pd.notna(sub["score"]) else None
                                    row[sub["label"] + " allowed/game"] = round(sub["allowed"], 1) if pd.notna(sub["allowed"]) else None
                                game_export.append(row)
                        ranked_export = sorted(
                            [r for r in game_export if pd.notna(r.get("Overall grade"))],
                            key=lambda r: r["Overall grade"], reverse=True
                        )
                        top_keys = {(r["Offensive team"], r["Position"]) for r in ranked_export[:3]}
                        for row in game_export:
                            row["Top 3 in game"] = (row["Offensive team"], row["Position"]) in top_keys
                            export_rows.append(row)
                    if export_rows:
                        st.download_button(
                            "Download weekly position grades (CSV)",
                            data=pd.DataFrame(export_rows).to_csv(index=False).encode("utf-8"),
                            file_name=f"nfl_week_{betting_week}_position_grades_{season}.csv",
                            mime="text/csv", key="download_betting_matchups",
                        )
    with st.expander("🏈 Touchdowns Allowed by Defense", expanded=False):
        st.markdown('<div class="panel-title">Defensive touchdowns allowed by position</div>', unsafe_allow_html=True)
        st.caption("Shows touchdowns surrendered per game and total touchdowns in the selected sample. This is a descriptive stat table, separate from the positional matchup grade.")

        td_defense_rows = player_stats[
            player_stats["position"].isin(["QB", "RB", "WR", "TE"])
        ].copy()
        td_metric_map = {
            "QB passing TDs": ("QB", "passing_tds"),
            "RB rushing TDs": ("RB", "rushing_tds"),
            "RB receiving TDs": ("RB", "receiving_tds"),
            "WR receiving TDs": ("WR", "receiving_tds"),
            "TE receiving TDs": ("TE", "receiving_tds"),
        }
        for _, metric_col in td_metric_map.values():
            if metric_col not in td_defense_rows.columns:
                td_defense_rows[metric_col] = 0
            td_defense_rows[metric_col] = pd.to_numeric(
                td_defense_rows[metric_col], errors="coerce"
            ).fillna(0)

        td_game_rows = []
        for (game_id, week, defense), group in td_defense_rows.groupby(
            ["game_id", "week", "opponent_team"], dropna=False
        ):
            row = {"game_id": game_id, "Week": week, "Defense": defense}
            for label, (position, metric_col) in td_metric_map.items():
                row[label] = float(group.loc[group["position"] == position, metric_col].sum())
            td_game_rows.append(row)

        if not td_game_rows:
            st.info("No completed player touchdown data is available for this season yet.")
        else:
            td_by_game = pd.DataFrame(td_game_rows)
            td_by_game["Week"] = pd.to_numeric(td_by_game["Week"], errors="coerce")
            td_by_game = td_by_game.sort_values(["Defense", "Week", "game_id"], ascending=[True, False, False])
            sample_n = None if betting_window == "Season" else (5 if betting_window == "Last 5 games" else 3)
            if sample_n is not None:
                td_by_game = td_by_game.groupby("Defense", group_keys=False).head(sample_n)

            summary_rows = []
            for defense, group in td_by_game.groupby("Defense"):
                row = {
                    "Defense": f"{TEAM_NAMES.get(str(defense), str(defense))} ({defense})",
                    "Games": int(group["game_id"].nunique()),
                }
                for label in td_metric_map:
                    row[f"{label}/game"] = round(float(group[label].sum() / max(group["game_id"].nunique(), 1)), 2)
                    row[f"{label} total"] = int(group[label].sum())
                summary_rows.append(row)
            td_summary = pd.DataFrame(summary_rows)
            td_summary = td_summary.sort_values("QB passing TDs/game", ascending=True)
            st.dataframe(td_summary, hide_index=True, use_container_width=True)
            st.download_button(
                "Download defensive touchdowns allowed (CSV)",
                data=td_summary.to_csv(index=False).encode("utf-8"),
                file_name=f"nfl_defensive_touchdowns_allowed_{season}_{betting_window.lower().replace(' ', '_')}.csv",
                mime="text/csv", key="download_defensive_tds",
            )

    with st.expander("📈 Team Offense by Position", expanded=False):
        st.markdown('<div class="panel-title">Team production by position</div>', unsafe_allow_html=True)
        oc1, oc2, oc3 = st.columns(3)
        with oc1:
            off_team = st.selectbox("Offensive team", TEAM_CODES, index=TEAM_CODES.index("CHI"),
                                    format_func=lambda x: f"{TEAM_NAMES[x]} ({x})", key="position_off_team")
        with oc2:
            off_pos = st.selectbox("Position", ["QB", "RB", "WR", "TE"], key="position_off_pos")
        with oc3:
            off_window = st.selectbox("Recent sample", [3, 5, 10], index=1,
                                      format_func=lambda n: f"Last {n} team games", key="position_off_window")
        metrics = POSITION_METRICS[off_pos]
        off_rows = player_stats[(player_stats["team"] == off_team) & (player_stats["position"] == off_pos)].copy()
        if off_rows.empty:
            st.info(f"No {off_pos} player statistics found for {TEAM_NAMES[off_team]} in {season}.")
        else:
            # Sum players at a position within each team game, then average across games.
            agg_cols = [c for c in metrics.values() if c in off_rows.columns]
            game_group_cols = [c for c in ["game_id", "week", "opponent_team"] if c in off_rows.columns]
            game_totals = off_rows.groupby(game_group_cols, dropna=False)[agg_cols].sum(min_count=1).reset_index()
            game_totals = game_totals.sort_values([c for c in ["week", "game_id"] if c in game_totals.columns], ascending=False)
            recent_totals = game_totals.head(off_window)
            st.markdown(f"### {TEAM_NAMES[off_team]} — {off_pos}")
            st.caption("Team totals include all players at the selected position in each game.")
            cards = st.columns(len(metrics))
            for card, (label, col) in zip(cards, metrics.items()):
                if col in game_totals.columns:
                    card.metric(f"Season {label} / game", display_num(safe_mean(game_totals[col])))
                    card.caption(f"Last {len(recent_totals)}: {display_num(safe_mean(recent_totals[col]))}")
            st.markdown("#### Position production by game")
            rename = {"week": "Week", "opponent_team": "Opponent"}
            rename.update({col: label for label, col in metrics.items() if col in game_totals.columns})
            show_cols = [c for c in ["week", "opponent_team"] + agg_cols if c in game_totals.columns]
            display_game_totals = game_totals[show_cols].rename(columns=rename)
            st.dataframe(display_game_totals, use_container_width=True, hide_index=True)
            st.download_button("Download position game log", display_game_totals.to_csv(index=False).encode("utf-8"),
                               file_name=f"{off_team}_{off_pos}_{season}_position_stats.csv", mime="text/csv", key="download_off_position")

    with st.expander("🛡️ Defense vs. Position", expanded=False):
        st.markdown('<div class="panel-title">Opponent production allowed by position</div>', unsafe_allow_html=True)
        dc1, dc2, dc3 = st.columns(3)
        with dc1:
            def_team = st.selectbox("Defense", TEAM_CODES, index=TEAM_CODES.index("CHI"),
                                    format_func=lambda x: f"{TEAM_NAMES[x]} ({x})", key="position_def_team")
        with dc2:
            def_pos = st.selectbox("Opposing position", ["QB", "RB", "WR", "TE"], key="position_def_pos")
        with dc3:
            def_window = st.selectbox("Recent sample", [3, 5, 10], index=1,
                                      format_func=lambda n: f"Last {n} defensive games", key="position_def_window")
        metrics = POSITION_METRICS[def_pos]
        allowed_players = player_stats[(player_stats["opponent_team"] == def_team) & (player_stats["position"] == def_pos)].copy()
        if allowed_players.empty:
            st.info(f"No opposing {def_pos} statistics found against {TEAM_NAMES[def_team]} in {season}.")
        else:
            agg_cols = [c for c in metrics.values() if c in allowed_players.columns]
            game_group_cols = [c for c in ["game_id", "week", "team"] if c in allowed_players.columns]
            game_totals = allowed_players.groupby(game_group_cols, dropna=False)[agg_cols].sum(min_count=1).reset_index()
            game_totals = game_totals.sort_values([c for c in ["week", "game_id"] if c in game_totals.columns], ascending=False)
            recent_totals = game_totals.head(def_window)
            st.markdown(f"### {TEAM_NAMES[def_team]} defense vs. {def_pos}")
            st.caption("Allowed totals combine all opposing players at the selected position within each game before averaging.")
            cards = st.columns(len(metrics))
            for card, (label, col) in zip(cards, metrics.items()):
                if col in game_totals.columns:
                    card.metric(f"{label} allowed / game", display_num(safe_mean(game_totals[col])))
                    card.caption(f"Last {len(recent_totals)}: {display_num(safe_mean(recent_totals[col]))}")
            st.markdown("#### Position production allowed by game")
            rename = {"week": "Week", "team": "Opponent"}
            rename.update({col: f"{label} allowed" for label, col in metrics.items() if col in game_totals.columns})
            show_cols = [c for c in ["week", "team"] + agg_cols if c in game_totals.columns]
            display_game_totals = game_totals[show_cols].rename(columns=rename)
            st.dataframe(display_game_totals, use_container_width=True, hide_index=True)
            st.download_button("Download defensive position log", display_game_totals.to_csv(index=False).encode("utf-8"),
                               file_name=f"{def_team}_vs_{def_pos}_{season}_allowed.csv", mime="text/csv", key="download_def_position")

# ------------------------------------------------------------
# 4. DASHBOARD / RANKINGS
# ------------------------------------------------------------
with tab_dashboard:
    st.markdown('<div class="panel-title">League-wide team rankings</div>', unsafe_allow_html=True)
    dash_metric = st.selectbox(
        "Rank teams by",
        ["Points scored / game", "Passing yards / game", "Rushing yards / game",
         "Points allowed / game", "Passing yards allowed / game", "Rushing yards allowed / game"],
        key="dash_metric",
    )
    metric_map = {
        "Points scored / game": ("points_for", False),
        "Passing yards / game": ("pass_for", False),
        "Rushing yards / game": ("rush_for", False),
        "Points allowed / game": ("points_allowed", True),
        "Passing yards allowed / game": ("pass_allowed", True),
        "Rushing yards allowed / game": ("rush_allowed", True),
    }
    col, ascending = metric_map[dash_metric]
    rows = []
    for code in TEAM_CODES:
        summary = team_summary(code)
        rows.append({
            "Team": TEAM_NAMES[code],
            "Games": summary["games"],
            "Points scored / game": summary["points_for"],
            "Pass yards / game": summary["pass_for"],
            "Rush yards / game": summary["rush_for"],
            "Points allowed / game": summary["points_allowed"],
            "Pass yards allowed / game": summary["pass_allowed"],
            "Rush yards allowed / game": summary["rush_allowed"],
        })
    dashboard = pd.DataFrame(rows)
    dashboard = dashboard.sort_values(col if col in dashboard.columns else "Team", ascending=ascending)
    # Map internal metric keys to displayed column names for ordering.
    sort_column = {
        "points_for": "Points scored / game", "pass_for": "Pass yards / game",
        "rush_for": "Rush yards / game", "points_allowed": "Points allowed / game",
        "pass_allowed": "Pass yards allowed / game", "rush_allowed": "Rush yards allowed / game",
    }[col]
    dashboard = dashboard.sort_values(sort_column, ascending=ascending, na_position="last")
    dashboard.insert(0, "Rank", range(1, len(dashboard) + 1))
    st.dataframe(
        dashboard.style.format({
            "Points scored / game": "{:.1f}", "Pass yards / game": "{:.1f}",
            "Rush yards / game": "{:.1f}", "Points allowed / game": "{:.1f}",
            "Pass yards allowed / game": "{:.1f}", "Rush yards allowed / game": "{:.1f}",
        }, na_rep="—"),
        use_container_width=True,
        hide_index=True,
    )
    st.download_button(
        "Download all-team dashboard CSV",
        data=dashboard.to_csv(index=False).encode("utf-8"),
        file_name=f"nfl_team_dashboard_{season}.csv",
        mime="text/csv",
    )
    st.caption("For yards/points allowed, lower values indicate stronger defense; the table sorts low-to-high for allowed categories.")

st.divider()
st.caption("Data source: nflverse via nflreadpy. This tool provides descriptive statistics and research context, not betting recommendations.")
