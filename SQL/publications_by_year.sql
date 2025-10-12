SELECT EXTRACT(
        YEAR
        FROM p.date_published
    ) AS year, COUNT(*) AS publication_count
FROM
    author_publication ap
    JOIN publication p ON ap.publication_id = p.id
WHERE
    p.date_published IS NOT NULL
GROUP BY
    year
ORDER BY year ASC;