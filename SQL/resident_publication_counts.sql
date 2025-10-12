SELECT
    r.id AS resident_id,
    MAKE_FULL_NAME (
        r.first_name,
        r.middle_name,
        r.last_name
    ) AS full_name,
    r.match_year,
    r.grad_year,
    ms.name AS medical_school,
    res.name AS residency_program,
    COUNT(DISTINCT ap.publication_id) as total_publications,
    COUNT(
        DISTINCT CASE
            WHEN ap.order_of_authorship = '1st' THEN ap.publication_id
        END
    ) AS first_author,
    COUNT(
        DISTINCT CASE
            WHEN ap.order_of_authorship = '2nd' THEN ap.publication_id
        END
    ) AS second_author,
    COUNT(
        DISTINCT CASE
            WHEN ap.order_of_authorship = 'mid' THEN ap.publication_id
        END
    ) AS middle_author,
    COUNT(
        DISTINCT CASE
            WHEN ap.order_of_authorship = 'last' THEN ap.publication_id
        END
    ) AS last_author,
    MIN(p.date_published) as earliest_pub,
    MAX(p.date_published) as latest_pub
FROM
    resident r
    LEFT JOIN medical_school ms ON r.medical_school_id = ms.id
    LEFT JOIN residency res ON r.residency_id = res.id
    LEFT JOIN author a ON a.resident_id = r.id
    LEFT JOIN author_publication ap ON ap.author_id = a.id
    LEFT JOIN publication p ON p.id = ap.publication_id
GROUP BY
    r.id,
    r.first_name,
    r.middle_name,
    r.last_name,
    r.match_year,
    r.grad_year,
    ms.name,
    res.name
ORDER BY total_publications DESC;