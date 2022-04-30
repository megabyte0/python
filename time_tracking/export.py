import mysql.connector
import os,os.path
import datetime
import json
import sys
import urllib.request
import re
import ssl
import certifi
connection_init_dict = {
    'user':'root',
    'password':'12345678',
    'database':'time_tracking',
    }
fields = r'''id
label
task_id
start_at
end_at
finished
exported'''.split('\n')
sql_connection=mysql.connector.connect(**connection_init_dict)
sql = ('select %s from time_tracking '
       'where exported = 0 '
       'and end_at != start_at '
       'and task_id is not null')%(', '.join(fields))
cursor = sql_connection.cursor(buffered=True)
cursor.execute(sql)
data = [{k:v for k,v in zip(fields,i)} for i in cursor]

har_path = '.'
har_file = 'har/softrize.atlassian.net_Archive [22-04-11 20-21-13].har'
with open(har_file,'rt') as fp:
    har = json.load(fp)

elems = [
    i
    for i in har['log']['entries']
    if 'request' in i
    and 'url' in i['request']
    and '/worklog?' in i['request']['url']
    ]

if not elems:
    sys.exit(1)

elem = elems[0]
request_params = {
    'headers': {
        i['name']:i['value']
        for i in elem['request']['headers']
        if i['name'] not in ['Host', 'Content-Length', 'Connection']
        },
    'method': elem['request']['method'],
    }
url = re.sub(r'/TIPS\-(\d+)/', lambda m:'/TIPS-%d/', elem['request']['url'])
update_sql = 'update time_tracking set exported = 1 where id = %s'
context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
context.load_verify_locations(certifi.where())
print(len(data),end='',flush=True)
for item in data:
    minutes = int(
        ((item['end_at']-item['start_at']) / datetime.timedelta(seconds=60))
        +0.5)
    start_time_formatted = (
        (item['start_at'].strftime('%Y-%m-%dT%H:%M:%S.%f'))[:-3]+'+0000'
        )
    req_data = {
        'timeSpent': '%dm'%(minutes),
        'comment': {
            'version': 1,
            'type': 'doc',
            'content': [
                {
                    'type': 'paragraph',
                    'content': [
                        {
                            'type': 'text',
                            'text': item['label'] or ''
                            }
                        ]
                    }
                ]
            },
        'started': start_time_formatted
        }
    req = urllib.request.Request(
        url%(item['task_id']),
             data=json.dumps(req_data).encode(),
             **request_params
             )
    with urllib.request.urlopen(req, context=context) as fp:
        response = fp.read()
    assert fp.status == 201
    cursor.execute(update_sql, (item['id'],))
    sql_connection.commit()
    print('.',sep='',end='',flush=True)

cursor.close()
sql_connection.close()
