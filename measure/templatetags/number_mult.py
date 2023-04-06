from django import template
register = template.Library()

@register.filter
def mult(number, scalar):
    return number*scalar