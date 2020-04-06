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
import config
from django.template.loader import get_template
from django.core.mail import EmailMessage
from django.contrib.auth.models import User
from engine.models import Publication, MLModel, Topic, Log
from itertools import islice
from log import log


now = datetime.datetime.now()
day = now.day

# # This script is run as a daily task (monthly is not possible), but we want it to be run only as a monthly task, on a specified day of the month (day = 14).
# if (day != 28):
#     exit()

# Set the name of this script, for use in saving the log.
event = 'alert.py'

# Set the topic.
topic = Topic.objects.get(topic='existential risk')

# Get the threshold value for the ML predictions for this topic.
THRESHOLD = MLModel.objects.get(
    topic=topic,
    target_recall=0.75  # For the medium recall model.
).threshold

# Get the pk values of new publications to be sent in this alert (new publications have a pk value greater than the maximum pk value of the old publications that were sent in the last alert).
try:
    max_publication_pks = Log.objects.filter(event='alert.py').values_list('max_publication_pk', flat=True)
    old_max = max(max_publication_pks)
except:
    note = 'This is the first call to alert.py, and therefore no email was sent. The next call to alert.py will send an email only if there are new publications that are predicted to be relevant after this first alert.'
    log(event=event, note=note)
    print(note)
    exit()

# If there are new publications, continue. If not, exit.
if Publication.objects.filter(
    mlprediction__prediction__gte=THRESHOLD,
    mlprediction__topic=topic,
    pk__gt=old_max
).exists():
    publications = Publication.objects.filter(
        mlprediction__prediction__gte=THRESHOLD,
        mlprediction__topic=topic,
        pk__gt=old_max
    ).order_by('-mlprediction__prediction')
else:
    note = 'No new publications are predicted to be relevant, and therefore no email was sent.'
    log(event=event, note=note)
    print(note)
    exit()

mailing_list = []
users = User.objects.filter(is_active=True)
for user in users:
    mailing_list.append(user.email)

EMAIL_HOST_USER = config.EMAIL_HOST_USER
subject = 'New Publications about Existential Risk or Global Catastrophic Risk'
context = {
    'publications': publications,
    'topic': topic,
    'domain': config.DOMAIN,
    'protocol': 'http'
}

# Divide the mailing_list into chunks of 50.
mailing_list = iter(mailing_list)
mailing_list = list(iter(lambda: tuple(islice(mailing_list, 50)), ()))

# Send email to each chunk.
for chunk in mailing_list:
    message = get_template('engine/alert_email.html').render(context)
    message = EmailMessage(subject, message, to=[EMAIL_HOST_USER], bcc=chunk)
    message.send()

    note = 'An email alert was sent to a chunk of the mailing list for {topic}, with publications that were recently predicted to be relevant by the machine-learning model. Here is this chunk of the mailing list: {chunk}'.format(topic=topic, chunk=chunk)
    log(event=event, note=note)
    print(note)
