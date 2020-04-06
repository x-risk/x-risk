########################################
# Create secret key file
# https://gist.github.com/ndarville/3452907
########################################

"""
Two things are wrong with Django's default `SECRET_KEY` system:
1. It is not random but pseudo-random
2. It saves and displays the SECRET_KEY in `settings.py`
This snippet
1. uses `SystemRandom()` instead to generate a random key
2. saves a local `secret.txt`
The result is a random and safely hidden `SECRET_KEY`.
"""

import os

SECRET_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.py')

try:
    import random
    SECRET_KEY = ''.join([random.SystemRandom().choice('abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)') for i in range(70)])
    secret = open(SECRET_FILE, 'a')
    secret.write("SECRET_KEY='" + SECRET_KEY + "'\n")
    secret.close()
except IOError:
    Exception('Please create a %s file with random characters \
    to generate your secret key!' % SECRET_FILE)
