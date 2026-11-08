select
    client_id,
    date,
    channel_group,
    sum(sessions) as sessions,
    sum(engaged_sessions) as engaged_sessions,
    sum(users) as users,
    sum(key_events) as key_events,
    sum(revenue) as revenue
from {{ ref('stg_ga4__traffic_daily') }}
group by client_id, date, channel_group
