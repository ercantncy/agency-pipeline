{# Platform clicks vs GA4 sessions per day. Full outer join so days with clicks but no GA4 rows still appear. #}
with platform as (
    select
        client_id,
        date,
        channel,
        sum(clicks) as platform_clicks,
        sum(platform_conversions) as platform_conversions
    from {{ ref('fct_paid_daily') }}
    group by client_id, date, channel
),

ga4 as (
    select
        client_id,
        date,
        case channel_group
            when 'paid_search' then 'google_ads'
            when 'paid_social' then 'meta_ads'
        end as channel,
        sessions as ga4_sessions,
        key_events as ga4_key_events
    from {{ ref('fct_web_daily') }}
    where channel_group in ('paid_search', 'paid_social')
),

joined as (
    select
        coalesce(p.client_id, g.client_id) as client_id,
        coalesce(p.date, g.date) as date,
        coalesce(p.channel, g.channel) as channel,
        coalesce(p.platform_clicks, 0) as platform_clicks,
        coalesce(g.ga4_sessions, 0) as ga4_sessions,
        p.platform_conversions as platform_conversions,
        coalesce(g.ga4_key_events, 0) as ga4_key_events
    from platform p
    full outer join ga4 g
        on p.client_id = g.client_id and p.date = g.date and p.channel = g.channel
),

ratios as (
    select
        *,
        case when platform_clicks > 0 then ga4_sessions * 1.0 / platform_clicks end as session_click_ratio
    from joined
)

select
    client_id,
    date,
    channel,
    platform_clicks,
    ga4_sessions,
    session_click_ratio,
    coalesce(platform_conversions, 0) as platform_conversions,
    ga4_key_events,
    case
        when session_click_ratio is null then 'ok'
        when session_click_ratio < case channel
            when 'google_ads' then {{ var('recon_google_ads_critical') }}
            else {{ var('recon_meta_ads_critical') }} end then 'critical'
        when session_click_ratio < case channel
            when 'google_ads' then {{ var('recon_google_ads_warn') }}
            else {{ var('recon_meta_ads_warn') }} end then 'warn'
        else 'ok'
    end as status
from ratios
