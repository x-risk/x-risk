##########################
##########################
# Script to send sample alert to 'from' user - useful in order to check formatting and links
##########################
##########################

##########################
# Load variables from Django config file
##########################

. config.py

###########################
# Send sample alert email
###########################

echo "Sending sample alert email to: $EMAIL_HOST_USER"
python3 engine/sample_alert.py
