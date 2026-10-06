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
from hall_management.views import dashboard, log_in, log_out, tester, user_create, users_page , New_booking , Expense_form , New_staff , New_inventory , New_inventory_category , Inventory_view , booking_view , Availability_view , Customers_view, Packages_view,Payments_view, Invoices_view, Reports_view, Expenses_view, Staff_view, Notifications_view, Settings_view

urlpatterns = [
    path('admin/', admin.site.urls),
        path('login/', log_in, name='login'),
        path('logout/', log_out, name='logout'),
        path('' , dashboard , name ="dashboard"),
        path('inventory/' , Inventory_view , name ="inventory"),
        path('availability/' , Availability_view , name ="availability"),
        path('customers/' , Customers_view , name ="customers"),
        path('packages/' , Packages_view , name ="packages"),
        path('payments/' , Payments_view , name ="payments"),
        path('invoices/' , Invoices_view , name ="invoices"),
        path('reports/' , Reports_view , name ="reports"),
        path('expenses/' , Expenses_view , name ="expenses"),
        path('staff/' , Staff_view , name ="staff"),
        path('users/', users_page, name='users'),
        path('adduser/', user_create, name='user_create'),
        path('notifications/' , Notifications_view , name ="notifications"),
        path('settings/' , Settings_view , name ="settings"),
        path('bookings/' , booking_view , name ="bookings"),
        path('bookingform/' , New_booking , name = "bookingform"),
        path('addexpense/', Expense_form , name = "expensesform"),
        path('addstaff/' , New_staff , name = "staffform"),
        path('addinventory/' , New_inventory , name = "inventoryform"),
        path('addinventorycategory/' , New_inventory_category , name = "inventorycategoryform"),
        path('tester/', tester, name='tester'),

]

