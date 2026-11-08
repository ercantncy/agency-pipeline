select
    client_id,
    cast(date_trunc('month', date) as date) as month,
    query,
    sum(clicks) as clicks,
    sum(impressions) as impressions,
    sum(clicks) * 1.0 / nullif(sum(impressions), 0) as ctr,
    sum(position * impressions) / nullif(sum(impressions), 0) as avg_position
from {{ ref('stg_gsc__search_daily') }}
group by client_id, cast(date_trunc('month', date) as date), query
