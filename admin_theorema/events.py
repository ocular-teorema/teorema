import time
import os
import json
import configparser
from functools import partial

from twisted.internet.protocol import Protocol, ReconnectingClientFactory, Factory
from twisted.internet import reactor
from twisted.internet.endpoints import TCP4ServerEndpoint

from settings import *

config = configparser.ConfigParser()
config.read(SUPERVISOR_CAMERAS_CONF)
raw_cams =[{'id': int(k[len('program:cam'):]), 'directory': v['directory']} for k,v in config.items() if k.startswith('program:cam')]

cams = []
for c in raw_cams:
    cam_config = configparser.ConfigParser()
    cam_config.read(os.path.join(c['directory'], 'theorem.conf'), 'utf-8')
    try:
        c['port'] = int(cam_config['General']['Port'])
    except:
        print('cam %s ignored due to config error' % c['id'])
    else:
        cams.append(c)
print(cams)


class CamListener(Protocol):
    camera_id = None

    def __init__(self, camera_id):
        self.camera_id = camera_id

    def dataReceived(self, data):
        print(self.camera_id, data, flush=True)
        [x for x in cams if x['id'] == self.camera_id][0]['connection'] = self # kill me
        try:
            j = json.loads(data.strip(b'\0').decode())
            j['camera_id'] = self.camera_id
        except json.decoder.JSONDecodeError:
            pass
        else:
            if sender:
                sender.transport.write(json.dumps(j).encode())
                print('sent', flush=True)


class CamListenerClientFactory(ReconnectingClientFactory):
    camera_id = None

    def __init__(self, camera_id):
        self.camera_id = camera_id

    def buildProtocol(self, addr):
        self.resetDelay()
        return CamListener(camera_id=self.camera_id)


sender = None

class CamSender(Protocol):
    def __init__(self):
        print('new connection from admin server', flush=True)
        global sender
        sender = self

    def dataReceived(self, data):
        print('data received from admin server', data, flush=True)
        j = json.loads(data.decode())
        if 'reaction' in j:
            camera_id = j.pop('camera_id')
            [x for x in cams if x['id'] == camera_id][0]['connection'].transport.write(json.dumps(j).encode()) # kill me 2
            print('reaction sent to camera', camera_id, flush=True)


class CamSenderFactory(Factory):
    def buildProtocol(self, addr):
        print(addr.host)
#        if addr.host not in (ADMIN_ADDR, '127.0.0.1', '10.0.2.2'):
#            print('connect dropped')
#            return None
        return CamSender()



reactor.listenTCP(5006, CamSenderFactory())
time.sleep(1)
for c in cams:
     reactor.connectTCP('localhost', c['port'], CamListenerClientFactory(c['id']))




reactor.run()
