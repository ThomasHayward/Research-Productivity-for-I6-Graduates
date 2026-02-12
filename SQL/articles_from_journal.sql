-- Change the journal_id value below to get publications from a different journal
SET @journal_id = 461;

SELECT
    p.id AS publication_id,
    p.topic,
    p.date_published,
    p.type,
    p.doi,
    j.name AS journal_name,
    j.specialty,
    j.avg_impact_factor,
    GROUP_CONCAT(
        CONCAT(
            r.first_name,
            ' ',
            COALESCE(r.middle_name, ''),
            ' ',
            r.last_name
        )
        ORDER BY ap.order_of_authorship, a.id SEPARATOR '; '
    ) AS authors
FROM
    publication p
    INNER JOIN journal j ON p.journal_id = j.id
    LEFT JOIN author_publication ap ON p.id = ap.publication_id
    LEFT JOIN author a ON ap.author_id = a.id
    LEFT JOIN resident r ON a.resident_id = r.id
WHERE
    j.id = @journal_id
GROUP BY
    p.id,
    p.topic,
    p.date_published,
    p.type,
    p.doi,
    j.name,
    j.specialty,
    j.avg_impact_factor
ORDER BY p.date_published DESC;