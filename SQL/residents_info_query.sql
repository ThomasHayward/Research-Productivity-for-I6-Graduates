SELECT 
    CONCAT(r.first_name, ' ', 
           CASE 
               WHEN r.middle_name IS NOT NULL THEN CONCAT(r.middle_name, ' ')
               ELSE ''
           END,
           r.last_name) AS full_name,
    r.grad_year,
    r.match_year,
    ms.name AS medical_school,
    res.name AS residency_program
FROM resident r
LEFT JOIN medical_school ms ON r.medical_school_id = ms.id
LEFT JOIN residency res ON r.residency_id = res.id
ORDER BY r.last_name, r.first_name;
