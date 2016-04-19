from django.http import HttpResponse


def home(request):
    return HttpResponse("<h1>Hola mundo</h1>")