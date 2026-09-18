from django.urls import path

from . import views


urlpatterns = [
    path('asistente/', views.chat_view, name='rag_chat'),
]
