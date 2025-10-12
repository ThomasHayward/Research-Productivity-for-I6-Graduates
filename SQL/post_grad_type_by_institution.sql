SELECT
    res.name AS institution,
    prc.type AS post_grad_type,
    COUNT(r.id) AS num_residents
FROM
    resident r
    JOIN residency res ON r.residency_id = res.id
    JOIN post_residency_career prc ON r.post_residency_career_id = prc.id
WHERE
    prc.type IN ('Academic', 'Private')
GROUP BY
    res.name,
    prc.type
ORDER BY res.name, prc.type;