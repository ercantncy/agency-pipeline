select
    client_id,
    client_name,
    agency_name,
    agency_primary_color,
    agency_logo_text,
    currency,
    scenario,
    google_ads_customer_id,
    meta_account_id,
    ga4_property_id,
    gsc_site_url
from {{ source('raw', 'clients') }}
