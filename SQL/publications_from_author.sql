SELECT 
    r.id,
    MAKE_FULL_NAME(r.first_name, r.middle_name, r.last_name) AS full_name,
    p.topic,
    p.doi,
    j.name as journal_name,
    ap.order_of_authorship,
    p.date_published
FROM resident r
JOIN author a ON r.id = a.resident_id
JOIN author_publication ap ON a.id = ap.author_id
JOIN publication p ON ap.publication_id = p.id
JOIN journal j ON p.journal_id = j.id
ORDER BY r.last_name, r.first_name, p.date_published LIMIT 1000;
