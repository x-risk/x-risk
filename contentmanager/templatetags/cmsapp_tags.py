from django import template
from django.utils.translation import gettext_lazy as _
from django.conf import settings

import re
import markdown

register = template.Library()
    
@register.simple_tag
def settings_value(name):
    return getattr(settings, name, "")


@register.assignment_tag
def get_tagged_articles(tag):
    from contentmanager.models import DefaultPage

    allpages = DefaultPage.objects.live()
    taggedpages = allpages.filter(tags__name=tag)

    # Order by most recent date first
    taggedpages = taggedpages.order_by('-date')

    return taggedpages

@register.assignment_tag(takes_context=True)
def get_assessment_data(context, slug):
    '''
    Get assessment data for general use in templates
    '''
    from engine.models import Topic
    from engine.views import get_status

    assessor = context['request'].user
    search_topic = Topic.objects.get(slug=slug)
    status = get_status(assessor, search_topic)
    next_assessment = status.get('item').next_assessment
    publications_count = status.get('publications_count')
    publications_assessed_count = status.get('publications_assessed_count')
    publications_assessed_percent = status.get('publications_assessed_percent')

    context = {
        'slug': slug,
        'search_topic': str(search_topic).capitalize(),
        'publications_count': publications_count,
        'publications_assessed_count': publications_assessed_count,
        'publications_assessed_percent': publications_assessed_percent,
        'next_assessment': next_assessment
    }

    return context

@register.assignment_tag(takes_context=True)
def get_latest_publications(context, slug, show_number):
    '''
    Gets latest publications with specific slug, limiting number to show_number
    '''
    from engine.models import Topic
    from engine.views import get_latest_unassessed_publications

    assessor = context['request'].user
    search_topic = Topic.objects.get(slug=slug)
    publications = get_latest_unassessed_publications(assessor, search_topic, show_number)

    context = {
        'slug': slug,
        'search_topic': str(search_topic).capitalize(),
        'publications': publications
    }

    return context

@register.filter(name='range') 
def filter_range(start, end):   
    return range(start, end)

@register.filter(name='times') 
def times(number):
    return range(number)

@register.tag(name='captureas')
def do_captureas(parser, token):
    try:
        tag_name, args = token.contents.split(None, 1)
    except ValueError:
        raise template.TemplateSyntaxError("'captureas' node requires a variable name.")
    nodelist = parser.parse(('endcaptureas',))
    parser.delete_first_token()
    return CaptureasNode(nodelist, args)

class CaptureasNode(template.Node):
    def __init__(self, nodelist, varname):
        self.nodelist = nodelist
        self.varname = varname

    def render(self, context):
        output = self.nodelist.render(context)
        context[self.varname] = output
        return ''

@register.filter(name='markdown')
def markdown_filter(value):
    return markdown.markdown(
        value,
        extensions=[
            'toc',
            'extra',
            'codehilite',
        ],
        extension_configs={
            'codehilite': [
                ('css_class', "highlight")
            ]
        },
        output_format='html5'
    )

@register.assignment_tag(takes_context=True)
def get_site_root(context):
    # NB this returns a core.Page, not the implementation-specific model used
    # so object-comparison to self will return false as objects would differ
    return context['request'].site.root_page

def has_menu_children(page):
    return page.get_children().live().in_menu().exists()


# Retrieves the top menu items - the immediate children of the parent page
# The has_menu_children method is necessary because the bootstrap menu requires
# a dropdown class to be applied to a parent
@register.inclusion_tag('contentmanager/tags/top_menu.html', takes_context=True)
def top_menu(context, parent, calling_page=None):
    menuitems = parent.get_children().live().in_menu()
    for menuitem in menuitems:
        menuitem.show_dropdown = has_menu_children(menuitem)
        # We don't directly check if calling_page is None since the template
        # engine can pass an empty string to calling_page
        # if the variable passed as calling_page does not exist.
        menuitem.active = (calling_page.path.startswith(menuitem.path)
                           if calling_page else False)
    return {
        'calling_page': calling_page,
        'menuitems': menuitems,
        # required by the pageurl tag that we want to use within this template
        'request': context['request'],
    }

# Retrieves the children of the top menu items for the drop downs
@register.inclusion_tag('contentmanager/tags/top_menu_children.html', takes_context=True)
def top_menu_children(context, parent):
    menuitems_children = parent.get_children()
    menuitems_children = menuitems_children.live().in_menu()
    return {
        'parent': parent,
        'menuitems_children': menuitems_children,
        # required by the pageurl tag that we want to use within this template
        'request': context['request'],
    }

class ExprNode(template.Node):
    def __init__(self, expr_string, var_name):
        self.expr_string = expr_string
        self.var_name = var_name
    
    def render(self, context):
        try:
            clist = list(context)
            clist.reverse()
            d = {}
            d['_'] = _
            for c in clist:
                d.update(c)
            if self.var_name:
                context[self.var_name] = eval(self.expr_string, d)
                return ''
            else:
                return str(eval(self.expr_string, d))
        except:
            raise

r_expr = re.compile(r'(.*?)\s+as\s+(\w+)', re.DOTALL)    
def do_expr(parser, token):
    try:
        tag_name, arg = token.contents.split(None, 1)
    except ValueError:
        raise (template.TemplateSyntaxError, "%r tag requires arguments" % token.contents[0])
    m = r_expr.search(arg)
    if m:
        expr_string, var_name = m.groups()
    else:
        if not arg:
            raise (template.TemplateSyntaxError, "%r tag at least require one argument" % tag_name)
            
        expr_string, var_name = arg, None
    return ExprNode(expr_string, var_name)
do_expr = register.tag('expr', do_expr)
