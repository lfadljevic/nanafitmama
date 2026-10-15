import urllib.request,io
from PIL import Image
ids=['34d2fc930b9a4cd4a1ff0953fae87826','0ec0af06375d4541b61440eb5c86403e','bf39ebcacea4475096676be566628278','1d895285025f4097a727b594099938a6','d79f5b1ec5ba4b20ab1335b98bf968c9','f4026d73a00d4b26a38a9d0149c3b178','ca1d24d516a848dc90ada3d64db60d5c','983a4c58e3c844ab94d83e54adc1f2f0']
for n,i in enumerate(ids,9):
    req=urllib.request.Request(f'https://static.wixstatic.com/media/379b48_{i}~mv2.png',headers={'User-Agent':'Mozilla/5.0'})
    d=urllib.request.urlopen(req,timeout=60).read()
    open(f'images/o-meni/img{n}.png','wb').write(d); print(n,len(d),Image.open(io.BytesIO(d)).size,flush=True)
