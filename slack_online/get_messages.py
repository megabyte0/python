import time
import urllib.request
import json
import os,os.path
import re
import random
import pickle

import socket
import urllib.error

har_path = './har/'
matcher = re.compile(
    '^%s'%(
        re.escape('wss://wss-primary.slack.com/')
        .replace('wss-primary','.*?')
        )
    )
har_files = {i:os.stat(i) for i in (
    os.path.join(har_path,j)
    for j in os.listdir(har_path)
    )}
latest_har_file = max(
    har_files.items(),
    key=lambda x:x[1].st_ctime
    )[0]
with open(latest_har_file,'rt') as fp:
    har = json.load(fp)
entry = [
    i
    for i in har['log']['entries']
    if ('request' in i
        and 'url' in i['request']
        and matcher.match(i['request']['url']))
    ]
assert entry
entry = entry[0]
url, params = entry['request']['url'].split('?',1)
params = dict(tuple(i.split('=',1)) for i in params.split('&'))
assert 'token' in params
token = params['token']

headers = {i['name']:i['value']
           for i in entry['request']['headers']
           #if i['name'] not in ['Host','Connection']
           if i['name'] in ['User-Agent','Cookie']
           }
#print(token, headers)
#assert False
headers.update({'Authorization': 'Bearer %s'%token})
user = 'U02K32EM1RP'
def get(api,**params):
    url = 'https://slack.com/api/%s'%api
    pass_url = [
        url,'&'.join('%s=%s'%(k,str(v)) for k,v in params.items())]
    req = urllib.request.Request('?'.join(pass_url),headers=headers)
    wait = 3.75
    while True:
        try:
            with urllib.request.urlopen(req) as fp:
                data = fp.read()
            break
        except urllib.error.HTTPError as e:
            print(dir(e))
            print('waiting %g sec:'%wait, end='')
            time.sleep(wait)
            print()
            wait *= 2
    return json.loads(data)

def post_json(api,**params):
    url = 'https://slack.com/api/%s'%api
    headers_post = {k:v for k,v in headers.items()}
    headers_post['Content-Type'] = 'application/json'
    data = json.dumps(params).encode()
    headers_post['Content-Length'] = str(len(data))
    req = urllib.request.Request(
        url,headers=headers_post,data=data,method='POST'
        )
    with urllib.request.urlopen(req) as fp:
        data = fp.read()
    return json.loads(data)

channels = [
    'C02LSE38SAJ', #mpdm-yuliia--dmitriy--alexey.burdin-1
    'C02RW060UE5', #mpdm-yuliia--alexey.burdin--dmitriy--timur-1
    'D02JQEYJ5M0', #UQ6CTP9C7 Yuliia Borshcheva
    'D02J9PFSQ87', #U45A9GW6A Roman Patsalovskyi
    'D02JHNUFH0W', #U021ZCGH6PN Dmitriy Makukha
    'C01V3L1GF4G', #tips-project
    'D03HV2N6CTE', #U03HC424H2T Olena Stepanova
    #'D03DS5L62QL', #U03DPQRKHQB Anna Nikiforchuk
    'D0380BBND2R', #U0385J51U5S Veronika Bezpala
    #'D037L23PTLZ', #U037X6HEDQ8 "is_user_deleted": true Tanya Tychkovska
    #'D031JP51K6X', #UDLC66Y9G logger
    #'D0311R997QX', #U01UL8ZHA20 github2
    #'D030DJVUE7R', #U030MHFH24W megabyte_github_bot
    #'D02UXGMQK7S', #U02UA311ALU "is_user_deleted": true Aleksandra Hatman
    #'D02QJQU2Q6B', #U02RP2EH6U8 Yulia Suzdaleva
    #'D02PZRDSVJ4', #U02P2P8C0F8 "is_user_deleted": true Andrii Shtynda
    'D02JMFAARMK', #U01V1UG00SX Timur Lavrentsov
    'D02JHNUEE22', #U02H0LNPLCT Vladimir Lozinskii
    'D02KE5565RN', #U02GA54DP7W Andrey Dotsenko
    'D04PPTFGS11', #U04NL3KNC0P Oleksii Borzak
    'C064U0Y4DKJ', #cf
    'C077C95AP2S', #jv
    'D07GSN00CQ6', #U07G5QA7WL8 Nicolai Gheorghiev
    'D02JMFACMC5', #U58JHAD8D Eugene Lyulka
    ]

def get_history(api_endpoint, **params):
    res=[]
    params_now = {}
    while True:
        response = get(api_endpoint,**params,**params_now)
        if 'ok' not in response or not response['ok']:
            break
        if 'messages' not in response:
            break
        if not len(response['messages']):
            break
        ts = response['messages'][-1]['ts']
        print(len(response['messages']),ts)
        res.extend(response['messages'])
        if 'has_more' in response and not response['has_more']:
            break
        params_now['latest']=ts
        params_now['inclusive']=0
    return res

def get_entire_channel(channel):
    messages = get_history('conversations.history',channel=channel)
    threads = {
        message['thread_ts']:get_thread(channel,message['thread_ts'])
        for message in messages
        if ('thread_ts' in message
            and 'reply_count' in message
            and message['reply_count'] > 0)
    }
    return {'messages':messages, 'threads':threads}

def get_thread(channel,ts):
    return get_history('conversations.replies',channel=channel,ts=ts)

d={}
for channel in channels:
    print(channel)
    d[channel]=get_entire_channel(channel)
fn_date_part = time.strftime('%Y_%m_%d_%H_%M_%S',time.gmtime())
with open('all_messages_%s.pickle'%fn_date_part,'wb') as fp:
    pickle.dump(d,fp)
