select
    client_id,
    strptime(date, '%Y%m%d')::date as date,
    property_id,
    session_source as source,
    session_medium as medium,
    session_campaign_name as campaign_name,
    {{ channel_group('session_source', 'session_medium') }} as channel_group,
    cast(sessions as bigint) as sessions,
    cast(engaged_sessions as bigint) as engaged_sessions,
    cast(total_users as bigint) as users,
    cast(key_events as double) as key_events,
    cast(purchase_revenue as double) as revenue
from {{ source('raw', 'ga4_traffic_daily') }}
