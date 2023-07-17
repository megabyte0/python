import mysql.connector
import pickle
import time
from collections import defaultdict
import calendar
from read_jetbrains_history import read_jetbrains_history

import os, os.path
import re
import itertools

slack_history_path = '/home/user/work/softrize/misc/slack_online'
def get_slack_history(path = slack_history_path):
    matcher = re.compile(r'all_messages_.*?\.pickle')
    elems = [
        os.path.join(path,fn)
        for fn in os.listdir(path)
        if matcher.match(fn)
        ]
    full_fn = max(elems,key=lambda full_fn:os.stat(full_fn).st_ctime)
    with open(full_fn,'rb') as fp:
        res = pickle.load(fp)
    return res

slack_letters_config = {
    'U021ZCGH6PN': 'D',
    'UKZDH1RME': None, #'J', #Jira
    'U02K32EM1RP': 'L',
    'U03HC424H2T': 'O',
    'U45A9GW6A': 'R',
    'U01V1UG00SX': 'i', #Timur
    'U02H0LNPLCT': 'V',
    'U02GA54DP7W': None, #Andrey
    'UQ6CTP9C7': 'Y',
    'USLACKBOT': None,
    'U04NL3KNC0P': 'l', #Oleksii Borzak
    }

def slack_history_users(history):
    return set(
        message['user']
    for channel, channel_history in history.items()
        for message in itertools.chain(
            channel_history['messages'],*(channel_history['threads'].values())
            )
        if 'user' in message
        )

def slack_history_linear(history, time_start = None):
    res = dict()
    for channel, channel_history in history.items():
        for message in itertools.chain(
            channel_history['messages'],*(channel_history['threads'].values())
            ):
            if 'user' in message and 'ts' in message:
                ts = int(message['ts'].split('.')[0])
                if time_start and ts < time_start:
                    continue
                #if config[message['user']]:
                res[ts] = message
    return sorted(res.items(),key=lambda i:i[0])

is_chat = lambda item:(
    item['task_id'] in [72,1489]
    or any(
        item['label'] and
        item['label'].startswith('%s '%i)
        for i in ['chat', 'call', 'logging']
        )
    )
is_not_logged = lambda item:item['task_id'] == None
dt_dt_to_utc_minute = lambda x:calendar.timegm(x.timetuple())//60

letter_priority = '|TtNnWwPpAaFfCcUu@' + (
    ''.join(v for v in slack_letters_config.values() if v)
    ) + '/*-!.'
letter_sort_key = lambda l:(
    letter_priority.index(l)
    if l in letter_priority
    else len(letter_priority)
    )

utc_minute_to_local_tuple = lambda x:time.localtime(x*60)

if __name__ == '__main__':
    slack_history = get_slack_history(slack_history_path)
    assert slack_history_users(slack_history) - set(slack_letters_config) == set()

    #with open('2022_11_29_08_05_08.pickle','rb') as fp:
    #    file_changes = pickle.load(fp)
    file_changes = read_jetbrains_history()
    file_changes[(
        # calendar.timegm((2023, 2, 8, 8,0,0,0,0,-1))
        time.time() - 17*24*60*60
        )*1000] = {'letter':'/'}

    connection_init_dict = {
        'user':'root',
        'password':'12345678',
        'database':'time_tracking',
        }
    fields = [
        'id',
        'label',
        'task_id',
        'start_at',
        'end_at',
        'finished',
        'exported',
    ]

    sql_connection=mysql.connector.connect(**connection_init_dict)
    sql = ('select %s from time_tracking '
           'where end_at >= %%s '
           #'and end_at != start_at'
           #' and task_id is not null'
           )%(', '.join(fields))
    cursor = sql_connection.cursor(buffered=True)
    cursor.execute(
        sql,
        (time.strftime('%Y-%m-%d %H:%M:%S',time.gmtime(min(file_changes)/1000)),)
        )
    data = [{k:v for k,v in zip(fields,i)} for i in cursor]
    ##sql_permissions = (
    ##    'select updated_at from route_permissions '
    ##    'where updated_at is not null'
    ##    )
    ##cursor.execute(sql_permissions)
    ##permissions_updated = [i[0] for i in cursor]
    cursor.close()
    sql_connection.close()

    minutes = defaultdict(set)
    for sql_item in data:
        _char = (
            ['*','-','!','!'][
                int(is_chat(sql_item))+int(is_not_logged(sql_item))*2
            ] if sql_item['start_at'] != sql_item['end_at']
            else '|'
            )
        for utc_minute in range(
            dt_dt_to_utc_minute(sql_item['start_at']),
            dt_dt_to_utc_minute(sql_item['end_at'])+1
            ):
            minutes[utc_minute].add(_char)

    get_slack_linear_history = lambda file_changes:slack_history_linear(
        slack_history,
        min(file_changes.keys())//1000
        )

    for k,v in get_slack_linear_history(file_changes):
        if slack_letters_config[v['user']]:
            if 'text' in v and '<@U02K32EM1RP>' in v['text']:
                letter = '@'
            else:
                letter = slack_letters_config[v['user']]
            minutes[k//60].add(letter)

    ##minutes.update({
    ##        k//60:slack_letters_config[v['user']]
    ##        for k,v in slack_linear_history
    ##        if slack_letters_config[v['user']]
    ##    })

    ##minutes.update({
    ##        dt_dt_to_utc_minute(permission_update_time):'U'
    ##        for permission_update_time in permissions_updated
    ##    })

    for k,v in file_changes.items():
        utc_minute = k//60000
        minutes[utc_minute].add(v['letter'])

    res=defaultdict(lambda:defaultdict(lambda:['.' for i in range(60)]))

    for utc_minute,letters in minutes.items():
        local_tuple = utc_minute_to_local_tuple(utc_minute)
        res[local_tuple[:3]][local_tuple.tm_hour][local_tuple.tm_min] = (
            min(letters, key = letter_sort_key)
            )

    for _date, v in sorted(res.items()):
        print(_date)
        print('   %s'%(''.join(('%d'%(i))*10 for i in range(6))))
        print('   %s'%('0123456789'*6))
        for hour, minute_chrs in sorted(v.items()):
            print('%2d %s'%(hour,''.join(minute_chrs)))

def get_filtered_history(
    common,
    start,
    end,
    filtered_history_f,
    ):
    if not isinstance(start,tuple):
        start = (start,)
    if not isinstance(end,tuple):
        end = (end,)
    start,end=[
        time.mktime(
            (lambda filled,unfilled:filled+unfilled[len(filled):])(
                common+i,(0,)*8+(-1,)
                )
            ) + n*({6:1,5:60,4:60*60}[len(common+i)])
        for n,i in enumerate([start,end])
        ]
    filtered_history = filtered_history_f(start, end)
    return filtered_history

def insert_something(
    common,
    start,
    end,
    reason,
    filtered_history_f,
    task_num,
    project
    ):
    filtered_history = get_filtered_history(
        common,
        start,
        end,
        filtered_history_f,
    )
    if not filtered_history:
        return
    start,end = [
        ('%s'+_format)%(
            time.strftime('%Y-%m-%d %H:%M:%S',time.gmtime(i)),
            _value
            )
        for i, _format, _value in [f(filtered_history) for f in [min,max]]
        ]
    insert_sql = (
        'insert into time_tracking '
        '(start_at,end_at,task_id,label,jira_project) '
        'values (%s, %s, %s, %s, %s)'
        )
    sql_connection=mysql.connector.connect(**connection_init_dict)
    cursor = sql_connection.cursor(buffered=True)
    cursor.execute(
        insert_sql,(start,end,task_num,reason,project)
    )
    sql_connection.commit()
    cursor.close()
    sql_connection.close()
    #if (project, task_num) == ('TIPS', 72):
    #    show_chat(common,start,end)

def insert_chat(common,start,end,task_num = None,reason = None):
    jira_project = 'TDS'
    if (jira_project, task_num) == ('TDS', None):
        task_num, jira_project = (72, 'TIPS')
    insert_something(
        common,start,end,reason,
        lambda start,end:[
        (k, '%s', '')
        for k,v in slack_linear_history
        if start<=k<end and slack_letters_config[v['user']]
        ], task_num, jira_project)

def show_chat(common,start,end,reason = None):
    filtered_history = get_filtered_history(
        common,start,end,
        lambda start,end:[
        (k, v)
        for k,v in slack_linear_history
        if start<=k<end and slack_letters_config[v['user']]
        ])
    print_filtered_history(filtered_history)

def print_filtered_history(filtered_history):
    print('\n'.join(
        '%s %s %s'%(
            time.strftime('%H:%M:%S', time.localtime(k)),
            slack_letters_config[v['user']],
            repr(v['text'])[1:-1]
            )
        for k,v in filtered_history
        ))

def insert_log(common, start, end, task_num = None, reason = None):
    insert_something(
        common,start,end,reason,
        lambda start,end:[
        (k/1000, '.%03d', k%1000)
        for k,v in file_changes.items()
        if start*1000<=k<end*1000
        ], task_num, 'TDS')
#x=[('%s.%03d'%(time.strftime('%Y-%m-%d %H:%M:%S',time.gmtime(k/1000)),k%1000),v) for k,v in file_changes.items() if '20220623170000' < time.strftime('%Y%m%d%H%M%S',time.localtime(k/1000)) < '20220623185959']
#min(x)[0],max(x)[0]
#x=[i for i in ['%s.%06d'%(time.strftime('%Y-%m-%d %H:%M:%S',i.timetuple()),i.microsecond) for i in permissions_updated] if '2022-07-27 16'<i<'2022-07-27 17'];(min(x),max(x))
