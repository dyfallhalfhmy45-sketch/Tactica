"""Tactica: single-process authoritative collaboration server."""
import asyncio
import json
import math
import os
import re
import secrets
import sqlite3
import time
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

ROOT = Path(__file__).parent
DB = os.getenv('DATABASE_PATH', str(ROOT / 'rooms.sqlite3'))
app = FastAPI(title='Tactica')
app.add_middleware(CORSMiddleware, allow_origins=[o for o in os.getenv('ALLOWED_ORIGINS','').split(',') if o], allow_methods=['POST','GET'], allow_headers=['Content-Type'])
rooms = {}
lock = asyncio.Lock()

def database():
    db = sqlite3.connect(DB)
    db.execute('CREATE TABLE IF NOT EXISTS rooms (id TEXT PRIMARY KEY, state TEXT NOT NULL)')
    return db

def initial():
    formation = [(7,50),(24,15),(24,38),(24,62),(24,85),(42,24),(37,50),(42,76),(61,18),(65,50),(61,82)]
    return {'players': [{'id': f'{team}{i}', 'x': x if team=='a' else 100-x, 'y': y, 'team':team, 'number':i+1, 'name':''} for team in ('a','b') for i,(x,y) in enumerate(formation)], 'ball': {'x':50,'y':50}, 'arrows':[], 'messages':[], 'revision':0}

def persist(key, state):
    with database() as db:
        db.execute('INSERT OR REPLACE INTO rooms VALUES (?,?)', (key,json.dumps(state)))

def get_room(key):
    if key not in rooms:
        with database() as db:
            row = db.execute('SELECT state FROM rooms WHERE id=?',(key,)).fetchone()
        if not row: return None
        rooms[key] = {'state':json.loads(row[0]), 'clients':{}}
    return rooms[key]

def coordinate(value):
    if isinstance(value,bool) or not isinstance(value,(float,int)) or not math.isfinite(value): raise ValueError()
    return max(2,min(98,value))

def apply(state, data, name):
    kind = data.get('type')
    if kind == 'move':
        obj = state['ball'] if data.get('id')=='ball' else next((p for p in state['players'] if p['id']==data.get('id')),None)
        if obj is None: raise ValueError()
        x,y=coordinate(data.get('x')),coordinate(data.get('y'))
        obj.update(x=x,y=y)
    elif kind == 'arrow':
        if len(state['arrows']) >= 150: raise ValueError()
        arrow = {k:coordinate(data.get(k)) for k in ('x','y','x2','y2')}
        arrow['id']=secrets.token_hex(8)
        state['arrows'].append(arrow)
    elif kind == 'clear': state['arrows']=[]
    elif kind == 'rename':
        player=next((p for p in state['players'] if p['id']==data.get('id')),None)
        if player is None: raise ValueError()
        player['name']=str(data.get('name','')).strip()[:24]
    elif kind == 'chat':
        message=str(data.get('text','')).strip()[:500]
        if not message: raise ValueError()
        state['messages']=(state['messages']+[{'name':name,'text':message}])[-100:]
    else: raise ValueError()
    state['revision'] += 1

@app.get('/api/health')
def health(): return {'ok':True}

@app.post('/api/rooms')
async def create_room():
    async with lock:
        with database() as db:
            count=db.execute('SELECT COUNT(*) FROM rooms').fetchone()[0]
        if count >= int(os.getenv('MAX_ROOMS','1000')): raise HTTPException(503,'Room capacity reached')
        key=secrets.token_urlsafe(18)
        persist(key,initial())
        return {'room':key}

async def broadcast(room):
    payload={'type':'state','state':room['state'],'participants':list(room['clients'].values())}
    dead=[]
    for client in tuple(room['clients']):
        try: await asyncio.wait_for(client.send_json(payload),2)
        except Exception: dead.append(client)
    for client in dead: room['clients'].pop(client,None)

@app.websocket('/ws/{key}')
async def socket(ws:WebSocket,key:str):
    origin=ws.headers.get('origin','')
    allowed=os.getenv('ALLOWED_ORIGINS','').split(',')
    same=origin in ('http://'+ws.headers.get('host',''),'https://'+ws.headers.get('host',''))
    if origin and not same and origin not in allowed:
        await ws.close(code=1008); return
    if not re.fullmatch(r'[A-Za-z0-9_-]{24}',key):
        await ws.close(code=1008); return
    async with lock:
        room=get_room(key)
        if room is None or len(room['clients'])>=20:
            await ws.close(code=1008); return
        await ws.accept()
        room['clients'][ws]=(ws.query_params.get('name','Analyst').strip() or 'Analyst')[:30]
        await broadcast(room)
    window=time.monotonic(); events=0
    try:
        while True:
            raw=await ws.receive_text()
            if len(raw)>4096: await ws.close(code=1009); break
            now=time.monotonic()
            if now-window>1: window=now; events=0
            events+=1
            if events>50: await ws.close(code=1008); break
            try:
                data=json.loads(raw)
                if not isinstance(data,dict): raise ValueError()
                async with lock:
                    apply(room['state'],data,room['clients'][ws])
                    persist(key,room['state'])
                    await broadcast(room)
            except (ValueError,TypeError): await ws.send_json({'type':'error','message':'Invalid operation'})
    except WebSocketDisconnect: pass
    finally:
        async with lock:
            room['clients'].pop(ws,None)
            await broadcast(room)
            if not room['clients']: rooms.pop(key,None)

app.mount('/',StaticFiles(directory=ROOT/'static',html=True),name='static')
