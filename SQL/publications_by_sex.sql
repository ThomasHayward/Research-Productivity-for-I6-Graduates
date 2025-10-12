SELECT
    r.sex,
    COUNT(DISTINCT ap.publication_id) AS total_publications,
    (
        SELECT COUNT(*)
        FROM resident r2
        WHERE
            r2.sex = r.sex
    ) AS total_residents,
    SUM(
        ap.order_of_authorship = '1st'
    ) AS first_author,
    SUM(
        ap.order_of_authorship = '2nd'
    ) AS second_author,
    SUM(
        ap.order_of_authorship = 'mid'
    ) AS mid_author,
    SUM(
        ap.order_of_authorship = 'last'
    ) AS last_author
FROM
    resident r
    JOIN author a ON a.resident_id = r.id
    JOIN author_publication ap ON ap.author_id = a.id
GROUP BY
    r.sex;