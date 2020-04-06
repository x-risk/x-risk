from django.conf.urls import url
from django.conf import settings  # For django-debug-toolbar
from django.conf.urls import include  # For django-debug-toolbar
from . import views


urlpatterns = [
    url(r'^$', views.home, name='home'),
    url(r'^signup/$', views.signup, name='signup'),
    url(r'^profile/$', views.profile, name='profile'),
    url(r'^topics/(?P<slug>[\w\-]+)/$', views.topics, name='topics'),
    url(r'^topics/(?P<slug>[\w\-]+)/(?P<state>[\w]+)/$', views.topics, name='topics'),
    url(r'^topics/(?P<slug>[\w\-]+)/(?P<state>[\w]+)/(?P<relevance>[\w]+)/(?P<to_do>[\w]+)/$', views.topics, name='topics'),
    url(r'^assessments/(?P<slug>[\w\-]+)/(?P<pk>\d+)/$', views.assessments, name='assessments'),
    url(r'^scoreboard/$', views.scoreboard, name='scoreboard'),
    url(r'^email_sent/$', views.email_sent, name='email_sent'),
    url(r'^email_confirmed/$', views.email_confirmed, name='email_confirmed'),
    url(r'^email_not_confirmed/$', views.email_not_confirmed, name='email_not_confirmed'),
    url(r'^confirm_email/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$', views.confirm_email, name='confirm_email'),
    url(r'^deactivate/$', views.deactivate, name='deactivate'),
    url(r'^deactivate_confirm/$', views.deactivate_confirm, name='deactivate_confirm'),
    url(r'^download_csv/(?P<slug>[\w\-]+)/$', views.download_csv, name='download_csv'),
    url(r'^download_ris/(?P<slug>[\w\-]+)/$', views.download_ris, name='download_ris'),
    url(r'^download_csv/(?P<slug>[\w\-]+)/(?P<state>[\w\-]+)/$', views.download_csv, name='download_csv'),
    url(r'^download_ris/(?P<slug>[\w\-]+)/(?P<state>[\w\-]+)/$', views.download_ris, name='download_ris'),
    url(r'^ml/$', views.ml, name='ml'),
    url(r'^home/$', views.home, name='home'),
    url(r'^search/(?P<slug>[\w\-]+)/$', views.MySearchView.as_view(), name='haystack_search'),
]

if settings.DEBUG:
   import debug_toolbar
   urlpatterns += [
       url(r'^__debug__/', include(debug_toolbar.urls)),
   ]
