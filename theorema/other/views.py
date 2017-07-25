from django.shortcuts import render_to_response
from django.middleware import csrf

def index(request):
    csrf_token = csrf.get_token(request)
    return render_to_response('index.html', {'csrf_token': csrf_token, 'request': request}) #, RequestContext(request))

def login(request):
    csrf_token = csrf.get_token(request)
    return render_to_response('login.html', {'csrf_token': csrf_token, 'request': request}) #, RequestContext(request))


