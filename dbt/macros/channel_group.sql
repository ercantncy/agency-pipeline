{# GA4 default-channel-group style derivation from source / medium (case-insensitive). #}
{% macro channel_group(source, medium) -%}
case
    when lower({{ medium }}) in ('cpc', 'ppc', 'paidsearch') then 'paid_search'
    when lower({{ medium }}) in ('paid', 'paid_social', 'cpm')
         and lower({{ source }}) in ('facebook', 'fb', 'instagram', 'ig', 'meta', 'linkedin') then 'paid_social'
    when lower({{ medium }}) = 'organic' then 'organic_search'
    when lower({{ medium }}) = 'email' then 'email'
    when lower({{ medium }}) = 'referral' then 'referral'
    when lower({{ source }}) = '(direct)' and lower({{ medium }}) in ('(none)', '(not set)') then 'direct'
    else 'other'
end
{%- endmacro %}
