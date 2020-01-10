#!/usr/bin/python3

import boto3
import mayfly

s3 = boto3.client('s3');

def lambda_handler(event, context):
    print("Downloading csv")
    s3.download_file('ezybrs.hursts.org.uk', 'mayfly.csv', "/tmp/mayfly.csv")
    print("Done")
    with open('/tmp/mayfly.csv') as f:
        bins = mayfly.process_csv(f.readlines())
        with open('/tmp/mayfly.html', "w") as o:
            o.write(mayfly.build_page(bins))
            print("Uploading html")
            s3.upload_file(
                '/tmp/mayfly.html',
                'ezybrs.hursts.org.uk', 'mayfly.html',
                ExtraArgs={
                    'ACL': 'public-read',
                    'ContentType': 'text/html',
                    'CacheControl': 'no-cache'
                }
            )
            print("Done")
