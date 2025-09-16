from smtplib import SMTPResponseException
from tkinter.font import names

from django.shortcuts import render
from django.utils.termcolors import RESET
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse,HttpResponse,StreamingHttpResponse
from ailoginTest import models
from django.contrib.auth import login,authenticate
from django.contrib.sessions.models import Session

# Create your views here.
@require_http_methods(['GET'])
def get_all_student(request):
    """
    params
    return all stutents info
    """
    age = request.GET.get('age')
    # meta = request.META['ip']
    all_students = models.student.objects.all().values()
    all_students =   [{"id": 1, "name": '133', "sex": 'girl', "address": 'dfhgjsfjkdhgujknbehkj'}]
    # search = models.school.objects.filter(name='abd').values('school_name')
    # dele = models.school.objects.filter(name='abd').delete()
    # update = models.school.objects.filter(name='abd').update(age=age)
    # get_cre = models.school.objects.get_or_create(name='abd',age=age)
    req = {}
    if age is None:
        req['code'] = 10003
        req['msg'] = ('no age info')
    else:
        req['code'] = 0
        req['msg'] = ('success')
        req['data'] = all_students
    return JsonResponse(req, status=200)

@require_http_methods(['POST'])
def add_school(request):
    req = {}
    school_name = request.POST.get('school_name')
    sex = request.POST.get('sex')
    create_date = request.POST.get('create_date')

    if not school_name:
        req['code'] = 10001
        req['msg'] = ('no school name')
        return JsonResponse(req, status=200)

    if not sex:
        req['code'] = 10002
        req['msg'] = ('no sex info')
        return JsonResponse(req, status=200)

    if not create_date:
        req['code'] = 10003
        req['msg'] = ('no create_date info')
        return JsonResponse(req, status=200)

    try:
        creater = models.school.objects.create(school_name=school_name, sex=sex, create_date=create_date)
    except Exception as e:
        req['code'] = 10005
        req['msg'] = (str(e))
        return JsonResponse(req, status=400)
    if creater[1] == False:
        req['code'] =1004
        req['msg'] = ('school already exist')
        return JsonResponse(req, status=200)
    req['code'] = 0
    req['msg'] = ('success')
    return JsonResponse(req, status=200)


@require_http_methods('GET')
def get_numbers_by_phone(request):
    phone=request.GET.get('phone')
    req = {}
    if not phone:
        req['code'] = 10001
        req['msg'] = ('no phone info')

    try:
        users = models.school.objects.get(phone=phone)
    except Exception as e:
        req['code'] = 10002
        req['msg'] = e

    if not users:
        req['code'] = 10003
        req['msg'] = ('no user info')

    return JsonResponse(req, status=200)


@require_http_methods('GET')
def download_file(request):
    file_path = "D:\1.txt"
    response = StreamingHttpResponse(open(file_path, 'rb'))
    response['content_type'] = 'application/octet-stream'
    response['Content-Disposition'] = 'attachment; filename={0}'.format(file_path)
    return response

@require_http_methods('POST')
def login(request):
    req = {}
    user = request.POST.get('user')
    password = request.POST.get('password')
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



