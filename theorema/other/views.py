import requests
import json
from django.shortcuts import render_to_response
from django.middleware import csrf
from django.http import JsonResponse
from theorema.cameras.models import Server

def index(request):
    csrf_token = csrf.get_token(request)
    return render_to_response('index.html', {'csrf_token': csrf_token, 'request': request})

def login(request):
    csrf_token = csrf.get_token(request)
    return render_to_response('login.html', {'csrf_token': csrf_token, 'request': request})

def video(request):
    csrf_token = csrf.get_token(request)
    return render_to_response('video.html', {'csrf_token': csrf_token, 'request': request})

def stat(request):
    server = Server.objects.get(id=request.GET['server'])
    try:
        return JsonResponse(json.loads(requests.get('http://{}:5005/stat'.format(server.address)).content.decode()))
    except Exception as e:
        return JsonResponse({'status': 1, 'message': str(e)})
