"""
database.py
------------
All SQLite persistence logic lives here. This module exposes a single
`Database` class that owns the connection and provides typed helper
methods for every table in the schema. No other module should ever
open a raw sqlite3 connection - everything routes through this class
so that business logic (scorer.py, analytics.py) stays decoupled from
SQL.

Tables
------
matches            - one row per match (metadata, toss, status, result)
teams               - master list of team names (reusable across matches)
players             - master list of players (reusable across matches)
match_squads        - links players to a match/team with jersey #, role
innings             - one row per innings of a match
batting             - per-player batting figures for an innings
bowling             - per-player bowling figures for an innings
ball_by_ball        - every single ball bowled (source of truth)
overs               - per-over aggregated summary
partnerships        - partnership records between two batters
fall_of_wickets     - wicket fall snapshots
statistics          - career/aggregate player statistics (rebuilt from data)
result              - final match result details
"""

import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime

import config


def new_id():
    """Generate a short unique id string for primary keys."""
    return uuid.uuid4().hex


class Database:
    """Thin wrapper around sqlite3 providing schema management and
    convenience CRUD methods for the whole application."""

    def __init__(self, db_path=None):
        self.db_path = db_path or config.DATABASE_PATH
        self._init_schema()

    # ------------------------------------------------------------------
    # CONNECTION HANDLING
    # ------------------------------------------------------------------
    @contextmanager
    def get_conn(self):
        """Context manager yielding a connection with row factory set,
        foreign keys enabled, and automatic commit/rollback."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # SCHEMA CREATION
    # ------------------------------------------------------------------
    def _init_schema(self):
        with self.get_conn() as conn:
            c = conn.cursor()

            c.execute("""
            CREATE TABLE IF NOT EXISTS teams (
                team_id TEXT PRIMARY KEY,
                team_name TEXT UNIQUE NOT NULL
            );
            """)

            c.execute("""
            CREATE TABLE IF NOT EXISTS players (
                player_id TEXT PRIMARY KEY,
                player_name TEXT NOT NULL,
                team_id TEXT,
                FOREIGN KEY (team_id) REFERENCES teams(team_id)
            );
            """)

            c.execute("""
            CREATE TABLE IF NOT EXISTS matches (
                match_id TEXT PRIMARY KEY,
                tournament_name TEXT,
                match_name TEXT,
                match_number TEXT,
                venue TEXT,
                match_date TEXT,
                team_a_id TEXT NOT NULL,
                team_b_id TEXT NOT NULL,
                match_type TEXT NOT NULL,
                total_overs INTEGER,
                toss_winner_team_id TEXT,
                toss_decision TEXT,
                status TEXT DEFAULT 'Setup',   -- Setup, Live, Completed
                current_innings INTEGER DEFAULT 1,
                created_at TEXT,
                FOREIGN KEY (team_a_id) REFERENCES teams(team_id),
                FOREIGN KEY (team_b_id) REFERENCES teams(team_id)
            );
            """)

            c.execute("""
            CREATE TABLE IF NOT EXISTS match_squads (
                squad_id TEXT PRIMARY KEY,
                match_id TEXT NOT NULL,
                team_id TEXT NOT NULL,
                player_id TEXT NOT NULL,
                jersey_number TEXT,
                is_captain INTEGER DEFAULT 0,
                is_keeper INTEGER DEFAULT 0,
                batting_order INTEGER,
                FOREIGN KEY (match_id) REFERENCES matches(match_id) ON DELETE CASCADE,
                FOREIGN KEY (team_id) REFERENCES teams(team_id),
                FOREIGN KEY (player_id) REFERENCES players(player_id)
            );
            """)

            c.execute("""
            CREATE TABLE IF NOT EXISTS innings (
                innings_id TEXT PRIMARY KEY,
                match_id TEXT NOT NULL,
                innings_number INTEGER NOT NULL,
                batting_team_id TEXT NOT NULL,
                bowling_team_id TEXT NOT NULL,
                total_runs INTEGER DEFAULT 0,
                total_wickets INTEGER DEFAULT 0,
                total_balls INTEGER DEFAULT 0,
                extras_wide INTEGER DEFAULT 0,
                extras_noball INTEGER DEFAULT 0,
                extras_bye INTEGER DEFAULT 0,
                extras_legbye INTEGER DEFAULT 0,
                extras_penalty INTEGER DEFAULT 0,
                target INTEGER,
                is_completed INTEGER DEFAULT 0,
                current_striker_id TEXT,
                current_non_striker_id TEXT,
                current_bowler_id TEXT,
                last_bowler_id TEXT,
                balls_this_over INTEGER DEFAULT 0,
                FOREIGN KEY (match_id) REFERENCES matches(match_id) ON DELETE CASCADE
            );
            """)

            c.execute("""
            CREATE TABLE IF NOT EXISTS batting (
                batting_id TEXT PRIMARY KEY,
                innings_id TEXT NOT NULL,
                player_id TEXT NOT NULL,
                runs INTEGER DEFAULT 0,
                balls INTEGER DEFAULT 0,
                fours INTEGER DEFAULT 0,
                sixes INTEGER DEFAULT 0,
                is_out INTEGER DEFAULT 0,
                dismissal_type TEXT,
                bowler_id TEXT,
                fielder_id TEXT,
                bat_position INTEGER,
                status TEXT DEFAULT 'Did Not Bat',  -- Batting, Not Out, Out, Did Not Bat
                FOREIGN KEY (innings_id) REFERENCES innings(innings_id) ON DELETE CASCADE,
                FOREIGN KEY (player_id) REFERENCES players(player_id)
            );
            """)

            c.execute("""
            CREATE TABLE IF NOT EXISTS bowling (
                bowling_id TEXT PRIMARY KEY,
                innings_id TEXT NOT NULL,
                player_id TEXT NOT NULL,
                balls INTEGER DEFAULT 0,
                maidens INTEGER DEFAULT 0,
                runs_conceded INTEGER DEFAULT 0,
                wickets INTEGER DEFAULT 0,
                wides INTEGER DEFAULT 0,
                no_balls INTEGER DEFAULT 0,
                FOREIGN KEY (innings_id) REFERENCES innings(innings_id) ON DELETE CASCADE,
                FOREIGN KEY (player_id) REFERENCES players(player_id)
            );
            """)

            c.execute("""
            CREATE TABLE IF NOT EXISTS ball_by_ball (
                ball_id TEXT PRIMARY KEY,
                innings_id TEXT NOT NULL,
                over_number INTEGER NOT NULL,
                ball_in_over INTEGER NOT NULL,
                striker_id TEXT NOT NULL,
                non_striker_id TEXT,
                bowler_id TEXT NOT NULL,
                runs_batter INTEGER DEFAULT 0,
                extra_type TEXT,             -- Wide, No Ball, Bye, Leg Bye, Penalty, NULL
                extra_runs INTEGER DEFAULT 0,
                is_wicket INTEGER DEFAULT 0,
                dismissal_type TEXT,
                dismissed_player_id TEXT,
                fielder_id TEXT,
                is_legal_delivery INTEGER DEFAULT 1,
                timestamp TEXT,
                FOREIGN KEY (innings_id) REFERENCES innings(innings_id) ON DELETE CASCADE
            );
            """)

            c.execute("""
            CREATE TABLE IF NOT EXISTS overs (
                over_id TEXT PRIMARY KEY,
                innings_id TEXT NOT NULL,
                over_number INTEGER NOT NULL,
                bowler_id TEXT NOT NULL,
                runs_in_over INTEGER DEFAULT 0,
                wickets_in_over INTEGER DEFAULT 0,
                is_maiden INTEGER DEFAULT 0,
                UNIQUE(innings_id, over_number),
                FOREIGN KEY (innings_id) REFERENCES innings(innings_id) ON DELETE CASCADE
            );
            """)

            c.execute("""
            CREATE TABLE IF NOT EXISTS partnerships (
                partnership_id TEXT PRIMARY KEY,
                innings_id TEXT NOT NULL,
                wicket_number INTEGER NOT NULL,
                batter1_id TEXT NOT NULL,
                batter2_id TEXT NOT NULL,
                runs INTEGER DEFAULT 0,
                balls INTEGER DEFAULT 0,
                batter1_runs INTEGER DEFAULT 0,
                batter2_runs INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                FOREIGN KEY (innings_id) REFERENCES innings(innings_id) ON DELETE CASCADE
            );
            """)

            c.execute("""
            CREATE TABLE IF NOT EXISTS fall_of_wickets (
                fow_id TEXT PRIMARY KEY,
                innings_id TEXT NOT NULL,
                wicket_number INTEGER NOT NULL,
                team_score INTEGER NOT NULL,
                over_ball TEXT NOT NULL,
                player_out_id TEXT NOT NULL,
                FOREIGN KEY (innings_id) REFERENCES innings(innings_id) ON DELETE CASCADE
            );
            """)

            c.execute("""
            CREATE TABLE IF NOT EXISTS statistics (
                stat_id TEXT PRIMARY KEY,
                player_id TEXT NOT NULL UNIQUE,
                matches INTEGER DEFAULT 0,
                innings_batted INTEGER DEFAULT 0,
                runs INTEGER DEFAULT 0,
                balls_faced INTEGER DEFAULT 0,
                fours INTEGER DEFAULT 0,
                sixes INTEGER DEFAULT 0,
                fifties INTEGER DEFAULT 0,
                hundreds INTEGER DEFAULT 0,
                highest_score INTEGER DEFAULT 0,
                innings_bowled INTEGER DEFAULT 0,
                balls_bowled INTEGER DEFAULT 0,
                runs_conceded INTEGER DEFAULT 0,
                wickets INTEGER DEFAULT 0,
                best_bowling TEXT,
                FOREIGN KEY (player_id) REFERENCES players(player_id)
            );
            """)

            c.execute("""
            CREATE TABLE IF NOT EXISTS result (
                result_id TEXT PRIMARY KEY,
                match_id TEXT NOT NULL UNIQUE,
                winner_team_id TEXT,
                result_type TEXT,     -- Won by Runs, Won by Wickets, Tie, No Result, Super Over
                margin TEXT,
                player_of_match_id TEXT,
                summary TEXT,
                FOREIGN KEY (match_id) REFERENCES matches(match_id) ON DELETE CASCADE
            );
            """)

            conn.commit()

    # ------------------------------------------------------------------
    # TEAMS & PLAYERS
    # ------------------------------------------------------------------
    def get_or_create_team(self, team_name):
        team_name = team_name.strip()
        with self.get_conn() as conn:
            row = conn.execute(
                "SELECT team_id FROM teams WHERE team_name = ?", (team_name,)
            ).fetchone()
            if row:
                return row["team_id"]
            team_id = new_id()
            conn.execute(
                "INSERT INTO teams (team_id, team_name) VALUES (?, ?)",
                (team_id, team_name),
            )
            return team_id

    def get_or_create_player(self, player_name, team_id=None):
        player_name = player_name.strip()
        with self.get_conn() as conn:
            row = conn.execute(
                "SELECT player_id FROM players WHERE player_name = ? AND "
                "(team_id = ? OR ? IS NULL)",
                (player_name, team_id, team_id),
            ).fetchone()
            if row:
                return row["player_id"]
            player_id = new_id()
            conn.execute(
                "INSERT INTO players (player_id, player_name, team_id) VALUES (?, ?, ?)",
                (player_id, player_name, team_id),
            )
            return player_id

    def get_team_name(self, team_id):
        with self.get_conn() as conn:
            row = conn.execute(
                "SELECT team_name FROM teams WHERE team_id = ?", (team_id,)
            ).fetchone()
            return row["team_name"] if row else "Unknown"

    def get_player_name(self, player_id):
        if not player_id:
            return ""
        with self.get_conn() as conn:
            row = conn.execute(
                "SELECT player_name FROM players WHERE player_id = ?", (player_id,)
            ).fetchone()
            return row["player_name"] if row else "Unknown"

    # ------------------------------------------------------------------
    # MATCH SQUADS
    # ------------------------------------------------------------------
    def add_squad_player(self, match_id, team_id, player_id, jersey_number,
                          is_captain, is_keeper, batting_order):
        with self.get_conn() as conn:
            conn.execute("""
                INSERT INTO match_squads
                (squad_id, match_id, team_id, player_id, jersey_number,
                 is_captain, is_keeper, batting_order)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (new_id(), match_id, team_id, player_id, jersey_number,
                  int(is_captain), int(is_keeper), batting_order))

    def get_squad(self, match_id, team_id):
        with self.get_conn() as conn:
            rows = conn.execute("""
                SELECT ms.*, p.player_name FROM match_squads ms
                JOIN players p ON p.player_id = ms.player_id
                WHERE ms.match_id = ? AND ms.team_id = ?
                ORDER BY ms.batting_order ASC
            """, (match_id, team_id)).fetchall()
            return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # MATCHES
    # ------------------------------------------------------------------
    def create_match(self, tournament_name, match_name, match_number, venue,
                      match_date, team_a_id, team_b_id, match_type,
                      total_overs):
        match_id = new_id()
        with self.get_conn() as conn:
            conn.execute("""
                INSERT INTO matches
                (match_id, tournament_name, match_name, match_number, venue,
                 match_date, team_a_id, team_b_id, match_type, total_overs,
                 status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Setup', ?)
            """, (match_id, tournament_name, match_name, match_number, venue,
                  match_date, team_a_id, team_b_id, match_type, total_overs,
                  datetime.now().strftime(config.DATETIME_FORMAT)))
        return match_id

    def set_toss(self, match_id, toss_winner_team_id, toss_decision):
        with self.get_conn() as conn:
            conn.execute("""
                UPDATE matches SET toss_winner_team_id = ?, toss_decision = ?
                WHERE match_id = ?
            """, (toss_winner_team_id, toss_decision, match_id))

    def update_match_status(self, match_id, status, current_innings=None):
        with self.get_conn() as conn:
            if current_innings is not None:
                conn.execute("""
                    UPDATE matches SET status = ?, current_innings = ?
                    WHERE match_id = ?
                """, (status, current_innings, match_id))
            else:
                conn.execute(
                    "UPDATE matches SET status = ? WHERE match_id = ?",
                    (status, match_id)
                )

    def get_match(self, match_id):
        with self.get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM matches WHERE match_id = ?", (match_id,)
            ).fetchone()
            return dict(row) if row else None

    def get_all_matches(self):
        with self.get_conn() as conn:
            rows = conn.execute("""
                SELECT m.*, ta.team_name AS team_a_name, tb.team_name AS team_b_name
                FROM matches m
                JOIN teams ta ON ta.team_id = m.team_a_id
                JOIN teams tb ON tb.team_id = m.team_b_id
                ORDER BY m.created_at DESC
            """).fetchall()
            return [dict(r) for r in rows]

    def delete_match(self, match_id):
        with self.get_conn() as conn:
            conn.execute("DELETE FROM matches WHERE match_id = ?", (match_id,))

    # ------------------------------------------------------------------
    # INNINGS
    # ------------------------------------------------------------------
    def create_innings(self, match_id, innings_number, batting_team_id,
                        bowling_team_id, target=None):
        innings_id = new_id()
        with self.get_conn() as conn:
            conn.execute("""
                INSERT INTO innings
                (innings_id, match_id, innings_number, batting_team_id,
                 bowling_team_id, target)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (innings_id, match_id, innings_number, batting_team_id,
                  bowling_team_id, target))
        return innings_id

    def get_innings(self, innings_id):
        with self.get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM innings WHERE innings_id = ?", (innings_id,)
            ).fetchone()
            return dict(row) if row else None

    def get_innings_by_match(self, match_id):
        with self.get_conn() as conn:
            rows = conn.execute("""
                SELECT * FROM innings WHERE match_id = ? ORDER BY innings_number ASC
            """, (match_id,)).fetchall()
            return [dict(r) for r in rows]

    def update_innings_totals(self, innings_id, **kwargs):
        """Generic updater: pass column=value pairs to update."""
        if not kwargs:
            return
        cols = ", ".join(f"{k} = ?" for k in kwargs)
        values = list(kwargs.values()) + [innings_id]
        with self.get_conn() as conn:
            conn.execute(
                f"UPDATE innings SET {cols} WHERE innings_id = ?", values
            )

    def set_live_state(self, innings_id, striker_id=None, non_striker_id=None,
                        bowler_id=None, last_bowler_id=None, balls_this_over=None):
        """Persist who is on strike / bowling right now so a match can be
        resumed later without losing live-scoring context."""
        fields = {}
        if striker_id is not None:
            fields["current_striker_id"] = striker_id
        if non_striker_id is not None:
            fields["current_non_striker_id"] = non_striker_id
        if bowler_id is not None:
            fields["current_bowler_id"] = bowler_id
        if last_bowler_id is not None:
            fields["last_bowler_id"] = last_bowler_id
        if balls_this_over is not None:
            fields["balls_this_over"] = balls_this_over
        self.update_innings_totals(innings_id, **fields)

    def complete_innings(self, innings_id):
        with self.get_conn() as conn:
            conn.execute(
                "UPDATE innings SET is_completed = 1 WHERE innings_id = ?",
                (innings_id,)
            )

    # ------------------------------------------------------------------
    # BATTING
    # ------------------------------------------------------------------
    def ensure_batting_row(self, innings_id, player_id, bat_position=None):
        with self.get_conn() as conn:
            row = conn.execute("""
                SELECT batting_id FROM batting
                WHERE innings_id = ? AND player_id = ?
            """, (innings_id, player_id)).fetchone()
            if row:
                return row["batting_id"]
            batting_id = new_id()
            conn.execute("""
                INSERT INTO batting (batting_id, innings_id, player_id,
                                      bat_position, status)
                VALUES (?, ?, ?, ?, 'Batting')
            """, (batting_id, innings_id, player_id, bat_position))
            return batting_id

    def update_batting_stats(self, innings_id, player_id, runs_delta=0,
                              balls_delta=0, four=False, six=False):
        self.ensure_batting_row(innings_id, player_id)
        with self.get_conn() as conn:
            conn.execute(f"""
                UPDATE batting SET
                    runs = runs + ?,
                    balls = balls + ?,
                    fours = fours + {1 if four else 0},
                    sixes = sixes + {1 if six else 0}
                WHERE innings_id = ? AND player_id = ?
            """, (runs_delta, balls_delta, innings_id, player_id))

    def dismiss_batter(self, innings_id, player_id, dismissal_type,
                        bowler_id=None, fielder_id=None):
        with self.get_conn() as conn:
            conn.execute("""
                UPDATE batting SET is_out = 1, status = 'Out',
                    dismissal_type = ?, bowler_id = ?, fielder_id = ?
                WHERE innings_id = ? AND player_id = ?
            """, (dismissal_type, bowler_id, fielder_id, innings_id, player_id))

    def set_batter_status(self, innings_id, player_id, status):
        with self.get_conn() as conn:
            conn.execute("""
                UPDATE batting SET status = ? WHERE innings_id = ? AND player_id = ?
            """, (status, innings_id, player_id))

    def get_batting_card(self, innings_id):
        with self.get_conn() as conn:
            rows = conn.execute("""
                SELECT b.*, p.player_name FROM batting b
                JOIN players p ON p.player_id = b.player_id
                WHERE b.innings_id = ?
                ORDER BY b.bat_position ASC
            """, (innings_id,)).fetchall()
            return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # BOWLING
    # ------------------------------------------------------------------
    def ensure_bowling_row(self, innings_id, player_id):
        with self.get_conn() as conn:
            row = conn.execute("""
                SELECT bowling_id FROM bowling
                WHERE innings_id = ? AND player_id = ?
            """, (innings_id, player_id)).fetchone()
            if row:
                return row["bowling_id"]
            bowling_id = new_id()
            conn.execute("""
                INSERT INTO bowling (bowling_id, innings_id, player_id)
                VALUES (?, ?, ?)
            """, (bowling_id, innings_id, player_id))
            return bowling_id

    def update_bowling_stats(self, innings_id, player_id, balls_delta=0,
                              runs_delta=0, wicket=False, wide=False,
                              no_ball=False):
        self.ensure_bowling_row(innings_id, player_id)
        with self.get_conn() as conn:
            conn.execute(f"""
                UPDATE bowling SET
                    balls = balls + ?,
                    runs_conceded = runs_conceded + ?,
                    wickets = wickets + {1 if wicket else 0},
                    wides = wides + {1 if wide else 0},
                    no_balls = no_balls + {1 if no_ball else 0}
                WHERE innings_id = ? AND player_id = ?
            """, (balls_delta, runs_delta, innings_id, player_id))

    def set_maiden(self, innings_id, player_id):
        with self.get_conn() as conn:
            conn.execute("""
                UPDATE bowling SET maidens = maidens + 1
                WHERE innings_id = ? AND player_id = ?
            """, (innings_id, player_id))

    def get_bowling_card(self, innings_id):
        with self.get_conn() as conn:
            rows = conn.execute("""
                SELECT bo.*, p.player_name FROM bowling bo
                JOIN players p ON p.player_id = bo.player_id
                WHERE bo.innings_id = ?
                ORDER BY bo.balls DESC
            """, (innings_id,)).fetchall()
            return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # BALL BY BALL
    # ------------------------------------------------------------------
    def insert_ball(self, innings_id, over_number, ball_in_over, striker_id,
                     non_striker_id, bowler_id, runs_batter=0, extra_type=None,
                     extra_runs=0, is_wicket=False, dismissal_type=None,
                     dismissed_player_id=None, fielder_id=None,
                     is_legal_delivery=True):
        ball_id = new_id()
        with self.get_conn() as conn:
            conn.execute("""
                INSERT INTO ball_by_ball
                (ball_id, innings_id, over_number, ball_in_over, striker_id,
                 non_striker_id, bowler_id, runs_batter, extra_type,
                 extra_runs, is_wicket, dismissal_type, dismissed_player_id,
                 fielder_id, is_legal_delivery, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (ball_id, innings_id, over_number, ball_in_over, striker_id,
                  non_striker_id, bowler_id, runs_batter, extra_type,
                  extra_runs, int(is_wicket), dismissal_type,
                  dismissed_player_id, fielder_id, int(is_legal_delivery),
                  datetime.now().strftime(config.DATETIME_FORMAT)))
        return ball_id

    def get_balls(self, innings_id):
        with self.get_conn() as conn:
            rows = conn.execute("""
                SELECT * FROM ball_by_ball WHERE innings_id = ?
                ORDER BY over_number ASC, ball_in_over ASC, timestamp ASC
            """, (innings_id,)).fetchall()
            return [dict(r) for r in rows]

    def delete_last_ball(self, innings_id):
        """Used by Undo - removes the most recently inserted ball row."""
        with self.get_conn() as conn:
            row = conn.execute("""
                SELECT ball_id FROM ball_by_ball WHERE innings_id = ?
                ORDER BY timestamp DESC LIMIT 1
            """, (innings_id,)).fetchone()
            if row:
                conn.execute(
                    "DELETE FROM ball_by_ball WHERE ball_id = ?", (row["ball_id"],)
                )
                return True
            return False

    # ------------------------------------------------------------------
    # OVERS
    # ------------------------------------------------------------------
    def upsert_over(self, innings_id, over_number, bowler_id, runs_in_over,
                     wickets_in_over, is_maiden=False):
        with self.get_conn() as conn:
            conn.execute("""
                INSERT INTO overs (over_id, innings_id, over_number, bowler_id,
                                    runs_in_over, wickets_in_over, is_maiden)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(innings_id, over_number) DO UPDATE SET
                    bowler_id = excluded.bowler_id,
                    runs_in_over = excluded.runs_in_over,
                    wickets_in_over = excluded.wickets_in_over,
                    is_maiden = excluded.is_maiden
            """, (new_id(), innings_id, over_number, bowler_id, runs_in_over,
                  wickets_in_over, int(is_maiden)))

    def get_overs(self, innings_id):
        with self.get_conn() as conn:
            rows = conn.execute("""
                SELECT * FROM overs WHERE innings_id = ? ORDER BY over_number ASC
            """, (innings_id,)).fetchall()
            return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # PARTNERSHIPS
    # ------------------------------------------------------------------
    def start_partnership(self, innings_id, wicket_number, batter1_id, batter2_id):
        with self.get_conn() as conn:
            conn.execute("""
                UPDATE partnerships SET is_active = 0
                WHERE innings_id = ? AND is_active = 1
            """, (innings_id,))
            conn.execute("""
                INSERT INTO partnerships
                (partnership_id, innings_id, wicket_number, batter1_id,
                 batter2_id, is_active)
                VALUES (?, ?, ?, ?, ?, 1)
            """, (new_id(), innings_id, wicket_number, batter1_id, batter2_id))

    def update_active_partnership(self, innings_id, scoring_batter_id, runs):
        with self.get_conn() as conn:
            row = conn.execute("""
                SELECT * FROM partnerships WHERE innings_id = ? AND is_active = 1
            """, (innings_id,)).fetchone()
            if not row:
                return
            if scoring_batter_id == row["batter1_id"]:
                conn.execute("""
                    UPDATE partnerships SET runs = runs + ?, balls = balls + 1,
                    batter1_runs = batter1_runs + ? WHERE partnership_id = ?
                """, (runs, runs, row["partnership_id"]))
            elif scoring_batter_id == row["batter2_id"]:
                conn.execute("""
                    UPDATE partnerships SET runs = runs + ?, balls = balls + 1,
                    batter2_runs = batter2_runs + ? WHERE partnership_id = ?
                """, (runs, runs, row["partnership_id"]))
            else:
                conn.execute("""
                    UPDATE partnerships SET runs = runs + ?, balls = balls + 1
                    WHERE partnership_id = ?
                """, (runs, row["partnership_id"]))

    def get_active_partnership(self, innings_id):
        with self.get_conn() as conn:
            row = conn.execute("""
                SELECT * FROM partnerships WHERE innings_id = ? AND is_active = 1
            """, (innings_id,)).fetchone()
            return dict(row) if row else None

    def get_partnerships(self, innings_id):
        with self.get_conn() as conn:
            rows = conn.execute("""
                SELECT * FROM partnerships WHERE innings_id = ? ORDER BY wicket_number ASC
            """, (innings_id,)).fetchall()
            return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # FALL OF WICKETS
    # ------------------------------------------------------------------
    def add_fall_of_wicket(self, innings_id, wicket_number, team_score,
                            over_ball, player_out_id):
        with self.get_conn() as conn:
            conn.execute("""
                INSERT INTO fall_of_wickets
                (fow_id, innings_id, wicket_number, team_score, over_ball,
                 player_out_id)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (new_id(), innings_id, wicket_number, team_score, over_ball,
                  player_out_id))

    def get_fall_of_wickets(self, innings_id):
        with self.get_conn() as conn:
            rows = conn.execute("""
                SELECT * FROM fall_of_wickets WHERE innings_id = ?
                ORDER BY wicket_number ASC
            """, (innings_id,)).fetchall()
            return [dict(r) for r in rows]

    def delete_last_fall_of_wicket(self, innings_id):
        with self.get_conn() as conn:
            row = conn.execute("""
                SELECT fow_id FROM fall_of_wickets WHERE innings_id = ?
                ORDER BY wicket_number DESC LIMIT 1
            """, (innings_id,)).fetchone()
            if row:
                conn.execute(
                    "DELETE FROM fall_of_wickets WHERE fow_id = ?", (row["fow_id"],)
                )

    # ------------------------------------------------------------------
    # RESULT
    # ------------------------------------------------------------------
    def save_result(self, match_id, winner_team_id, result_type, margin,
                     player_of_match_id, summary):
        with self.get_conn() as conn:
            conn.execute("""
                INSERT INTO result (result_id, match_id, winner_team_id,
                                     result_type, margin, player_of_match_id, summary)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(match_id) DO UPDATE SET
                    winner_team_id = excluded.winner_team_id,
                    result_type = excluded.result_type,
                    margin = excluded.margin,
                    player_of_match_id = excluded.player_of_match_id,
                    summary = excluded.summary
            """, (new_id(), match_id, winner_team_id, result_type, margin,
                  player_of_match_id, summary))

    def get_result(self, match_id):
        with self.get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM result WHERE match_id = ?", (match_id,)
            ).fetchone()
            return dict(row) if row else None

    # ------------------------------------------------------------------
    # STATISTICS (aggregate, rebuilt on demand)
    # ------------------------------------------------------------------
    def rebuild_player_statistics(self, player_id):
        """Recomputes aggregate career statistics for a player from raw
        batting/bowling rows across all innings. Called after a match
        is completed."""
        with self.get_conn() as conn:
            bat_rows = conn.execute("""
                SELECT * FROM batting WHERE player_id = ?
            """, (player_id,)).fetchall()
            bowl_rows = conn.execute("""
                SELECT * FROM bowling WHERE player_id = ?
            """, (player_id,)).fetchall()

            innings_batted = sum(1 for r in bat_rows if r["balls"] > 0 or r["is_out"])
            runs = sum(r["runs"] for r in bat_rows)
            balls_faced = sum(r["balls"] for r in bat_rows)
            fours = sum(r["fours"] for r in bat_rows)
            sixes = sum(r["sixes"] for r in bat_rows)
            fifties = sum(1 for r in bat_rows if 50 <= r["runs"] < 100)
            hundreds = sum(1 for r in bat_rows if r["runs"] >= 100)
            highest = max([r["runs"] for r in bat_rows], default=0)

            innings_bowled = sum(1 for r in bowl_rows if r["balls"] > 0)
            balls_bowled = sum(r["balls"] for r in bowl_rows)
            runs_conceded = sum(r["runs_conceded"] for r in bowl_rows)
            wickets = sum(r["wickets"] for r in bowl_rows)
            best = max(bowl_rows, key=lambda r: (r["wickets"], -r["runs_conceded"]),
                       default=None)
            best_bowling = f"{best['wickets']}/{best['runs_conceded']}" if best else None

            matches = len({r["innings_id"] for r in bat_rows} |
                          {r["innings_id"] for r in bowl_rows})

            conn.execute("""
                INSERT INTO statistics
                (stat_id, player_id, matches, innings_batted, runs, balls_faced,
                 fours, sixes, fifties, hundreds, highest_score, innings_bowled,
                 balls_bowled, runs_conceded, wickets, best_bowling)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(player_id) DO UPDATE SET
                    matches = excluded.matches,
                    innings_batted = excluded.innings_batted,
                    runs = excluded.runs,
                    balls_faced = excluded.balls_faced,
                    fours = excluded.fours,
                    sixes = excluded.sixes,
                    fifties = excluded.fifties,
                    hundreds = excluded.hundreds,
                    highest_score = excluded.highest_score,
                    innings_bowled = excluded.innings_bowled,
                    balls_bowled = excluded.balls_bowled,
                    runs_conceded = excluded.runs_conceded,
                    wickets = excluded.wickets,
                    best_bowling = excluded.best_bowling
            """, (new_id(), player_id, matches, innings_batted, runs, balls_faced,
                  fours, sixes, fifties, hundreds, highest, innings_bowled,
                  balls_bowled, runs_conceded, wickets, best_bowling))

    def get_all_statistics(self):
        with self.get_conn() as conn:
            rows = conn.execute("""
                SELECT s.*, p.player_name FROM statistics s
                JOIN players p ON p.player_id = s.player_id
                ORDER BY s.runs DESC
            """).fetchall()
            return [dict(r) for r in rows]

    def get_player_statistics(self, player_id):
        with self.get_conn() as conn:
            row = conn.execute("""
                SELECT s.*, p.player_name FROM statistics s
                JOIN players p ON p.player_id = s.player_id
                WHERE s.player_id = ?
            """, (player_id,)).fetchone()
            return dict(row) if row else None

    def get_all_players(self):
        with self.get_conn() as conn:
            rows = conn.execute("SELECT * FROM players ORDER BY player_name ASC").fetchall()
            return [dict(r) for r in rows]
