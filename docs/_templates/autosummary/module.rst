{{ fullname | escape | underline(line='~') }}

.. automodule:: {{ fullname }}

.. currentmodule:: {{ fullname }}

{% if classes %}
{% for class in classes %}
{{class | escape | underline}}

.. autoclass:: {{class}}
  :members:

{% endfor %}

{% endif %}

{% if exceptions %}
{% for ex in exceptions %}
{{ex | escape | underline}}

.. autoexception:: {{ex}}
  :members:

{% endfor %}

{% endif %}

{% if functions %}
.. autosummary::
    :toctree: generated

{% for function in functions %}

{{function | escape | underline}}
.. autofunction:: {{function}}

{% endfor %}

{% endif %}