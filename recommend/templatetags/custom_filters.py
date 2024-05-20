from django import template

register = template.Library()

@register.filter
def custom_range(start):
    return range(1, start + 1)
