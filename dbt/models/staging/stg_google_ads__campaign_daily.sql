select
    client_id,
    cast(segments_date as date) as date,
    customer_id,
    campaign_id,
    campaign_name,
    campaign_advertising_channel_type as channel_type,
    cast(metrics_impressions as bigint) as impressions,
    cast(metrics_clicks as bigint) as clicks,
    cast(metrics_cost_micros as double) / 1000000.0 as spend,
    cast(metrics_conversions as double) as conversions,
    cast(metrics_conversions_value as double) as conversion_value
from {{ source('raw', 'google_ads_campaign_daily') }}
