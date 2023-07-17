import re
import pickle
import os,os.path
import struct
import time

path_to_letter = {
    '/home/user/work/softrize/fe1zx/':'w',
    '/home/user/work/softrize/working/public/tips/api/':'a',
    '/home/user/work/softrize/working/public/tips/form/':'f',
    '/home/user/work/softrize/working/public/tips/pay/':'p',
    '/home/user/work/softrize/working/public/tips/':'t',
    '/home/user/work/softrize/misc/country_flags/':'c',
    '/home/user/work/softrize/misc/find_selectors/extract_hardcode_2_rename/':'u',
    '/home/user/work/time_table/':'s',
    '/home/user/work/time_tracking_html/':'s',
    }

def read_jetbrains_history():
    path = '/home/user/.cache/JetBrains/PhpStorm2023.1/LocalHistory/'
    index_file = 'changes.storageRecordIndex'
    data_file = 'changes.storageData'

    with open(os.path.join(path,index_file),'rb') as fp:
        index = fp.read()
    index_entries = [
        struct.unpack_from('>QIIIIQ',buffer=index,offset=offset)
        for offset in range(0x20,len(index),0x20)
        ]
    index_entries = list(filter(any, index_entries))

    split_string = rb'/home/user/'
    matcher = re.compile(split_string)
    with open(os.path.join(path,data_file),'rb') as fp:
        data = fp.read()


    d = dict()
    for n,(start, _len, real_len, _1, _2, _time) in enumerate(index_entries):
        if _time == 0:
            continue
        chunk = data[start:start+_len]
        chunk_split = matcher.split(chunk)
        files = []
        for prev,_next in zip(chunk_split,chunk_split[1:]):
            fn_len = prev[-1]
            files.append((split_string+_next)[:fn_len])
        external_change = b'External change' in chunk
        letters = set()
        for fn in files:
            for k,v in path_to_letter.items():
                if fn.startswith(k.encode()):
                    letter = v
                    break
            else:
                letter = None
            letters.add(letter)
        letters.discard(None)
        if len(letters) == 1:
            letter = list(letters)[0]
        elif len(letters) == 0:
            letter = 'n'
        else:
            letter = 'm'
        if external_change:
            letter = letter.upper()
        d[_time] = {'files':files, 'letter':letter}
    return d

if __name__ == '__main__':
    d = read_jetbrains_history()
    out_path = './jetbrains_history_pickle/'
    pickle_out_fn = os.path.join(
        out_path,
        '%s.pickle'%(
            time.strftime('%Y_%m_%d_%H_%M_%S', time.localtime(max(d)/1000))
            )
        )
    with open(pickle_out_fn,'wb') as fp:
        pickle.dump(d,fp)
    print(pickle_out_fn)
