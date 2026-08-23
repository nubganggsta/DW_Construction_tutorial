with source as (

    select * from {{ source('northwind', 'inventory_transaction_types') }}
)
select
    *,
    current_localtimestamp() as ingestion_timestamp
from source