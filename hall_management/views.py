from django.shortcuts import render , redirect
from django.contrib.auth import login, logout
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.views.decorators.http import require_POST
from .form import hallmaster_user_creation, new_booking , new_expense ,new_inventory ,new_staff ,new_inventory_category, loginform , new_payment
from django.views.generic import ListView, DetailView
from django.contrib import messages
from django.http import HttpResponse
from django.db.models import Q
from django.core.paginator import Paginator
from .models import newbooking , staff , expense , Inventory, InventoryCategory , payment
from django.db.models import Sum ,Max 
from datetime import date , datetime
import csv

def log_in(request):
        
    if request.method == "POST":
        form = loginform( request = request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request , user)
            return redirect("dashboard")
    else:
        form = loginform(request = request)
    return render(request , 'login.html' , {'form': form})

@require_POST
def log_out(request):
    logout(request)
    return redirect('login')


@login_required(login_url='login')
def dashboard(request):
    dashboard_booking_list = newbooking.objects.all().order_by('-booking_id')[:5]
    total_bookings = newbooking.objects.count()
    
    
    context = {
        'dashboard_booking_list': dashboard_booking_list,
        'total_bookings': total_bookings,
    }
    return render(request ,"dashboard.html" , context)

@login_required(login_url='login')
def booking_view(request):
    current_month = datetime.today().month
    previous_month = current_month -1
    current_year = datetime.today().year
    previous_year = current_year - 1
    booking_status = ['confirmed','confirm', 'Confirmed','Confirm']
    booking_status_pending = ['pending','Pending', 'notconfirmed','NotConfirm']
    booking_total = newbooking.objects.filter(event_date__month = current_month , event_date__year  = current_year).count()
    total_booking_previous = newbooking.objects.filter(event_date__month = previous_month , event_date__year = current_year).count()
    total_booking_percentage = ((booking_total - total_booking_previous)/ total_booking_previous)* 100 
    confirmed_booking= newbooking.objects.filter(event_date__month = current_month , event_date__year = current_year ,status__in = booking_status).count() 
    confirmed_booking_previous= newbooking.objects.filter(event_date__month = previous_month , event_date__year = current_year , status__in = booking_status).count()
    percentage = ((confirmed_booking - confirmed_booking_previous) / confirmed_booking_previous) * 100 or 0
    pending_booking = newbooking.objects.filter(status__in = booking_status_pending , event_date__month = current_month , event_date__year = current_year).count() 
    
    pending_booking_previous = newbooking.objects.filter(event_date__month = previous_month , event_date__year = current_year ,status__in = booking_status_pending).count()
    pending_booking_percentage = ((pending_booking - pending_booking_previous) / pending_booking_previous) * 100 or 0
    booking_cancelled = newbooking.objects.filter(event_date__month = current_month , status = 'cancelled').count()
    booking_cancelled_previous = newbooking.objects.filter(event_date__month = previous_month , status = 'cancelled').count()
    booking_cancelled_percentage = ((booking_cancelled - booking_cancelled_previous) /booking_cancelled_previous) * 100 or 0

    search = request.GET.get('search', '')
    booking_status_filter = request.GET.get('status', '')
    booking_date = request.GET.get('event_date', '')

    booking_list = newbooking.objects.all().order_by('-booking_id')
    if search:
        booking_list = booking_list.filter(
            Q(customer_name__icontains = search)|
            Q(booking_id__icontains = search)|
            Q(event_name__icontains = search)|
            Q(event_hall__icontains = search)|
            Q(status__icontains = search)
        )
    if booking_status_filter.lower() == 'confirmed':
        booking_list = booking_list.filter(status__in=booking_status)
    elif booking_status_filter.lower() == 'pending':
        booking_list = booking_list.filter(status__in=booking_status_pending)
    elif booking_status_filter:
        booking_list = booking_list.filter(status__iexact=booking_status_filter)
    if booking_date:
        booking_list = booking_list.filter(event_date=booking_date)

    paginator = Paginator(booking_list, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
                'booking_total':booking_total,
                'total_booking_percentage':total_booking_percentage,
                'page_obj': page_obj,
                'confirmed_booking':confirmed_booking,
                'percentage':percentage,
                'pending_booking':pending_booking,
               'pending_booking_percentage':pending_booking_percentage,
                'booking_cancelled':booking_cancelled,
                'booking_cancelled_percentage': booking_cancelled_percentage,
                'search':search,
                'booking_status_filter':booking_status_filter,
                'booking_date':booking_date,
                'pending_booking_previous':pending_booking_previous,
            }
    return render(request, 'bookings.html', context)
def export_booking_data(request):
    today = datetime.now()
    current_time = today.strftime("%I:%M %p")
    currrent_date = today.strftime('%d %b %Y')
    #used in booking data download
    bookings = newbooking.objects.all().order_by('-event_date')
    response = HttpResponse(content_type = 'text/csv')
    response['content-Disposition'] = f' attachment; filename=Booking Records {current_time} {currrent_date}.csv'
    writer = csv.writer(response)
    
    #Write row heading

    writer.writerow([
        'Booking ID'.upper(),
        'Customer'.upper(),
        'Event'.upper(),
        'Date'.upper(),
        'Time'.upper(),
        'Guest'.upper(),
        'Hall portion'.upper(),
        'Amount'.upper(),
        'payment'.upper(),
        'status'.upper()
    ])

    for booking in bookings:
        writer.writerow([
            booking.booking_id,
            booking.customer_name,
            booking.event_name,
            booking.event_date,
            booking.event_time,
            booking.event_guest,
            booking.event_hall,
            booking.hall_price,
            booking.payment_status,
            booking.status
        ])
    return response
@login_required(login_url='login')
def Availability_view(request):
    return render(request , 'availability.html')
    
@login_required(login_url='login')
def Inventory_view(request):
    total_inventory = Inventory.objects.all()
    total_inventory_num = Inventory.objects.all().count()
    available_inventory = Inventory.objects.aggregate(Sum('available_quantity'))['available_quantity__sum'] or 0
    total_category = InventoryCategory.objects.all().count()
    damage_inventory = Inventory.objects.aggregate(Sum('damage_quantity'))['damage_quantity__sum'] or 0
    available_percentage = available_inventory / damage_inventory
    search = request.GET.get('search' , "")
    if search:
        inventory_obj = Inventory.objects.filter(
            Q(inventory_name__icontains = search)|
            Q(category__category_name__icontains = search)
        )
        paginator = Paginator(inventory_obj , 10)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        context={
            'total_inventory':total_inventory,
            'total_inventory_num':total_inventory_num,
            'available_inventory':available_inventory,
            'damage_inventory':damage_inventory,
            'total_category':total_category,
            'available_percentage':available_percentage,
            'search':search,
            'page_obj':page_obj
        }
        return render(request , 'inventory.html', context)
    else:
        total_inventory = Inventory.objects.all()
        total_inventory_num = Inventory.objects.all().count()
        available_inventory = Inventory.objects.aggregate(Sum('available_quantity'))['available_quantity__sum'] or 0
        total_category = Inventory.objects.aggregate(Sum('category'))['category__sum'] or 0
        damage_inventory = Inventory.objects.aggregate(Sum('damage_quantity'))['damage_quantity__sum'] or 0
        available_percentage = available_inventory / damage_inventory
        paginator = Paginator(total_inventory , 1)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
    context={
                'total_inventory':total_inventory,
                'total_inventory_num':total_inventory_num,
                'available_inventory':available_inventory,
                'damage_inventory':damage_inventory,
                'total_category':total_category,
                'available_percentage':available_percentage,
                'page_obj':page_obj
            }
    return render(request , 'inventory.html' , context)

@login_required(login_url='login')
def Availability_view(request):
    return render(request , 'availability.html')
@login_required(login_url='login')
def Customers_view(request):
    return render(request , 'customers.html')
@login_required(login_url='login')
def Packages_view(request):
    return render(request , 'packages.html')
@login_required(login_url='login')
def Payments_view(request):
    payment_details = payment.objects.all().order_by('-payment_id')
    search = request.GET.get('search' , '')
    payment_method = request.GET.get('method')
    today = datetime.now()
    current_month = today.strftime('%b')
    current__month = date.today().month
    previous_month = current__month - 1
    current_year = date.today().year
    previous_year = current_year - 1
    today_collection = payment.objects.filter(payment_date = today , payment_status = 'paid').aggregate(Sum('amount'))['amount__sum'] or 0
    status=['paid' ,'Paid','advance', 'Advance']
    month_collection = payment.objects.filter(payment_date__month = current__month ,payment_date__year = current_year , payment_status__in = status ).aggregate(Sum('amount'))['amount__sum'] or 0
    previous_month_collection = payment.objects.filter(payment_date__month = previous_month ,payment_date__year = current_year , payment_status__in = status ).aggregate(Sum('amount'))['amount__sum'] or 0
    pending_status = ['Pending' , 'pending']
    pending_collection = payment.objects.filter(payment_date__month = current__month , payment_status__in = pending_status).aggregate(Sum('amount'))['amount__sum'] or 0
    pending_count = payment.objects.filter(payment_status__in = pending_status).count()
    total_collection = payment.objects.filter(payment_date__year = current_year).aggregate(Sum('amount'))['amount__sum'] or 0
    pre_total_collection = payment.objects.filter(payment_date__year = previous_year).aggregate(Sum('amount'))['amount__sum'] or 0
    year_colloection_in_precentage = ((total_collection-pre_total_collection) / pre_total_collection ) * 100 if pre_total_collection else 0
    monthly_colloection_in_precentage = ((month_collection-previous_month_collection) / previous_month_collection ) * 100 if previous_month_collection else 0

    
    if search:
        payment_obj = payment.objects.filter(
            Q(payment_id__icontains = search)|
            Q(refference_num__icontains = search)|
            Q(payment_status__icontains = search)|
            Q(amount__icontains = search)|
            Q(booking__customer_name__icontains = search)|
            Q(payment_date__icontains = search)
        )
        paginator = Paginator(payment_obj , 1)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        context = {
            'page_obj':page_obj,
            'current_month': current_month,
            'previous_month':previous_month,
            'today_collection':today_collection,
            'month_collection':month_collection,
            'pending_collection':pending_collection,
            'total_collection':total_collection,
            'pending_count':pending_count,
            'year_colloection_in_precentage':year_colloection_in_precentage,
            'monthly_colloection_in_precentage':monthly_colloection_in_precentage,
            'search':search,
            'selected_method':payment_method,
        }
        return render(request , 'payments.html' , context)
    elif payment_method:
        payment_obj = payment.objects.filter(method = payment_method)
        paginator = Paginator(payment_obj , 1)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        context = {
                    'page_obj':page_obj,
                    'search':search,
                    'selected_method':payment_method,
                    'current_month':current_month,
                    'today_collection':today_collection,
                    'month_collection':month_collection,
                    'pending_collection':pending_collection,
                    'total_collection':total_collection,
                    'pending_count':pending_count,
                    'year_colloection_in_precentage':year_colloection_in_precentage,
                    'monthly_colloection_in_precentage':monthly_colloection_in_precentage,
                }
        return render(request , 'payments.html' , context)

    else:
        page_content = payment_details
    paginator = Paginator(payment_details , 1)
    page_number = request.GET.get('page')
    page_obj  = paginator.get_page(page_number)
    context = {
        'page_obj':page_obj,
        'payment_details': payment_details,
        'selected_method':payment_method,
        'current_month':current_month,
        "previous_month":previous_month,
        'page_content':page_content,
        'today_collection':today_collection,
        'month_collection':month_collection,
        'pending_collection':pending_collection,
        'total_collection':total_collection,
        'pending_count':pending_count,
        'year_colloection_in_precentage':year_colloection_in_precentage,
        'monthly_colloection_in_precentage':monthly_colloection_in_precentage,
    }
    return render(request , 'payments.html' , context)
@login_required(login_url='login')
def Invoices_view(request):
    return render(request , 'invoices.html')
@login_required(login_url='login')
def Expenses_view(request):
    total_expenses = expense.objects.aggregate(Sum('amount'))['amount__sum'] or 0
    today = datetime.now()
    current__month = today.strftime('%B')
    current_month = date.today().month
    current_year = date.today().year
    previous_year = current_year - 1
    confirm_status = ['Paid' ,'paid']
    pending_status = ['pending','Pending']
    yearly_expenses = expense.objects.filter(date__year = current_year , status__in = confirm_status).aggregate(Sum('amount'))['amount__sum'] or 0
    yearly_expenses_previous = expense.objects.filter(date__year = previous_year , status__in = confirm_status).aggregate(Sum('amount'))['amount__sum'] or 0
    yearly_expenses_per = ((yearly_expenses-yearly_expenses_previous) / yearly_expenses_previous) * 100 or 0
    previous_month = current_month - 1
    monthly_expenses = expense.objects.filter(date__month = current_month, date__year = current_year, status ='paid').aggregate(Sum('amount'))['amount__sum'] or 0
    monthly_expenses_previous = expense.objects.filter(date__month = previous_month,date__year = current_year, status__in =confirm_status).aggregate(Sum('amount'))['amount__sum'] or 0
    monthly_expenses_per =(( monthly_expenses - monthly_expenses_previous) / monthly_expenses_previous) * 100 or 0
    monthly_expenses_pending = expense.objects.filter(date__month = current_month, status ='pending').aggregate(Sum('amount'))['amount__sum'] or 0
    calculate_pending = expense.objects.filter(status__in = pending_status ).count()
    largest_expense = expense.objects.all().aggregate(Max('amount'))['amount__max'] or 0
    expense_list = expense.objects.all().order_by('-expense_id')[:10]
    paginator = Paginator(expense_list , 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number) 
    search =request.GET.get('search', '')
    if search:
        expense_obj = expense.objects.filter(
            Q(expense_id__icontains = search)|
            Q(expense_title__icontains =search)|
            Q(status__icontains = search)|
            Q(paid_by__icontains = search)|
            Q(date__icontains=search)
        )
        paginator =Paginator(expense_obj , 1)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        context ={
                'expense_list': expense_list,
                'page_obj': page_obj,
                'total_expenses': total_expenses,
                'monthly_expenses': monthly_expenses,
                'monthly_expenses_per': monthly_expenses_per,
                'monthly_expenses_pending': monthly_expenses_pending,
                'largest_expense': largest_expense,
                'yearly_expenses':yearly_expenses,
                'yearly_expenses_per':yearly_expenses_per,
                'current_year': current_year,
                'current_month': current_month,
                'current__month':current__month,
                'calculate_pending':calculate_pending,
                'search':search
            } 
        return render(request , 'expenses.html', context)
    else:
        expense_list = expense.objects.all().order_by('-expense_id')[:10]
        paginator = Paginator(expense_list , 1)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)   
    context ={
        'expense_list': expense_list,
        'page_obj': page_obj,
        'total_expenses': total_expenses,
        'monthly_expenses': monthly_expenses,
        'monthly_expenses_per': monthly_expenses_per,
        'monthly_expenses_pending': monthly_expenses_pending,
        'largest_expense': largest_expense,
        'yearly_expenses':yearly_expenses,
        'yearly_expenses_per':yearly_expenses_per,
        'current_year': current_year,
        'current_month': current_month,
        'current__month':current__month,
        'calculate_pending':calculate_pending,
    } 
    return render(request , 'expenses.html' , context)
@login_required(login_url='login')
def Reports_view(request):  
    return render(request , 'reports.html')
@login_required(login_url='login')
def Staff_view(request):
    total_staff = staff.objects.all().count()
    active_staff = staff.objects.filter(staff_status = 'active').count()
    manager_count = staff.objects.filter(staff_role = 'manager').count()
    staff_list = staff.objects.all().order_by('-staff_id')[:10]
    search = request.GET.get('search' , '')
    if search:
        staff_obj = staff.objects.filter(
            Q(staff_id__icontains = search)|
            Q(staff_name__icontains = search)|
            Q(staff_email__icontains = search)|
            Q(staff_number__icontains = search)|
            Q(staff_role__icontains = search)|
            Q(staff_status__icontains = search)|
            Q(staff_join_date__icontains = search)|
            Q(staff_nic_num__icontains = search)
        )
        paginator = Paginator(staff_obj , 10)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        context={
            'staff_list': staff_list,
            'page_obj': page_obj,
            'total_staff': total_staff,
            'active_staff': active_staff,
            'manager_count': manager_count,
            'search':search, 
        }
        return render(request , 'staff.html' , context)
    else:
        staff_list = staff.objects.all().order_by('-staff_id')[:10]
        paginator = Paginator(staff_list , 10)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
    context={
        'staff_list': staff_list,
        'page_obj': page_obj,
        'total_staff': total_staff,
        'active_staff': active_staff,
        'manager_count': manager_count,
        'search':search
    }

    return render(request , 'staff.html' , context) 
@login_required(login_url='login')
def Notifications_view(request):
    return render(request , 'notifications.html')
@login_required(login_url='login')
def Settings_view(request):
    return render(request , 'settings.html')
@login_required(login_url='login')
def New_booking(request):
    if request.method == 'POST':
        form = new_booking(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Booking created successfully.")
            return redirect('bookings')
        elif form.is_not_valid():
            messages.error(request, "Please correct the errors below.")
    else:
        form = new_booking()
    context  = {'form': form}
    return render(request , 'bookingform.html', context)

@login_required(login_url='login')
def Expense_form(request):
    if request.method =='POST':
        form = new_expense(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request , "Expense created successfully.")
            return redirect('expensesform')
        elif form.is_not_valid():
            messages.error(request , "Please correct the errors below.")
    else:
        form = new_expense()
    context = {'form': form}
    return render(request , 'addexpense.html' , context)
@login_required(login_url='login')
def New_staff(request):
    if request.method =='POST':
        form =new_staff(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request , "Staff created successfully.")
            return redirect('staffform')
        elif form.is_not_valid():
            messages.error(request , "Please correct the errors below.")
    else:
        form =new_staff()
    context = {'form': form}
    return render (request , 'addstaff.html' , context)
@login_required(login_url='login')
def New_inventory(request):
    if request.method =='POST':
        form = new_inventory(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request , "Inventory created successfully.")
            return redirect('inventoryform')
        elif form.is_not_valid():
            messages.error(request , "Please correct the errors below.")
    else:
        form  = new_inventory()
    context = {'form' : form}
    return render(request , 'addinventory.html' , context)
@login_required(login_url='login')
def New_inventory_category(request):
    if request.method =='POST':
        form = new_inventory_category(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request , "Inventory category created successfully.")
            return redirect('inventorycategoryform')
        elif form.is_not_valid():
            messages.error(request , "Please correct the errors below.")
    else:
        form  = new_inventory_category()
    context = {'form' : form}
    return render(request , 'addinventorycategory.html' , context) 
        
class ViewBooking(ListView):
    model = newbooking
    template_name = 'booking.html'
    context_object_name = 'bookings'

def can_manage_users(user):
    return user.is_staff or user.has_perm('auth.add_user')


@login_required(login_url='login')
def users_page(request):
    user_model = get_user_model()
    accounts = user_model._default_manager.order_by('-date_joined', 'username')
    user_rows = []

    for account in accounts:
        name = account.get_full_name().strip() or account.get_username()
        initials = ''.join(part[0] for part in name.split()[:2]).upper() or 'U'
        role = 'Administrator' if account.is_superuser else 'Staff' if account.is_staff else 'Member'
        user_rows.append({
            'account': account,
            'name': name,
            'initials': initials,
            'role': role,
            'role_key': role.lower(),
        })

    return render(request, 'users.html', {
        'page': 'users',
        'users': user_rows,
        'total_users': len(user_rows),
        'active_users': sum(account['account'].is_active for account in user_rows),
        'inactive_users': sum(not account['account'].is_active for account in user_rows),
        'admin_users': sum(account['account'].is_superuser for account in user_rows),
        'can_add_user': can_manage_users(request.user),
    })


@login_required(login_url='login')
def user_create(request):
    if not can_manage_users(request.user):
        raise PermissionDenied

    form = hallmaster_user_creation(
        request.POST or None,
        can_create_admin=request.user.is_superuser,
    )
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('users')

    return render(request, 'user_create.html', {
        'page': 'users',
        'form': form,
        'can_create_admin': request.user.is_superuser,
    })


INVOICE_DETAILS = {
    'INV-2026-126': {
        'customer': 'Sarah Khan', 'booking': 'BK-2026-084', 'event': 'Wedding Reception',
        'venue': 'Grand Ballroom', 'event_date': '05 Oct 2026', 'issued': '19 Sep 2026',
        'due': '28 Sep 2026', 'total': '1,850,000', 'paid': '350,000', 'balance': '1,500,000',
        'status': 'pending', 'items': [('Grand Ballroom rental', '920,000'), ('Catering and service, 420 guests', '680,000'), ('Stage and event setup', '250,000')],
    },
    'INV-2026-125': {
        'customer': 'Ahmed Malik', 'booking': 'BK-2026-083', 'event': 'Corporate Gala',
        'venue': 'Crystal Hall', 'event_date': '12 Oct 2026', 'issued': '18 Sep 2026',
        'due': '30 Sep 2026', 'total': '960,000', 'paid': '960,000', 'balance': '0',
        'status': 'paid', 'items': [('Crystal Hall rental', '480,000'), ('Catering and service', '360,000'), ('Audio and visual setup', '120,000')],
    },
    'INV-2026-124': {
        'customer': 'Ayesha Siddiqui', 'booking': 'BK-2026-082', 'event': 'Engagement Celebration',
        'venue': 'Royal Terrace', 'event_date': '12 Oct 2026', 'issued': '16 Sep 2026',
        'due': '03 Oct 2026', 'total': '1,420,000', 'paid': '200,000', 'balance': '1,220,000',
        'status': 'pending', 'items': [('Royal Terrace venue package', '700,000'), ('Dinner service', '520,000'), ('Floral event setup', '200,000')],
    },
    'INV-2026-123': {
        'customer': 'Mariam Ali', 'booking': 'BK-2026-081', 'event': 'Mehndi Night',
        'venue': 'Garden Pavilion', 'event_date': '11 Oct 2026', 'issued': '15 Sep 2026',
        'due': '05 Oct 2026', 'total': '625,000', 'paid': '150,000', 'balance': '475,000',
        'status': 'pending', 'items': [('Garden Pavilion rental', '250,000'), ('Dinner service', '275,000'), ('Stage and lighting', '100,000')],
    },
    'INV-2026-122': {
        'customer': 'Bilal Ahmed', 'booking': 'BK-2026-079', 'event': 'Corporate Banquet',
        'venue': 'Grand Ballroom', 'event_date': '20 Sep 2026', 'issued': '08 Sep 2026',
        'due': '14 Sep 2026', 'total': '2,150,000', 'paid': '0', 'balance': '2,150,000',
        'status': 'overdue', 'items': [('Grand Ballroom rental', '1,000,000'), ('Catering and service', '900,000'), ('Event production and setup', '250,000')],
    },
}


def invoice_detail(request, invoice_id):
    invoice = INVOICE_DETAILS.get(invoice_id)
    if invoice is None:
        from django.http import Http404
        raise Http404('Invoice not found')
    return render(request, 'genrateinvoice.html', {'page': 'invoices', 'invoice_id': invoice_id, 'invoice': invoice})


def hallmaster_login(request):
    return render(request, 'login.html')


def tester(request):
        return render(request , "testerbase.html")

# Create your views here