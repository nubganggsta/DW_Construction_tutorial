with source as (

    select * from {{ source('northwind', 'suppliers') }}
)
select
    *,
    current_localtimestamp() as ingestion_timestamp
from source