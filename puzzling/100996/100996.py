import itertools
from collections import defaultdict,Counter
import math
from PIL import Image, ImageDraw
d=defaultdict(set)
for i in itertools.product(range(1,11),repeat=2):
    d[sum(i)].add(i)
x=[2, 4, 5, 6, 7, 8, 10, 11, 12, 13]
#print(math.prod(len(d[i]) for i in x))
y=[d[j] for j in x]
def take(t,callback):
    global y
    if len(t)==len(y):
        if all(set(Counter(j[k] for j in t).values())==set([2])
               for k in [0,1]):
            callback(t)
        return
    c=[Counter(j[k] for j in t) for k in [0,1]]
    for x in y[len(t)]:
        if all(((x[k] not in c[k]) or (c[k][x[k]]<2))
            for k in [0,1]):
            take(t+[x],callback)
def callback(x):
    global c,l
    c+=1
    l.append(x)
c=0
l=[]
take([],callback)
'''
for n,i in enumerate(itertools.product(*[d[j] for j in x])):
    if (n+1)%int(1e6)==0:
        print('.',sep='',end='')
    if all(set(Counter(j[k] for j in i).values())==set([2])
           for k in [0,1]):
        c+=1
        l.append(i)
'''
print(c)
#print('\n'.join(str(i) for i in l))
c=[tuple(j*255//2 for j in i)
   for i in itertools.product([0,1,2],repeat=3)
   if i not in [(0,0,0),(2,2,2)]]
r=[3,6,7,16,25,1,14,12,17,19,22]
def colors():
    global c,r
    im=Image.new('RGB',(100,100),(255,255,255))
    draw=ImageDraw.Draw(im)
    for x,y in itertools.product(range(5),repeat=2):
        if x+5*y+1 not in r:
            draw.rectangle((x*20,y*20,x*20+19,y*20+19),
                           fill=c[x+5*y],outline=None,width=0)
    im.show()
c_=[i for n,i in enumerate(c,1) if n not in r]
def paint(draw):
    global l
    for x,y in itertools.product(range(10),range(47)):
        n=x+y*10
        border(draw,x,y)
        lines(draw,x,y)
        points(draw,x,y,l[n])
        path(draw,x,y,l[n])
        circles(draw,x,y,l[n])

def border(draw,x,y):
    draw.rectangle((x*110,y*110,x*110+110,y*110+110),
                           fill=None,outline=(0,0,0),width=1)

def lines(draw,x_,y_):
    global c_,x
    for n,c in zip(x,c_):
        #x+y=n*10
        xy=[[max(0,n*10-110),min(n*10,110)],
            [min(n*10,110),max(0,n*10-110)]]
        draw.line(tuple(xy_*110+j for i in xy for j,xy_ in zip(i,[x_,y_])),
                  fill=c,width=1)
    
def points(draw,x,y,l=[]):
    for i,j in itertools.product(range(1,11),repeat=2):
        w=1+((i,j) in l)
        x_,y_=x*110+i*10,y*110+j*10
        draw.ellipse((x_-w,y_-w,x_+w,y_+w),
                     fill=(0,0,0),outline=None,width=0)

def path(draw,x_,y_,l):
    s=set(l)
    while s:
        for x in s:break
        s.discard(x)
        l=[x]
        while True:
            for y in s:
                if any(i==j for i,j in zip(x,y)):
                    break
            else:
                break
            s.discard(y)
            l.append(y)
            x=y
        for i,j in zip(l,l[1:]+l[:1]):
            draw.line(tuple(xy_*110+c*10
                            for k in [i,j]
                            for c,xy_ in zip(k,[x_,y_])
                            ),
                      fill=(0,0,0),width=3)

def circles(draw,x_,y_,l):
    global c_,x
    for i,j in l:
        w=2
        c=c_[x.index(i+j)]
        x0,y0=x_*110+i*10,y_*110+j*10
        draw.ellipse((x0-w,y0-w,x0+w,y0+w),
                     fill=c,outline=None,width=0)

def test():
    global l
    im=Image.new('RGB',(111,111),(255,255,255))
    draw=ImageDraw.Draw(im)
    lines(draw,0,0)
    border(draw,0,0)
    points(draw,0,0,l[0])
    path(draw,0,0,l[0])
    circles(draw,0,0,l[0])
    im.show()
    
#test()

im=Image.new('RGB',(110*10+1,110*47+1),(255,255,255))
draw=ImageDraw.Draw(im)
paint(draw)
im.save('./100996.png','PNG')
im.show()
