from twisted.internet.protocol import Protocol, Factory
from twisted.internet.endpoints import TCP4ServerEndpoint
from twisted.internet import reactor
import random
import datetime
import json

j = {"archiveEndHint":"/dummy/dummy.mp4","archiveStartHint":"/dummy/dummy.mp4","confidence":29,"end_timestamp":-10800000,"file_offset_sec":0,"id":300,"isStarted":True,"reaction":"-1","start_timestamp":1543396153520,"type":1}

class DummyCam(Protocol):
    def connectionMade(self):
        self.send_event()

    def send_event(self):
        j['id'] = random.randrange(100000)
        j['start_timestamp'] = int(datetime.datetime.now().timestamp() * 1000)
        print('sending', j, flush=True)
        self.transport.write(json.dumps(j).encode())
        reactor.callLater(2, self.send_event)


class DummyCamFactory(Factory):
    def buildProtocol(self, addr):
        return DummyCam()

reactor.listenTCP(21200, DummyCamFactory())
reactor.run()
