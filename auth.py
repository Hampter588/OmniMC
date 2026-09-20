import base64, hashlib, json, secrets, socket, time, urllib.parse, webbrowser
from pathlib import Path
import requests

MS_AUTHORIZE='https://login.microsoftonline.com/consumers/oauth2/v2.0/authorize'
MS_TOKEN='https://login.microsoftonline.com/consumers/oauth2/v2.0/token'
XBL='https://user.auth.xboxlive.com/user/authenticate'
XSTS='https://xsts.auth.xboxlive.com/xsts/authorize'
MC_LOGIN='https://api.minecraftservices.com/authentication/login_with_xbox'
MC_PROFILE='https://api.minecraftservices.com/minecraft/profile'
MC_ENT='https://api.minecraftservices.com/entitlements/mcstore'

def b64u(b): return base64.urlsafe_b64encode(b).decode().rstrip('=')

def login(client_id, log=print):
    if not client_id.strip(): raise RuntimeError('Set Microsoft App Client ID in Settings first.')
    verifier=b64u(secrets.token_bytes(48)); challenge=b64u(hashlib.sha256(verifier.encode()).digest()); state=secrets.token_urlsafe(24)
    s=socket.socket(); s.bind(('127.0.0.1',0)); s.listen(1); s.settimeout(180); port=s.getsockname()[1]
    redirect=f'http://localhost:{port}'
    q=urllib.parse.urlencode({'client_id':client_id,'response_type':'code','redirect_uri':redirect,'scope':'XboxLive.signin offline_access','response_mode':'query','code_challenge':challenge,'code_challenge_method':'S256','state':state})
    log('Opening Microsoft sign-in…'); webbrowser.open(MS_AUTHORIZE+'?'+q)
    c,_=s.accept(); line=c.recv(8192).decode('utf8','ignore').splitlines()[0]; target=line.split(' ')[1]
    params=urllib.parse.parse_qs(urllib.parse.urlparse(target).query); body=b'<h2>OmniMC sign-in received. You can close this tab.</h2>'
    c.sendall(b'HTTP/1.1 200 OK\r\nContent-Type:text/html\r\nContent-Length:'+str(len(body)).encode()+b'\r\n\r\n'+body); c.close(); s.close()
    if params.get('state',[''])[0]!=state: raise RuntimeError('OAuth state mismatch')
    if 'error' in params: raise RuntimeError(params.get('error_description',params['error'])[0])
    code=params.get('code',[None])[0]
    t=requests.post(MS_TOKEN,data={'client_id':client_id,'grant_type':'authorization_code','code':code,'redirect_uri':redirect,'code_verifier':verifier,'scope':'XboxLive.signin offline_access'},timeout=30); t.raise_for_status(); ms=t.json()
    log('Microsoft OAuth OK → Xbox Live…')
    r=requests.post(XBL,json={'Properties':{'AuthMethod':'RPS','SiteName':'user.auth.xboxlive.com','RpsTicket':'d='+ms['access_token']},'RelyingParty':'http://auth.xboxlive.com','TokenType':'JWT'},timeout=30); r.raise_for_status(); xbl=r.json(); uhs=xbl['DisplayClaims']['xui'][0]['uhs']
    log('Xbox Live OK → XSTS…')
    r=requests.post(XSTS,json={'Properties':{'SandboxId':'RETAIL','UserTokens':[xbl['Token']]},'RelyingParty':'rp://api.minecraftservices.com/','TokenType':'JWT'},timeout=30)
    if not r.ok: raise RuntimeError(f'XSTS failed {r.status_code}: {r.text}')
    xt=r.json(); log('XSTS OK → Minecraft Services…')
    r=requests.post(MC_LOGIN,json={'identityToken':f"XBL3.0 x={uhs};{xt['Token']}"},timeout=30)
    if not r.ok: raise RuntimeError(f'Minecraft Services failed {r.status_code}: {r.text}\nIf it says Invalid app registration, Microsoft has not authorized this client ID for Minecraft Services.')
    token=r.json()['access_token']
    e=requests.get(MC_ENT,headers={'Authorization':'Bearer '+token},timeout=30); e.raise_for_status()
    if not e.json().get('items'): raise RuntimeError('This account does not appear to own Minecraft Java Edition.')
    p=requests.get(MC_PROFILE,headers={'Authorization':'Bearer '+token},timeout=30); p.raise_for_status(); prof=p.json()
    return {'name':prof['name'],'uuid':prof['id'].replace('-',''),'access_token':token,'refresh_token':ms.get('refresh_token',''),'client_id':client_id,'signed_in_at':int(time.time())}
