BEGIN;

CREATE TABLE data_sources (
    id SMALLINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO data_sources (code, name)
VALUES
    ('TRANSFERMARKT_CSV', 'Transfermarkt CSV archive'),
    ('API_FOOTBALL', 'API-Football')
ON CONFLICT (code) DO NOTHING;

CREATE TABLE club_source_identifiers (
    club_id BIGINT NOT NULL REFERENCES clubs(id) ON DELETE CASCADE,
    source_id SMALLINT NOT NULL REFERENCES data_sources(id),
    external_id TEXT NOT NULL,
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    source_etl_run_id BIGINT REFERENCES etl_runs(id),
    PRIMARY KEY (club_id, source_id),
    UNIQUE (source_id, external_id)
);

CREATE TABLE player_source_identifiers (
    player_id BIGINT NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    source_id SMALLINT NOT NULL REFERENCES data_sources(id),
    external_id TEXT NOT NULL,
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    source_etl_run_id BIGINT REFERENCES etl_runs(id),
    PRIMARY KEY (player_id, source_id),
    UNIQUE (source_id, external_id)
);

INSERT INTO club_source_identifiers
    (club_id, source_id, external_id, source_etl_run_id)
SELECT club.id, source.id, club.source_external_id::TEXT, club.source_etl_run_id
FROM clubs club
CROSS JOIN data_sources source
WHERE source.code = 'TRANSFERMARKT_CSV'
ON CONFLICT (club_id, source_id) DO NOTHING;

INSERT INTO player_source_identifiers
    (player_id, source_id, external_id, source_etl_run_id)
SELECT player.id, source.id, player.source_external_id::TEXT, player.source_etl_run_id
FROM players player
CROSS JOIN data_sources source
WHERE source.code = 'TRANSFERMARKT_CSV'
ON CONFLICT (player_id, source_id) DO NOTHING;

ALTER TABLE players ALTER COLUMN source_external_id DROP NOT NULL;

ALTER TABLE player_club_memberships
    DROP CONSTRAINT player_club_memberships_evidence_type_check;

ALTER TABLE player_club_memberships
    ADD CONSTRAINT player_club_memberships_evidence_type_check
    CHECK (evidence_type IN (
        'PROFILE_SNAPSHOT', 'LIVE_SQUAD', 'TRANSFER_INFERRED', 'PERFORMANCE_INFERRED'
    ));

ALTER TABLE player_club_memberships
    ADD COLUMN squad_number SMALLINT CHECK (squad_number BETWEEN 1 AND 99);

INSERT INTO positions (group_id, code, name)
SELECT id, 'DEFENDER', 'Defender' FROM position_groups WHERE code = 'DEFENDER'
ON CONFLICT (code) DO NOTHING;

INSERT INTO positions (group_id, code, name)
SELECT id, 'MIDFIELDER', 'Midfielder' FROM position_groups WHERE code = 'MIDFIELD'
ON CONFLICT (code) DO NOTHING;

INSERT INTO positions (group_id, code, name)
SELECT id, 'ATTACKER', 'Attacker' FROM position_groups WHERE code = 'ATTACK'
ON CONFLICT (code) DO NOTHING;

COMMIT;
