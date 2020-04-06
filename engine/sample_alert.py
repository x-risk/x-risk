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
    exit()

# For the sake of creating a sample alert, don't worry if there are no new publications
publications = Publication.objects.filter(
    mlprediction__prediction__gte=THRESHOLD,
    mlprediction__topic=topic,
    pk__gt=old_max
).order_by('-mlprediction__prediction')

EMAIL_HOST_USER = config.EMAIL_HOST_USER
subject = 'New Publications about Existential Risk or Global Catastrophic Risk'
context = {
    'publications': publications,
    'topic': topic,
    'domain': config.DOMAIN,
    'protocol': 'http'
}

message = get_template('engine/alert_email.html').render(context)
message = EmailMessage(subject, message, to=[EMAIL_HOST_USER])
message.send()

print("Sample alert email sent")
