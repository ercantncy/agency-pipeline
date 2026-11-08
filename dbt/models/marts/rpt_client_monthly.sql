with by_channel as (
    select
        client_id,
        cast(date_trunc('month', date) as date) as month,
        channel,
        sum(spend) as spend,
        sum(impressions) as impressions,
        sum(clicks) as clicks,
        sum(platform_conversions) as conversions,
        sum(platform_conversion_value) as conversion_value
    from {{ ref('fct_paid_daily') }}
    group by 1, 2, 3
),

total as (
    select
        client_id, month, 'total_paid' as channel,
        sum(spend) as spend, sum(impressions) as impressions, sum(clicks) as clicks,
        sum(conversions) as conversions, sum(conversion_value) as conversion_value
    from by_channel
    group by client_id, month
),

unioned as (
    select * from by_channel
    union all
    select * from total
),

kpis as (
    select
        client_id, month, channel, spend, clicks, conversions, conversion_value,
        spend / nullif(conversions, 0) as cpa,
        conversion_value / nullif(spend, 0) as roas,
        clicks * 1.0 / nullif(impressions, 0) as ctr
    from unioned
),

lagged as (
    select
        *,
        lag(spend) over w as prev_spend,
        lag(conversions) over w as prev_conversions,
        lag(cpa) over w as prev_cpa,
        lag(roas) over w as prev_roas
    from kpis
    window w as (partition by client_id, channel order by month)
)

select
    client_id, month, channel,
    spend, clicks, conversions, conversion_value, cpa, roas, ctr,
    (spend / nullif(prev_spend, 0) - 1) as spend_mom_pct,
    (conversions / nullif(prev_conversions, 0) - 1) as conversions_mom_pct,
    (cpa / nullif(prev_cpa, 0) - 1) as cpa_mom_pct,
    (roas / nullif(prev_roas, 0) - 1) as roas_mom_pct
from lagged
