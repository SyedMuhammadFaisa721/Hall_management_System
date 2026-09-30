"""
URL configuration for Hall_managemnet project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from hall_management.views import hallmaster_login, hallmaster_page, tester, login, invoice_detail

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', login, name='login'),
    path('', hallmaster_page, {'page': 'dashboard'}, name='dashboard'),
    path('bookings/', hallmaster_page, {'page': 'bookings'}, name='bookings'),
    path('bookingform/', hallmaster_page, {'page': 'bookingform'}, name='bookingform'),
    path('availability/', hallmaster_page, {'page': 'availability'}, name='availability'),
    path('customers/', hallmaster_page, {'page': 'customers'}, name='customers'),
    path('packages/', hallmaster_page, {'page': 'packages'}, name='packages'),
    path('payments/', hallmaster_page, {'page': 'payments'}, name='payments'),
    path('invoices/', hallmaster_page, {'page': 'invoices'}, name='invoices'),
    path('invoices/<str:invoice_id>/', invoice_detail, name='invoice_detail'),
    path('expenses/', hallmaster_page, {'page': 'expenses'}, name='expenses'),
    path('reports/', hallmaster_page, {'page': 'reports'}, name='reports'),
    path('staff/', hallmaster_page, {'page': 'staff'}, name='staff'),
    path('notifications/', hallmaster_page, {'page': 'notifications'}, name='notifications'),
    path('settings/', hallmaster_page, {'page': 'settings'}, name='settings'),
    path('tester/', tester, name='tester'),
]
