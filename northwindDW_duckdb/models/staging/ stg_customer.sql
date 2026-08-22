with source as (

    select * from {{ source('northwind', 'customer') }}
)
select
    *,
    current_localtimestamp() as ingestion_timestamp
from source