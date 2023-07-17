import os, os.path
import pickle
import time
path = '/home/user/'
d={}
for root,dirs,files in os.walk(path):
    print(root[len(path):len(path)+79].ljust(79,' '),end='\r')
    for fn in files:
        full_fn = os.path.join(root,fn)
        try:
            d[full_fn] = os.stat(full_fn)
        except Exception as e:
            pass
with open('%s.pickle'%(
    time.strftime('%Y_%m_%d_%H_%M_%S',time.localtime())
    ),'wb') as fp:
    pickle.dump(d,fp)
