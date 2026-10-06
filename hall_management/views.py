from django.shortcuts import render , redirect
from django.contrib.auth import login, logout
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.views.decorators.http import require_POST
from .form import hallmaster_user_creation, new_booking , new_expense ,new_inventory ,new_staff ,new_inventory_category, loginform
from django.views.generic import ListView, DetailView
from django.contrib import messages
from django.http import HttpResponse
from django.db.models import Q
from django.core.paginator import Paginator
from .models import newbooking , staff , expense , Inventory, InventoryCategory
from django.db.models import Sum ,Max 
from datetime import date , datetime

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
    booking_total = newbooking.objects.all().count()

    booking_confirmed = newbooking.objects.filter(status = 'confirmed').count()
    booking_pending = newbooking.objects.filter(status = 'pending').count()
    booking_canceled = newbooking.objects.filter(status = 'canceled').count()

    search = request.GET.get('search', '')
    if search:
        booking_obj = newbooking.objects,filter(
            Q(customer_name__icontains = search)|
            Q(booking_id__icontains = search)|
            Q(event_name__icontains = search)|
            Q(event_hall__icontains = search)|
            Q(status__icontains = search)
        )
        paginator = Paginator(booking_obj ,10)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        context = {
            'booking_total': booking_total,
            'booking_obj': booking_obj,
            'booking_confirmed': booking_confirmed,
            'booking_pending': booking_pending,
            'booking_canceled': booking_canceled,
            'page_obj': page_obj,
        }
        return render(request, 'bookings.html', context)
    else:
        booking_list = newbooking.objects.all().order_by('-booking_id')
        paginator =Paginator(booking_list , 10)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)


    context = {
        'booking_total': booking_total,
        'booking_confirmed': booking_confirmed,
        'booking_pending': booking_pending,
        'booking_canceled': booking_canceled,
        'page_obj': page_obj,
    }
    return render(request, 'bookings.html', context)
@login_required(login_url='login')
def Availability_view(request):
    return render(request , 'availability.html')
    
@login_required(login_url='login')
def Inventory_view(request):
    return render(request , 'inventory.html')

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
    return render(request , 'payments.html')
@login_required(login_url='login')
def Invoices_view(request):
    return render(request , 'invoices.html')
@login_required(login_url='login')
def Expenses_view(request):
    total_expenses = expense.objects.aggregate(Sum('amount'))['amount__sum'] or 0
    current_month = date.today().month
    current_year = date.today().year
    previous_year = current_year - 1
    yearly_expenses = expense.objects.filter(date__year = current_year , status = 'paid').aggregate(Sum('amount'))['amount__sum'] or 0
    yearly_expenses_previous = expense.objects.filter(date__year = previous_year , status = 'paid').aggregate(Sum('amount'))['amount__sum'] or 0
    yearly_expenses_per = yearly_expenses / yearly_expenses_previous or 0
    previous_month = current_month - 1
    monthly_expenses = expense.objects.filter(date__month = current_month, status ='paid').aggregate(Sum('amount'))['amount__sum'] or 0
    monthly_expenses_previous = expense.objects.filter(date__month = previous_month, status ='paid').aggregate(Sum('amount'))['amount__sum'] or 0
    monthly_expenses_per = monthly_expenses / monthly_expenses_previous or 0
    monthly_expenses_pending = expense.objects.filter(date__month = current_month, status ='pending').aggregate(Sum('amount'))['amount__sum'] or 0
    largest_expense = expense.objects.all().aggregate(Max('amount'))['amount__max'] or 0
    search =request.GET.get('search', '')
    if search:
        expense_obj = expense.objects.filter(
            Q(expense_id__icontains = search)|
            Q(expense_title__icontains =search)|
            Q(status__icontains = search)|
            Q(paid_by__icontains = search)|
            Q(date__icontains=search)
        )
        paginator =Paginator(expense_obj , 10)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        context={
            'expense_obj': expense_obj,
            'page_obj': page_obj,
            'total_expenses': total_expenses,
            'monthly_expenses_pending':monthly_expenses_pending
        }
        return render(request , 'expenses.html', context)
    else:
        expense_list = expense.objects.all().order_by('-expense_id')[:10]
        paginator = Paginator(expense_list , 10)
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
    } 
    return render(request , 'expenses.html' , context)
@login_required(login_url='login')
def Reports_view(request):  
    return render(request , 'reports.html')
@login_required(login_url='login')
def Staff_view(request):
    return render(request , 'staff.html') 
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