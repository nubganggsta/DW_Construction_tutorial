with source as (

    select * from {{ source('northwind', 'inventory_transactions') }}
)
select
    *,
    current_localtimestamp() as ingestion_timestamp
from source