from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.forms import modelformset_factory
from django.db import transaction
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib.sites.shortcuts import get_current_site
from django.utils.encoding import force_bytes, force_text
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.template import loader
from django.template.loader import render_to_string
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from datetime import date
from ast import literal_eval
from random import shuffle
from .tokens import account_activation_token
from .models import Assessment, AssessmentStatus, HumanPrediction, Log, MLModel, Publication, Topic
from .forms import AssessmentForm, ProfileForm, SignUpForm, UserForm
import config
import csv
import json
import urllib
import logging
import random

logger = logging.getLogger(__name__)

@login_required
def scoreboard(request):
    scoreboard = []
    assessors = User.objects.distinct().filter(assessment__in=Assessment.objects.all())
    for assessor in assessors:
        publication_count = Publication.objects.distinct().filter(
            assessment__in=Assessment.objects.filter(assessor=assessor)
        ).values_list('pk', flat=True).count()
        scoreboard.append({'first_name': assessor.first_name, 'last_name': assessor.last_name, 'institution': assessor.profile.institution, 'publication_count': publication_count})
    return render(request, 'engine/scoreboard.html', {'scoreboard': scoreboard})


def signup(request):
    if request.user.is_authenticated():
        return redirect('profile')

    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():

            ''' Begin reCAPTCHA validation '''

            recaptcha_response = request.POST.get('g-recaptcha-response')
            url = 'https://www.google.com/recaptcha/api/siteverify'
            values = {
                'secret': config.GOOGLE_RECAPTCHA_SECRET_KEY,
                'response': recaptcha_response
            }
            data = urllib.parse.urlencode(values).encode()
            req =  urllib.request.Request(url, data=data)
            response = urllib.request.urlopen(req)
            result = json.loads(response.read().decode())

            ''' End reCAPTCHA validation '''

            if result['success']:
                user = form.save()
                user.refresh_from_db()  # Load the profile instance created by the signal.
                user.profile.institution = form.cleaned_data.get('institution')
                user.profile.educational_attainment = form.cleaned_data.get('educational_attainment')
                user.profile.topics = form.cleaned_data.get('topics')
                user.is_active = False
                user.save()
                current_site = get_current_site(request)
                subject = 'Existential Risk Research Network'
                message = render_to_string('engine/confirm_email.html', {
                    'user': user,
                    'domain': current_site.domain,
                    'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                    'token': account_activation_token.make_token(user),
                })
                user.email_user(subject, message)
                return redirect('email_sent')
            else:
                form.add_error(None, "Please click 'I'm not a robot'")
    else:
        form = SignUpForm()
    return render(request, 'engine/signup.html', {'form': form})


def email_sent(request):
    return render(request, 'engine/email_sent.html')


def email_confirmed(request):
    return render(request, 'engine/email_confirmed.html')


def email_not_confirmed(request):
    return render(request, 'engine/email_not_confirmed.html')


def confirm_email(request, uidb64, token):
    try:
        uid = force_text(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.profile.email_is_confirmed = True
        user.save()
        login(request, user)
        return render(request, 'engine/email_confirmed.html')
    else:
        return render(request, 'engine/email_not_confirmed.html')


@login_required
def deactivate_confirm(request):
    return render(request, 'engine/deactivate_confirm.html')


@login_required
def deactivate(request):
    user = request.user
    user.is_active = False
    user.save()
    return render(request, 'engine/deactivate.html')


@login_required
@transaction.atomic
def profile(request):
    if request.method == 'POST':
        user_form = UserForm(request.POST, instance=request.user)
        profile_form = ProfileForm(request.POST, instance=request.user.profile)
        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save()
            user.first_name = user_form.cleaned_data.get('first_name')
            user.last_name = user_form.cleaned_data.get('last_name')
            user.profile.institution = profile_form.cleaned_data.get('institution')
            user.profile.topics = profile_form.cleaned_data.get('topics')
            user.profile.educational_attainment = profile_form.cleaned_data.get('educational_attainment')
            user.save()
            return render(request, 'engine/profile_updated.html')
    else:
        user_form = UserForm(instance=request.user)
        profile_form = ProfileForm(instance=request.user.profile)

    context = {
        'user_form': user_form,
        'profile_form': profile_form
    }

    return render(request, 'engine/profile.html', context)


def download_csv(request, slug, state='default'):
    # Create the HttpResponse object with the appropriate CSV header.
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="bibliography.csv"'

    search_topic = Topic.objects.get(slug=slug)

    if (state == 'low_recall'):
        THRESHOLD = MLModel.objects.get(
            topic=search_topic,
            target_recall=0.5
        ).threshold
        publications = Publication.objects.filter(
            mlprediction__prediction__gte=THRESHOLD,
            mlprediction__topic=search_topic
        ).order_by('-mlprediction__prediction')
    elif (state == 'medium_recall'):
        THRESHOLD = MLModel.objects.get(
            topic=search_topic,
            target_recall=0.75
        ).threshold
        publications = Publication.objects.filter(
            mlprediction__prediction__gte=THRESHOLD,
            mlprediction__topic=search_topic
        ).order_by('-mlprediction__prediction')
    elif (state == 'high_recall'):
        THRESHOLD = MLModel.objects.get(
            topic=search_topic,
            target_recall=0.95
        ).threshold
        publications = Publication.objects.filter(
            mlprediction__prediction__gte=THRESHOLD,
            mlprediction__topic=search_topic
        ).order_by('-mlprediction__prediction')
    else:  # If state='default'
        publications = Publication.objects.distinct().filter(
            assessment__in=Assessment.objects.filter(
                topic=search_topic,
                is_relevant=True
            )
        ).order_by('-humanprediction__relevance', '-humanprediction__n_assessments')

    writer = csv.writer(response, quoting=csv.QUOTE_ALL)
    if (state == 'default'):  # Additional data for the default bibliography only
        human_predictions = HumanPrediction.objects.filter(topic=search_topic).order_by('-relevance', '-n_assessments')
        writer.writerow(['Authors', 'Year', 'Title', 'Journal', 'Volume', 'Issue', 'DOI', 'Number_of_Assessments', 'Number_Relevant', 'Relevance'])
        for publication, human_prediction in zip(publications, human_predictions):
            writer.writerow([publication.author, publication.year, publication.title, publication.journal, publication.volume, publication.issue, publication.doi, human_prediction.n_assessments, human_prediction.n_relevant, human_prediction.relevance])
    else:
        writer.writerow(['Authors', 'Year', 'Title', 'Journal', 'Volume', 'Issue', 'DOI'])
        for publication in publications:
            writer.writerow([publication.author, publication.year, publication.title, publication.journal, publication.volume, publication.issue, publication.doi])
    return response


def download_ris(request, slug, state='default'):
    # Create the HttpResponse object with the appropriate CSV header.
    response = HttpResponse(content_type='text/ris; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="bibliography.ris"'

    search_topic = Topic.objects.get(slug=slug)

    if (state == 'low_recall'):
        THRESHOLD = MLModel.objects.get(
            topic=search_topic,
            target_recall=0.5
        ).threshold
        publications = Publication.objects.filter(
            mlprediction__prediction__gte=THRESHOLD,
            mlprediction__topic=search_topic
        ).order_by('-mlprediction__prediction')
    elif (state == 'medium_recall'):
        THRESHOLD = MLModel.objects.get(
            topic=search_topic,
            target_recall=0.75
        ).threshold
        publications = Publication.objects.filter(
            mlprediction__prediction__gte=THRESHOLD,
            mlprediction__topic=search_topic
        ).order_by('-mlprediction__prediction')
    elif (state == 'high_recall'):
        THRESHOLD = MLModel.objects.get(
            topic=search_topic,
            target_recall=0.95
        ).threshold
        publications = Publication.objects.filter(
            mlprediction__prediction__gte=THRESHOLD,
            mlprediction__topic=search_topic
        ).order_by('-mlprediction__prediction')
    else:  # If state='default'
        publications = Publication.objects.distinct().filter(
            assessment__in=Assessment.objects.filter(
                topic=search_topic,
                is_relevant=True
            )
        ).order_by('-humanprediction__relevance', '-humanprediction__n_assessments')

    t = loader.get_template('engine/ris_template.txt')
    c = {'publications': publications}
    response.write(t.render(c))
    return response


def ml(request):
    target_recalls = (0.95, 0.75, 0.50)
    ml_models = MLModel.objects.filter(target_recall__in=target_recalls)
    n_predicted = []
    n_relevant = []
    for ml_model in ml_models:
        threshold = ml_model.threshold
        topic = ml_model.topic
        n = Publication.objects.filter(
            mlprediction__prediction__gte=threshold,
            mlprediction__topic=topic
        ).count()
        n_predicted.append(n)
        n_relevant.append(ml_model.precision * n)
    context = {
        'ml_models': zip(ml_models, n_predicted, n_relevant),
        'n_predicted_example': n_predicted[0],
        'n_relevant_example': n_relevant[0],
    }
    return render(request, 'engine/ml.html', context)


def topics(request, slug, state='default'):
    """
    This view has alternative states. It displays publications for a topic, but it can display different subsets of these publications:
    (1) [Default] Publications that have been assessed as relevant by any user: this is the publicly-available list of publications on this topic [if user is not authenticated OR if the state variable is not passed to this view (state='default')]
    (2) Publications that have not been assessed by this user [if user is authenticated AND state='unassessed']
    (3) Publications that have been assessed by this user [if user is authenticated AND state='assessed']
    (4) Publications that have been assessed as relevant by this user [if user is authenticated AND state='relevant']
    (5) Publications that have been assessed as irrelevant by this user [if user is authenticated AND state='irrelevant']
    (6) Publications that the machine-learning algorithm has predicted to be relevant, with low recall [if state='low_recall'], medium recall [if state='medium_recall'], or high recall [if state='high_recall']
    """

    assessor = request.user
    search_topic = Topic.objects.get(slug=slug)

    if request.user.is_authenticated():

        status = get_status(assessor, search_topic)

        next_assessment = status.get('item').next_assessment
        publications_count = status.get('publications_count')
        publications_assessed_count = status.get('publications_assessed_count')
        publications_assessed_percent = status.get('publications_assessed_percent')

        # Publications that this user has assessed as relevant (in contrast to those that any user assessed as relevant, which is the default for this view)
        if (state == 'relevant'):
            publications = Publication.objects.distinct().filter(
                assessment__in=Assessment.objects.filter(
                    topic=search_topic,
                    assessor=assessor,
                    is_relevant=True
                )
            ).order_by('title')

        # Publications that this user has assessed as irrelevant
        elif (state == 'irrelevant'):
            publications = Publication.objects.distinct().filter(
                assessment__in=Assessment.objects.filter(
                    topic=search_topic,
                    assessor=assessor,
                    is_relevant=False
                )
            ).order_by('title')

        # Publications that this user has assessed as relevant or irrelevant
        elif (state == 'assessed'):
            publications = Publication.objects.distinct().filter(
                assessment__in=Assessment.objects.filter(
                    topic=search_topic,
                    assessor=assessor
                )
            ).order_by('title')

        # Publications that this user has not yet assessed
        elif (state == 'unassessed'):
            publications = Publication.objects.distinct().exclude(
                assessment__in=Assessment.objects.filter(
                    topic=search_topic,
                    assessor=assessor
                )
            ).order_by('title')

        # Publications that the machine-learning algorithm has predicted to be relevant, with low recall, medium recall, or high recall
        elif (state == 'low_recall'):
            THRESHOLD = MLModel.objects.get(
                topic=search_topic,
                target_recall=0.5
            ).threshold
            publications = Publication.objects.filter(
                mlprediction__prediction__gte=THRESHOLD,
                mlprediction__topic=search_topic
            ).order_by('-mlprediction__prediction')

        elif (state == 'medium_recall'):
            THRESHOLD = MLModel.objects.get(
                topic=search_topic,
                target_recall=0.75
            ).threshold
            publications = Publication.objects.filter(
                mlprediction__prediction__gte=THRESHOLD,
                mlprediction__topic=search_topic
            ).order_by('-mlprediction__prediction')

        elif (state == 'high_recall'):
            THRESHOLD = MLModel.objects.get(
                topic=search_topic,
                target_recall=0.95
            ).threshold
            publications = Publication.objects.filter(
                mlprediction__prediction__gte=THRESHOLD,
                mlprediction__topic=search_topic
            ).order_by('-mlprediction__prediction')

        elif (state == 'new_low_recall'):
            THRESHOLD = MLModel.objects.get(
                topic=search_topic,
                target_recall=0.5
            ).threshold
            # Get the pk values of new publications (new publications have a pk value greater than the maximum pk value of the old publications that were sent in the last alert).
            try:
                max_publication_pks = Log.objects.filter(event='alert.py').values_list('max_publication_pk', flat=True)
                max_publication_pks = set(max_publication_pks)
                new_max = max(max_publication_pks)
                old_max_publication_pks = max_publication_pks - set([new_max])
                old_max = max(old_max_publication_pks)
            except:
                old_max = 0
            publications = Publication.objects.filter(
                mlprediction__prediction__gte=THRESHOLD,
                mlprediction__topic=search_topic,
                pk__gt=old_max
            ).order_by('-mlprediction__prediction')

        elif (state == 'new_medium_recall'):
            THRESHOLD = MLModel.objects.get(
                topic=search_topic,
                target_recall=0.75
            ).threshold
            # Get the pk values of new publications (new publications have a pk value greater than the maximum pk value of the old publications that were sent in the last alert).
            try:
                max_publication_pks = Log.objects.filter(event='alert.py').values_list('max_publication_pk', flat=True)
                max_publication_pks = set(max_publication_pks)
                new_max = max(max_publication_pks)
                old_max_publication_pks = max_publication_pks - set([new_max])
                old_max = max(old_max_publication_pks)
            except:
                old_max = 0
            publications = Publication.objects.filter(
                mlprediction__prediction__gte=THRESHOLD,
                mlprediction__topic=search_topic,
                pk__gt=old_max
            ).order_by('-mlprediction__prediction')

        # Publications that any user has assessed as relevant (the default view)
        else:
            publications = Publication.objects.distinct().filter(
                assessment__in=Assessment.objects.filter(
                    topic=search_topic,
                    is_relevant=True
                )
            ).order_by('-humanprediction__relevance', '-humanprediction__n_assessments')

    else:  # If the user is not authenticated
        # Publications that the machine-learning algorithm has predicted to be relevant, with low recall, medium recall, or high recall
        if (state == 'low_recall'):
            THRESHOLD = MLModel.objects.get(
                topic=search_topic,
                target_recall=0.5
            ).threshold
            publications = Publication.objects.filter(
                mlprediction__prediction__gte=THRESHOLD,
                mlprediction__topic=search_topic
            ).order_by('-mlprediction__prediction')

        elif (state == 'medium_recall'):
            THRESHOLD = MLModel.objects.get(
                topic=search_topic,
                target_recall=0.75
            ).threshold
            publications = Publication.objects.filter(
                mlprediction__prediction__gte=THRESHOLD,
                mlprediction__topic=search_topic
            ).order_by('-mlprediction__prediction')

        elif (state == 'high_recall'):
            THRESHOLD = MLModel.objects.get(
                topic=search_topic,
                target_recall=0.95
            ).threshold
            publications = Publication.objects.filter(
                mlprediction__prediction__gte=THRESHOLD,
                mlprediction__topic=search_topic
            ).order_by('-mlprediction__prediction')

        elif (state == 'new_low_recall'):
            THRESHOLD = MLModel.objects.get(
                topic=search_topic,
                target_recall=0.5
            ).threshold
            # Get the pk values of new publications to be sent in this alert (new publications have a pk value greater than the maximum pk value of the old publications that were sent in the last alert).
            try:
                max_publication_pks = Log.objects.filter(event='alert.py').values_list('max_publication_pk', flat=True)
                max_publication_pks = set(max_publication_pks)
                new_max = max(max_publication_pks)
                old_max_publication_pks = max_publication_pks - set([new_max])
                old_max = max(old_max_publication_pks)
            except:
                old_max = 0
            publications = Publication.objects.filter(
                mlprediction__prediction__gte=THRESHOLD,
                mlprediction__topic=search_topic,
                pk__gt=old_max
            ).order_by('-mlprediction__prediction')

        elif (state == 'new_medium_recall'):
            THRESHOLD = MLModel.objects.get(
                topic=search_topic,
                target_recall=0.75
            ).threshold
            # Get the pk values of new publications (new publications have a pk value greater than the maximum pk value of the old publications that were sent in the last alert).
            try:
                max_publication_pks = Log.objects.filter(event='alert.py').values_list('max_publication_pk', flat=True)
                max_publication_pks = set(max_publication_pks)
                new_max = max(max_publication_pks)
                old_max_publication_pks = max_publication_pks - set([new_max])
                old_max = max(old_max_publication_pks)
            except:
                old_max = 0
            publications = Publication.objects.filter(
                mlprediction__prediction__gte=THRESHOLD,
                mlprediction__topic=search_topic,
                pk__gt=old_max
            ).order_by('-mlprediction__prediction')

        else:
            publications = Publication.objects.distinct().filter(
                assessment__in=Assessment.objects.filter(
                    topic=search_topic,
                    is_relevant=True
                )
            ).order_by('-humanprediction__relevance', '-humanprediction__n_assessments')

    page = request.GET.get('page', 1)
    paginator = Paginator(publications, 10)
    try:
        publications = paginator.page(page)
    except PageNotAnInteger:
        publications = paginator.page(1)
    except EmptyPage:
        publications = paginator.page(paginator.num_pages)

    if request.user.is_authenticated():
        if state is 'default': state = 'All'
        context = {
            'search_topic': search_topic,
            'publications': publications,
            'publications_count': publications_count,
            'publications_assessed_count': publications_assessed_count,
            'publications_assessed_percent': publications_assessed_percent,
            'next_assessment': next_assessment,
            'state': state.replace("_", " ").capitalize()
        }
    else:
        context = {
            'search_topic': search_topic,
            'publications': publications,
            'state' : 'All'
        }

    return render(request, 'engine/topics.html', context)


@login_required
def assessments(request, slug, pk):
    """
    This view displays one publication at a time for a given search topic. The
    user is asked to assess the relevance of this publication to all the
    topics in the Topic model.
    """
    assessor = request.user
    search_topic = Topic.objects.get(slug=slug)  # This topic
    other_topics = Topic.objects.exclude(slug=slug)  # Other topics
    pk = int(pk)

    # The publication that is going to be assessed
    publication = Publication.objects.get(pk=pk)

    # Data for the sidebar (also used after clicking "Save", "Reset", or "Pass" to update next_unassessed_pk in the database)
    status = get_status(assessor, search_topic)

    item = status.get('item')

    assessment_order_list = item.assessment_order_list
    completed_assessments_list = item.completed_assessments_list
    next_assessment = item.next_assessment

    publications_count = status.get('publications_count')
    publications_assessed_count = status.get('publications_assessed_count')
    publications_assessed_percent = status.get('publications_assessed_percent')

    # The next pk and previous pk in assessment_order_list, to be used for navigation
    previous_pk = assessment_order_list[assessment_order_list.index(pk) - 1]
    try:
        next_pk = assessment_order_list[assessment_order_list.index(pk) + 1]
    except:
        next_pk = assessment_order_list[0]

    # If any new topics were added to the Topic model after this publication was assessed, then they will not display correctly, and so we need to know whether or not this publication has been assessed by this user.
    if Assessment.objects.filter(publication=publication, assessor=assessor).exists():
        assessed_topics = Topic.objects.filter(
            assessment__in=Assessment.objects.filter(
                    publication=publication, assessor=assessor
                )
        )
        unassessed_topics = Topic.objects.exclude(
            assessment__in=Assessment.objects.filter(
                    publication=publication, assessor=assessor
                )
        )
        # Initial data for the AssessmentFormSet (one form for each topic)
        initial = [{'topic': topic} for topic in unassessed_topics]
    else:
        initial = [{'topic': topic} for topic in other_topics]

    AssessmentFormSet = modelformset_factory(Assessment, form=AssessmentForm,
        extra=len(initial), max_num=len(other_topics))

    if request.method == 'POST':
        assessment_form = AssessmentForm(request.POST, prefix="search_topic")
        assessment_formset = AssessmentFormSet(request.POST, prefix="other_topics")

        if assessment_form.is_valid() and assessment_formset.is_valid():
            old_assessments = []
            new_assessments = []

            if 'save' in request.POST:

                is_relevant = assessment_form.cleaned_data.get('is_relevant')

                # If this user has already assessed the relevance of this publication to the search_topic, append the pk of the old assessment to the old_assessments list. Assessments in this list will be bulk deleted.
                if Assessment.objects.filter(publication=publication, assessor=assessor, topic=search_topic).exists():
                    old_assessments.append(Assessment.objects.get(
                        assessor=assessor, publication=publication,
                            topic=search_topic).pk)

                # Append a new instance of the Assessment model to the new_assessments list. Assessments in this list will be bulk created.
                new_assessments.append(Assessment(publication=publication,
                                                  is_relevant=is_relevant,
                                                  topic=search_topic,
                                                  assessor=assessor))

                for assessment_form in assessment_formset:
                    is_relevant = assessment_form.cleaned_data.get('is_relevant')
                    topic = assessment_form.cleaned_data.get('topic')

                    # If this user has already assessed the relevance of this publication to this topic, append the pk of the old assessment to the old_assessments list. Assessments in this list will be bulk deleted.
                    if Assessment.objects.filter(assessor=assessor,
                        publication=publication, topic=topic).exists():
                            old_assessments.append(Assessment.objects.get(
                                assessor=assessor, publication=publication,
                                    topic=topic).pk)

                    # Append a new instance of the Assessment model to the new_assessments list. Assessments in this list will be bulk created.
                    new_assessments.append(Assessment(publication=publication,
                                                      is_relevant=is_relevant,
                                                      topic=topic,
                                                      assessor=assessor))

                next_assessment = get_next_assessment(pk, next_pk, assessment_order_list, completed_assessments_list)

                # Bulk create the new_assessments and/or bulk delete the old assessments. This is an atomic transaction, so the old_assessments will not be deleted unless the new_assessments are created.
                with transaction.atomic():
                    Assessment.objects.filter(pk__in=old_assessments).delete()
                    Assessment.objects.bulk_create(new_assessments)
                    item.next_assessment = next_assessment
                    if pk not in completed_assessments_list:
                        completed_assessments_list.append(pk)
                        item.completed_assessments_list = completed_assessments_list
                    item.save()
                return HttpResponseRedirect(reverse('assessments', args=(), kwargs={'slug': search_topic.slug, 'pk': next_assessment}))

            if 'reset' in request.POST:
                with transaction.atomic():
                    Assessment.objects.filter(publication=publication,
                        assessor=assessor).delete()
                    if pk in completed_assessments_list:
                        completed_assessments_list.remove(pk)
                        item.completed_assessments_list = completed_assessments_list
                        item.save()
                return HttpResponseRedirect(reverse('assessments', args=(), kwargs={'slug': search_topic.slug, 'pk': pk}))

            if 'pass' in request.POST:
                next_assessment = get_next_assessment(pk, next_pk, assessment_order_list, completed_assessments_list)
                item.next_assessment = next_assessment
                item.save()
                return HttpResponseRedirect(reverse('assessments', args=(), kwargs={'slug': search_topic.slug, 'pk': next_assessment}))

    else:
        assessment_formset = AssessmentFormSet(initial=initial,
                queryset=Assessment.objects.filter(publication=publication,
                    assessor=assessor).exclude(topic=search_topic), prefix="other_topics")
        if Assessment.objects.filter(publication=publication, assessor=assessor, topic=search_topic).exists():
                assessment = Assessment.objects.get(publication=publication, assessor=assessor, topic=search_topic)
                assessment_form = AssessmentForm(instance=assessment, prefix="search_topic")
        else:
            assessment_form = AssessmentForm(initial={'topic': search_topic}, prefix="search_topic")

    context = {
        'publication': publication,
        'assessment_form': assessment_form,
        'assessment_formset': assessment_formset,
        'next_pk': next_pk,
        'previous_pk': previous_pk,
        'search_topic': search_topic,
        'publications_count': publications_count,
        'publications_assessed_count': publications_assessed_count,
        'publications_assessed_percent': publications_assessed_percent,
        'next_assessment': next_assessment,
    }

    return render(request, 'engine/assessments.html', context)

@login_required
def home(request):
    return render(request, 'engine/home.html', {})

def get_latest_unassessed_publications(assessor, search_topic, show_number=20):
    """
    Get latest unassessed randomly-ordered publications
    show_number determines the first 'show_number' articles that will be returned to user
    """

    # Get ids of articles that have already been assessed by anyone
    # assessed_publications_ids = Assessment.objects.filter(assessor=assessor, topic=search_topic).values_list('publication_id', flat=True)
    assessed_publications_ids = Assessment.objects.filter(topic=search_topic).values_list('publication_id', flat=True)

    # Get most recently-created non-assessed article
    unassessed_publications_mostrecent = Publication.objects.filter(search_topics=search_topic).exclude(pk__in=assessed_publications_ids).order_by('-created')[:1]
    if len(unassessed_publications_mostrecent) == 0: return None

    # Select all articles with same 'created' date as most recent article
    mostrecent_date = unassessed_publications_mostrecent[0].created
    unassessed_publications_mostrecent = Publication.objects.filter(search_topics=search_topic, created__date=date(mostrecent_date.year, mostrecent_date.month, mostrecent_date.day)).exclude(pk__in=assessed_publications_ids)

    # Randomize most recent articles and slice top 'show_number' number of them
    unassessed_publications_random = sorted(unassessed_publications_mostrecent, key=lambda x: random.random())[:show_number]

    return(unassessed_publications_random)


def get_status(assessor, search_topic):
    """
    The sidebar shows the status of the assessment (number of publications, number of assessments, and the percentage of publications that have been assessed). It has links to the next_assessment, unassessed publications, assessed publications, relevant publications, and irrelevant publications for this user.
    """

    # Publications should be assessed in a random order, but each user should see the same order from session to session. Therefore, a random assessment_order is created for each user (for each topic), and it is saved in the database.

    # If an assessment_order_list has been created for this user and topic, get it from the database.
    if AssessmentStatus.objects.filter(assessor=assessor, topic=search_topic).exists():
        item = AssessmentStatus.objects.get(assessor=assessor, topic=search_topic)
        assessment_order_list = item.assessment_order_list
        next_assessment = item.next_assessment
        completed_assessments_list = item.completed_assessments_list

        # If new publications have been added to the database, then randomly append their pks to the end of assessment_order_list.
        publication_count = len(assessment_order_list)
        new_publication_count = Publication.objects.filter(search_topics=search_topic).count()

        if publication_count < new_publication_count:
            pks = Publication.objects.filter(search_topics=search_topic).values_list('pk', flat=True)
            new_publications = list(pks)
            new_publications = list(set(new_publications) - set(assessment_order_list))
            shuffle(new_publications)
            assessment_order_list = assessment_order_list + new_publications
            item.assessment_order_list = assessment_order_list
            item.save()

    # If an assessment_order_list has not been created for this user and topic, create it and save it in the database.
    else:
        pks = Publication.objects.filter(search_topics=search_topic).values_list('pk', flat=True)
        assessment_order_list = list(pks)
        shuffle(assessment_order_list)
        next_assessment = assessment_order_list[0]
        completed_assessments_list = []
        item = AssessmentStatus(
            topic=search_topic,
            assessor=assessor,
            assessment_order_list=assessment_order_list,
            next_assessment=next_assessment,
            completed_assessments_list=completed_assessments_list
        )
        item.save()

    publications_count = len(assessment_order_list)
    publications_assessed_count = len(completed_assessments_list)

    if publications_count != 0:
        publications_assessed_percent = int(publications_assessed_count / publications_count * 100)
    else:
        publications_assessed_percent = 100

    status = {
        'item': item,
        'publications_count': publications_count,
        'publications_assessed_count': publications_assessed_count,
        'publications_assessed_percent': publications_assessed_percent
    }

    return(status)


def get_next_assessment(pk, next_pk, assessment_order_list, completed_assessments_list):
    next_assessment = next_pk
    for i in assessment_order_list:
        if next_assessment not in completed_assessments_list:
            if next_assessment != pk:
                break
        else:
            try:
                next_assessment = assessment_order_list[assessment_order_list.index(next_assessment) + 1]
            except:
                next_assessment = assessment_order_list[0]
    return(next_assessment)


from haystack.generic_views import SearchView
from haystack.forms import SearchForm
from haystack.query import SearchQuerySet

class MySearchView(SearchView):
    template_name = 'engine/search.html'

    def get_queryset(self, *args, **kwargs):
        #slug = self.kwargs['slug']
        #topic = Topic.objects.get(slug=slug)
        queryset = super(MySearchView, self).get_queryset()
        return queryset

    def get_context_data(self, *args, **kwargs):
        context = super(MySearchView, self).get_context_data(*args, **kwargs)
        return context

