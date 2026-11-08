{# Generic test: column has no negative values (nulls are ignored; use not_null for those). #}
{% test non_negative(model, column_name) %}
select {{ column_name }} from {{ model }} where {{ column_name }} < 0
{% endtest %}
