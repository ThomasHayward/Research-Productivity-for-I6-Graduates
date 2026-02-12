-- Change avg_impact_factor column from int to varchar to preserve decimal values
ALTER TABLE journal MODIFY COLUMN avg_impact_factor VARCHAR(10);

-- Change max_impact_factor column as well if needed
ALTER TABLE journal MODIFY COLUMN max_impact_factor VARCHAR(10);

-- Delete journals that have no publications linked to them
DELETE FROM journal
WHERE
    id NOT IN(
        SELECT DISTINCT
            journal_id
        FROM publication
        WHERE
            journal_id IS NOT NULL
    );

-- Check how many would be deleted first (run this before the DELETE):
SELECT
    COUNT(*) AS journals_to_delete,
    (
        SELECT COUNT(*)
        FROM journal
    ) AS total_journals,
    COUNT(*) * 100.0 / (
        SELECT COUNT(*)
        FROM journal
    ) AS percentage
FROM journal j
    LEFT JOIN publication p ON j.id = p.journal_id
WHERE
    p.id IS NULL;

-- Count residents by publication/IF status
SELECT
    CASE
        WHEN pub_count = 0 THEN 'No publications'
        WHEN valid_if_count = 0 THEN 'Has pubs, but no valid IF'
        WHEN valid_if_count < pub_count THEN 'Some pubs with IF'
        ELSE 'All pubs have IF'
    END AS status,
    COUNT(*) AS resident_count
FROM (
        SELECT r.id, COUNT(p.id) AS pub_count, COUNT(
                CASE
                    WHEN j.avg_impact_factor REGEXP '^[0-9]+\\.?[0-9]*$' THEN 1
                END
            ) AS valid_if_count
        FROM
            resident r
            LEFT JOIN author a ON a.resident_id = r.id
            LEFT JOIN author_publication ap ON ap.author_id = a.id
            LEFT JOIN publication p ON p.id = ap.publication_id
            LEFT JOIN journal j ON j.id = p.journal_id
        GROUP BY
            r.id
    ) AS resident_stats
GROUP BY
    status;