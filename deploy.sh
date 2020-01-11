#!/bin/bash

#usage: deploy.sh [html|js|css|py|all]

PROJ_DIR="/home/jon/proj/mayfly"
BUCKET="s3://ezybrs.hursts.org.uk"
STDOPTS="--region=eu-west-2 --acl=public-read --cache-control=no-cache"
ZIPFILE="deploy.zip"
FUNCTIONID=update_mayfly

cd $PROJ_DIR

if [ "$1" = "html" -o "$1" = "all" ]
then
aws s3 cp --region=eu-west-2 ${BUCKET}/mayfly.csv ${PROJ_DIR}/mayfly.csv
./mayfly.py mayfly.csv mayfly.html
aws s3 cp $STDOPTS --content-type="text/html" mayfly.html $BUCKET
rm mayfly.csv mayfly.html
fi

if [ "$1" = "js" -o "$1" = "all" ]
then
aws s3 cp $STDOPTS --content-type="application/javascript" mayfly.js $BUCKET
fi

if [ "$1" = "css" -o "$1" = "all" ]
then
aws s3 cp $STDOPTS --content-type="text/css" mayfly.css $BUCKET
fi

if [ "$1" = "py" -o "$1" = "all" ]
then
#upload lambda function
zip $ZIPFILE *.py
aws lambda update-function-code \
    --region "us-east-1" \
    --function-name  "$FUNCTIONID" \
    --zip-file "fileb://${PROJ_DIR}/${ZIPFILE}"
rm $ZIPFILE
fi