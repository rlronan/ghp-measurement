from django import template
register = template.Library()

@register.filter
def list_index(indexable, i):
    return indexable[i]