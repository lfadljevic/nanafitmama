import urllib.request
for name,i in [('img7','379b48_83df78565a4743e0932351394e070d91~mv2'),('img8','379b48_5436eb131f48423b82d9da615f6b4032~mv2')]:
    req=urllib.request.Request(f'https://static.wixstatic.com/media/{i}.png',headers={'User-Agent':'Mozilla/5.0'})
    d=urllib.request.urlopen(req,timeout=60).read()
    open(f'images/o-meni/{name}.png','wb').write(d); print(name,len(d))
