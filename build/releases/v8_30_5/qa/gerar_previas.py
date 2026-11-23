"""Gera lâminas axiais de dois fantomas matemáticos e relê os contornos do STUDY."""
import argparse
from datetime import datetime
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

import cv2
import numpy as np
import pydicom
from scipy import ndimage

ROOT = Path(__file__).resolve().parent
STAGE = Path.cwd() / "programa"
PIXEL, DZ = 1.5, 3.0
ROWS, COLS, DEPTH = 210, 286, 27
MID = DEPTH // 2
Z, Y, X = np.ogrid[:DEPTH, :ROWS, :COLS]
X = X - (COLS-1)/2
Y = Y - 106
Z = (Z - MID) * DZ / PIXEL


def ellipse(x, y, rx, ry, angle=0):
    a = np.radians(angle)
    u, v = X-x, Y-y
    return ((u*np.cos(a)+v*np.sin(a))/rx)**2 + ((v*np.cos(a)-u*np.sin(a))/ry)**2


def texture(image, body):
    rng = np.random.default_rng(8305)
    noise = rng.normal(size=image.shape).astype(np.float32)
    soft = ndimage.gaussian_filter(noise, (1.3,2.1,2.1))
    image = ndimage.gaussian_filter(image.astype(np.float32), (.38,.54,.54))
    image += np.where(body, 7*noise + 153*soft, 1.3*noise)
    return np.rint(image).astype(np.int16)


def spine(img, y):
    for val, r in [(725,1.),(155,.86)]:
        part = ellipse(0,y,12*r,9*r) < 1
        np.copyto(img,val,where=np.broadcast_to(part,img.shape))
    for sign in (-1,1):
        for x,cy,r,s,a in [(sign*9,y+8,8,2.7,sign*54),
                             (sign*6,y+15,8,2.4,-sign*38),
                             (sign*16,y+8,10,2.3,-sign*10)]:
            np.copyto(img,490,where=np.broadcast_to(ellipse(x,cy,r,s,a)<1,img.shape))
    np.copyto(img,430,where=np.broadcast_to(ellipse(0,y+21,2.2,6)<1,img.shape))


def thorax():
    left = ellipse(61,-46+0.09*Z,43,29,-14) + (Z/84)**2 - 1
    right = ellipse(-62,-46+0.09*Z,44,28,14) + (Z/85)**2 - 1
    breast_l,breast_r = left<0,right<0
    trunk = ellipse(0,4,117,61.5) +(Z/180)**2 - 1
    body = np.logaddexp(-6.5*trunk, -6.5*np.minimum(left,right)) > 0
    image = np.where(body, -92, -995).astype(np.float32)
    image[ellipse(0,4,108,54)+(Z/180)**2<1] = 41
    skin=body & ~ndimage.binary_erosion(body, structure=np.ones((1,3,3)))
    image[skin]=16
    heart = ellipse(13,-9+Z*.12,33,36, -31) + ((Z+2)/58)**2 < 1
    # The mediastinal surfaces of both lungs follow the heart.
    lungs = {}
    for sign,side in [(-1,"right"),(1,"left")]:
        rim = ellipse(sign*51,3+Z*.045,48,49,-sign*8) + (Z/128)**2
        lung = (rim<1) & (ellipse(sign*4,-5+Z*.09,32+(9 if sign==1 else 0),39,-24)+(Z/62)**2>1)
        lung &= ~heart
        upper = lung & (Y < 8 + sign*.19*(X-sign*48) + .48*Z)
        lungs["lung_upper_lobe_"+side]=upper
        lungs["lung_lower_lobe_"+side]=lung & ~upper
        image[lung]=-808
        # Obliquely cut, tapering bronchovascular branches towards the pleura.
        for k in range(DEPTH):
            branches=np.zeros((ROWS,COLS),np.uint8)
            rng=np.random.default_rng(1883+(sign+1))
            for i,t in enumerate(np.linspace(-1.6,1.5,6)):
                root=np.array([COLS/2+sign*(34+2*i),104+i*2.9+3*np.sin(k*.12+i)])
                stem=root+[sign*(4+i*.7),12*np.sin(t)]
                cv2.line(branches,tuple(root.astype(int)),tuple(stem.astype(int)),1,2)
                for branch in (-1,1):
                    angle=t+branch*.33
                    mid=stem+[sign*16*np.cos(angle),15*np.sin(angle)]
                    cv2.line(branches,tuple(stem.astype(int)),tuple(mid.astype(int)),1,1)
                    for bifurc in (-1,1):
                        ang=angle+bifurc*.44
                        end=mid+[sign*12*np.cos(ang),12*np.sin(ang)]
                        cv2.line(branches,tuple(mid.astype(int)),tuple(end.astype(int)),1,1)
            for i in range(135):
                xx=int(COLS/2+sign*rng.uniform(18,96)+2*np.cos(k*.17+i)); yy=int(rng.uniform(65,150)+2*np.sin(k*.2+i))
                cv2.ellipse(branches,(xx,yy),(1+i%2,1),i*23,0,360,1,-1)
            image[k][lung[k] & (branches!=0)] = -300
    image[heart]=57
    image[(ellipse(8,-11,22,23,-27)+(Z/47)**2 <1)&heart] = 39
    breasts={}
    for side,sgn,breast in [("left",1,breast_l),("right",-1,breast_r)]:
        pectoral=ellipse(sgn*59,-39+.04*Z,37,3.7,-sgn*16)+(Z/100)**2<1
        image[pectoral & body]=54
        gland=breast & (ellipse(sgn*64,-54+.06*Z,28,18,-sgn*12)+(Z/70)**2 <
               .85+.09*np.sin(X*.23+Y*.19)+.045*np.cos(Z*.35+Y*.31))
        breasts["breast_"+side]=gland
        image[gland]=12+16*np.sin((X+Y)*.43+Z*.12)[gland]
        for ang in np.linspace(-1.22,1.22,8):
            bx,by=sgn*105*np.cos(ang),4+55*np.sin(ang)
            rib=ellipse(bx,by+2*np.sin(Z*.16+ang*2),7,2.8,sgn*np.degrees(ang)+90)+(Z/115)**2
            image[rib<1]=650
            image[rib<.52]=170
    spine(image,36)
    np.copyto(image,580,where=np.broadcast_to(ellipse(0,-50,10,2.5)<1,image.shape))
    return texture(image,body), {"total":{"heart":heart,**lungs},"breasts":{"breast":breasts["breast_left"]|breasts["breast_right"]}}, breasts


def bowel():
    wall = ellipse(0,0,116,67)+(Z/190)**2 < 1
    cav = (ellipse(0,-4,92,50)+(Z/150)**2 <
           1+.018*np.sin(X*.12+Y*.07)+.010*np.cos(Y*.23+Z*.12))
    posterior = ellipse(0,34,26,18)+(Z/108)**2<1
    cav &= ~posterior
    img=np.where(wall,-99,-995).astype(np.float32)
    muscle=ellipse(0,0,103,58)+(Z/180)**2<1
    img[muscle]=44
    img[cav]=-86
    loops=np.zeros_like(cav)
    for i in range(5):
        for j in range(3):
            x=-58+i*28+6*np.cos(j+i+Z*.04)
            y=-24+j*20+5*np.sin(i*1.45+j+Z*.047)
            dist=ellipse(x,y,12+3.8*np.sin(i+j),7+2.4*np.cos(i-j),37*np.sin(i+j*.8)+Z*.4)
            m=(dist<1)&cav
            img[m]=43
            inner=(dist<.62)&cav
            img[inner]=-610 if (i+2*j)%4==1 else 9
            loops |= m
    # Psoas contours, paraspinal musculature, vertebra and subcutaneous fat.
    for side in (-1,1):
        psoas=ellipse(side*23,27,12,17,-side*18)+(Z/110)**2<1
        img[psoas]=47
        cav &= ~psoas
        img[(ellipse(side*27,47,18,11,side*12)+(Z/130)**2)<1]=46
    spine(img,27)
    img[(ellipse(3,10,5,5.6)+(Z/116)**2)<1]=68
    img[(ellipse(-9,12,6.3,4)+(Z/116)**2)<1]=47
    return texture(img,wall),{"total":{"small_intestine":loops&cav},"trunk_cavities":{"abdominal_cavity":cav}},None


def desenhar(hu,ds,k,sample):
    scale=3
    lo,hi=(-820,405) if sample=="thorax" else (-184,227)
    gray=np.rint(np.clip((hu[k].astype(float)-lo)/(hi-lo),0,1)*255).astype("uint8")
    rgb=cv2.cvtColor(cv2.resize(gray,None,fx=scale,fy=scale,interpolation=cv2.INTER_CUBIC),cv2.COLOR_GRAY2BGR)
    names={int(r.ROINumber):str(r.ROIName) for r in ds.StructureSetROISequence}
    wanted=({"heart":(108,130,255),"lung":(241,206,82),"breast":(153,194,252)}
            if sample=="thorax" else {"bag_bowel_oar":(97,209,237)})
    hits={}
    for rc in ds.ROIContourSequence:
        key=names[int(rc.ReferencedROINumber)].lower()
        category=next((s for s in wanted if key.startswith(s)),None)
        if not category or (category=="lung" and key.split("_")[1] not in ("l","r")): continue
        for c in rc.ContourSequence:
            points=np.asarray(c.ContourData,float).reshape(-1,3)
            if abs(points[0,2]-k*DZ)>.05: continue
            xy=points[:,:2]/PIXEL+np.array([COLS/2,ROWS/2])
            pixel=np.rint(((xy+.5)*scale-.5)*16).astype(np.int32)
            cv2.polylines(rgb,[pixel],True,wanted[category],2,cv2.LINE_AA,4)
            hits[key]=hits.get(key,0)+len(xy)
    if {s for s in wanted if any(n.startswith(s) for n in hits)}!=set(wanted):
        raise RuntimeError(f"Estrutura ausente: {hits}. Entregues: {list(names.values())}")
    # Same zoom, slice, LUT, and colors for every level. Crop only the margins.
    view=rgb[(20 if sample=="thorax" else 30)*scale:178*scale,17*scale:269*scale]
    _,buf=cv2.imencode(".png",view,[cv2.IMWRITE_PNG_COMPRESSION,9])
    return buf.tobytes(),hits


def main():
    global STAGE
    ap=argparse.ArgumentParser()
    ap.add_argument("--prova",action="store_true",help="Verifica a estação de imagens usando o perfil padrão.")
    ap.add_argument("--programa",type=Path,default=STAGE,help="Pasta programa do SETUP extraído")
    args=ap.parse_args()
    STAGE=args.programa.resolve()
    sys.path[:0]=[str(STAGE/"app"),str(STAGE/"tools")]
    import engine, make_test_series as make
    from radai_output import Saida
    out=ROOT if args.prova else STAGE/"app/data/fast_previews"
    out.mkdir(exist_ok=True,parents=True)
    report={}
    with tempfile.TemporaryDirectory(prefix="suite-fantomas-") as tmp:
        temp=Path(tmp)
        env={"RADAI_CONFIG":str(temp/"config"),"RADAI_CALIB_DIR":str(temp/"calib"),"RADAI_REGISTRO_DIR":str(temp/"registro")}
        with patch.dict(os.environ,env):
            for kind,gen in [("thorax",thorax),("bowel",bowel)]:
                hu,raw,cads=gen()
                serie=temp/kind
                with patch.multiple(make, ROWS=ROWS, COLS=COLS, PIXEL_MM=PIXEL, THICK_MM=DZ, fatia=lambda i,n: hu[i]):
                    make.escreve_serie(serie,"SYNTHETIC",datetime(2026,1,1),DEPTH)
                for level in ([2] if args.prova else range(5)):
                    dst=temp/("out-"+kind+str(level))
                    dst.mkdir()
                    saida=Saida(engine,serie,dst,"RS_GEOMETRIA.dcm",tasks=tuple(raw),modalidade="CT")
                    kw={} if args.prova else {"fast_nivel":level}
                    # trabalhar sempre em máscaras independentes: o pipeline aceita vistas mutáveis.
                    inputs={t:{n:m.copy() for n,m in rows.items()} for t,rows in raw.items()}
                    resposta=saida.full_e_oar(inputs,volume_hu=hu,cads=cads,modo="perso" if kind=="thorax" else "auto",
                        acabamento="fast" if kind=="thorax" else "padrao",regioes=("torax",) if kind=="thorax" else ("abdome","pelve"),
                        arcos_costais_moose=False,reto_jhu=False,coronaria_rocards=False,**kw)
                    ds=pydicom.dcmread(resposta["oar"])
                    doc=pydicom.dcmread(serie/("CT_%04d.dcm"%(MID+1)))
                    assert np.array_equal(hu[MID],doc.pixel_array)
                    pic,hits=desenhar(hu,ds,MID,kind)
                    name=f"{kind}-{level}.png"
                    (out/name).write_bytes(pic)
                    report[name]={"points":hits,"sha256":sha256(pic).hexdigest(),"slice":MID+1}
                    print(name,hits,flush=True)
    (ROOT/("verificacao-fantomas"+("-prova" if args.prova else "")+".json")).write_text(json.dumps(report,indent=2),encoding="utf-8")


if __name__=="__main__":main()
