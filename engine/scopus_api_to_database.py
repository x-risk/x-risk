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

import datetime
import re
from ast import literal_eval
from engine.models import Search, Publication
from log import log


now = datetime.datetime.now()
day = now.day

# This script is run as a daily task (monthly is not possible), but we want it to be run only as a monthly task, on a specified day of the month (day = 14).
# if (day != 28):
#     exit()

publications = Publication.objects.values('title','doi','year')

# The most recent search
search = Search.objects.latest()
topic = search.topic
results = literal_eval(search.results)  # The results string is Python code.

for result in results:

    doi = result.get('prism:doi', '')  # Blank if 'prism:doi' does not exist
    if doi != '':
        # If a publication with this doi is already in the database, do not add it, but do update it with this search and search topic.
        if publications.filter(doi__iexact=doi).exists():
            record = Publication.objects.get(doi=doi)
            record.searches.add(search)
            record.search_topics.add(topic)
            continue  # Go to the next result.

    title = result.get('dc:title', '')  # Blank if 'dc:title' does not exist

    year = result.get('prism:coverDate', '')
    year = year.split('-')[0]  # 'yyyy' from 'yyyy-mm-dd'

    if title != '':
        title = re.sub('<[^<]+?>', '', title)  # Strip html tags from the title.
        # If a publication with this title and year is already in the database, do not add it, but do update it with this search and search topic.
        if publications.filter(title__iexact=title, year__iexact=year).exists():
            record = Publication.objects.get(title=title, year=year)
            record.searches.add(search)
            record.search_topics.add(topic)
            continue  # Go to the next result.

    abstract = result.get('dc:description', '')
    journal = result.get('prism:publicationName', '')
    volume = result.get('prism:volume', '')
    issue = result.get('prism:issueIdentifier', '')
    pages = result.get('prism:pageRange', '')
    if pages is not None:  # Unlike the other fields, Scopus sets pageRange to "None" rather than leaving it blank.
        pass
    else:
        pages = ''
    author_list = []
    author_data = result.get('author', '')  # A list of dictionaries
    try:
        for author in author_data:
            author_list.append('{surname} {initials}'.format(
                surname=author.get('surname', ''),
                initials=author.get('initials', ''),
                )
            )
        author_list = set(author_list)  # Unique author names
        author_string = ', '.join(author_list)
    except:
        author_string = ''

    # Check that the data do not exceed the maximum lengths in the database. They should not, except in the case of errors in the data (or metadata in the same field). If the length is exceeded, delete the excess.
    if len(title) > 510:
        title = title[0:510]
    if len(year) > 30:
        year = year[0:30]
    if len(journal) > 254:
        journal = journal[0:254]
    if len(issue) > 30:
        issue = issue[0:30]
    if len(volume) > 30:
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
    record.searches.add(search)

event = 'scopus_api_to_database.py'
note = 'New publications from the lastest Scopus search (for {topic}) were saved to the Publication model.'.format(topic=topic)
log(event=event, note=note)
