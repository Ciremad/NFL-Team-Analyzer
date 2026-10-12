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
for c in player_stats.columns:
    if c in {"passing_yards", "rushing_yards", "receiving_yards", "receptions", "passing_tds",
             "rushing_tds", "receiving_tds", "attempts", "carries", "targets", "completions"}:
        player_stats[c] = pd.to_numeric(player_stats[c], errors="coerce")


# Position-specific stat definitions. TDs are combined for RBs as rushing + receiving TDs.
POSITION_METRICS = {
    "QB": {"Passing yards": "passing_yards", "Passing TDs": "passing_tds", "Rushing yards": "rushing_yards"},
    "RB": {"Rushing yards": "rushing_yards", "Receiving yards": "receiving_yards", "Receptions": "receptions", "Total TDs": "total_tds"},
    "WR": {"Receiving yards": "receiving_yards", "Receptions": "receptions", "Receiving TDs": "receiving_tds"},
    "TE": {"Receiving yards": "receiving_yards", "Receptions": "receptions", "Receiving TDs": "receiving_tds"},
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

tab_matchup, tab_offense, tab_defense, tab_players, tab_betting, tab_dashboard = st.tabs([
    "⚔️ Matchup Analyzer", "📈 Team Offense by Position", "🛡️ Defense vs. Position",
    "🎯 Player Research", "💸 Betting Matchups", "🏆 Team Rankings"
])

# ------------------------------------------------------------
# 2. MATCHUP ANALYZER
# ------------------------------------------------------------
with tab_matchup:
    st.markdown('<div class="panel-title">Head-to-head matchup</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        team_a = st.selectbox("Team A offense", TEAM_CODES, index=TEAM_CODES.index("CHI"),
                              format_func=lambda x: f"{TEAM_NAMES[x]} ({x})", key="match_a")
    with c2:
        default_b = TEAM_CODES.index("GB")
        team_b = st.selectbox("Team B defense", TEAM_CODES, index=default_b,
                              format_func=lambda x: f"{TEAM_NAMES[x]} ({x})", key="match_b")
    if team_a == team_b:
        st.warning("Choose two different teams for a matchup.")
    else:
        a = team_summary(team_a)
        b = team_summary(team_b)
        c = team_summary(team_b)
        d = team_summary(team_a)

        st.markdown(f"### {TEAM_NAMES[team_a]} offense vs. {TEAM_NAMES[team_b]} defense")
        x1, x2, x3 = st.columns(3)
        x1.metric("A rushing yards / game", display_num(a["rush_for"]), f"Defense allows {display_num(b['rush_allowed'])}")
        x2.metric("A passing yards / game", display_num(a["pass_for"]), f"Defense allows {display_num(b['pass_allowed'])}")
        x3.metric("A points / game", display_num(a["points_for"]), f"Defense allows {display_num(b['points_allowed'])}")
        st.markdown("#### Simple matchup reference")
        m1, m2, m3 = st.columns(3)
        m1.metric("Rushing-yard midpoint", display_num(np.nanmean([a["rush_for"], b["rush_allowed"]])))
        m2.metric("Passing-yard midpoint", display_num(np.nanmean([a["pass_for"], b["pass_allowed"]])))
        m3.metric("Points midpoint", display_num(np.nanmean([a["points_for"], b["points_allowed"]])))
        st.caption("Midpoints are simple descriptive benchmarks (average of offense production and opponent allowance), not predictive models or betting advice.")

        st.divider()
        st.markdown(f"### {TEAM_NAMES[team_b]} offense vs. {TEAM_NAMES[team_a]} defense")
        x1, x2, x3 = st.columns(3)
        x1.metric("B rushing yards / game", display_num(c["rush_for"]), f"Defense allows {display_num(d['rush_allowed'])}")
        x2.metric("B passing yards / game", display_num(c["pass_for"]), f"Defense allows {display_num(d['pass_allowed'])}")
        x3.metric("B points / game", display_num(c["points_for"]), f"Defense allows {display_num(d['points_allowed'])}")
        y1, y2, y3 = st.columns(3)
        y1.metric("Rushing-yard midpoint", display_num(np.nanmean([c["rush_for"], d["rush_allowed"]])))
        y2.metric("Passing-yard midpoint", display_num(np.nanmean([c["pass_for"], d["pass_allowed"]])))
        y3.metric("Points midpoint", display_num(np.nanmean([c["points_for"], d["points_allowed"]])))

# ------------------------------------------------------------
# TEAM OFFENSE BY POSITION
# ------------------------------------------------------------
with tab_offense:
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

# ------------------------------------------------------------
# DEFENSE VS. POSITION
# ------------------------------------------------------------
with tab_defense:
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
                k1, k2, k3, k4 = st.columns(4)
                k1.metric("Season average", display_num(season_avg))
                k2.metric(f"Last {len(recent)} games", display_num(recent_avg))
                k3.metric("Latest game", display_num(pd.to_numeric(pd.Series([latest.get(metric_col)]), errors="coerce").iloc[0]))
                k4.metric("Position", pos)
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
    st.write("Each game shows an overall grade for QB, RB, WR, and TE on both teams, plus the subgrades that make up each score.")
    st.caption("Grades are based on what the opposing defense allows at each position compared with league averages. Overall grade is the simple average of that position's subgrades.")
    st.markdown("""
    <style>
    .grade-card {border:1px solid #2b394a;border-radius:12px;padding:12px;background:linear-gradient(145deg,#171f2b,#10151d);margin-bottom:8px;}
    .grade-head {display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:8px;}
    .grade-pos {font-size:1.05rem;font-weight:800;color:#f4f7fb;}
    .grade-score {font-size:1.5rem;font-weight:900;}
    .grade-sub {display:flex;justify-content:space-between;gap:8px;padding:5px 0;border-top:1px solid #2b394a;font-size:.88rem;color:#c4ceda;}
    .grade-green {color:#4ade80;} .grade-yellow {color:#facc15;} .grade-red {color:#fb7185;}
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

                    def offensive_average(team_code, position, metric_col, n=None):
                        rows = pos_game_totals[(pos_game_totals["team"] == team_code) & (pos_game_totals["position"] == position)].copy()
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

                    def grade_matchup(offense_value, allowed_value, league_value):
                        if any(pd.isna(value) for value in [offense_value, allowed_value, league_value]) or league_value <= 0:
                            return np.nan
                        # Blend the offense's normal production with what this defense allows.
                        # A matchup projection 25% above league average earns about an 8.5,
                        # making the scale more forgiving and intuitive than defense-only grading.
                        projected_value = (offense_value + allowed_value) / 2
                        ratio = projected_value / league_value
                        return float(np.clip(5.5 + 12 * (ratio - 1), 1, 10))

                    def grade_class(score):
                        if pd.isna(score):
                            return "grade-yellow", "N/A"
                        if score >= 8:
                            return "grade-green", "GREEN"
                        if score >= 5:
                            return "grade-yellow", "YELLOW"
                        return "grade-red", "RED"

                    def make_position_grade(offense, defense, position):
                        subgrades = []
                        for label, metric_col in GRADE_METRICS[position].items():
                            if metric_col not in pos_game_totals.columns:
                                continue
                            offense_avg = offensive_average(offense, position, metric_col, n_games)
                            allowed = defensive_allowed(defense, position, metric_col, n_games)
                            league_avg = league_allowed(position, metric_col, n_games)
                            score = grade_matchup(offense_avg, allowed, league_avg)
                            subgrades.append({"label": label, "score": score, "offense_avg": offense_avg, "allowed": allowed, "league": league_avg})
                        available = [item["score"] for item in subgrades if pd.notna(item["score"])]
                        overall = float(np.mean(available)) if available else np.nan
                        return overall, subgrades

                    def render_grade_card(team_name, position, overall, subgrades):
                        css, tag = grade_class(overall)
                        score_text = f"{overall:.1f}/10" if pd.notna(overall) else "N/A"
                        rows_html = ""
                        for item in subgrades:
                            sub_css, _ = grade_class(item["score"])
                            sub_score = f"{item['score']:.1f}" if pd.notna(item["score"]) else "N/A"
                            rows_html += f'<div class="grade-sub"><span>{item["label"]}</span><strong class="{sub_css}">{sub_score}/10</strong></div>'
                        st.markdown(
                            f'<div class="grade-card"><div class="grade-head"><span class="grade-pos">{position}</span><span class="grade-score {css}">{score_text}</span></div><div style="font-size:.78rem;color:#9ba8ba;margin-bottom:8px">{team_name} vs. opposing defense · {tag}</div>{rows_html}</div>',
                            unsafe_allow_html=True,
                        )

                    st.markdown(f"### Week {betting_week} position grades")
                    st.caption("Grades blend the offense's average production with what the opposing defense allows, then compare that matchup estimate with the league average. Green (8.0–10) = favorable · Yellow (5.0–7.9) = mixed/average · Red (1.0–4.9) = difficult. The scale is intentionally lenient: a matchup projection 25% above league average grades about 8.5.")
                    for _, game in week_games.iterrows():
                        home_team = str(game["home_team"]).upper()
                        away_team = str(game["away_team"]).upper()
                        if home_team not in TEAM_NAMES or away_team not in TEAM_NAMES:
                            continue
                        st.markdown(f"#### {TEAM_NAMES[away_team]} at {TEAM_NAMES[home_team]}")
                        sides = st.columns(2)
                        for side_col, offense_team, defense_team in [
                            (sides[0], away_team, home_team),
                            (sides[1], home_team, away_team),
                        ]:
                            with side_col:
                                st.markdown(f"**{TEAM_NAMES[offense_team]} offense**")
                                st.caption(f"Faces {TEAM_NAMES[defense_team]} defense")
                                for pos in ["QB", "RB", "WR", "TE"]:
                                    overall, subgrades = make_position_grade(offense_team, defense_team, pos)
                                    render_grade_card(TEAM_NAMES[offense_team], pos, overall, subgrades)

                    # CSV gives one row per team/position, including overall and component grades.
                    export_rows = []
                    for _, game in week_games.iterrows():
                        home_team = str(game["home_team"]).upper()
                        away_team = str(game["away_team"]).upper()
                        if home_team not in TEAM_NAMES or away_team not in TEAM_NAMES:
                            continue
                        for offense_team, defense_team in [(away_team, home_team), (home_team, away_team)]:
                            for pos in ["QB", "RB", "WR", "TE"]:
                                overall, subgrades = make_position_grade(offense_team, defense_team, pos)
                                row = {"Week": betting_week, "Matchup": f"{TEAM_NAMES[away_team]} at {TEAM_NAMES[home_team]}",
                                       "Offensive team": TEAM_NAMES[offense_team], "Position": pos,
                                       "Opponent defense": TEAM_NAMES[defense_team],
                                       "Overall grade": round(overall, 1) if pd.notna(overall) else None}
                                for sub in subgrades:
                                    row[sub["label"] + " grade"] = round(sub["score"], 1) if pd.notna(sub["score"]) else None
                                    row[sub["label"] + " offense avg/game"] = round(sub["offense_avg"], 1) if pd.notna(sub["offense_avg"]) else None
                                    row[sub["label"] + " allowed/game"] = round(sub["allowed"], 1) if pd.notna(sub["allowed"]) else None
                                export_rows.append(row)
                    if export_rows:
                        st.download_button(
                            "Download weekly position grades (CSV)",
                            data=pd.DataFrame(export_rows).to_csv(index=False).encode("utf-8"),
                            file_name=f"nfl_week_{betting_week}_position_grades_{season}.csv",
                            mime="text/csv", key="download_betting_matchups",
                        )
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
