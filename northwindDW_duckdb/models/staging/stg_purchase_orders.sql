with source as (

    select * from {{ source('northwind', 'purchase_orders') }}
)
select
    *,
    current_localtimestamp() as ingestion_timestamp
from source