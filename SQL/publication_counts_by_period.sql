WITH
    ResidentDates AS (
        SELECT
            r.id,
            r.match_year,
            r.grad_year,
            prc.type as career_type,
            r.sex,
            res.name as institution,
            CASE
                WHEN f.id IS NOT NULL THEN TRUE
                ELSE FALSE
            END as fellowship
        FROM
            resident r
            JOIN post_residency_career prc ON r.post_residency_career_id = prc.id
            JOIN residency res ON r.residency_id = res.id
            LEFT JOIN fellowship f ON r.fellowship_id = f.id
    )
SELECT
    rd.id as resident_id,
    rd.career_type as post_residency_career_type,
    rd.sex,
    rd.institution,
    rd.fellowship,
    COUNT(
        DISTINCT CASE
            WHEN p.date_published BETWEEN CONCAT(rd.match_year, '-07-01') AND CONCAT(rd.grad_year, '-06-30')  THEN p.id
            ELSE NULL
        END
    ) as total_publications
FROM
    ResidentDates rd
    LEFT JOIN author a ON rd.id = a.resident_id
    LEFT JOIN author_publication ap ON a.id = ap.author_id
    LEFT JOIN publication p ON ap.publication_id = p.id
GROUP BY
    rd.id,
    rd.career_type,
    rd.sex,
    rd.institution,
    rd.fellowship
ORDER BY rd.career_type;

-- Query for publications post residency
WITH
    ResidentDates AS (
        SELECT
            r.id,
            r.grad_year,
            prc.type as career_type,
            r.sex,
            res.name as institution,
            CASE
                WHEN f.id IS NOT NULL THEN TRUE
                ELSE FALSE
            END as fellowship
        FROM
            resident r
            JOIN post_residency_career prc ON r.post_residency_career_id = prc.id
            JOIN residency res ON r.residency_id = res.id
            LEFT JOIN fellowship f ON r.fellowship_id = f.id
    )
SELECT
    rd.id as resident_id,
    rd.career_type as post_residency_career_type,
    rd.sex,
    rd.institution,
    rd.fellowship,
    COUNT(
        DISTINCT CASE
            WHEN p.date_published > CONCAT(rd.grad_year, '-06-30') THEN p.id
            ELSE NULL
        END
    ) as total_publications
FROM
    ResidentDates rd
    LEFT JOIN author a ON rd.id = a.resident_id
    LEFT JOIN author_publication ap ON a.id = ap.author_id
    LEFT JOIN publication p ON ap.publication_id = p.id
GROUP BY
    rd.id,
    rd.career_type,
    rd.sex,
    rd.institution,
    rd.fellowship
ORDER BY rd.career_type;