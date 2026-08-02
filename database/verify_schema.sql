\set ON_ERROR_STOP on

DO $$
DECLARE
    missing_tables TEXT[];
BEGIN
    SELECT ARRAY_AGG(required.name ORDER BY required.name)
    INTO missing_tables
    FROM (
        VALUES
            ('agents'), ('club_competition_seasons'), ('club_relationships'), ('clubs'),
            ('competitions'), ('countries'), ('etl_file_results'), ('etl_rejections'),
            ('etl_runs'), ('injuries'), ('market_values'), ('performances'),
            ('player_agent_representations'), ('player_citizenships'),
            ('player_club_memberships'), ('player_positions'), ('players'),
            ('position_groups'), ('positions'), ('seasons'), ('transfers')
    ) AS required(name)
    LEFT JOIN information_schema.tables actual
        ON actual.table_schema = 'public' AND actual.table_name = required.name
    WHERE actual.table_name IS NULL;

    IF missing_tables IS NOT NULL THEN
        RAISE EXCEPTION 'Missing tables: %', missing_tables;
    END IF;
END $$;

DO $$
BEGIN
    IF (SELECT COUNT(*) FROM position_groups) <> 4 THEN
        RAISE EXCEPTION 'Expected 4 position groups';
    END IF;

    IF (SELECT COUNT(*) FROM positions) <> 13 THEN
        RAISE EXCEPTION 'Expected 13 seeded positions';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM position_groups
        GROUP BY code
        HAVING COUNT(*) > 1
    ) THEN
        RAISE EXCEPTION 'Position group codes are not unique';
    END IF;
END $$;

SELECT 'PlayerHub schema verification passed' AS result;

