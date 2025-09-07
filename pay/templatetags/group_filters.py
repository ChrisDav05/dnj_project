from django import template

register = template.Library()

@register.filter(name='group')
def has_group(user, group_names):
    groups = group_names.split(', ')
    return user.groups.filter(name__in=groups).exists()