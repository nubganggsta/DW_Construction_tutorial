with source as (

    select * from {{ source('northwind', 'employees') }}
)
select
    *,
    current_localtimestamp() as ingestion_timestamp
from source