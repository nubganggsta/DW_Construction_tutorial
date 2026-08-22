with source as (

    select * from {{ source('northwind', 'products') }}
)
select
    *,
    current_localtimestamp() as ingestion_timestamp
from source