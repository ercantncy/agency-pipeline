with src as (
    select * from {{ source('raw', 'meta_ads_insights_daily') }}
),

parsed as (
    select
        *,
        cast(actions as json) as actions_json,
        cast(action_values as json) as action_values_json
    from src
)

select
    client_id,
    cast(date_start as date) as date,
    account_id,
    campaign_id,
    campaign_name,
    objective,
    cast(impressions as bigint) as impressions,
    cast(inline_link_clicks as bigint) as inline_link_clicks,
    cast(spend as double) as spend,
    coalesce(cast((
        select sum(cast(json_extract_string(a, '$.value') as double))
        from unnest(cast(actions_json as json[])) as t(a)
        where json_extract_string(a, '$.action_type') = 'link_click'
    ) as bigint), 0) as link_clicks,
    coalesce(cast((
        select sum(cast(json_extract_string(a, '$.value') as double))
        from unnest(cast(actions_json as json[])) as t(a)
        where json_extract_string(a, '$.action_type') = 'offsite_conversion.fb_pixel_purchase'
    ) as bigint), 0) as purchases,
    coalesce(cast((
        select sum(cast(json_extract_string(a, '$.value') as double))
        from unnest(cast(actions_json as json[])) as t(a)
        where json_extract_string(a, '$.action_type') = 'offsite_conversion.fb_pixel_lead'
    ) as bigint), 0) as leads,
    coalesce((
        select sum(cast(json_extract_string(a, '$.value') as double))
        from unnest(cast(action_values_json as json[])) as t(a)
        where json_extract_string(a, '$.action_type') = 'offsite_conversion.fb_pixel_purchase'
    ), 0.0) as purchase_value
from parsed
