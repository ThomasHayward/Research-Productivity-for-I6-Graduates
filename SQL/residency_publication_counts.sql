SELECT
    res.name AS residency,
    COUNT(DISTINCT ap.publication_id) AS total_publications,
    COUNT(DISTINCT CASE WHEN ap.order_of_authorship = '1st' THEN ap.publication_id END) AS first_author_count,
    COUNT(DISTINCT CASE WHEN ap.order_of_authorship = '2nd' THEN ap.publication_id END) AS second_author_count,
    COUNT(DISTINCT CASE WHEN ap.order_of_authorship = 'mid' THEN ap.publication_id END) AS mid_author_count,
    COUNT(DISTINCT CASE WHEN ap.order_of_authorship = 'last' THEN ap.publication_id END) AS last_author_count
FROM residency res
JOIN resident r ON r.residency_id = res.id
LEFT JOIN author a ON a.resident_id = r.id
LEFT JOIN author_publication ap ON ap.author_id = a.id
GROUP BY res.id, res.name
ORDER BY total_publications DESC;
