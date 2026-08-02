from datetime import date
from typing import Any

import psycopg
from psycopg.rows import dict_row

from .normalize import clean_entity_name


class Repository:
    def __init__(self, database_url: str):
        self.connection = psycopg.connect(database_url, row_factory=dict_row)

    def __enter__(self) -> "Repository":
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        if exc_type is not None:
            self.connection.rollback()
        self.connection.close()

    def start_run(self, importer_version: str, dataset_fingerprint: str, data_as_of: date) -> int:
        row = self.connection.execute(
            """
            INSERT INTO etl_runs (importer_version, dataset_fingerprint, data_as_of, status)
            VALUES (%s, %s, %s, 'RUNNING')
            RETURNING id
            """,
            (importer_version, dataset_fingerprint, data_as_of),
        ).fetchone()
        run_id = int(row["id"])
        self.connection.commit()
        return run_id

    def finish_run(self, run_id: int, rows_read: int, rows_written: int) -> None:
        self.connection.execute(
            """
            UPDATE etl_runs
            SET status = 'SUCCEEDED', finished_at = CURRENT_TIMESTAMP,
                rows_read = %s, rows_written = %s
            WHERE id = %s
            """,
            (rows_read, rows_written, run_id),
        )

    def fail_run(self, run_id: int, error: Exception) -> None:
        self.connection.rollback()
        self.connection.execute(
            """
            UPDATE etl_runs
            SET status = 'FAILED', finished_at = CURRENT_TIMESTAMP, error_message = %s
            WHERE id = %s
            """,
            (str(error)[:4000], run_id),
        )
        self.connection.commit()

    def record_file_result(
        self,
        run_id: int,
        file_name: str,
        fingerprint: str,
        rows_read: int,
        rows_inserted: int,
        rows_updated: int,
    ) -> None:
        self.connection.execute(
            """
            INSERT INTO etl_file_results
                (etl_run_id, file_name, file_fingerprint, rows_read, rows_inserted,
                 rows_updated)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (etl_run_id, file_name) DO NOTHING
            """,
            (run_id, file_name, fingerprint, rows_read, rows_inserted, rows_updated),
        )

    def existing_player_external_ids(self, external_ids: list[int]) -> set[int]:
        rows = self.connection.execute(
            """
            SELECT source_external_id
            FROM players
            WHERE source_external_id = ANY(%s)
            """,
            (external_ids,),
        ).fetchall()
        return {int(row["source_external_id"]) for row in rows}

    def upsert_country(self, name: str) -> int:
        row = self.connection.execute(
            """
            INSERT INTO countries (name) VALUES (%s)
            ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name
            RETURNING id
            """,
            (name,),
        ).fetchone()
        return int(row["id"])

    def upsert_club(
        self,
        external_id: int,
        name: str,
        run_id: int,
        *,
        slug: str | None = None,
        country_id: int | None = None,
        logo_url: str | None = None,
        is_complete: bool = False,
        data_as_of: date | None = None,
    ) -> int:
        row = self.connection.execute(
            """
            INSERT INTO clubs
                (source_external_id, name, slug, country_id, logo_url, is_complete,
                 data_as_of, source_etl_run_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (source_external_id) DO UPDATE SET
                name = EXCLUDED.name,
                slug = COALESCE(EXCLUDED.slug, clubs.slug),
                country_id = COALESCE(EXCLUDED.country_id, clubs.country_id),
                logo_url = COALESCE(EXCLUDED.logo_url, clubs.logo_url),
                is_complete = clubs.is_complete OR EXCLUDED.is_complete,
                data_as_of = COALESCE(EXCLUDED.data_as_of, clubs.data_as_of),
                source_etl_run_id = EXCLUDED.source_etl_run_id,
                updated_at = CURRENT_TIMESTAMP
            RETURNING id
            """,
            (external_id, name, slug, country_id, logo_url, is_complete, data_as_of, run_id),
        ).fetchone()
        return int(row["id"])

    def upsert_agent(self, external_id: int, name: str, run_id: int) -> int:
        row = self.connection.execute(
            """
            INSERT INTO agents (source_external_id, name, is_complete, source_etl_run_id)
            VALUES (%s, %s, FALSE, %s)
            ON CONFLICT (source_external_id) DO UPDATE SET
                name = EXCLUDED.name, source_etl_run_id = EXCLUDED.source_etl_run_id
            RETURNING id
            """,
            (external_id, name, run_id),
        ).fetchone()
        return int(row["id"])

    def upsert_season(
        self, label: str, start_year: int, end_year: int, calendar_type: str
    ) -> int:
        row = self.connection.execute(
            """
            INSERT INTO seasons (label, start_year, end_year, calendar_type)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (label, start_year, end_year) DO UPDATE SET
                calendar_type = EXCLUDED.calendar_type
            RETURNING id
            """,
            (label, start_year, end_year, calendar_type),
        ).fetchone()
        return int(row["id"])

    def upsert_competition(
        self, external_id: str, name: str, run_id: int
    ) -> int:
        row = self.connection.execute(
            """
            INSERT INTO competitions
                (source_external_id, name, is_complete, source_etl_run_id)
            VALUES (%s, %s, FALSE, %s)
            ON CONFLICT (source_external_id) DO UPDATE SET
                name = EXCLUDED.name,
                source_etl_run_id = EXCLUDED.source_etl_run_id
            RETURNING id
            """,
            (external_id, name, run_id),
        ).fetchone()
        return int(row["id"])

    def upsert_player(self, values: dict[str, Any]) -> int:
        row = self.connection.execute(
            """
            INSERT INTO players
                (source_external_id, slug, display_name, full_name, date_of_birth,
                 date_of_death, place_of_birth, country_of_birth_id, height_cm,
                 preferred_foot, career_status, image_url, is_complete, data_as_of,
                 source_etl_run_id)
            VALUES
                (%(source_external_id)s, %(slug)s, %(display_name)s, %(full_name)s,
                 %(date_of_birth)s, %(date_of_death)s, %(place_of_birth)s,
                 %(country_of_birth_id)s, %(height_cm)s, %(preferred_foot)s,
                 %(career_status)s, %(image_url)s, TRUE, %(data_as_of)s,
                 %(source_etl_run_id)s)
            ON CONFLICT (source_external_id) DO UPDATE SET
                slug = EXCLUDED.slug,
                display_name = EXCLUDED.display_name,
                full_name = EXCLUDED.full_name,
                date_of_birth = EXCLUDED.date_of_birth,
                date_of_death = EXCLUDED.date_of_death,
                place_of_birth = EXCLUDED.place_of_birth,
                country_of_birth_id = EXCLUDED.country_of_birth_id,
                height_cm = EXCLUDED.height_cm,
                preferred_foot = EXCLUDED.preferred_foot,
                career_status = EXCLUDED.career_status,
                image_url = EXCLUDED.image_url,
                is_complete = TRUE,
                data_as_of = EXCLUDED.data_as_of,
                source_etl_run_id = EXCLUDED.source_etl_run_id,
                updated_at = CURRENT_TIMESTAMP
            RETURNING id
            """,
            values,
        ).fetchone()
        return int(row["id"])

    def replace_citizenships(self, player_id: int, country_ids: list[int], run_id: int) -> None:
        self.connection.execute("DELETE FROM player_citizenships WHERE player_id = %s", (player_id,))
        with self.connection.cursor() as cursor:
            cursor.executemany(
                """
                INSERT INTO player_citizenships (player_id, country_id, source_etl_run_id)
                VALUES (%s, %s, %s)
                """,
                [(player_id, country_id, run_id) for country_id in country_ids],
            )

    def replace_primary_position(self, player_id: int, position_code: str | None, run_id: int) -> None:
        self.connection.execute("DELETE FROM player_positions WHERE player_id = %s", (player_id,))
        if position_code:
            self.connection.execute(
                """
                INSERT INTO player_positions (player_id, position_id, is_primary, source_etl_run_id)
                SELECT %s, id, TRUE, %s FROM positions WHERE code = %s
                """,
                (player_id, run_id, position_code),
            )

    def replace_current_agent(
        self, player_id: int, agent_id: int | None, data_as_of: date, run_id: int
    ) -> None:
        self.connection.execute(
            "DELETE FROM player_agent_representations WHERE player_id = %s AND is_current",
            (player_id,),
        )
        if agent_id:
            self.connection.execute(
                """
                INSERT INTO player_agent_representations
                    (player_id, agent_id, is_current, data_as_of, source_etl_run_id)
                VALUES (%s, %s, TRUE, %s, %s)
                """,
                (player_id, agent_id, data_as_of, run_id),
            )

    def replace_profile_memberships(
        self, player_id: int, memberships: list[dict[str, Any]], run_id: int
    ) -> None:
        self.connection.execute(
            """
            DELETE FROM player_club_memberships
            WHERE player_id = %s AND evidence_type = 'PROFILE_SNAPSHOT'
            """,
            (player_id,),
        )
        with self.connection.cursor() as cursor:
            cursor.executemany(
                """
                INSERT INTO player_club_memberships
                    (player_id, club_id, membership_type, start_date, end_date, is_current,
                     evidence_type, confidence, data_as_of, source_etl_run_id)
                VALUES
                    (%(player_id)s, %(club_id)s, %(membership_type)s, %(start_date)s,
                     %(end_date)s, TRUE, 'PROFILE_SNAPSHOT', 'CONFIRMED', %(data_as_of)s,
                     %(run_id)s)
                """,
                [
                    {**membership, "player_id": player_id, "run_id": run_id}
                    for membership in memberships
                ],
            )

    def upsert_performance(self, values: dict[str, Any]) -> bool:
        inserted = self.connection.execute(
            """
            INSERT INTO performances
                (player_id, club_id, competition_id, season_id, squad_appearances,
                 appearances, goals, assists, own_goals, substituted_in,
                 substituted_out, yellow_cards, second_yellow_cards, red_cards,
                 penalty_goals, minutes_played, goals_conceded, clean_sheets,
                 source_etl_run_id)
            VALUES
                (%(player_id)s, %(club_id)s, %(competition_id)s, %(season_id)s,
                 %(squad_appearances)s, %(appearances)s, %(goals)s, %(assists)s,
                 %(own_goals)s, %(substituted_in)s, %(substituted_out)s,
                 %(yellow_cards)s, %(second_yellow_cards)s, %(red_cards)s,
                 %(penalty_goals)s, %(minutes_played)s, %(goals_conceded)s,
                 %(clean_sheets)s, %(source_etl_run_id)s)
            ON CONFLICT (player_id, club_id, competition_id, season_id) DO NOTHING
            RETURNING id
            """,
            values,
        ).fetchone()
        if inserted:
            return True

        self.connection.execute(
            """
            UPDATE performances SET
                squad_appearances = %(squad_appearances)s,
                appearances = %(appearances)s,
                goals = %(goals)s,
                assists = %(assists)s,
                own_goals = %(own_goals)s,
                substituted_in = %(substituted_in)s,
                substituted_out = %(substituted_out)s,
                yellow_cards = %(yellow_cards)s,
                second_yellow_cards = %(second_yellow_cards)s,
                red_cards = %(red_cards)s,
                penalty_goals = %(penalty_goals)s,
                minutes_played = %(minutes_played)s,
                goals_conceded = %(goals_conceded)s,
                clean_sheets = %(clean_sheets)s,
                source_etl_run_id = %(source_etl_run_id)s
            WHERE player_id = %(player_id)s
              AND club_id = %(club_id)s
              AND competition_id = %(competition_id)s
              AND season_id = %(season_id)s
            """,
            values,
        )
        return False

    def upsert_market_value(self, values: dict[str, Any]) -> bool:
        inserted = self.connection.execute(
            """
            INSERT INTO market_values
                (player_id, valued_on, amount, currency_code, source_etl_run_id)
            VALUES
                (%(player_id)s, %(valued_on)s, %(amount)s, %(currency_code)s,
                 %(source_etl_run_id)s)
            ON CONFLICT (player_id, valued_on) DO NOTHING
            RETURNING id
            """,
            values,
        ).fetchone()
        if inserted:
            return True

        self.connection.execute(
            """
            UPDATE market_values SET
                amount = %(amount)s,
                currency_code = %(currency_code)s,
                source_etl_run_id = %(source_etl_run_id)s
            WHERE player_id = %(player_id)s AND valued_on = %(valued_on)s
            """,
            values,
        )
        return False

    def upsert_transfer(self, values: dict[str, Any]) -> bool:
        inserted = self.connection.execute(
            """
            INSERT INTO transfers
                (player_id, season_id, transfer_date, from_club_id, to_club_id,
                 transfer_type, from_career_state, to_career_state,
                 market_value_amount, fee_amount, currency_code, source_fingerprint,
                 source_etl_run_id)
            VALUES
                (%(player_id)s, %(season_id)s, %(transfer_date)s, %(from_club_id)s,
                 %(to_club_id)s, %(transfer_type)s, %(from_career_state)s,
                 %(to_career_state)s, %(market_value_amount)s, %(fee_amount)s,
                 %(currency_code)s, %(source_fingerprint)s, %(source_etl_run_id)s)
            ON CONFLICT (source_fingerprint) DO NOTHING
            RETURNING id
            """,
            values,
        ).fetchone()
        if inserted:
            return True

        self.connection.execute(
            """
            UPDATE transfers SET
                season_id = %(season_id)s,
                transfer_date = %(transfer_date)s,
                from_club_id = %(from_club_id)s,
                to_club_id = %(to_club_id)s,
                transfer_type = %(transfer_type)s,
                from_career_state = %(from_career_state)s,
                to_career_state = %(to_career_state)s,
                market_value_amount = %(market_value_amount)s,
                fee_amount = %(fee_amount)s,
                currency_code = %(currency_code)s,
                source_etl_run_id = %(source_etl_run_id)s
            WHERE source_fingerprint = %(source_fingerprint)s
            """,
            values,
        )
        return False

    def upsert_injury(self, values: dict[str, Any]) -> bool:
        inserted = self.connection.execute(
            """
            INSERT INTO injuries
                (player_id, season_id, reason, started_on, ended_on, days_missed,
                 games_missed, source_fingerprint, source_etl_run_id)
            VALUES
                (%(player_id)s, %(season_id)s, %(reason)s, %(started_on)s,
                 %(ended_on)s, %(days_missed)s, %(games_missed)s,
                 %(source_fingerprint)s, %(source_etl_run_id)s)
            ON CONFLICT (source_fingerprint) DO NOTHING
            RETURNING id
            """,
            values,
        ).fetchone()
        if inserted:
            return True

        self.connection.execute(
            """
            UPDATE injuries SET
                season_id = %(season_id)s,
                reason = %(reason)s,
                started_on = %(started_on)s,
                ended_on = %(ended_on)s,
                days_missed = %(days_missed)s,
                games_missed = %(games_missed)s,
                source_etl_run_id = %(source_etl_run_id)s
            WHERE source_fingerprint = %(source_fingerprint)s
            """,
            values,
        )
        return False

    def player_ids_by_external_id(self, external_ids: set[int]) -> dict[int, int]:
        rows = self.connection.execute(
            """
            SELECT id, source_external_id FROM players
            WHERE source_external_id = ANY(%s)
            """,
            (list(external_ids),),
        ).fetchall()
        return {int(row["source_external_id"]): int(row["id"]) for row in rows}

    def commit(self) -> None:
        self.connection.commit()
