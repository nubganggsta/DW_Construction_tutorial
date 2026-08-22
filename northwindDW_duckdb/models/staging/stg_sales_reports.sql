with source as (

    select * from {{ source('northwind', 'sales_reports') }}
)
select
    *,
    current_localtimestamp() as ingestion_timestamp
from source