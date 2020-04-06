#!/bin/sh

# Get path of current shell script so it can be used to absolutely reference other local scripts
SCRIPT="$(readlink --canonicalize-existing "$0")"
SCRIPTPATH="$(dirname "$SCRIPT")"

# Load parameters from local config.py
. $SCRIPTPATH/config.py

# Dump MySQL database to local location, copy to backup location, and delete local file
echo "Dumping MySQL database"
MYSQLDUMPFILE="xrisk.$(date +%d).sql.gz"
mysqldump -u$DB_USER -p$DB_PASSWORD $DB_NAME | gzip -c > $SCRIPTPATH/$MYSQLDUMPFILE
eval "cp $SCRIPTPATH/$MYSQLDUMPFILE $DB_BACKUPDIR/$MYSQLDUMPFILE"
# If using Google bucket, comment out previous line and specify the user the bucket was mounted under below
#su - [google_bucket_user] -c "cp $SCRIPTPATH/$MYSQLDUMPFILE $DB_BACKUPDIR/$MYSQLDUMPFILE"
rm $SCRIPTPATH/$MYSQLDUMPFILE

echo "Process assessments so far"
$SCRIPTPATH/venv/bin/python $SCRIPTPATH/engine/existential_risk_relevance.py

echo "Update index"
$SCRIPTPATH/venv/bin/python $SCRIPTPATH/manage.py rebuild_index --noinput
#$SCRIPTPATH/venv/bin/python $SCRIPTPATH/manage.py update_index 

echo "Update permissions on index in case newly created"
chown -R www-data:www-data $SCRIPTPATH/xrisk/whoosh_index

echo "Daily tasks finished"

