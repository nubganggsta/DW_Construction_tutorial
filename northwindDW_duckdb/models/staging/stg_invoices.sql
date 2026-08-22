with source as (

    select * from {{ source('northwind', 'invoices') }}
)
select
    *,
    current_localtimestamp() as ingestion_timestamp
from source