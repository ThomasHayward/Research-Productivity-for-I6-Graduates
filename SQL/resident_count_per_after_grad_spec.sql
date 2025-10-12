-- Number of residents by post-residency career type (Academic vs Private)
SELECT prc.type AS career_type, COUNT(*) AS resident_count
FROM
    resident r
    JOIN post_residency_career prc ON r.post_residency_career_id = prc.id
WHERE
    prc.type IN ('Academic', 'Private')
GROUP BY
    prc.type;