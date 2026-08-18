"""
analytics.py
------------
Pure analytics/derivation layer. Takes raw data pulled from the
Database class and turns it into summary dictionaries and Plotly
figures for the Match Analytics and Player Statistics pages. Contains
no Streamlit calls and no direct SQL - only pandas/numpy/plotly logic
operating on data already fetched via database.py.
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

import config
import utils


# --------------------------------------------------------------------------
# MATCH SUMMARY
# --------------------------------------------------------------------------
def build_match_summary(db, innings_id):
    """Returns a dict of headline summary stats for one innings:
    highest scorer, best bowler, phase-wise scores, boundary count,
    dot balls, overall run rate."""
    innings = db.get_innings(innings_id)
    match = db.get_match(innings["match_id"])
    batting_card = db.get_batting_card(innings_id)
    bowling_card = db.get_bowling_card(innings_id)
    balls = db.get_balls(innings_id)

    total_overs = match["total_overs"] or (len(balls) // config.BALLS_PER_OVER + 1)
    powerplay_end_over = max(1, round(total_overs * config.POWERPLAY_OVERS_FRACTION))
    death_start_over = max(1, total_overs - round(total_overs * config.DEATH_OVERS_FRACTION))

    powerplay_runs = sum(b["runs_batter"] + b["extra_runs"] for b in balls
                          if b["over_number"] < powerplay_end_over)
    death_runs = sum(b["runs_batter"] + b["extra_runs"] for b in balls
                      if b["over_number"] >= death_start_over)
    middle_runs = (innings["total_runs"] or 0) - powerplay_runs - death_runs

    boundary_count = sum(1 for b in balls if b["runs_batter"] in (4, 6))
    dot_balls = sum(1 for b in balls if b["is_legal_delivery"] and
                     b["runs_batter"] == 0 and not b["extra_type"] and not b["is_wicket"])

    highest_scorer = max(batting_card, key=lambda r: r["runs"], default=None)
    best_bowler = max(bowling_card, key=lambda r: (r["wickets"], -r["runs_conceded"]),
                       default=None)

    run_rate = utils.calc_run_rate(innings["total_runs"] or 0, innings["total_balls"] or 0)

    return {
        "highest_scorer": db.get_player_name(highest_scorer["player_id"]) if highest_scorer else "-",
        "highest_scorer_runs": highest_scorer["runs"] if highest_scorer else 0,
        "best_bowler": db.get_player_name(best_bowler["player_id"]) if best_bowler else "-",
        "best_bowler_figures": f"{best_bowler['wickets']}/{best_bowler['runs_conceded']}" if best_bowler else "-",
        "powerplay_runs": powerplay_runs,
        "middle_overs_runs": max(middle_runs, 0),
        "death_overs_runs": death_runs,
        "boundary_count": boundary_count,
        "dot_balls": dot_balls,
        "run_rate": run_rate,
    }


# --------------------------------------------------------------------------
# RESULT DETERMINATION
# --------------------------------------------------------------------------
def determine_result(db, match_id):
    """Compares both innings and returns winner/margin/result type."""
    match = db.get_match(match_id)
    innings_list = db.get_innings_by_match(match_id)
    if len(innings_list) < 2:
        return None

    first, second = innings_list[0], innings_list[1]
    team_a_id, team_b_id = match["team_a_id"], match["team_b_id"]

    first_runs, second_runs = first["total_runs"] or 0, second["total_runs"] or 0

    if second_runs > first_runs:
        winner_team_id = second["batting_team_id"]
        wickets_left = 10 - (second["total_wickets"] or 0)
        result_type = "Won by Wickets"
        margin = f"{wickets_left} wicket{'s' if wickets_left != 1 else ''}"
    elif first_runs > second_runs:
        winner_team_id = first["batting_team_id"]
        run_margin = first_runs - second_runs
        result_type = "Won by Runs"
        margin = f"{run_margin} run{'s' if run_margin != 1 else ''}"
    else:
        winner_team_id = None
        result_type = "Tie"
        margin = "Scores Level - Super Over Required"

    # Player of the match: highest combined runs+wickets impact across both innings
    candidates = {}
    for inn in innings_list:
        for row in db.get_batting_card(inn["innings_id"]):
            pid = row["player_id"]
            candidates.setdefault(pid, {"runs": 0, "wickets": 0})
            candidates[pid]["runs"] += row["runs"]
        for row in db.get_bowling_card(inn["innings_id"]):
            pid = row["player_id"]
            candidates.setdefault(pid, {"runs": 0, "wickets": 0})
            candidates[pid]["wickets"] += row["wickets"]

    def impact_score(v):
        return v["runs"] + v["wickets"] * 25  # simple weighted impact metric

    player_of_match_id = max(candidates, key=lambda k: impact_score(candidates[k]),
                              default=None)

    summary = (f"{db.get_team_name(winner_team_id)} won by {margin}"
               if winner_team_id else "Match Tied - Super Over Required")

    return {
        "winner_team_id": winner_team_id,
        "result_type": result_type,
        "margin": margin,
        "player_of_match_id": player_of_match_id,
        "summary": summary,
    }


# --------------------------------------------------------------------------
# CHART BUILDERS (all return plotly Figure objects)
# --------------------------------------------------------------------------
def _cumulative_series(balls):
    """Helper: returns (over_progress, cumulative_runs, cumulative_wkts)."""
    progress, cum_runs, cum_wkts = [0.0], [0], [0]
    r, w = 0, 0
    for b in balls:
        r += b["runs_batter"] + b["extra_runs"]
        if b["is_wicket"]:
            w += 1
        if b["is_legal_delivery"]:
            over_num = b["over_number"] + (b["ball_in_over"] / config.BALLS_PER_OVER)
        else:
            over_num = progress[-1]
        progress.append(over_num)
        cum_runs.append(r)
        cum_wkts.append(w)
    return progress, cum_runs, cum_wkts


def worm_graph(db, innings_list, team_names):
    """Cumulative runs across overs for each innings (the classic 'worm')."""
    fig = go.Figure()
    colors = [config.THEME["team_a"], config.THEME["team_b"]]
    for i, inn in enumerate(innings_list):
        balls = db.get_balls(inn["innings_id"])
        progress, cum_runs, _ = _cumulative_series(balls)
        fig.add_trace(go.Scatter(
            x=progress, y=cum_runs, mode="lines+markers",
            name=team_names[i], line=dict(color=colors[i % 2], width=3),
        ))
    fig.update_layout(
        template=config.PLOTLY_TEMPLATE, title="Worm Graph - Cumulative Runs",
        xaxis_title="Overs", yaxis_title="Runs", height=420,
        legend=dict(orientation="h", y=-0.2),
    )
    return fig


def manhattan_graph(db, innings_id, team_name):
    """Bar chart of runs scored per over."""
    overs = db.get_overs(innings_id)
    df = pd.DataFrame(overs) if overs else pd.DataFrame(columns=["over_number", "runs_in_over", "wickets_in_over"])
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["over_number"] + 1 if not df.empty else [],
        y=df["runs_in_over"] if not df.empty else [],
        marker_color=config.THEME["primary"], name="Runs",
        text=df["wickets_in_over"].apply(lambda w: f"{w}W" if w else "") if not df.empty else [],
        textposition="outside",
    ))
    fig.update_layout(
        template=config.PLOTLY_TEMPLATE, title=f"Manhattan Graph - {team_name}",
        xaxis_title="Over", yaxis_title="Runs in Over", height=380,
    )
    return fig


def run_rate_graph(db, innings_list, team_names):
    fig = go.Figure()
    colors = [config.THEME["team_a"], config.THEME["team_b"]]
    for i, inn in enumerate(innings_list):
        overs = db.get_overs(inn["innings_id"])
        if not overs:
            continue
        cum_runs, rrs = 0, []
        over_nums = []
        for o in overs:
            cum_runs += o["runs_in_over"]
            balls_bowled = (o["over_number"] + 1) * config.BALLS_PER_OVER
            rrs.append(utils.calc_run_rate(cum_runs, balls_bowled))
            over_nums.append(o["over_number"] + 1)
        fig.add_trace(go.Scatter(
            x=over_nums, y=rrs, mode="lines+markers", name=team_names[i],
            line=dict(color=colors[i % 2], width=3),
        ))
    fig.update_layout(
        template=config.PLOTLY_TEMPLATE, title="Run Rate Progression",
        xaxis_title="Over", yaxis_title="Run Rate", height=380,
    )
    return fig


def wickets_timeline(db, innings_id):
    fow = db.get_fall_of_wickets(innings_id)
    df = pd.DataFrame(fow) if fow else pd.DataFrame(columns=["wicket_number", "team_score", "over_ball"])
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["over_ball"] if not df.empty else [],
        y=df["team_score"] if not df.empty else [],
        mode="markers+text", marker=dict(size=14, color=config.THEME["danger"]),
        text=df["wicket_number"].apply(lambda w: f"W{w}") if not df.empty else [],
        textposition="top center", name="Wickets",
    ))
    fig.update_layout(
        template=config.PLOTLY_TEMPLATE, title="Wickets Timeline",
        xaxis_title="Over.Ball", yaxis_title="Team Score", height=380,
    )
    return fig


def boundary_timeline(db, innings_id):
    balls = db.get_balls(innings_id)
    fours = [(b["over_number"] + b["ball_in_over"] / config.BALLS_PER_OVER)
             for b in balls if b["runs_batter"] == 4]
    sixes = [(b["over_number"] + b["ball_in_over"] / config.BALLS_PER_OVER)
             for b in balls if b["runs_batter"] == 6]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=fours, y=[4] * len(fours), mode="markers",
                              marker=dict(size=10, color=config.THEME["primary"]),
                              name="Fours"))
    fig.add_trace(go.Scatter(x=sixes, y=[6] * len(sixes), mode="markers",
                              marker=dict(size=12, color=config.THEME["secondary"],
                                          symbol="star"),
                              name="Sixes"))
    fig.update_layout(
        template=config.PLOTLY_TEMPLATE, title="Boundary Timeline",
        xaxis_title="Over", yaxis_title="Boundary Runs", height=380,
        yaxis=dict(tickvals=[4, 6]),
    )
    return fig


def run_distribution_pie(innings_summary_runs):
    """innings_summary_runs: dict like {'1s':.., '2s':.., '4s':.., '6s':.., 'Extras':..}"""
    labels = list(innings_summary_runs.keys())
    values = list(innings_summary_runs.values())
    fig = px.pie(names=labels, values=values, hole=0.45,
                 color_discrete_sequence=px.colors.sequential.Teal)
    fig.update_layout(template=config.PLOTLY_TEMPLATE,
                       title="Run Distribution", height=380)
    return fig


def run_distribution_breakdown(db, innings_id):
    balls = db.get_balls(innings_id)
    dist = {"1s": 0, "2s": 0, "3s": 0, "4s": 0, "6s": 0, "Dots": 0, "Extras": 0}
    for b in balls:
        if b["extra_type"]:
            dist["Extras"] += b["extra_runs"] + (b["runs_batter"] if b["extra_type"] == "No Ball" else 0)
            continue
        r = b["runs_batter"]
        if r == 0:
            dist["Dots"] += 1
        elif r == 1:
            dist["1s"] += 1
        elif r == 2:
            dist["2s"] += 1
        elif r == 3:
            dist["3s"] += 1
        elif r == 4:
            dist["4s"] += 1
        elif r == 6:
            dist["6s"] += 1
    return {k: v for k, v in dist.items() if v > 0} or {"No Data": 1}


# --------------------------------------------------------------------------
# FUTURE AI FEATURE PLACEHOLDERS (design-only, not implemented)
# --------------------------------------------------------------------------
def predict_final_score_placeholder(current_runs, overs_bowled, total_overs):
    """Naive projection placeholder - to be replaced by a trained ML model."""
    if overs_bowled <= 0:
        return None
    run_rate = current_runs / overs_bowled
    return round(run_rate * total_overs)


def player_performance_prediction_placeholder(player_name):
    return f"Prediction model for {player_name} coming soon (AI feature placeholder)."


def team_strength_comparison_placeholder(team_a_name, team_b_name):
    return {
        "note": "Team strength comparison model is a placeholder for a future "
                "AI feature and does not reflect real analysis.",
        "team_a": team_a_name,
        "team_b": team_b_name,
    }
