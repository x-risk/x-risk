#!/bin/sh

# Get path of current shell script so it can be used to absolutely reference other local scripts
SCRIPT="$(readlink --canonicalize-existing "$0")"
SCRIPTPATH="$(dirname "$SCRIPT")"

echo "Sending email alerts"
$SCRIPTPATH/venv/bin/python $SCRIPTPATH/engine/alert.py

echo "Monthly tasks [2] finished"
