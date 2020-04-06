from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.text import slugify
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from urllib.parse import quote_plus
from ast import literal_eval

import logging

logger = logging.getLogger(__name__)

class Topic(models.Model):
    topic = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=150, blank=True)

    def save(self, *args, **kwargs):
        self.topic = self.topic.lower()
        self.slug = slugify(self.topic)
        super(Topic, self).save(*args, **kwargs)

    def __str__(self):
        return self.topic

    class Meta:
        ordering = ['topic']


class Source(models.Model):
    source = models.CharField(max_length=254)

    def __str__(self):
        return self.source


class SearchString(models.Model):
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE)
    search_string_for_title_and_abstract = models.TextField()
    search_string_for_references = models.TextField(blank=True)  # Optional
    date_created = models.DateTimeField(default=timezone.now)

    class Meta:
        get_latest_by = 'date_created'

    def __str__(self):
        return 'A search string about \"{topic}\" created on {date}'.format(
            topic=self.topic, date=self.date_created
        )


class Search(models.Model):
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE)
    search_string = models.ForeignKey(SearchString, on_delete=models.CASCADE)
    source = models.ForeignKey(Source, on_delete=models.CASCADE)
    date_searched = models.DateTimeField(default=timezone.now)
    results = models.TextField()

    class Meta:
        get_latest_by = 'date_searched'

    def __str__(self):
        return 'Topic: "{topic}"; Source: {source}; Date: {date}'.format(
            topic=self.topic, date=self.date_searched, source=self.source
        )


class Publication(models.Model):
    title = models.CharField(max_length=510, blank=True)
    abstract = models.TextField(blank=True)
    author = models.TextField(blank=True)
    year = models.CharField(max_length=30, blank=True)
    journal = models.CharField(max_length=254, blank=True)
    volume = models.CharField(max_length=30, blank=True)
    issue = models.CharField(max_length=30, blank=True)
    pages = models.CharField(max_length=30, blank=True)
    doi = models.CharField(max_length=254, blank=True)
    search_topics = models.ManyToManyField(Topic)
    searches = models.ManyToManyField(Search, blank=True)  # blank=True for manual searches uploaded by csv.
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    def split_author(self):
        split_author = self.author.split(',')
        author_list = []
        for author in split_author:
            split_name = author.split(' ')
            split_name = list(filter(None, split_name))  # Delete the blanks.
            author_list.append(split_name)
        return author_list

    def split_pages(self):
        return self.pages.split('-')

    @property
    def google_string(self):
        string = quote_plus(self.title)
        return string


class Assessment(models.Model):
    publication = models.ForeignKey(Publication, on_delete=models.CASCADE)
    is_relevant = models.BooleanField()
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE)
    assessor = models.ForeignKey(settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return '{boolean}: "{publication}" is relevant to "{topic}"'.format(
            boolean=self.is_relevant, publication=self.publication,
            topic=self.topic
        )


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    email_is_confirmed = models.BooleanField(default=False)
    institution = models.CharField(max_length=254, blank=True)
    EDUCATIONAL_ATTAINMENT_CHOICES = (
        (0, "No formal education"),
        (1, "Secondary school"),
        (2, "Degree"),
        (3, "Masters"),
        (4, "Doctorate"),
        (5, "Postdoctoral research or equivalent")
    )
    educational_attainment = models.IntegerField(choices=EDUCATIONAL_ATTAINMENT_CHOICES, default=0)
    topics = models.ManyToManyField(Topic, blank=True)

    def __str__(self):
        return 'Profile for username "{username}"'.format(username=self.user.username)


@receiver(post_save, sender=User)
def update_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    instance.profile.save()


class AssessmentStatus(models.Model):
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE)
    assessor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    assessment_order = models.TextField()
    next_assessment = models.IntegerField(blank=True, null=True)
    completed_assessments = models.TextField(blank=True)

    def get_list_as_string(self, list):
        return '[' + ','.join(map( str, list)) + ']'

    @property
    def assessment_order_list(self):
        return literal_eval(self.assessment_order)

    @assessment_order_list.setter
    def assessment_order_list(self, value):
        self.assessment_order = self.get_list_as_string(value)

    @property
    def completed_assessments_list(self):
        return literal_eval(self.completed_assessments)

    @completed_assessments_list.setter
    def completed_assessments_list(self, value):
        self.completed_assessments = self.get_list_as_string(value)

    def __str__(self):
        return 'Progress report for username "{username}" and topic "{topic}"'.format(username=self.assessor.username, topic=self.topic)


class MLModel(models.Model):
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE)
    threshold = models.FloatField()
    accuracy = models.FloatField()
    precision = models.FloatField()
    test_recall = models.FloatField()
    target_recall = models.FloatField()

    def __str__(self):
        return 'Topic: "{topic}"; Precision: {precision}; Recall: {test_recall}'.format(topic=self.topic, precision=self.precision, test_recall=self.test_recall)


class MLPrediction(models.Model):
    publication = models.ForeignKey(Publication, on_delete=models.CASCADE)
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE)
    prediction = models.FloatField()

    def __str__(self):
        return 'Prediction: {prediction}; Topic: "{topic}"; Publication: "{publication}"'.format(prediction=self.prediction, topic=self.topic, publication=self.publication)


class HumanPrediction(models.Model):
    publication = models.ForeignKey(Publication, on_delete=models.CASCADE)
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE)
    n_assessments = models.IntegerField()
    n_relevant = models.IntegerField()
    relevance = models.FloatField()

    class Meta:
        ordering = ['-relevance', '-n_assessments']

    def __str__(self):
        return 'Relevance: {relevance}; Topic: "{topic}"; Publication: "{publication}"'.format(relevance=self.relevance, topic=self.topic, publication=self.publication)


class Log(models.Model):
    event = models.CharField(max_length=254)
    note = models.TextField(blank=True)
    date_time = models.DateTimeField(default=timezone.now)
    n_users = models.IntegerField()
    n_publications = models.IntegerField()
    n_assessments = models.IntegerField()
    n_assessed_publications = models.IntegerField()
    max_publication_pk = models.IntegerField()

    class Meta:
        get_latest_by = 'date_time'

    def __str__(self):
        return 'Event: {event}; DateTime: {date_time}'.format(
                event=self.event,
                date_time=self.date_time
            )
