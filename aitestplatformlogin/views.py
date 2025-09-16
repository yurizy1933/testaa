from django.shortcuts import render
from django.contrib.auth import authenticate, login

# Create your views here.
from django.contrib.auth import login,authenticate
from django.contrib.sessions.models import Session
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse,HttpResponse,StreamingHttpResponse
import json

@require_http_methods('POST')
def aiplatform_login(request):
    req = {}
    data = json.loads(request.body)
    user = data.get('username')
    password = data.get('password')
    if not user:
        req['code'] = 10043
        req['msg'] = 'no user'
        return JsonResponse(req, status=400)
    if not password:
        req['code'] = 10042
        req['msg'] = 'no password'
        return JsonResponse(req, status=400)
    user_obj = authenticate(username=user, password=password)
    if not user_obj:
        req['code'] = 10044
        req['msg'] = 'wrong password'
        return JsonResponse(req, status=400)
    try:
        login(request, user_obj)
        req['code'] = 0
        req['msg'] = ('success')
    except Exception as e:
        req['code'] = 10005
        req['msg'] = (str(e))
    return JsonResponse(req, status=200)

@require_http_methods('GET')
def is_ok_request(request):
    res = []
    session = request.session
    session = Session.objects.get(pk=session['id'])
    if not session:
        res['code'] =1001
        res['msg'] = ('no session')
        return JsonResponse(res, status=401)
    res['code'] = 0
    res['msg'] = ('success')
    return JsonResponse(res, status=200)
