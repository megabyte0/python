from fractions import Fraction as R
#from PIL import Image, ImageDraw
import itertools
import random
points=[[226,21],[291,406],[10,211],[343,110],[168,437],[42,102],[122,20],[378,334],[40,330]]
lines=[(a+c,b+c) for a,b in [(0,1),(1,2),(2,0)] for c in [0,3,6]]
##im=Image.new('RGB',tuple(
##    max(i[j] for i in points)+10
##    for j in [0,1]),(255,255,255))
##draw = ImageDraw.Draw(im)
##for i,j in lines:
##    draw.line(tuple(points[i]+points[j]),fill=(0,0,0))
##im.show()
d_=dict()
def intersection(i,j):
    if (i,j) in d_:
        return d_[(i,j)]
    a,b,c,d,e,f,g,h=[R(x)
        for k in lines[i]+lines[j]
        for x in points[k]
        ]
    #al:=(1-u)*{a,b}+u*{c,d};
    #bl:=(1-v)*{e,f}+v*{g,h};
    if (d*(e - g) + b*(-e + g) + (a - c)*(f - h))==R(0):
        return None
    u=-((-(b*e) + a*f + b*g - f*g - a*h + e*h)/(b*e - d*e - a*f + c*f - b*g + d*g + a*h - c*h))
    v=-((-(b*c) + a*d + b*e - d*e - a*f + c*f)/(-(b*e) + d*e + a*f - c*f + b*g - d*g - a*h + c*h))
    if not (0<=u<=1) or not (0<=v<=1):
        d_[(i,j)]=None
        return None
    d_[(i,j)]=True
    return True#((-(c*f*g) + b*c*(-e + g) + c*e*h + a*(d*e - d*g + f*g - e*h))/(d*(e - g) + b*(-e + g) + (a - c)*(f - h)), (d*(-(f*g) + a*(f - h) + e*h) + b*(f*g - e*h + c*(-f + h)))/(d*(e - g) + b*(-e + g) + (a - c)*(f - h)))

##intersections=[
##    frozenset([i,j])
##    for i,j in itertools.combinations(range(len(lines)),2)
##    if intersection(i,j)
##    ]
##
triangles=lambda:[
    frozenset(list(x))
    for x in itertools.combinations(range(len(lines)),3)
    if all(intersection(i,j)
           for i,j in itertools.combinations(x,2)
           )
    ]
m=0
for i in range(int(1e5)):
    d_=dict()
    points=[[random.randrange(0,100) for j in [0,1]]
            for i in range(9)]
    if (k:=len(set(triangles())))>m:
        m=k
        mi=points
        print(i,m)
