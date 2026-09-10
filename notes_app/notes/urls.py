from django.urls import path

from . import views

app_name = 'notes'

urlpatterns = [
    path('new/', views.note_create, name='note_create'),
]
