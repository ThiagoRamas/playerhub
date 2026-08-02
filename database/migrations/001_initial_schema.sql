BEGIN;

CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE etl_runs (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    importer_version TEXT NOT NULL,
    dataset_fingerprint TEXT NOT NULL,
    data_as_of DATE,
    status TEXT NOT NULL CHECK (status IN ('RUNNING', 'SUCCEEDED', 'FAILED')),
    started_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finished_at TIMESTAMPTZ,
    rows_read BIGINT NOT NULL DEFAULT 0 CHECK (rows_read >= 0),
    rows_written BIGINT NOT NULL DEFAULT 0 CHECK (rows_written >= 0),
    rows_rejected BIGINT NOT NULL DEFAULT 0 CHECK (rows_rejected >= 0),
    error_message TEXT,
    CONSTRAINT etl_runs_finished_after_start CHECK (finished_at IS NULL OR finished_at >= started_at),
    CONSTRAINT etl_runs_finished_state CHECK (
        (status = 'RUNNING' AND finished_at IS NULL)
        OR (status IN ('SUCCEEDED', 'FAILED') AND finished_at IS NOT NULL)
    )
);

CREATE TABLE etl_file_results (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    etl_run_id BIGINT NOT NULL REFERENCES etl_runs(id) ON DELETE CASCADE,
    file_name TEXT NOT NULL,
    file_fingerprint TEXT NOT NULL,
    rows_read BIGINT NOT NULL DEFAULT 0 CHECK (rows_read >= 0),
    rows_inserted BIGINT NOT NULL DEFAULT 0 CHECK (rows_inserted >= 0),
    rows_updated BIGINT NOT NULL DEFAULT 0 CHECK (rows_updated >= 0),
    rows_skipped BIGINT NOT NULL DEFAULT 0 CHECK (rows_skipped >= 0),
    rows_rejected BIGINT NOT NULL DEFAULT 0 CHECK (rows_rejected >= 0),
    UNIQUE (etl_run_id, file_name)
);

CREATE TABLE etl_rejections (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    etl_run_id BIGINT NOT NULL REFERENCES etl_runs(id) ON DELETE CASCADE,
    file_name TEXT NOT NULL,
    row_number BIGINT CHECK (row_number > 0),
    reason_code TEXT NOT NULL,
    reason_detail TEXT,
    row_data JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_etl_rejections_run_file ON etl_rejections (etl_run_id, file_name);

CREATE TABLE countries (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    iso_code CHAR(2) UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE position_groups (
    id SMALLINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code TEXT NOT NULL UNIQUE CHECK (code IN ('GOALKEEPER', 'DEFENDER', 'MIDFIELD', 'ATTACK')),
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE positions (
    id SMALLINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    group_id SMALLINT NOT NULL REFERENCES position_groups(id),
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    UNIQUE (group_id, name)
);

CREATE TABLE seasons (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    label TEXT NOT NULL,
    start_year SMALLINT NOT NULL CHECK (start_year BETWEEN 1800 AND 2200),
    end_year SMALLINT NOT NULL CHECK (end_year BETWEEN 1800 AND 2200),
    calendar_type TEXT NOT NULL CHECK (calendar_type IN ('SPLIT_YEAR', 'CALENDAR_YEAR', 'UNKNOWN')),
    UNIQUE (label, start_year, end_year),
    CHECK (end_year >= start_year AND end_year <= start_year + 1)
);

CREATE TABLE competitions (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_external_id TEXT UNIQUE,
    name TEXT NOT NULL,
    slug TEXT,
    country_id BIGINT REFERENCES countries(id),
    is_complete BOOLEAN NOT NULL DEFAULT FALSE,
    source_etl_run_id BIGINT REFERENCES etl_runs(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE players (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_external_id BIGINT NOT NULL UNIQUE CHECK (source_external_id > 0),
    slug TEXT,
    display_name TEXT NOT NULL,
    full_name TEXT,
    date_of_birth DATE,
    date_of_death DATE,
    place_of_birth TEXT,
    country_of_birth_id BIGINT REFERENCES countries(id),
    height_cm SMALLINT CHECK (height_cm BETWEEN 100 AND 250),
    preferred_foot TEXT NOT NULL DEFAULT 'UNKNOWN' CHECK (preferred_foot IN ('RIGHT', 'LEFT', 'BOTH', 'UNKNOWN')),
    career_status TEXT NOT NULL DEFAULT 'UNKNOWN' CHECK (career_status IN ('ACTIVE', 'RETIRED', 'WITHOUT_CLUB', 'CAREER_BREAK', 'UNKNOWN')),
    image_url TEXT,
    is_complete BOOLEAN NOT NULL DEFAULT FALSE,
    data_as_of DATE,
    source_etl_run_id BIGINT REFERENCES etl_runs(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (date_of_death IS NULL OR date_of_birth IS NULL OR date_of_death >= date_of_birth)
);

CREATE INDEX idx_players_display_name_trgm ON players USING GIN (display_name gin_trgm_ops);
CREATE INDEX idx_players_birth_date ON players (date_of_birth);
CREATE INDEX idx_players_career_status ON players (career_status);

CREATE TABLE player_citizenships (
    player_id BIGINT NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    country_id BIGINT NOT NULL REFERENCES countries(id),
    source_etl_run_id BIGINT REFERENCES etl_runs(id),
    PRIMARY KEY (player_id, country_id)
);

CREATE TABLE player_positions (
    player_id BIGINT NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    position_id SMALLINT NOT NULL REFERENCES positions(id),
    is_primary BOOLEAN NOT NULL DEFAULT FALSE,
    source_etl_run_id BIGINT REFERENCES etl_runs(id),
    PRIMARY KEY (player_id, position_id)
);

CREATE UNIQUE INDEX uq_player_primary_position ON player_positions (player_id) WHERE is_primary;

CREATE TABLE clubs (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_external_id BIGINT NOT NULL UNIQUE CHECK (source_external_id > 0),
    name TEXT NOT NULL,
    slug TEXT,
    country_id BIGINT REFERENCES countries(id),
    team_type TEXT NOT NULL DEFAULT 'OTHER' CHECK (team_type IN ('FIRST_TEAM', 'RESERVE', 'YOUTH', 'NATIONAL_TEAM', 'OTHER')),
    logo_url TEXT,
    is_complete BOOLEAN NOT NULL DEFAULT FALSE,
    data_as_of DATE,
    source_etl_run_id BIGINT REFERENCES etl_runs(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_clubs_name_trgm ON clubs USING GIN (name gin_trgm_ops);
CREATE INDEX idx_clubs_country ON clubs (country_id);

CREATE TABLE club_relationships (
    parent_club_id BIGINT NOT NULL REFERENCES clubs(id) ON DELETE CASCADE,
    child_club_id BIGINT NOT NULL REFERENCES clubs(id) ON DELETE CASCADE,
    relationship_type TEXT NOT NULL CHECK (relationship_type IN ('RESERVE', 'YOUTH', 'AFFILIATE', 'OTHER')),
    source_etl_run_id BIGINT REFERENCES etl_runs(id),
    PRIMARY KEY (parent_club_id, child_club_id, relationship_type),
    CHECK (parent_club_id <> child_club_id)
);

CREATE TABLE agents (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_external_id BIGINT UNIQUE CHECK (source_external_id > 0),
    name TEXT NOT NULL,
    is_complete BOOLEAN NOT NULL DEFAULT FALSE,
    source_etl_run_id BIGINT REFERENCES etl_runs(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE player_agent_representations (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    player_id BIGINT NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    agent_id BIGINT NOT NULL REFERENCES agents(id),
    start_date DATE,
    end_date DATE,
    is_current BOOLEAN NOT NULL DEFAULT FALSE,
    data_as_of DATE,
    source_etl_run_id BIGINT REFERENCES etl_runs(id),
    CHECK (end_date IS NULL OR start_date IS NULL OR end_date >= start_date),
    UNIQUE NULLS NOT DISTINCT (player_id, agent_id, start_date, end_date)
);

CREATE UNIQUE INDEX uq_player_current_agent ON player_agent_representations (player_id) WHERE is_current;

CREATE TABLE player_club_memberships (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    player_id BIGINT NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    club_id BIGINT NOT NULL REFERENCES clubs(id),
    membership_type TEXT NOT NULL CHECK (membership_type IN ('PERMANENT', 'LOAN', 'YOUTH', 'UNKNOWN')),
    start_date DATE,
    end_date DATE,
    is_current BOOLEAN NOT NULL DEFAULT FALSE,
    evidence_type TEXT NOT NULL CHECK (evidence_type IN ('PROFILE_SNAPSHOT', 'TRANSFER_INFERRED', 'PERFORMANCE_INFERRED')),
    confidence TEXT NOT NULL CHECK (confidence IN ('CONFIRMED', 'HIGH', 'MEDIUM', 'LOW')),
    data_as_of DATE,
    source_etl_run_id BIGINT REFERENCES etl_runs(id),
    CHECK (end_date IS NULL OR start_date IS NULL OR end_date >= start_date),
    CHECK (NOT is_current OR data_as_of IS NOT NULL),
    UNIQUE NULLS NOT DISTINCT (player_id, club_id, membership_type, start_date, end_date, evidence_type)
);

CREATE INDEX idx_memberships_current_club ON player_club_memberships (club_id, player_id) WHERE is_current;
CREATE INDEX idx_memberships_player_dates ON player_club_memberships (player_id, start_date, end_date);

CREATE TABLE club_competition_seasons (
    club_id BIGINT NOT NULL REFERENCES clubs(id) ON DELETE CASCADE,
    competition_id BIGINT NOT NULL REFERENCES competitions(id) ON DELETE CASCADE,
    season_id BIGINT NOT NULL REFERENCES seasons(id) ON DELETE CASCADE,
    division_name TEXT,
    source_etl_run_id BIGINT REFERENCES etl_runs(id),
    PRIMARY KEY (club_id, competition_id, season_id)
);

CREATE INDEX idx_club_competition_seasons_competition ON club_competition_seasons (competition_id, season_id);

CREATE TABLE performances (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    player_id BIGINT NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    club_id BIGINT NOT NULL REFERENCES clubs(id),
    competition_id BIGINT NOT NULL REFERENCES competitions(id),
    season_id BIGINT NOT NULL REFERENCES seasons(id),
    squad_appearances INTEGER CHECK (squad_appearances >= 0),
    appearances INTEGER CHECK (appearances >= 0),
    goals INTEGER CHECK (goals >= 0),
    assists INTEGER CHECK (assists >= 0),
    own_goals INTEGER CHECK (own_goals >= 0),
    substituted_in INTEGER CHECK (substituted_in >= 0),
    substituted_out INTEGER CHECK (substituted_out >= 0),
    yellow_cards INTEGER CHECK (yellow_cards >= 0),
    second_yellow_cards INTEGER CHECK (second_yellow_cards >= 0),
    red_cards INTEGER CHECK (red_cards >= 0),
    penalty_goals INTEGER CHECK (penalty_goals >= 0),
    minutes_played INTEGER CHECK (minutes_played >= 0),
    goals_conceded INTEGER CHECK (goals_conceded >= 0),
    clean_sheets INTEGER CHECK (clean_sheets >= 0),
    source_etl_run_id BIGINT REFERENCES etl_runs(id),
    UNIQUE (player_id, club_id, competition_id, season_id)
);

CREATE INDEX idx_performances_club_season ON performances (club_id, season_id);
CREATE INDEX idx_performances_competition_season ON performances (competition_id, season_id);
CREATE INDEX idx_performances_player_season ON performances (player_id, season_id);

CREATE TABLE market_values (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    player_id BIGINT NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    valued_on DATE NOT NULL,
    amount BIGINT NOT NULL CHECK (amount >= 0),
    currency_code CHAR(3),
    source_etl_run_id BIGINT REFERENCES etl_runs(id),
    UNIQUE (player_id, valued_on),
    CHECK (currency_code IS NULL OR currency_code ~ '^[A-Z]{3}$')
);

CREATE INDEX idx_market_values_player_latest ON market_values (player_id, valued_on DESC);

CREATE TABLE transfers (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    player_id BIGINT NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    season_id BIGINT REFERENCES seasons(id),
    transfer_date DATE,
    from_club_id BIGINT REFERENCES clubs(id),
    to_club_id BIGINT REFERENCES clubs(id),
    transfer_type TEXT NOT NULL CHECK (transfer_type IN ('TRANSFER', 'LOAN', 'LOAN_RETURN', 'DRAFT')),
    from_career_state TEXT CHECK (from_career_state IN ('WITHOUT_CLUB', 'RETIRED', 'CAREER_BREAK', 'UNKNOWN')),
    to_career_state TEXT CHECK (to_career_state IN ('WITHOUT_CLUB', 'RETIRED', 'CAREER_BREAK', 'UNKNOWN')),
    market_value_amount BIGINT CHECK (market_value_amount >= 0),
    fee_amount BIGINT CHECK (fee_amount >= 0),
    currency_code CHAR(3),
    source_fingerprint TEXT NOT NULL UNIQUE,
    source_etl_run_id BIGINT REFERENCES etl_runs(id),
    CHECK (from_club_id IS NOT NULL OR from_career_state IS NOT NULL),
    CHECK (to_club_id IS NOT NULL OR to_career_state IS NOT NULL),
    CHECK (currency_code IS NULL OR currency_code ~ '^[A-Z]{3}$')
);

CREATE INDEX idx_transfers_player_date ON transfers (player_id, transfer_date DESC);
CREATE INDEX idx_transfers_from_club ON transfers (from_club_id, transfer_date DESC);
CREATE INDEX idx_transfers_to_club ON transfers (to_club_id, transfer_date DESC);

CREATE TABLE injuries (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    player_id BIGINT NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    season_id BIGINT REFERENCES seasons(id),
    reason TEXT NOT NULL,
    started_on DATE,
    ended_on DATE,
    days_missed INTEGER CHECK (days_missed >= 0),
    games_missed INTEGER CHECK (games_missed >= 0),
    source_fingerprint TEXT NOT NULL UNIQUE,
    source_etl_run_id BIGINT REFERENCES etl_runs(id),
    CHECK (ended_on IS NULL OR started_on IS NULL OR ended_on >= started_on)
);

CREATE INDEX idx_injuries_player_date ON injuries (player_id, started_on DESC);

INSERT INTO position_groups (code, name)
VALUES
    ('GOALKEEPER', 'Goalkeeper'),
    ('DEFENDER', 'Defender'),
    ('MIDFIELD', 'Midfield'),
    ('ATTACK', 'Attack');

INSERT INTO positions (group_id, code, name)
SELECT id, 'GOALKEEPER', 'Goalkeeper' FROM position_groups WHERE code = 'GOALKEEPER'
UNION ALL
SELECT id, 'CENTRE_BACK', 'Centre-Back' FROM position_groups WHERE code = 'DEFENDER'
UNION ALL
SELECT id, 'RIGHT_BACK', 'Right-Back' FROM position_groups WHERE code = 'DEFENDER'
UNION ALL
SELECT id, 'LEFT_BACK', 'Left-Back' FROM position_groups WHERE code = 'DEFENDER'
UNION ALL
SELECT id, 'DEFENSIVE_MIDFIELD', 'Defensive Midfield' FROM position_groups WHERE code = 'MIDFIELD'
UNION ALL
SELECT id, 'CENTRAL_MIDFIELD', 'Central Midfield' FROM position_groups WHERE code = 'MIDFIELD'
UNION ALL
SELECT id, 'RIGHT_MIDFIELD', 'Right Midfield' FROM position_groups WHERE code = 'MIDFIELD'
UNION ALL
SELECT id, 'LEFT_MIDFIELD', 'Left Midfield' FROM position_groups WHERE code = 'MIDFIELD'
UNION ALL
SELECT id, 'ATTACKING_MIDFIELD', 'Attacking Midfield' FROM position_groups WHERE code = 'MIDFIELD'
UNION ALL
SELECT id, 'SECOND_STRIKER', 'Second Striker' FROM position_groups WHERE code = 'ATTACK'
UNION ALL
SELECT id, 'RIGHT_WINGER', 'Right Winger' FROM position_groups WHERE code = 'ATTACK'
UNION ALL
SELECT id, 'LEFT_WINGER', 'Left Winger' FROM position_groups WHERE code = 'ATTACK'
UNION ALL
SELECT id, 'CENTRE_FORWARD', 'Centre-Forward' FROM position_groups WHERE code = 'ATTACK';

COMMIT;

