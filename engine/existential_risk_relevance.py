# Run this script as a "standalone" script (terminology from the Django
# documentation) that uses the Djano ORM to get data from the database.
# This requires django.setup(), which requires the settings for this project.
# Appending the root directory to the system path also prevents errors when
# importing the models from the app.
if __name__ == '__main__':
    import sys
    import os
    import django
    parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__),
        os.path.pardir))
    sys.path.append(parent_dir)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "xrisk.settings")
    django.setup()

import pandas as pd
from django.db import transaction
from engine.models import Assessment, Publication, HumanPrediction, Topic


# Set the topic.
search_topic = Topic.objects.get(topic='existential risk')

# Get the publications.
relevant_publications = Publication.objects.distinct().filter(
    assessment__in=Assessment.objects.filter(
        topic=search_topic,
        is_relevant=True
    )
)

# Create a dataframe for the publications.
df = pd.DataFrame(list(relevant_publications.values('pk')))

# How many people have assessed each publication?
def get_n_assessments(row):
    n_assessments = Assessment.objects.filter(
        publication=row['pk'], topic=search_topic).count()
    return n_assessments
df['n_assessments'] = df.apply(get_n_assessments, axis=1)

# How many people have assessed each publication as relevant?
def get_n_relevant(row):
    n_relevant = Assessment.objects.filter(
        publication=row['pk'], topic=search_topic, is_relevant=True).count()
    return n_relevant
df['n_relevant'] = df.apply(get_n_relevant, axis=1)

# What is the relevance of each publication?
def get_relevance(row):
    return row['n_relevant'] - (row['n_assessments'] - row['n_relevant'])
df['relevance'] = df.apply(get_relevance, axis=1)

# Save the predictions to the database.
human_predictions = []
for row in df.itertuples():
    human_predictions.append(HumanPrediction(
        publication=Publication.objects.get(pk=row.pk),
        topic=search_topic,
        n_assessments = row.n_assessments,
        n_relevant = row.n_relevant,
        relevance = row.relevance
    ))
with transaction.atomic():
    HumanPrediction.objects.filter(topic=search_topic).delete()
    HumanPrediction.objects.bulk_create(human_predictions)
