import os
import tempfile
os.environ['DATABASE_PATH']=tempfile.mktemp(suffix='.sqlite3')
from fastapi.testclient import TestClient
from server import app

def test_two_analysts_sync_and_reconnect():
    with TestClient(app) as client:
        key=client.post('/api/rooms').json()['room']
        with client.websocket_connect('/ws/'+key+'?name=Ali') as a:
            assert a.receive_json()['state']['revision']==0
            with client.websocket_connect('/ws/'+key+'?name=Omar') as b:
                a.receive_json()
                assert b.receive_json()['participants']==['Ali','Omar']
                for action in [dict(type='move',id='ball',x=72,y=24),dict(type='arrow',x=10,y=20,x2=40,y2=70),dict(type='chat',text='Press here'),dict(type='rename',id='a0',name='Captain')]:
                    a.send_json(action)
                    assert a.receive_json()['state']==b.receive_json()['state']
                b.send_json(dict(type='move',id='a0',x=35,y=80))
                assert a.receive_json()['state']==b.receive_json()['state']
                b.send_json(dict(type='move',id='missing',x=3,y=4))
                assert b.receive_json()['type']=='error'
            a.receive_json()
        with client.websocket_connect('/ws/'+key) as c:
            state=c.receive_json()['state']
            assert state['ball']=={'x':72,'y':24}
            assert state['players'][0]['name']=='Captain'
            assert state['players'][0]['x']==35
            assert len(state['arrows'])==1
            assert state['messages'][0]['text']=='Press here'

def test_origin_rejected():
    from starlette.websockets import WebSocketDisconnect
    import pytest
    with TestClient(app) as client:
        key=client.post('/api/rooms').json()['room']
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect('/ws/'+key,headers={'origin':'https://untrusted.example'}): pass
