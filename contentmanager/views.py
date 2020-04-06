from django.shortcuts import render
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from wagtail.core.models import Page
from wagtail.search.models import Query
from django.db.models import Q
from contentmanager.models import DefaultPage

def search(request):
    # Search
    search_query = request.GET.get('q', '')
    if search_query:
        search_results = DefaultPage.objects.live().filter(Q(body__icontains=search_query) | Q(title__icontains=search_query))
        query = Query.get(search_query)

        # Record hit
        query.add_hit()
    else:
        search_results = DefaultPage.objects.none()

    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(search_results, 10)
    try:
        search_results = paginator.page(page)
    except PageNotAnInteger:
        search_results = paginator.page(1)
    except EmptyPage:
        search_results = paginator.page(paginator.num_pages)

    return render(request, 'contentmanager/default_page.html', {
        'search_term': search_query,
        'search_results': search_results,
        'search_type': 'search'
    })
