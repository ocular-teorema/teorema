import os
from subprocess import Popen, PIPE
from flask import Flask, request
from flask_restful import Resource, Api


from settings import *

app = Flask(__name__)
api = Api(app)


def get_cam_path(req):
    return os.path.join(CAMDIR, 'cam'+str(req['id']))


def get_filesystem_info():
        # man df
        return Popen(['df', ARCHDIR], stdout=PIPE).communicate()[0].decode().split()[-5:-2]


class Cam(Resource):
    def post(self):
        req = request.get_json()
        cam_path = get_cam_path(req)
        try:
            os.makedirs(os.path.join(cam_path, DBDIR))
            f = open(os.path.join(cam_path, CONFIG_NAME), 'w')
            # TODO: recode config to processInstace-compatible
            # TODO: create additional config to save run/stop status
            f.write('\n'.join(['{}={}'.format(k, v) for k, v in req.items()]))
            f.close()
            # TODO: create VideoArchive directory
        except Exception as e:
            return {'status': 1, 'message': str(e)}
        return {'status': 0}

    def delete(self):
        req = request.get_json()
        cam_path = get_cam_path(req)
        try:
            # TODO: stop camera
            os.removedirs(cam_path)
        except Exception as e:
            return {'status': 1, 'message': str(e)}
        return {'status': 0}

    def patch(self):
        req = request.get_json()
        cam_path = get_cam_path(req)
        # stop cam
        try:
            f = open(os.path.join(cam_path, CONFIG_NAME), 'w')

            f.close()
        except Exception as e:
            return {'status': 1, 'message': str(e)}
        # start cam
        return {'status': '0'}

class Stat(Resource):
    def get(request):
        try:
            return {
                'message': get_filesystem_info(),
                'status': 0
            }
        except Exception as e:
            return {'status': 1, 'message': str(e)}
            

api.add_resource(Cam, '/')
api.add_resource(Stat, '/stat')

if __name__ == '__main__':
    app.run(debug=True)
