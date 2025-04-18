SELECT 
    r.id,
    MAKE_FULL_NAME(r.first_name, r.middle_name, r.last_name) AS full_name,
    r.match_year,
    r.grad_year
FROM resident r
LEFT JOIN author a ON a.resident_id = r.id
LEFT JOIN author_publication ap ON ap.author_id = a.id
LEFT JOIN publication p ON p.id = ap.publication_id
WHERE a.id IS NULL;