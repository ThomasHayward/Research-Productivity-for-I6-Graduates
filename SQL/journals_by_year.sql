SELECT
    YEAR(p.date_published) AS year,
    j.name AS journal_name,
    COUNT(*) AS publication_count
FROM publication p
    JOIN journal j ON p.journal_id = j.id
GROUP BY
    YEAR(p.date_published),
    j.name
ORDER BY year DESC, publication_count DESC;