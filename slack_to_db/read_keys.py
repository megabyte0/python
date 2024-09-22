import pickle
import os, os.path
import re
from collections import defaultdict, Counter
from functools import reduce
import itertools
import json

import mysql.connector


class Reader:
    def __init__(self, _process):
        self.process = _process
        self.channels = {
            'D02JMFAARMK',
            'D04PPTFGS11',
            'C02LSE38SAJ',
            'C02RW060UE5',
            'C077C95AP2S',
            'D02KE5565RN',
            'C064U0Y4DKJ',
            'D02JHNUFH0W',
            'D02JMFACMC5',
            'D03HV2N6CTE',
            'D02JHNUEE22',
            'D02J9PFSQ87',
            'D07GSN00CQ6',
            'D02JQEYJ5M0',
            'D0380BBND2R',
            'C01V3L1GF4G',
        }

        self.thread_name_matcher = re.compile(r'\d{10}\.\d{0,6}')

    def read(self, path, ):
        dir_list = [
            fn
            for fn in os.listdir(path)
            if fn.endswith('.pickle')
        ]
        len_list_dir = len(dir_list)
        divider = 1
        while len_list_dir > 77:
            len_list_dir //= 2
            divider *= 2
        # print('[%s]\033[%dD' % (' ' * len_list_dir, len_list_dir + 1), end='', flush=True)
        print('%d[' % len_list_dir, end='', flush=True)
        for n, fn in enumerate(dir_list):
            full_fn = os.path.join(path, fn)
            with open(full_fn, 'rb') as fp:
                d = pickle.load(fp)
            assert set(d.keys()) <= self.channels, fn
            for k, v in d.items():
                if isinstance(v, list):  # or 'threads' not in v:
                    d[k] = {
                        'messages': v,
                        'threads': dict(),
                    }
            assert all(
                i in v
                for k, v in d.items()
                for i in ['messages', 'threads']
            ), fn
            assert all(
                (
                        isinstance(v['messages'], list)
                        and isinstance(v['threads'], dict)
                )
                for v in d.values()
            ), fn
            assert all(
                isinstance(_v, list)
                for v in d.values()
                for k, _v in v['threads'].items()
            ), fn
            assert all(
                self.thread_name_matcher.match(k)
                for v in d.values()
                for k in v['threads'].keys()
            ), fn
            self.process(d)
            del d
            if n % divider == 0:
                print('.', end='', flush=True)
        print(']', flush=True)


class Processor:
    def __init__(self, sql_connector):
        """

        :type sql_connector: SqlConnector
        """
        self.sql_connector = sql_connector
        self.channels = set()
        self.keys_ = Counter()
        self.types = defaultdict(set)
        self.lengths = defaultdict(int)
        self.fields_sets = {
            'user': {
                'U45A9GW6A',
                'U021ZCGH6PN',
                'UKZDH1RME',
                'U0385J51U5S',
                'U04NL3KNC0P',
                'USLACKBOT',
                'U03HC424H2T',
                'U02H0LNPLCT',
                'U58JHAD8D',
                'U01V1UG00SX',
                'UQ6CTP9C7',
                'U02GA54DP7W',
                'U02K32EM1RP',
            },
            'bot_id': {
                'BKN190810',
                'B02GW3FFK6C',
                'B06JU6M6ENB',
                'B0657JJDUHH',
            },
            'app_id': {
                'A2RPP3NFR',
            },
            'parent_user_id': {
                'U021ZCGH6PN',
                'U45A9GW6A',
                'UKZDH1RME',
                'U0385J51U5S',
                'U04NL3KNC0P',
                'USLACKBOT',
                'U03HC424H2T',
                'U02H0LNPLCT',
                'U58JHAD8D',
                'U01V1UG00SX',
                'UQ6CTP9C7',
                'U02K32EM1RP',
            },
            'subtype': {
                'bot_message',
                'sh_room_created',
                'thread_broadcast',
                'tombstone',
                'joiner_notification_for_inviter',
                'joiner_notification',
                'bot_remove',
                'channel_join',
                'bot_add',
                'slackbot_response',
            },
            'username': {
                'Jira Cloud',
                'incoming-webhook',
            },
            'inviter': {
                'UQ6CTP9C7',
                'U58JHAD8D',
            },
            'channel': {
                'D02JQEYJ5M0',
                'C064U0Y4DKJ',
            }
        }
        self.fields_sets = {
            k:set(v)
            for k, v in self.sql_connector.process_enums(
                self.sql_connector.enums()
            ).items()
        }
        self.channels = self.fields_sets['channel']
        self.excluded_fields = [
            'type',
            'team',
            'reply_count',
            'reply_users_count',
            'latest_reply',
            'reply_users',
            'last_read',
            'pinned_to',
            'pinned_info',
        ]

    def process(self, d):
        self.channels |= set(d.keys())
        assert all(
            isinstance(message, dict)
            for channel, thread_ts, message in self.messages(d)
        )
        self.keys_.update((
            tuple(message.keys())
            for channel, thread_ts, message in self.messages(d)
        ))
        for channel, thread_ts, message in self.messages_converted(d):
            for k, v in message.items():
                if k in self.excluded_fields:
                    continue
                if (
                        k in self.fields_sets
                        and v not in self.fields_sets[k]
                ):
                    self.sql_connector.append_enum(
                        self.sql_connector.tables['history'],
                        k,
                        [v]
                    )
                # assert (
                #         k not in self.fields_sets
                #         or v in self.fields_sets[k]
                # ), k
                if isinstance(v, dict) or k in [
                    'blocks',
                    'reactions',
                    'attachments',
                    'files',
                    'reply_users',
                    'pinned_to',
                ]:
                    self.types[k].add('json')
                else:
                    assert not isinstance(v, list), k
                    if len(self.types[k]) < 1000:
                        self.types[k].add(v)
                    if not isinstance(v, (bool, int, float)):
                        self.lengths[k] = max([self.lengths[k], len(v)])
        pre_encoded_json = self.sql_connector.pre_encode_json((
            {
                k:v
                for k,v in message.items()
                if k not in self.excluded_fields
            }
            for channel, thread_ts, message in self.messages_converted(d)
        ))
        self.sql_connector.insert(
            self.sql_connector.tables['history'],
            pre_encoded_json,
        )

    def messages_converted(self, d):
        for channel, thread_ts, message in self.messages(d):
            message['channel'] = channel
            if thread_ts is not None:
                message['thread_ts'] = thread_ts
            yield channel, thread_ts, message

    def messages(self, d):
        for channel, v in d.items():
            assert 'messages' in v
            assert isinstance(v['messages'], list)
            assert 'threads' in v
            assert isinstance(v['threads'], dict)
            assert all(
                isinstance(v_, list)
                for k, v_ in v['threads'].items()
            )
            yield from (
                (channel, None, message)
                for message in v['messages']
            )
            yield from (
                (channel, thread_ts, message)
                for thread_ts, messages in v['threads'].items()
                for message in messages
            )
        return


class SqlConnector:
    def __init__(self, connection_init_dict):
        self.connection_init_dict = connection_init_dict
        self.sql_connection = mysql.connector.connect(**self.connection_init_dict)
        self.cursor = self.sql_connection.cursor(buffered=True, dictionary=True)
        self.fields = {
            'slack.slack_history' : [
                i.strip()
                for i in r'''
                    channel
                    ts
                    thread_ts
                    client_msg_id
                    text
                    user
                    blocks
                    edited
                    reactions
                    attachments
                    files
                    upload
                    display_as_bot
                    bot_id
                    app_id
                    bot_profile
                    is_locked
                    subscribed
                    parent_user_id
                    subtype
                    username
                    bot_link
                    inviter
                    root
                    room
                    no_notifications
                    permalink
                    hidden
                    old_name
                    name
                '''.split('\n')
                if i.strip()
            ],
        }
        self.tables = {
            'history': 'slack.slack_history',
        }
        self.database_columns = None
        self.database_columns_dict = {}

    def close(self):
        self.cursor.close()
        self.sql_connection.close()

    def commit(self):
        self.sql_connection.commit()

    def get_columns(self):
        fields = ['COLUMN_NAME', 'DATA_TYPE', 'COLUMN_TYPE', 'IS_NULLABLE']
        sql = (
            'select %s from information_schema.COLUMNS '
            'where TABLE_SCHEMA = %%s '
            'and TABLE_NAME = %%s '%(', '.join(
            '`%s`'%i
            for i in fields
        ))
        )
        params = self.tables['history'].split('.')
        if len(params) == 1:
            sql = sql%('database()', '%s')
        self.cursor.execute(sql, params)
        data = self.cursor.fetchall()
        self.database_columns = [
            {
                k.lower():v
                for k, v in i.items()
            }
            for i in data
        ]
        self.database_columns_dict = {
            i['column_name']: i
            for i in self.database_columns
        }
        return self.database_columns_dict

    def enums(self):
        if self.database_columns is None:
            self.get_columns()
        return {
            i['column_name']: i['column_type']
            for i in self.database_columns
            if i['data_type'] in ('enum', )
        }

    def process_enum(self, enum):
        assert enum.startswith('enum(') and enum.endswith(')')
        return [
            i.strip().strip('\'')
            for i in enum[len('enum('):-len(')')].split(',')
        ]

    def process_enums(self, enums):
        return {
            k:self.process_enum(v)
            for k,v in enums.items()
        }

    def append_enum(self, table, column, values):
        enums = self.process_enums(self.enums())
        assert column in enums
        values = enums[column] + [
            i
            for i in values
            if i not in enums[column]
        ]
        nullable = self.database_columns_dict[column]['is_nullable'].lower() == 'yes'
        sql = 'alter table %s change `%s` `%s` enum%r %snull'%(
            table,
            column,
            column,
            tuple(values),
            ['not ', ''][nullable]
        )
        self.cursor.execute(sql)
        self.sql_connection.commit()

    def split_insert(self, data):
        assert isinstance(data, list)
        assert all(
            isinstance(i, dict)
            for i in data
        )
        key_fn = lambda keys_:tuple(sorted(keys_))
        data = sorted(data, key=key_fn)
        return {
            k: list(g)
            for k, g in itertools.groupby(data, key_fn)
        }

    def pre_encode_json_item(self, item):
        assert all(
            k in self.database_columns_dict
            for k in item.keys()
        )
        return dict(
            (
                k,
                (
                    json.dumps(v)
                    if self.database_columns_dict[k]['data_type'] in ('json', )
                    else v
                )
            )
            for k, v in item.items()
        )

    def pre_encode_json(self, values):
        return [
            self.pre_encode_json_item(value)
            for value in values
        ]

    def insert(self, table, data):
        for fields, values in self.split_insert(data).items():
            for batch in itertools.batched(values, 100):
                self.insert_batch(table, batch, fields)

    def insert_batch(self, table, data, fields):
        sql = 'insert ignore into %s (%s) values %s'%(
            table,
            self.convert_fields(fields),
            self.convert_values_sql(len(data), len(fields)),
        )
        self.cursor.execute(sql, self.convert_values(data, fields))
        self.sql_connection.commit()

    def convert_fields(self, fields):
        return ', '.join(
            '`%s`'%field
            for field in fields
        )

    def convert_values(self, values, fields):
        return sum(
            (
                tuple(
                    item[field]
                    for field in fields
                )
                for item in values
            ),
            ()
        )

    def convert_values_sql(self, len_values, len_fields):
        return ', '.join(
            [
                '(%s)'%(', '.join(
                    ['%s'] * len_fields
                ))
            ] * len_values
        )


if __name__ == '__main__':
    paths = [
        #'/mnt/ubuntu_18/home/user/work/softrize/misc/slack_online/',
        '/home/user/work/softrize/misc/slack_online/',
    ]
    sql_connector = SqlConnector({
        'host': 'localhost',
        'port': 3306,
        'user': 'root',
        'password': '12345678',
    })
    print('\n'.join(
        repr(i)
        for i in sql_connector.get_columns().items()
    ))
    processor = Processor(sql_connector)
    reader = Reader(processor.process)
    for path in paths:
        reader.read(path)
    print(len(processor.keys_))
    all_keys = reduce(
        lambda acc, item: acc | item,
        (
            set(i)
            for i in processor.keys_.keys()
        ),
        set(),
    )
    print(len(all_keys))
    # with open('keys.json', 'wt') as fp:
    #     json.dump([
    #         list(i)
    #         for i in processor.keys_.keys()
    #     ], fp, indent=2)
    # print(processor.channels)
    print('\n'.join(
        repr({k: v} if len(v) not in [1000, 62] else {k: processor.lengths[k]})
        for k, v in processor.types.items()
    ))
    sql_connector.close()
