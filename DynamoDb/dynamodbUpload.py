import boto3
import json

with open("student_data.json") as json_file:
    table = json.load(json_file)

print(table)
print(type(table))

dynamodb = boto3.resource('dynamodb')
dbtable = dynamodb.Table('g45-teammembers-academic')
for i in range(0, len(table)):
    dbtable.put_item(Item=table[i])
