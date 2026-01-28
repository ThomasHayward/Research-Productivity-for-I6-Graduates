-- Calculate publication rates (publications per year) for post-residency period
-- Controls for time since graduation by calculating rate instead of raw count

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
            END as fellowship,
            -- Calculate years since graduation (as of October 2025)
            (2025 - r.grad_year) as years_post_graduation
        FROM
            resident r
            JOIN post_residency_career prc ON r.post_residency_career_id = prc.id
            JOIN residency res ON r.residency_id = res.id
            LEFT JOIN fellowship f ON r.fellowship_id = f.id
        WHERE
            prc.type IN ('Academic', 'Private')
            AND r.grad_year IS NOT NULL
            -- Only include residents who have graduated (at least 1 year post-graduation)
            AND r.grad_year <= 2024
    )
SELECT
    rd.id as resident_id,
    rd.career_type as post_residency_career_type,
    rd.sex,
    rd.institution,
    rd.fellowship,
    rd.grad_year,
    rd.years_post_graduation,
    COUNT(
        DISTINCT CASE
            WHEN p.date_published > CONCAT(rd.grad_year, '-06-30') THEN p.id
            ELSE NULL
        END
    ) as total_publications,
    -- Calculate publication rate (publications per year)
    CASE
        WHEN rd.years_post_graduation > 0 THEN COUNT(
            DISTINCT CASE
                WHEN p.date_published > CONCAT(rd.grad_year, '-06-30') THEN p.id
                ELSE NULL
            END
        ) / rd.years_post_graduation
        ELSE 0
    END as publications_per_year
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
    rd.fellowship,
    rd.grad_year,
    rd.years_post_graduation
ORDER BY rd.career_type, rd.years_post_graduation DESC;