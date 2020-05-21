import os
import json
import logging
import decimal
from boto3.dynamodb.conditions import Key

import boto3

import get_config
from aws_lambda_powertools.logging import Logger
logger = Logger()


# Helper class to convert a DynamoDB item to JSON.
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            if o % 1 > 0:
                return float(o)
            else:
                return int(o)
        return super(DecimalEncoder, self).default(o)

def query_requirements():
    """
    Args:
    returns:
      items: All the requriements_txt of the latest packages
    """
    
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(os.environ['DB_NAME'])
    kwargs = {
        "KeyConditionExpression": Key('pk').eq('v0.reqs'),
    }
    items = []

    while True:
        response = table.query(**kwargs)
        items.extend(response['Items'])

        try:
            kwargs['ExclusiveStartKey'] = response['ExclusiveStartKey']
        except KeyError:
            logger.info(f"Reached end of query for returning {len(items)} items")
            break

    return items

@logger.inject_lambda_context
def main(event, context):

    """
    Gets requirements_txt to publish to packages dir
    """

    bucket = os.environ['BUCKET_NAME']
    items = query_requirements()

    for item in items:

        package_name = item['sk']
        requirements_txt = item['rqrmntsTxt']
        key = f'packages/{package_name}/requirements.txt'

        logger.info({
            "message": "Uploading to bucket",
            "package": package_name,
            "requirements_txt": requirements_txt,
            "bucket": bucket,
        })
        client = boto3.client('s3')
        client.put_object(Body=requirements_txt.encode('utf-8'),
                        Bucket=bucket,
                        Key=key,)

    return {
        "status": "Done",
        "num_packages": len(items),
    }   
