import json,sys,os,io,urllib.request
from PIL import Image
ids=json.load(open('scripts/gallery_ids.json'))
out='images/galerija'; os.makedirs(out,exist_ok=True)
res=[]
for n,i in enumerate(ids,1):
    path=f'{out}/galerija-{n:02d}.jpg'
    if n<=25 and os.path.exists(path):
        im=Image.open(path)
    else:
        req=urllib.request.Request(f'https://static.wixstatic.com/media/{i}.jpg',headers={'User-Agent':'Mozilla/5.0'})
        data=urllib.request.urlopen(req,timeout=60).read()
        open(path,'wb').write(data)
        im=Image.open(io.BytesIO(data))
    res.append({'n':n,'id':i,'w':im.width,'h':im.height,'fmt':im.format})
    print(n,i,im.width,im.height,im.format,flush=True)
json.dump(res,open('scripts/gallery_dims.json','w'),indent=1)
