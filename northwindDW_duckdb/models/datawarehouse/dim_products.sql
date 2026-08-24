WITH source AS (
    SELECT
        p.id AS product_id,
        p.product_code,
        p.product_name,
        p.description,
        s.company AS supplier_company,
        p.standard_cost,
        p.list_price,
        p.reorder_level,
        p.target_level,
        p.quantity_per_unit,
        p.discontinued,
        p.minimum_reorder_quantity,
        p.category,
        p.attachments,
        current_localtimestamp() AS insertion_timestamp
    FROM {{ ref('stg_products') }} AS p
    LEFT JOIN {{ ref('stg_suppliers') }} AS s
        ON s.id = CAST(NULLIF(split_part(p.supplier_ids, ';', 1), '') AS INTEGER)
),

unique_source AS (
    SELECT
        *,
        ROW_NUMBER() OVER (PARTITION BY product_id ORDER BY product_id) AS row_number
    FROM source
)

SELECT
    product_id,
    product_code,
    product_name,
    description,
    supplier_company,
    standard_cost,
    list_price,
    reorder_level,
    target_level,
    quantity_per_unit,
    discontinued,
    minimum_reorder_quantity,
    category,
    attachments,
    insertion_timestamp
FROM unique_source
WHERE row_number = 1