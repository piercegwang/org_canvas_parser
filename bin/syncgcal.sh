#!/bin/bash

# customize these
ACTIVATE="/ohsics_to_org/ohsical_to_org-env/bin/activate"
ICS2ORG="/ohsics_to_org/src/main.py"
ORGIGNOREFILE="file.org"
ICSFILE="/ohsics_to_org/data/ohs_assignments.ics"
ORGFILE="/gcal.org"
URL="Link to ICS file for curling"
FILEPREFIX="Any arbitrary text to put at beginning of generated file"

curl $URL -o $ICSFILE
source $ACTIVATE
python3 $ICS2ORG $ICSFILE $ORGFILE -oi $ORGIGNOREFILE -td 70 -ig "Class to ignore" -fp "$FILEPREFIX"
