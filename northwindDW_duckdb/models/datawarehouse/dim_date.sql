SELECT
    strftime(d, '%Y-%m-%d') AS id,
    d AS full_date,
    date_part('year', d) AS year,
    date_part('week', d) AS year_week,
    date_part('dayofyear', d) AS year_day,
    date_part('year', d) AS fiscal_year,
    strftime(d, '%Y') || '-Q' || CAST(date_part('quarter', d) AS VARCHAR) AS fiscal_qtr,
    date_part('month', d) AS month,
    monthname(d) AS month_name,
    date_part('dow', d) AS week_day,
    dayname(d) AS day_name,
    CASE
        WHEN date_part('dow', d) IN (0, 6) THEN 0
        ELSE 1
    END AS day_is_weekday
FROM (
    SELECT d
    FROM generate_series(DATE '2014-01-01', DATE '2050-01-01', INTERVAL 1 DAY) AS t(d)
)