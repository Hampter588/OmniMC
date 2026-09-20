import urllib.parse, requests
BASE='https://files.betacraft.uk/launcher/v2/assets/jsons/{name}.json'
ALIASES={'b1.0.2':'b1.0.2-0841','b1.2_02-20110517':'b1.2_02-dev-20110517','b1.3-pcgamer':'b1.3-demo','b1.8-pre1-091358':'b1.8-pre-091357','b1.8-pre1-081459':'b1.8-pre-081459'}
def get_descriptor(version):
    names=[]
    if version in ALIASES:names.append(ALIASES[version])
    names.append(version)
    errors=[]
    for name in dict.fromkeys(names):
        url=BASE.format(name=urllib.parse.quote(name,safe='._-'))
        try:
            r=requests.get(url,timeout=25)
            if r.ok:return r.json(),url
            errors.append(f'{name}: HTTP {r.status_code}')
        except Exception as e: errors.append(f'{name}: {e}')
    raise RuntimeError('No surviving legacy descriptor found for '+version+'\n'+'\n'.join(errors))
