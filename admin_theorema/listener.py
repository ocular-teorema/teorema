import os
from flask import Flask, request
from flask_restful import Resource, Api

from settings import *

app = Flask(__name__)
api = Api(app)

class Cam(Resource):
    def post(self):
        req = request.get_json()
        cam_path = os.path.join(CAMDIR, 'cam'+str(req['id']))
        try:
            os.makedirs(os.path.join(cam_path, DBDIR))
        except Exception as e:
            return {'status': 1, 'message': str(e)}
        return {}

api.add_resource(Cam, '/')

if __name__ == '__main__':
    app.run(debug=True)
