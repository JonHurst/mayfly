#!/usr/bin/python3

import boto3
import mayfly

s3 = boto3.client('s3');
BUCKET = 'ezybrs.hursts.org.uk'

def lambda_handler(event, context):
    global BUCKET
    print("Downloading csv")
    s3.download_file(BUCKET, 'mayfly.csv', "/tmp/mayfly.csv")
    print("Done")
    with open('/tmp/mayfly.csv') as f:
        updates = mayfly.create_update_dict()
        bins = mayfly.process_csv(f.readlines(), updates)
        with open('/tmp/mayfly.html', "w") as o:
            o.write(mayfly.build_page(bins))
            print("Uploading html")
            s3.upload_file(
                '/tmp/mayfly.html',
                BUCKET, 'mayfly.html',
                ExtraArgs={
                    'ACL': 'public-read',
                    'ContentType': 'text/html',
                    'CacheControl': 'no-cache'
                }
            )
            print("Done")


def staging_lambda_handler(event, context):
    global BUCKET
    BUCKET = 'ezybrs-staging.hursts.org.uk'
    lambda_handler(event, context)
