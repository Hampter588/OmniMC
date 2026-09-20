import json,os,sys,threading,queue,subprocess,shutil,hashlib,zipfile
from pathlib import Path
import tkinter as tk
from tkinter import ttk,messagebox
import requests,auth as msauth,archive as legacyarchive
from platformdirs import user_data_dir
BASE=Path(user_data_dir('OmniMC','OmniMC')); RES=Path(__file__).parent/'resources'; MAN='https://piston-meta.mojang.com/mc/game/version_manifest_v2.json'
VERS=BASE/'versions';LIBS=BASE/'libraries';ASSETS=BASE/'assets';INST=BASE/'instances';SET=BASE/'settings.json';ACC=BASE/'account.json'
for p in (BASE,VERS,LIBS,ASSETS,INST):p.mkdir(parents=True,exist_ok=True)
def rd(p,d):
 try:return json.loads(Path(p).read_text(encoding='utf8'))
 except:return d
def wr(p,x):Path(p).write_text(json.dumps(x,indent=2),encoding='utf8')
def dl(u,p,sha=None):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists() and (not sha or hashlib.sha1(p.read_bytes()).hexdigest()==sha):return
 r=requests.get(u,timeout=90);r.raise_for_status();p.write_bytes(r.content)
def rules(rs):
 if not rs:return True
 cur={'win32':'windows','darwin':'osx'}.get(sys.platform,'linux');ok=False
 for r in rs:
  o=r.get('os',{});applies=not o.get('name') or o.get('name')==cur
  if applies:ok=r.get('action')=='allow'
 return ok
def rep(s,v):
 for k,x in v.items():s=s.replace('${'+k+'}',str(x))
 return s
class Catalog:
 def __init__(self):self.arc=rd(RES/'archive_manifest.json',[]);self.live=[];self.urls={}
 def refresh(self):
  r=requests.get(MAN,timeout=20);r.raise_for_status();d=r.json();self.live=d['versions'];self.urls={x['id']:x['url'] for x in self.live}
 def all(self):
  out=[];seen=set()
  for x in self.live:out.append({'id':x['id'],'type':x['type'],'source':'Mojang'});seen.add(x['id'])
  for x in self.arc:
   if x['id'] not in seen:out.append({**x,'source':'Archive'});seen.add(x['id'])
  return out
class Installer:
 def __init__(self,c,log):self.c=c;self.log=log
 def meta(self,id):
  if id in self.c.urls:
   r=requests.get(self.c.urls[id],timeout=30);r.raise_for_status();return r.json()
  m,u=legacyarchive.get_descriptor(id);self.log('Archive metadata: '+u);return m
 def install(self,id):
  m=self.meta(id);vd=VERS/id;vd.mkdir(parents=True,exist_ok=True);wr(vd/f'{id}.json',m);c=m.get('downloads',{}).get('client')
  if not c:raise RuntimeError('No client download for '+id)
  self.log('Downloading client…');dl(c['url'],vd/f'{id}.jar',c.get('sha1'))
  for l in m.get('libraries',[]):
   if not rules(l.get('rules')):continue
   a=l.get('downloads',{}).get('artifact')
   if a:dl(a['url'],LIBS/a['path'],a.get('sha1'))
  ai=m.get('assetIndex')
  if ai:
   p=ASSETS/'indexes'/f"{ai['id']}.json";dl(ai['url'],p,ai.get('sha1'));idx=rd(p,{})
   for a in idx.get('objects',{}).values():h=a['hash'];dl('https://resources.download.minecraft.net/'+h[:2]+'/'+h,ASSETS/'objects'/h[:2]/h,h)
  return m
class App(tk.Tk):
 def __init__(self):
  super().__init__();self.title('OmniMC 0.4');self.geometry('1150x750');self.configure(bg='#111318');self.ev=queue.Queue();self.c=Catalog();self.items=[]
  self.s=rd(SET,{'java':'','ram':4096,'name':'Player','uuid':'0'*32,'token':'','ms_client_id':'8644f703-4853-42ec-9056-caea21312930'});a=rd(ACC,{})
  if a:self.s.update(name=a.get('name',self.s['name']),uuid=a.get('uuid',self.s['uuid']),token=a.get('access_token',self.s['token']))
  self.ui();self.items=self.c.all();self.filter();self.after(50,self.pump);threading.Thread(target=self.live,daemon=True).start()
 def ui(self):
  style=ttk.Style();style.theme_use('clam');style.configure('Treeview',background='#181b22',fieldbackground='#181b22',foreground='white',rowheight=30);style.configure('Treeview.Heading',background='#20242d',foreground='#9aa4b2');style.configure('TButton',padding=9);style.configure('TEntry',padding=7)
  top=tk.Frame(self,bg='#111318');top.pack(fill='x',padx=20,pady=15);tk.Label(top,text='◈  OMNIMC',bg='#111318',fg='white',font=('Segoe UI Semibold',20)).pack(side='left');self.user=tk.Label(top,text=self.s['name'],bg='#111318',fg='#9aa4b2');self.user.pack(side='right')
  bar=tk.Frame(self,bg='#111318');bar.pack(fill='x',padx=20);self.q=tk.StringVar();self.q.trace_add('write',lambda *_:self.filter());ttk.Entry(bar,textvariable=self.q).pack(side='left',fill='x',expand=True);self.k=tk.StringVar(value='All');cb=ttk.Combobox(bar,textvariable=self.k,state='readonly',values=['All','release','snapshot','experimental','beta','alpha','infdev','indev','classic','pre-classic','other'],width=16);cb.pack(side='left',padx=8);cb.bind('<<ComboboxSelected>>',lambda e:self.filter());ttk.Button(bar,text='Microsoft Login',command=self.login).pack(side='left');ttk.Button(bar,text='Settings',command=self.settings).pack(side='left',padx=(8,0))
  self.status=tk.Label(self,text='Bundled archive loaded; refreshing Mojang…',bg='#111318',fg='#9aa4b2');self.status.pack(anchor='w',padx=20,pady=8)
  box=tk.Frame(self,bg='#181b22');box.pack(fill='both',expand=True,padx=20);self.tree=ttk.Treeview(box,columns=('v','t','s'),show='headings');
  for c,h,w in [('v','VERSION',500),('t','TYPE',170),('s','SOURCE',170)]:self.tree.heading(c,text=h);self.tree.column(c,width=w)
  sb=ttk.Scrollbar(box,command=self.tree.yview);self.tree.configure(yscrollcommand=sb.set);self.tree.pack(side='left',fill='both',expand=True);sb.pack(side='right',fill='y')
  act=tk.Frame(self,bg='#111318');act.pack(fill='x',padx=20,pady=10);ttk.Button(act,text='INSTALL',command=self.install).pack(side='left');ttk.Button(act,text='PLAY',command=self.play).pack(side='left',padx=8)
  self.logbox=tk.Text(self,height=7,bg='#0b0d11',fg='#c8d1dc',relief='flat',font=('Cascadia Mono',9));self.logbox.pack(fill='x',padx=20,pady=(0,15))
 def log(self,x):self.ev.put(('log',str(x)))
 def live(self):
  try:self.c.refresh();self.ev.put(('catalog',self.c.all()))
  except Exception as e:self.ev.put(('log','Mojang refresh failed: '+str(e)))
 def pump(self):
  try:
   while 1:
    t,x=self.ev.get_nowait()
    if t=='log':self.logbox.insert('end',x+'\n');self.logbox.see('end')
    elif t=='catalog':self.items=x;self.filter();self.status.config(text=f'{len(x)} versions • Mojang live + archive')
    elif t=='error':messagebox.showerror('OmniMC',x)
    elif t=='login':self.s.update(name=x['name'],uuid=x['uuid'],token=x['access_token']);wr(ACC,x);self.user.config(text=x['name']);wr(SET,self.s);messagebox.showinfo('OmniMC','Signed in as '+x['name'])
  except queue.Empty:pass
  self.after(50,self.pump)
 def filter(self):
  if not hasattr(self,'tree'):return
  self.tree.delete(*self.tree.get_children());q=self.q.get().lower();k=self.k.get()
  for x in self.items:
   if q in x['id'].lower() and (k=='All' or x.get('type')==k):self.tree.insert('','end',values=(x['id'],x.get('type',''),x.get('source','')))
 def selected(self):
  s=self.tree.selection();return self.tree.item(s[0],'values')[0] if s else None
 def install(self):
  id=self.selected()
  if not id:return
  def f():
   try:Installer(self.c,self.log).install(id);self.log('Installed '+id)
   except Exception as e:self.ev.put(('error',str(e)))
  threading.Thread(target=f,daemon=True).start()
 def login(self):
  def f():
   try:self.ev.put(('login',msauth.login(self.s['ms_client_id'],self.log)))
   except Exception as e:self.ev.put(('error',str(e)))
  threading.Thread(target=f,daemon=True).start()
 def settings(self):
  w=tk.Toplevel(self);w.title('OmniMC Settings');w.configure(bg='#181b22');vars={k:tk.StringVar(value=str(self.s.get(k,''))) for k in ['java','ram','name','uuid','ms_client_id']}
  for i,k in enumerate(vars):tk.Label(w,text=k,bg='#181b22',fg='white').grid(row=i,column=0,sticky='w',padx=12,pady=8);ttk.Entry(w,textvariable=vars[k],width=60).grid(row=i,column=1,padx=12,pady=8)
  def save():
   for k,v in vars.items():self.s[k]=int(v.get()) if k=='ram' else v.get()
   wr(SET,self.s);w.destroy()
  ttk.Button(w,text='Save',command=save).grid(row=len(vars),column=1,sticky='e',padx=12,pady=12)
 def play(self):
  id=self.selected()
  if not id:return
  m=rd(VERS/id/f'{id}.json',None)
  if not m:return messagebox.showinfo('OmniMC','Install this version first.')
  try:
   java=self.s.get('java') or shutil.which('java')
   if not java:raise RuntimeError('Java not found. Set java.exe in Settings.')
   sep=';' if os.name=='nt' else ':';cp=[]
   for l in m.get('libraries',[]):
    if rules(l.get('rules')):
     a=l.get('downloads',{}).get('artifact')
     if a:cp.append(str(LIBS/a['path']))
   cp.append(str(VERS/id/f'{id}.jar'));game=INST/id;game.mkdir(parents=True,exist_ok=True);nat=VERS/id/'natives';nat.mkdir(exist_ok=True)
   v={'auth_player_name':self.s['name'],'version_name':id,'game_directory':game,'assets_root':ASSETS,'assets_index_name':m.get('assetIndex',{}).get('id','legacy'),'auth_uuid':self.s['uuid'],'auth_access_token':self.s.get('token') or '0','user_type':'msa' if self.s.get('token') else 'legacy','version_type':m.get('type','release'),'natives_directory':nat,'launcher_name':'OmniMC','launcher_version':'0.4','classpath':sep.join(cp),'classpath_separator':sep,'library_directory':LIBS}
   cmd=[java,f"-Xmx{self.s.get('ram',4096)}M",f'-Djava.library.path={nat}']
   if m.get('arguments'):
    for a in m['arguments'].get('jvm',[]):
     if isinstance(a,str):cmd.append(rep(a,v))
     elif rules(a.get('rules')):
      z=a['value'] if isinstance(a['value'],list) else [a['value']];cmd += [rep(y,v) for y in z]
    if '-cp' not in cmd and '-classpath' not in cmd:cmd += ['-cp',sep.join(cp)]
    cmd.append(m['mainClass'])
    for a in m['arguments'].get('game',[]):
     if isinstance(a,str):cmd.append(rep(a,v))
     elif rules(a.get('rules')):
      z=a['value'] if isinstance(a['value'],list) else [a['value']];cmd += [rep(y,v) for y in z]
   else:cmd += ['-cp',sep.join(cp),m['mainClass']] + rep(m.get('minecraftArguments',''),v).split()
   self.log('Launching '+id);subprocess.Popen(cmd,cwd=game)
  except Exception as e:messagebox.showerror('Launch failed',str(e))
if __name__=='__main__':App().mainloop()
