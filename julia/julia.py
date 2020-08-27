from PIL import Image, ImageDraw
import itertools
import pickle
import math
X,Y=1000,1000
#X,Y=X//2,Y//2
DX=-1
DY=-1
SX=1.5
SY=1.5
scale_down=lambda x,y:((x/X*2+DX)*SX,(y/Y*2+DY)*SY)
scale_up=lambda x,y:(round((x/SX-DX)/2*X),round((y/SY-DY)/2*Y))
scale_down_3k=(lambda x,y,X=3000,Y=3000,DX=-2+0.472,DY=-1:
               (x/X*2+DX,y/Y*2+DY))
scale_up_3k=(lambda x,y,X=3000,Y=3000,DX=-2+0.472,DY=-1:
             (round((x-DX)/2*X),round((y-DY)/2*Y))
             )
#with open('001_1500.pickle','rb') as fp:
#    cs=pickle.load(fp)
def dot():
    print('.',sep='',end='')

#for n_,(xc,yc) in enumerate(cs):
if True:
#np=200
#x_,y_,r_=2448,557,53
#for n_ in range(np):
#    a=2*math.pi/np*n_
    im=Image.new('RGB',(X,Y),(255,255,255))
    pix=im.load()
    xc,yc=(
    #xc,yc=(-0.08200000000000007, -0.9746666666666667)
    #xc,yc=(-0.03132756286370375, -0.7435054277811728)
    #xc,yc=(-0.908, 0.26766666666666666)
    #xc,yc=(-0.9163333333333333, 0.277)
    #xc,yc=(-0.912, 0.2613333333333333)
    #(-0.915, 0.25583333333333336)
        # (-0.779118059786213, -0.12649273719380208)
        #(-0.65488125,+0.439875)
        #(-0.65488125,-0.439875)
        #(-0.7229,-0.0938124999999995)
        #(-0.740375,-0.092153125)
        ##(-0.7426666666666667, -0.14800000000000002)
        #(0.1439999999999999, -0.652)
        #2448,557,53
        #scale_down_3k(x_+r_*(1+math.cos(a)),y_+r_*(1+math.sin(a)))
        #(-0.06772297977416836,0.665772290516008)
        #(-0.18288940477371218, -0.6525771021842957)
        #(-0.5039979248046875,-0.522308349609375)
        #(-0.20335400390625002,-0.677032470703125)
        #(-0.542678955078125, -0.53106689453125)
        #(-0.77232373046875,-0.121337890625)
        #(-0.19895184326171877,-0.675689697265625)
        #(-0.20376599121093752,-0.6741943359375)
        (-0.20281994628906252,-0.6738128662109375)
    )

    c=complex(xc,yc)
    for i,(x,y) in enumerate(itertools.product(range(X),range(Y))):
        if (i+1)%10000==0:
            dot()
        xy=scale_down(x,y)
        z=complex(*xy)
        n=0
        while abs(z)<10 and n<255:
            z=z**2+c
            n+=1
        pix[x,y]=(255-n,255-n,255)

    im.show()
    #im.save('images/1/%s_%s.png'%(
    #    str(xc).replace('.','_'),
    #    str(yc).replace('.','_')
    #    ),'PNG')
    #dot()

#'123'
#z=z^2+c
#D=1^2-4c
#z=1/2+-sqrt(1-4c)/2
#math.atan2(*((218,316)[::-1])) 0.9668991081574854
#arg(1/2+-sqrt(1-4*z))=0.9668991081574854, 1/2*(1-cos(arg(z-1/4)))=abs(z-1/4)    

#dist=lambda z,ratio=218/316:(k:=[abs(j-ratio) for i in [1+(1-4*z)**0.5,1-(1-4*z)**0.5] if i.real and i.imag for j in (i.real/i.imag,i.imag/i.real)]) and min(k) or 1e6
#cs_=sorted(enumerate(cs),key=lambda x:dist(complex(*(x[1]))))
#print([n for n,i in cs_[:20]])
# [ -0.18620312500000002, -0.654296875, 0.000030517578125, 0.000030517578125, 32768, 43968, 11328 ]
