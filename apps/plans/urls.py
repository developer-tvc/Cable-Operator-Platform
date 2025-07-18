from django.urls import path
from . import views

urlpatterns = [
    path('plans/', views.plan_list, name='plan_list'),
    path('plans/create/', views.create_plan, name='create_plan'),
    path('plans/update/<int:pk>/', views.update_plan, name='update_plan'),
    path('plans/delete/<int:pk>/', views.delete_plan, name='delete_plan'),
]
