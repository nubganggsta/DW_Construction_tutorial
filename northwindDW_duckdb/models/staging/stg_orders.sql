with source as (

    select * from {{ source('northwind', 'orders') }}
)
select
    *,
    current_localtimestamp() as ingestion_timestamp
from source