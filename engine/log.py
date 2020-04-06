from django.contrib.auth.models import User
from engine.models import Assessment, Publication, Log

def log(event, note=''):
    n_users = User.objects.all().values_list('pk', flat=True).count()
    n_publications = Publication.objects.all().values_list('pk', flat=True).count()
    n_assessments = []
    for assessor in User.objects.all():
        n = Publication.objects.distinct().filter(
                assessment__in=Assessment.objects.filter(assessor=assessor)
            ).values_list('pk', flat=True).count()
        n_assessments.append(n)
    n_assessments = sum(n_assessments)
    n_assessed_publications = Publication.objects.distinct().filter(assessment__in=Assessment.objects.all()).values_list('pk', flat=True).count()
    max_publication_pk = Publication.objects.latest('pk').pk

    log = Log(
        event = event,
        note = note,
        n_users = n_users,
        n_publications = n_publications,
        n_assessments = n_assessments,
        n_assessed_publications = n_assessed_publications,
        max_publication_pk = max_publication_pk
    )
    log.save()
    return()
