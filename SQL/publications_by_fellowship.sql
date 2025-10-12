SELECT
    t.fellowship_status,
    COUNT(DISTINCT ap.publication_id) AS total_publications,
    t.total_residents,
    SUM(
        ap.order_of_authorship = '1st'
    ) AS first_author,
    SUM(
        ap.order_of_authorship = '2nd'
    ) AS second_author,
    SUM(
        ap.order_of_authorship = 'mid'
    ) AS mid_author,
    SUM(
        ap.order_of_authorship = 'last'
    ) AS last_author
FROM (
        SELECT
            CASE
                WHEN fellowship_id IS NULL THEN 'No Fellowship'
                ELSE 'Fellowship'
            END AS fellowship_status,
            COUNT(*) AS total_residents
        FROM resident
        GROUP BY
            fellowship_status
    ) t
    JOIN resident r ON (
        CASE
            WHEN r.fellowship_id IS NULL THEN 'No Fellowship'
            ELSE 'Fellowship'
        END
    ) = t.fellowship_status
    JOIN author a ON a.resident_id = r.id
    JOIN author_publication ap ON ap.author_id = a.id
GROUP BY
    t.fellowship_status,
    t.total_residents;