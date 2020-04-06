#!/bin/sh

# Get path of current shell script so it can be used to absolutely reference other local scripts
SCRIPT="$(readlink --canonicalize-existing "$0")"
SCRIPTPATH="$(dirname "$SCRIPT")"

echo "Retrieving text data from Scopus text archive"
$SCRIPTPATH/venv/bin/python $SCRIPTPATH/engine/search_scopus.py

echo "Load Scopus text data into database"
$SCRIPTPATH/venv/bin/python $SCRIPTPATH/engine/scopus_api_to_database.py

echo "Run ML classifier on text data"
$SCRIPTPATH/venv/bin/python $SCRIPTPATH/engine/existential_risk_ml.py > $SCRIPTPATH/ml.log

echo "Monthly tasks [1] finished"

