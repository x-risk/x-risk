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
import re
from engine.models import Topic, Publication
from log import log

# Set the topic.
topic = Topic.objects.get(topic="existential risk")

# Load a csv file with results from a Scopus search (on the Scopus website, not using the API).
csv = "data/scopus/existential_risk/2011.csv"
df = pd.read_csv(csv, encoding='utf-8')

df = df.rename(columns={
    'Source title': 'Journal',
    'Page start': 'Page_start',
    'Page end': 'Page_end'
})

# Clean the data (replace Scopus placeholders with '').
df.Authors.replace('[No author name available]', '', inplace=True)
df.Abstract.replace('[No abstract available]', '', inplace=True)
df.DOI = df.DOI.fillna(value='')
df.Abstract = df.Abstract.fillna(value='')
df.Journal = df.Journal.fillna(value='')
df.Volume = df.Volume.fillna(value='')
df.Issue = df.Issue.fillna(value='')
df.Page_start = df.Page_start.fillna(value='')
df.Page_end = df.Page_end.fillna(value='')

# Get the data on all publications that are already in the database.
publications = Publication.objects.values('title','doi')

for result in df.itertuples():
    doi = result.DOI
    if doi != '':
        # If a publication with this doi is already in the database, do not add it, but do update it with this search topic.
        if publications.filter(doi__iexact=doi).exists():
            record = Publication.objects.get(doi=doi)
            record.search_topics.add(topic)
            continue  # Go to the next result.

    title = result.Title
    year = result.Year
    if title != '':
        title = re.sub('<[^<]+?>', '', title)  # Strip html tags from the title.
        # If a publication with this title and year is already in the database, do not add it, but do update it with this search topic.
        if publications.filter(title__iexact=title, year__iexact=year).exists():
            record = Publication.objects.get(title=title, year=year)
            record.search_topics.add(topic)
            continue  # Go to the next result.
    else:  # If this publication has no title, do not add it to the database.
        continue

    abstract = result.Abstract
    author_string = result.Authors
    journal = result.Journal
    volume = result.Volume
    issue = result.Issue
    if (result.Page_start != '') and (result.Page_end != ''):
        pages = result.Page_start + '-' + result.Page_end
    else:
        pages = ''

    # Check that the data do not exceed the maximum lengths in the database. They should not, except in the case of errors in the data (or metadata in the same field). If the length is exceeded, delete the excess.
    if len(title) > 510:
        title = title[0:510]
    if len(str(year)) > 30:
        year = year[0:30]
    if len(journal) > 254:
        journal = journal[0:254]
    if len(str(issue)) > 30:
        issue = issue[0:30]
    if len(str(volume)) > 30:
        volume = volume[0:30]
    if len(pages) > 30:
        pages = pages[0:30]
    if len(doi) > 254:
        doi = ''  # A broken DOI will not work, whereas truncated data in the the other fields could be informative.

    record = Publication(
        title=title,
        abstract=abstract,
        author=author_string,
        year=year,
        journal=journal,
        volume=volume,
        issue=issue,
        pages=pages,
        doi=doi,
    )
    record.save()
    # ManyToManyFields need to be added after the record is saved.
    record.search_topics.add(topic)

event = 'scopus_csv_to_database.py'
note = 'New publications from a search for {topic} (saved as a CSV file) were saved to the Publication model.'.format(topic=topic)
log(event=event, note=note)
