select
    client_id,
    date,
    'google_ads' as channel,
    campaign_id,
    campaign_name,
    spend,
    impressions,
    clicks,
    conversions as platform_conversions,
    conversion_value as platform_conversion_value
from {{ ref('stg_google_ads__campaign_daily') }}

union all

select
    client_id,
    date,
    'meta_ads' as channel,
    campaign_id,
    campaign_name,
    spend,
    impressions,
    inline_link_clicks as clicks,
    cast(purchases + leads as double) as platform_conversions,
    purchase_value as platform_conversion_value
from {{ ref('stg_meta_ads__campaign_daily') }}
