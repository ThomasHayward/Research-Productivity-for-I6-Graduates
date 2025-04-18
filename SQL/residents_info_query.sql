SELECT 
    MAKE_FULL_NAME(r.first_name, r.middle_name, r.last_name) AS full_name,
    r.match_year,
    r.grad_year,
    ms.name AS medical_school,
    res.name AS residency_program,
    COUNT(DISTINCT ap.publication_id) AS publication_count,
    SUM(CASE WHEN ap.order_of_authorship = '1st' THEN 1 ELSE 0 END) AS first_author_count,
    SUM(CASE WHEN ap.order_of_authorship = '2nd' THEN 1 ELSE 0 END) AS second_author_count,
    SUM(CASE WHEN ap.order_of_authorship = 'mid' THEN 1 ELSE 0 END) AS mid_author_count,
    SUM(CASE WHEN ap.order_of_authorship = 'last' THEN 1 ELSE 0 END) AS last_author_count
FROM resident r
LEFT JOIN medical_school ms ON r.medical_school_id = ms.id
LEFT JOIN residency res ON r.residency_id = res.id
LEFT JOIN author a ON a.resident_id = r.id
LEFT JOIN author_publication ap ON ap.author_id = a.id
GROUP BY r.id, r.first_name, r.middle_name, r.last_name, r.match_year, r.grad_year, ms.name, res.name;
