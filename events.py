import os
import sys
import json
import datetime

from twisted.internet import reactor, protocol, defer, task, defer
from twisted.python import log
from autobahn.twisted.websocket import WebSocketServerProtocol, WebSocketServerFactory
from autobahn.websocket.types import ConnectionDeny



os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'theorema.settings')
import django
django.setup()
from django.http.cookie import parse_cookie
from django.contrib.sessions.models import Session
from django.contrib.auth.models import User
from django.conf import settings

from theorema.cameras.models import *


class WSP(WebSocketServerProtocol):
    user = None
    cameras = set()

    def check_origin(self, origin):
        if origin not in settings.allowed_hosts:
            raise ConnectionDeny(404)

    def check_auth(self, cookie):
        session_key = cookie.get(settings.SESSION_COOKIE_NAME, '')
        try:
            session = Session.objects.get(session_key=session_key)
            user_id = session.get_decoded().get('_auth_user_id')
            self.user = User.objects.get(id=user_id, is_active=True)
        except:
            raise ConnectionDeny(403)

    def onConnect(self, request):
        origin = request.headers.get('origin', '')
#        self.check_origin(origin)
        cookie = parse_cookie(request.headers.get('cookie', ''))
#        self.check_auth(cookie)
        return super().onConnect(request)

    def onOpen(self):
        self.factory.connections_list.append(self)
        self.factory.pings_lost[self.peer] = 0
        print('opened', self.factory.connections_list)
        self.run = True
        self.doPing()

    def onMessage(self, payload, isBinary):
        print('user incoming', payload, flush=True)
        message = json.loads(payload.decode())
        if 'subscribe' in message:
            self.cameras = set(message['subscribe'])
            print('subscribe ok', flush=True)
        if 'reaction' in message:
            server_address = Camera.objects.get(id=int(message['camera_id'].split('_')[0])).server.address
            if server_address in worker_servers:
                worker_servers[server_address].transport.write(payload)
                print('reaction sent to worker server', flush=True)
        if 'quad_id' in message:
            quad = Quadrator.objects.filter(id=message['quad_id']).first()
            if quad:
                if not quad.is_active:
                    not_started = os.system('supervisorctl start quad' + str(quad.id))
                    if not_started:
                        print(not_started, flush=True)
                        print('quad' + str(quad.id), 'did not start', flush=True)
                    else:
                        quad.is_active = True
                        print('quad' + str(quad.id), 'started', flush=True)
                quad.last_ping_time = datetime.datetime.now().timestamp()
                quad.save()
            try:
                for c in factory.connections_list:
                    print('sending pong', flush=True)
                    c.sendMessage(payload, False)
                    print('sent pong', flush=True)
            except:
                print('fail in pong', flush=True)
        return

    def doPing(self):
        if self.run:
            if self.factory.pings_lost[self.peer] >= 3:
                print('closing due to timeout')
                self.sendClose()
            else:
                self.sendPing()
                self.factory.pings_lost[self.peer] += 1
                reactor.callLater(20, self.doPing)

    def onPong(self, payload):
        self.factory.pings_lost[self.peer] = 0

    def onClose(self, wasClean, code, reason):
        self.run = False
        self.factory.connections_list.remove(self)
        self.factory.pings_lost.pop(self.peer, None)


class ServerListener(protocol.Protocol):
    def connectionMade(self):
        peer = self.transport.getPeer()
        worker_servers[peer.host] = self # port?

    def dataReceived(self, data):
        print('server incoming', data, flush=True)
        message = json.loads(data.decode())
        for c in factory.connections_list:
            print(c.cameras, message['camera_id'], message['camera_id'] in c.cameras, flush=True)
            if message['camera_id'] in c.cameras:
                print('sending...', flush=True)
                c.sendMessage(data, False)
                print('sended', flush=True)


class ServerListenerClientFactory(protocol.ReconnectingClientFactory):
    def buildProtocol(self, addr):
        self.resetDelay()
        return ServerListener()


log.startLogging(sys.stdout)
factory = WebSocketServerFactory('ws://127.0.0.1:8077')
factory.protocol = WSP
factory.setProtocolOptions(maxConnections=1000)
factory.connections_list = []
factory.pings_lost = {}

reactor.listenTCP(8077, factory)

worker_servers = dict()

for server in Server.objects.all():
    print('server', server.address)
    reactor.connectTCP(server.address, 5006, ServerListenerClientFactory())

reactor.run()
