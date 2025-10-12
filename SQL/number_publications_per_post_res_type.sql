SELECT
    r.id as resident_id,
    MAKE_FULL_NAME (
        r.first_name,
        r.middle_name,
        r.last_name
    ) AS full_name,
    prc.type as post_residency_type,
    COUNT(
        DISTINCT CASE
            WHEN COALESCE(
                p.date_published,
                '9999-12-31'
            ) < r.match_year THEN ap.publication_id
            ELSE NULL
        END
    ) as pre_match_pubs,
    COUNT(
        DISTINCT CASE
            WHEN COALESCE(
                p.date_published,
                '9999-12-31'
            ) BETWEEN r.match_year AND COALESCE(r.grad_year, '9999')  THEN ap.publication_id
            ELSE NULL
        END
    ) as during_residency_pubs,
    COUNT(
        DISTINCT CASE
            WHEN COALESCE(
                p.date_published,
                '9999-12-31'
            ) > COALESCE(r.grad_year, '9999') THEN ap.publication_id
            ELSE NULL
        END
    ) as post_grad_pubs
FROM
    resident r
    LEFT JOIN post_residency_career prc ON r.post_residency_career_id = prc.id
    LEFT JOIN author a ON r.id = a.resident_id
    LEFT JOIN author_publication ap ON a.id = ap.author_id
    LEFT JOIN publication p ON ap.publication_id = p.id
GROUP BY
    r.id,
    prc.type
ORDER BY prc.type, r.last_name, r.first_name;