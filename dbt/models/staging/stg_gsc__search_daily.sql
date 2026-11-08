select
    client_id,
    cast(date as date) as date,
    site_url,
    query,
    page,
    cast(clicks as bigint) as clicks,
    cast(impressions as bigint) as impressions,
    cast(ctr as double) as ctr,
    cast(position as double) as position
from {{ source('raw', 'gsc_search_daily') }}
