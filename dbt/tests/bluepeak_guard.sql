-- Scenario guard: bluepeak's broken auto-tagging must keep showing as a low Google Ads ratio.
select sum(ga4_sessions) * 1.0 / sum(platform_clicks) as ratio
from {{ ref('fct_paid_vs_ga4_reconciliation') }}
where client_id = 'bluepeak-dental' and channel = 'google_ads'
having sum(ga4_sessions) * 1.0 / sum(platform_clicks) >= 0.3
