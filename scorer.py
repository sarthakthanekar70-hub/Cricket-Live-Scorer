"""
scorer.py
---------
The Scorer class is the single source of truth for turning a "ball
event" (a button click in the Live Scoring page) into every downstream
database update: totals, batting/bowling figures, overs, partnerships,
fall of wickets, strike rotation, over completion, innings completion
and final match result. Streamlit pages should never write scoring
data directly - they call methods on Scorer instead.
"""

import config
from database import Database


class Scorer:
    def __init__(self, db: Database, innings_id: str):
        self.db = db
        self.innings_id = innings_id
        self.innings = db.get_innings(innings_id)
        self.match = db.get_match(self.innings["match_id"])

    # ------------------------------------------------------------------
    # INITIAL SETUP FOR AN INNINGS
    # ------------------------------------------------------------------
    def set_openers(self, striker_id, non_striker_id, bowler_id):
        self.db.ensure_batting_row(self.innings_id, striker_id, bat_position=1)
        self.db.ensure_batting_row(self.innings_id, non_striker_id, bat_position=2)
        self.db.ensure_bowling_row(self.innings_id, bowler_id)
        self.db.set_live_state(
            self.innings_id, striker_id=striker_id,
            non_striker_id=non_striker_id, bowler_id=bowler_id,
            balls_this_over=0,
        )
        self.db.start_partnership(self.innings_id, wicket_number=1,
                                   batter1_id=striker_id, batter2_id=non_striker_id)

    # ------------------------------------------------------------------
    # CORE BALL PROCESSING
    # ------------------------------------------------------------------
    def process_ball(self, runs=0, extra_type=None, is_wicket=False,
                      dismissal_type=None, dismissed_player_id=None,
                      fielder_id=None, next_batter_id=None):
        """
        Handles ANY ball event.
        runs          : runs completed by batters (off the bat, or run-out runs)
        extra_type    : one of config.EXTRA_TYPES or None
        is_wicket     : True if a wicket fell on this delivery
        dismissed_player_id : who got out (defaults to striker unless run-out)
        next_batter_id: required if is_wicket and innings/team not all out
        """
        innings = self.db.get_innings(self.innings_id)
        striker = innings["current_striker_id"]
        non_striker = innings["current_non_striker_id"]
        bowler = innings["current_bowler_id"]
        balls_this_over = innings["balls_this_over"] or 0
        over_number = (innings["total_balls"] or 0) // config.BALLS_PER_OVER

        is_legal = extra_type not in ("Wide", "No Ball")
        batter_runs = runs if extra_type not in ("Bye", "Leg Bye") else 0
        extra_runs = 0
        team_runs_this_ball = runs

        # --- Extras run accounting -------------------------------------------------
        if extra_type == "Wide":
            extra_runs = 1 + runs
            team_runs_this_ball = extra_runs
        elif extra_type == "No Ball":
            extra_runs = 1
            team_runs_this_ball = extra_runs + runs
        elif extra_type in ("Bye", "Leg Bye"):
            extra_runs = runs
            team_runs_this_ball = runs
        elif extra_type == "Penalty":
            extra_runs = runs
            team_runs_this_ball = runs

        # --- Persist the ball ------------------------------------------------------
        self.db.insert_ball(
            innings_id=self.innings_id, over_number=over_number,
            ball_in_over=balls_this_over + (1 if is_legal else 0),
            striker_id=striker, non_striker_id=non_striker, bowler_id=bowler,
            runs_batter=batter_runs, extra_type=extra_type, extra_runs=extra_runs,
            is_wicket=is_wicket, dismissal_type=dismissal_type,
            dismissed_player_id=dismissed_player_id, fielder_id=fielder_id,
            is_legal_delivery=is_legal,
        )

        # --- Batter stats (runs off the bat only count towards batter) -------------
        if extra_type not in ("Wide", "Bye", "Leg Bye"):
            four = batter_runs == 4
            six = batter_runs == 6
            balls_faced_delta = 1 if extra_type != "No Ball" else 0
            # No-ball: batter still faces the ball in most scoring conventions
            # for strike rate; we count it as a ball faced but not legal for over.
            balls_faced_delta = 1
            self.db.update_batting_stats(
                self.innings_id, striker, runs_delta=batter_runs,
                balls_delta=balls_faced_delta, four=four, six=six,
            )
        elif extra_type in ("Bye", "Leg Bye"):
            self.db.update_batting_stats(
                self.innings_id, striker, runs_delta=0, balls_delta=1,
            )

        # --- Bowler stats ------------------------------------------------------------
        bowler_runs_conceded = team_runs_this_ball if extra_type != "Bye" and \
            extra_type != "Leg Bye" and extra_type != "Penalty" else \
            (extra_runs if extra_type in ("Wide", "No Ball") else 0)
        # Simplify: byes/leg-byes/penalty don't count against bowler; wides/no-balls do.
        if extra_type in ("Bye", "Leg Bye", "Penalty"):
            bowler_runs_conceded = 0
        elif extra_type in ("Wide", "No Ball"):
            bowler_runs_conceded = team_runs_this_ball
        else:
            bowler_runs_conceded = batter_runs

        self.db.update_bowling_stats(
            self.innings_id, bowler, balls_delta=(1 if is_legal else 0),
            runs_delta=bowler_runs_conceded, wicket=(is_wicket and dismissal_type
                                                       not in ("Run Out",)),
            wide=(extra_type == "Wide"), no_ball=(extra_type == "No Ball"),
        )

        # --- Innings totals ------------------------------------------------------------
        new_total_runs = (innings["total_runs"] or 0) + team_runs_this_ball
        new_total_balls = (innings["total_balls"] or 0) + (1 if is_legal else 0)
        new_wickets = (innings["total_wickets"] or 0) + (1 if is_wicket else 0)

        extras_update = {}
        if extra_type == "Wide":
            extras_update["extras_wide"] = (innings["extras_wide"] or 0) + extra_runs
        elif extra_type == "No Ball":
            extras_update["extras_noball"] = (innings["extras_noball"] or 0) + extra_runs
        elif extra_type == "Bye":
            extras_update["extras_bye"] = (innings["extras_bye"] or 0) + extra_runs
        elif extra_type == "Leg Bye":
            extras_update["extras_legbye"] = (innings["extras_legbye"] or 0) + extra_runs
        elif extra_type == "Penalty":
            extras_update["extras_penalty"] = (innings["extras_penalty"] or 0) + extra_runs

        self.db.update_innings_totals(
            self.innings_id, total_runs=new_total_runs,
            total_balls=new_total_balls, total_wickets=new_wickets,
            **extras_update,
        )

        # --- Partnership ------------------------------------------------------------
        self.db.update_active_partnership(self.innings_id, striker, batter_runs
                                           if extra_type not in ("Bye", "Leg Bye")
                                           else 0)

        # --- Wicket handling ------------------------------------------------------------
        out_player = dismissed_player_id or striker
        if is_wicket:
            self.db.dismiss_batter(self.innings_id, out_player, dismissal_type,
                                    bowler_id=bowler if dismissal_type != "Run Out" else None,
                                    fielder_id=fielder_id)
            self.db.add_fall_of_wicket(
                self.innings_id, wicket_number=new_wickets,
                team_score=new_total_runs,
                over_ball=f"{new_total_balls // config.BALLS_PER_OVER}."
                          f"{new_total_balls % config.BALLS_PER_OVER}",
                player_out_id=out_player,
            )
            # Determine surviving batter to keep on strike
            surviving = non_striker if out_player == striker else striker
            if next_batter_id:
                self.db.ensure_batting_row(self.innings_id, next_batter_id,
                                            bat_position=new_wickets + 2)
                self.db.set_live_state(self.innings_id, striker_id=surviving,
                                        non_striker_id=next_batter_id)
                self.db.start_partnership(self.innings_id, wicket_number=new_wickets + 1,
                                           batter1_id=surviving, batter2_id=next_batter_id)
            else:
                # All out / innings ending - just keep survivor on strike
                self.db.set_live_state(self.innings_id, striker_id=surviving,
                                        non_striker_id=None)
            striker, non_striker = surviving, next_batter_id

        # --- Strike rotation on odd runs (off legal/no-ball scoring, not on wide) -----
        if extra_type != "Wide" and not is_wicket:
            if runs % 2 == 1:
                striker, non_striker = non_striker, striker
                self.db.set_live_state(self.innings_id, striker_id=striker,
                                        non_striker_id=non_striker)

        # --- Over completion ------------------------------------------------------------
        balls_this_over = balls_this_over + 1 if is_legal else balls_this_over
        if is_legal and balls_this_over == config.BALLS_PER_OVER:
            over_runs = self._runs_in_over(over_number)
            over_wkts = self._wickets_in_over(over_number)
            self.db.upsert_over(self.innings_id, over_number, bowler,
                                 over_runs, over_wkts, is_maiden=(over_runs == 0))
            if over_wkts == 0 and over_runs == 0:
                self.db.set_maiden(self.innings_id, bowler)
            # Swap strike at end of over, reset over ball counter
            striker, non_striker = non_striker, striker
            self.db.set_live_state(self.innings_id, striker_id=striker,
                                    non_striker_id=non_striker,
                                    last_bowler_id=bowler, balls_this_over=0)
        elif is_legal:
            self.db.set_live_state(self.innings_id, balls_this_over=balls_this_over)

        return {
            "total_runs": new_total_runs,
            "total_balls": new_total_balls,
            "total_wickets": new_wickets,
        }

    def _runs_in_over(self, over_number):
        balls = [b for b in self.db.get_balls(self.innings_id)
                 if b["over_number"] == over_number]
        return sum(b["runs_batter"] + b["extra_runs"] for b in balls)

    def _wickets_in_over(self, over_number):
        balls = [b for b in self.db.get_balls(self.innings_id)
                 if b["over_number"] == over_number]
        return sum(1 for b in balls if b["is_wicket"])

    def change_bowler(self, new_bowler_id):
        self.db.ensure_bowling_row(self.innings_id, new_bowler_id)
        self.db.set_live_state(self.innings_id, bowler_id=new_bowler_id)

    # ------------------------------------------------------------------
    # UNDO
    # ------------------------------------------------------------------
    def undo_last_ball(self):
        """Best-effort undo: removes the last ball row. Full stat reversal
        is achieved by rebuilding totals from the remaining ball log,
        which keeps the logic simple and bug-resistant compared to trying
        to reverse each incremental update individually."""
        balls = self.db.get_balls(self.innings_id)
        if not balls:
            return False
        last = balls[-1]
        self.db.delete_last_ball(self.innings_id)
        if last["is_wicket"]:
            self.db.delete_last_fall_of_wicket(self.innings_id)
        self._rebuild_innings_from_balls()
        return True

    def _rebuild_innings_from_balls(self):
        """Recomputes all derived tables (batting, bowling, totals) purely
        from the ball_by_ball log for this innings. Used after Undo to
        guarantee consistency without complex reverse-update logic."""
        balls = self.db.get_balls(self.innings_id)
        innings = self.db.get_innings(self.innings_id)

        with self.db.get_conn() as conn:
            conn.execute("DELETE FROM batting WHERE innings_id = ?", (self.innings_id,))
            conn.execute("DELETE FROM bowling WHERE innings_id = ?", (self.innings_id,))
            conn.execute("DELETE FROM overs WHERE innings_id = ?", (self.innings_id,))
            conn.execute("""UPDATE innings SET total_runs=0, total_balls=0,
                total_wickets=0, extras_wide=0, extras_noball=0, extras_bye=0,
                extras_legbye=0, extras_penalty=0 WHERE innings_id = ?""",
                (self.innings_id,))

        total_runs = total_balls = total_wkts = 0
        extras = {"Wide": 0, "No Ball": 0, "Bye": 0, "Leg Bye": 0, "Penalty": 0}
        over_accum = {}

        for b in balls:
            extra_type = b["extra_type"]
            is_legal = bool(b["is_legal_delivery"])
            team_runs = b["runs_batter"] + b["extra_runs"]
            total_runs += team_runs
            if is_legal:
                total_balls += 1
            if b["is_wicket"]:
                total_wkts += 1
            if extra_type:
                extras[extra_type] = extras.get(extra_type, 0) + b["extra_runs"]

            if extra_type not in ("Wide", "Bye", "Leg Bye"):
                self.db.update_batting_stats(self.innings_id, b["striker_id"],
                                              runs_delta=b["runs_batter"],
                                              balls_delta=1,
                                              four=(b["runs_batter"] == 4),
                                              six=(b["runs_batter"] == 6))
            elif extra_type in ("Bye", "Leg Bye"):
                self.db.update_batting_stats(self.innings_id, b["striker_id"],
                                              runs_delta=0, balls_delta=1)

            bowler_runs = 0
            if extra_type in ("Wide", "No Ball"):
                bowler_runs = team_runs
            elif not extra_type:
                bowler_runs = b["runs_batter"]
            self.db.update_bowling_stats(
                self.innings_id, b["bowler_id"], balls_delta=(1 if is_legal else 0),
                runs_delta=bowler_runs,
                wicket=(b["is_wicket"] and b["dismissal_type"] != "Run Out"),
                wide=(extra_type == "Wide"), no_ball=(extra_type == "No Ball"),
            )

            if b["is_wicket"] and b["dismissed_player_id"]:
                self.db.dismiss_batter(self.innings_id, b["dismissed_player_id"],
                                        b["dismissal_type"], bowler_id=b["bowler_id"],
                                        fielder_id=b["fielder_id"])

            key = b["over_number"]
            over_accum.setdefault(key, {"runs": 0, "wkts": 0, "bowler": b["bowler_id"]})
            over_accum[key]["runs"] += team_runs
            over_accum[key]["wkts"] += 1 if b["is_wicket"] else 0

        for over_number, agg in over_accum.items():
            self.db.upsert_over(self.innings_id, over_number, agg["bowler"],
                                 agg["runs"], agg["wkts"], is_maiden=(agg["runs"] == 0))

        self.db.update_innings_totals(
            self.innings_id, total_runs=total_runs, total_balls=total_balls,
            total_wickets=total_wkts,
            extras_wide=extras["Wide"], extras_noball=extras["No Ball"],
            extras_bye=extras["Bye"], extras_legbye=extras["Leg Bye"],
            extras_penalty=extras["Penalty"],
        )

    # ------------------------------------------------------------------
    # INNINGS / MATCH LIFECYCLE
    # ------------------------------------------------------------------
    def is_innings_over(self):
        innings = self.db.get_innings(self.innings_id)
        match = self.db.get_match(innings["match_id"])
        squad_size = 11
        all_out = innings["total_wickets"] >= squad_size - 1
        overs_done = False
        if match["total_overs"]:
            overs_done = innings["total_balls"] >= match["total_overs"] * config.BALLS_PER_OVER
        target_chased = innings["target"] is not None and innings["total_runs"] >= innings["target"]
        return all_out or overs_done or target_chased

    def finish_innings(self):
        self.db.complete_innings(self.innings_id)
