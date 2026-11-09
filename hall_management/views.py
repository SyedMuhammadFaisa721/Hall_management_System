from django.shortcuts import render , redirect
from django.contrib.auth import login, logout
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.views.decorators.http import require_POST
from .form import hallmaster_user_creation, new_booking , new_expense ,new_inventory ,new_staff ,new_inventory_category, loginform , new_payment
from django.views.generic import ListView
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.db.models import Count, Q
from django.db.models.functions import ExtractMonth, ExtractYear
from django.core.paginator import Paginator
from .models import Hall_portion, newbooking , staff , expense , Inventory, InventoryCategory , payment
from django.db.models import Sum ,Max 
from datetime import date , datetime , timedelta
import csv
import math
from django.utils import timezone

def format_report_payment_amount(amount):
    if amount >= 1_000_000_000:
        value = f"{amount / 1_000_000_000:.4f}".rstrip('0').rstrip('.')
        return f"{value}B"
    elif amount >= 1_000_000:
        value = f"{amount / 1_000_000:.4f}".rstrip('0').rstrip('.')
        return f"{value}M"
    return f"{amount:,.4f}".rstrip('0').rstrip('.')


def format_report_chart_axis_label(amount):
    if amount == 0:
        return '0'
    for divisor, suffix in ((1_000_000_000, 'B'), (1_000_000, 'M'), (1_000, 'K')):
        if abs(amount) >= divisor:
            value = f"{amount / divisor:.1f}".rstrip('0').rstrip('.')
            return f'{value}{suffix}'
    return f'{amount:,.0f}'


def build_booking_status_donut(total_count, status_counts):
    status_colors = (
        ('Confirmed', 'confirmed', '#55c58a'),
        ('Pending', 'pending', '#e1c58e'),
        ('Cancelled', 'cancelled', '#F87171'),
        ('Advance', 'advance', '#8299bd'),
    )
    classified_count = sum(status_counts.values())
    other_count = max(total_count - classified_count, 0)
    segments = []
    gradient_parts = []
    current_count = 0

    for label, key, color in status_colors + (('Other', 'other', '#9aa3ab'),):
        count = other_count if key == 'other' else status_counts[key]
        start = current_count * 100 / total_count if total_count else 0
        current_count += count
        end = current_count * 100 / total_count if total_count else 0
        percentage = count * 100 / total_count if total_count else 0
        segments.append({
            'label': label,
            'key': key,
            'count': count,
            'percentage': percentage,
            'color': color,
        })
        if count:
            gradient_parts.append(f'{color} {start:.4f}% {end:.4f}%')

    gradient = (
        f"conic-gradient({', '.join(gradient_parts)})"
        if gradient_parts else 'conic-gradient(#d7dee5 0% 100%)'
    )
    return segments, gradient


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
    # Dashboard backend code starts here: prepare monthly revenue for the dashboard graph.
    today = timezone.now().date()
    previous_day = today - timedelta(days = 1)
    current_month = datetime.now().month
    current_year = datetime.now().year
    if current_month == 1:
        previous_month = 12
        previous_year = current_year - 1
    else:
        previous_month = current_month -1
        previous_year =  current_year
    previous__year = current_year - 1
    upcoming_event = newbooking.objects.filter(event_date__gte = today).order_by('event_date')[:4]
    today_event_count = newbooking.objects.filter(created_at = today).count()
    today_event_record = newbooking.objects.filter(created_at = today).order_by('-booking_id')[:5]
    dashboard_booking_list = newbooking.objects.all().order_by('-booking_id')[:6]
    total_bookings = newbooking.objects.count()
    yesterday_booking = newbooking.objects.filter(created_at = previous_day).count()
    if today_event_count == 0 :
        today_booking_percentage = 0
    elif yesterday_booking <= 0 :
        today_booking_percentage = 100
    else:
        today_booking_percentage = ((today_event_count - yesterday_booking) / yesterday_booking)* 100 
    total_booking = newbooking.objects.filter(created_at__month = current_month , created_at__year = current_year ).count()
    total_booking_previous = newbooking.objects.filter(created_at__month = previous_month , created_at__year = previous_year ).count()
    if total_booking_previous <= 0 :
        total_booking_percentage = 100
    else:
        total_booking_percentage= ((total_booking - total_booking_previous) / total_booking_previous) * 100
    status_confirmed = ['confirmed', 'Confirmed', 'confirm', 'Confirm' , 'Comfirmed' , 'Advance' , 'advance']
    total_revenue = newbooking.objects.filter(status__in = status_confirmed , event_date__year = current_year).aggregate(Sum('hall_price'))['hall_price__sum'] or 0
    total_revenue_previous = newbooking.objects.filter(status__in = status_confirmed , event_date__year = previous__year).aggregate(Sum('hall_price'))['hall_price__sum'] or 0
    if total_revenue == 0:
        total_revenue_percentage = 0
    elif total_revenue_previous < 0 :
        total_revenue_percentage = 100
    else:
        total_revenue_percentage = ((total_revenue -  total_revenue_previous)/ total_revenue_previous) * 100
    booking_created_confirm = newbooking.objects.filter(status__in = status_confirmed , created_at__month = current_month , created_at__year = current_year).count()
    booking_created_confirm_previous = newbooking.objects.filter(status__in = status_confirmed , created_at__month = previous_month , created_at__year = previous__year).count()
    if booking_created_confirm == 0:
        booking_created_confirm_percentage = 0
    elif booking_created_confirm_previous <= 0:
        booking_created_confirm_percentage = 100
    else:
        booking_created_confirm_percentage = ((booking_created_confirm - booking_created_confirm_previous) / booking_created_confirm_previous) * 100
    status_pending = ['Pending', 'pending','unpaid','not paid' , 'Unpaid','Notpaid']
    pending_payment = newbooking.objects.filter(status__in=status_pending , created_at__month = current_month , created_at__year =current_year ).aggregate(Sum('hall_price'))['hall_price__sum'] or 0
    pending_payment_count = newbooking.objects.filter(status__in = status_pending , created_at__month = current_month , created_at__year = current_year).count()

    # Dashboard graph backend code starts here: calculate confirmed revenue for each month.
    monthly_revenue = []
    for month in range(1, 13):
        month_revenue = newbooking.objects.filter(
            status__in=status_confirmed,
            event_date__year=current_year,
            event_date__month=month,
        ).aggregate(Sum('hall_price'))['hall_price__sum'] or 0
        monthly_revenue.append(float(month_revenue))

    
    
    
    context = {
        'dashboard_booking_list': dashboard_booking_list,
        'total_bookings': total_bookings,
        'upcoming_event':upcoming_event,
        'today_event_count':today_event_count,
        'today_booking_percentage':today_booking_percentage,
        'total_booking':total_booking,
        "total_booking_percentage":total_booking_percentage,
        'total_revenue_percentage':total_revenue_percentage,
        'total_revenue':total_revenue,
        'booking_created_confirm':booking_created_confirm,
        'booking_created_confirm_percentage':booking_created_confirm_percentage,
        'pending_payment':pending_payment,
        'current_year':current_year,
        'pending_payment_count':pending_payment_count,
        'today_event_record':today_event_record,
        # Dashboard graph context starts here: send the monthly values to the template.
        'monthly_revenue': monthly_revenue,
        'revenue_chart_months': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
    }
    return render(request ,"dashboard.html" , context)

@login_required(login_url='login')
def booking_view(request):
    today = timezone.now().date()
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
    today_event_count = newbooking.objects.filter(created_at = today).order_by('-booking_id')[:10]
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
                'today_event_count':today_event_count
            }
    return render(request, 'bookings.html', context)
@login_required(login_url='login')
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
        'CREATED AT'
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
            booking.created_at,
            booking.payment_status,
            booking.status
        ])
    return response
@login_required(login_url='login')
def Availability_view(request):
    today = timezone.localdate()
    current_month = today.strftime('%B')
    current__month = today.month
    previous_month_date = today.replace(day=1) - timedelta(days=1)
    previous_month = previous_month_date.month
    previous__month = previous_month_date.strftime('%B')
    current_year = today.year
    previous_year = current_year - 1
    status_confirmed = ['confirmed', 'Confirmed', 'confirm', 'Confirm' , 'Comfirmed']
    status_advance = ['advance', 'Advance']
    status_pending = ['Pending', 'pending','unpaid','not paid' , 'Unpaid','Notpaid']
    status_cancelled = ['cancelled', 'Cancelled', 'Cancel', 'Cancel']

    #Upcoming events backend logic starts here:
    upcoming_events = newbooking.objects.filter(event_date__gte = today).all()
    paginator = Paginator(upcoming_events , 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    #card data backend logic starts here:
    event_month = newbooking.objects.filter(event_date__month=current__month, event_date__year=current_year).count()
    confirmed_event_month = newbooking.objects.filter(event_date__month=current__month, event_date__year=current_year, status__in=status_confirmed).count()
    pending_event_month = newbooking.objects.filter(event_date__month=current__month, event_date__year=current_year, status__in=status_pending).count()
    cancelled_event_month = newbooking.objects.filter(event_date__month=current__month, event_date__year=current_year, status__in=status_cancelled).count()
    #available dates backend logic starts here:
    month_start = today.replace(day=1)
    next_month = (month_start + timedelta(days=32)).replace(day=1)
    active_portion_ids = set(
        Hall_portion.objects.filter(portion_status__iexact='Active').values_list('pk', flat=True)
    )
    booked_portions_by_date = {}
    if active_portion_ids:
        active_bookings = (
            newbooking.objects.filter(
                event_date__gte=today,
                event_date__lt=next_month,
                event_hall__portion_status__iexact='Active',
            )
            .exclude(
                Q(status__iexact='cancel')
                | Q(status__iexact='cancelled')
                | Q(status__iexact='canceled')
            )
            .values_list('event_date', 'event_hall__pk')
        )
        for event_date, portion_id in active_bookings:
            booked_portions_by_date.setdefault(event_date, set()).add(portion_id)

    available_dates = sum(
        1
        for day_offset in range((next_month - today).days)
        if active_portion_ids.difference(
            booked_portions_by_date.get(today + timedelta(days=day_offset), set())
        )
    )
    #logic ends here

    context = {
        'current_month': current_month,
        'previous_month': previous__month,
        'current_year': current_year,
        'previous_year': previous_year,
        'event_month': event_month,
        'confirmed_event_month': confirmed_event_month,
        'pending_event_month': pending_event_month,
        'cancelled_event_month': cancelled_event_month,
        'available_dates': available_dates,
        'calendar_portions': list(Hall_portion.objects.order_by('portion_name').values('id', 'portion_name')),
        # Upcoming events context starts here:
        'page_obj':page_obj,
    }
    return render(request , 'availability.html' , context)


@login_required(login_url='login')
def Availability_events(request):
    start_value = request.GET.get('start')
    end_value = request.GET.get('end')
    try:
        start = date.fromisoformat(start_value)
        end = date.fromisoformat(end_value)
    except (TypeError, ValueError):
        return JsonResponse({'error': 'Valid start and end dates are required.'}, status=400)

    if start >= end:
        return JsonResponse({'error': 'The end date must be after the start date.'}, status=400)

    bookings = (
        newbooking.objects.filter(event_date__gte=start, event_date__lt=end)
        .prefetch_related('event_hall')
        .order_by('event_date', 'event_time', 'booking_id')
    )
    events = []
    for booking in bookings:
        halls = [
            {'id': hall.pk, 'name': hall.portion_name}
            for hall in booking.event_hall.all()
        ]
        status = booking.status or 'Unknown'
        events.append({
            'id': booking.booking_id,
            'title': booking.event_name,
            'start': booking.event_date.isoformat(),
            'extendedProps': {
                'bookingId': booking.booking_id,
                'customerName': booking.customer_name,
                #'phoneNumber': booking.phone_number,
                #'customerEmail': booking.customer_email,
                #'eventType': booking.event_type,
                'guestCount': booking.event_guest,
                'eventTime': booking.event_time,
                'halls': halls,
                'hallPrice': booking.hall_price,
                'specialRequest': booking.special_req or '',
                'status': status,
                #'paymentStatus': booking.payment_status,
                'isCancelled': status.strip().lower() in {'cancel', 'cancelled', 'canceled'},
            },
        })

    return JsonResponse({'events': events})
    
@login_required(login_url='login')
def Inventory_view(request):
    total_inventory = Inventory.objects.all()
    inventory_categories = InventoryCategory.objects.all()
    total_inventory_num = Inventory.objects.all().count()
    available_inventory = Inventory.objects.aggregate(Sum('available_quantity'))['available_quantity__sum'] or 0
    total_stock = Inventory.objects.aggregate(Sum('inventory_quantity'))['inventory_quantity__sum'] or 0
    total_category = InventoryCategory.objects.all().count()
    damage_inventory = Inventory.objects.aggregate(Sum('damage_quantity'))['damage_quantity__sum'] or 0
    available_percentage = available_inventory / total_stock * 100 if total_stock else 0
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
            'page_obj':page_obj,
            'inventory_categories':inventory_categories
        }
        return render(request , 'inventory.html', context)
    else:
        total_inventory = Inventory.objects.all()
        total_inventory_num = Inventory.objects.all().count()
        available_inventory = Inventory.objects.aggregate(Sum('available_quantity'))['available_quantity__sum'] or 0
        total_category = Inventory.objects.aggregate(Sum('category'))['category__sum'] or 0
        available_percentage = available_inventory / total_stock * 100 if total_stock else 0
        paginator = Paginator(total_inventory , 10)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
    context={
                'total_inventory':total_inventory,
                'total_inventory_num':total_inventory_num,
                'available_inventory':available_inventory,
                'damage_inventory':damage_inventory,
                'total_category':total_category,
                'available_percentage':available_percentage,
                'page_obj':page_obj,
                'inventory_categories':inventory_categories
            }
    return render(request , 'inventory.html' , context)


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
    
    status=['paid' ,'Paid','advance', 'Advance','advance']
    today_collection = payment.objects.filter(payment_date = today , payment_status__in = status).aggregate(Sum('amount'))['amount__sum'] or 0
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
        paginator = Paginator(payment_obj , 10)
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
        paginator = Paginator(payment_obj , 10)
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
    paginator = Paginator(payment_details , 10)
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
def Payment_form(request):
    if request.method == 'POST':
        form = new_payment(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Payment recorded successfully.')
            return redirect('payments')
    else:
        form = new_payment()
    return render(request, 'addpaymentform.html', {'form': form, 'page': 'payments'})


#used for download payments records
@login_required(login_url='login')
def download_payments_records(request):
    today = datetime.now()
    current_date = today.strftime('%d %b %Y')
    current_time = today.strftime('%I %M %p')
    #payments = payment.objects.all().order_by('-payment_id')
    payment_details = payment.objects.all().order_by('-payment_id')
    response  = HttpResponse(content_type = 'text/csv')
    response['content-Disposition'] = f'attachment; filename = Payment Records {current_time} {current_date}.csv'
    #write row heading
    writer = csv.writer(response)
    writer.writerow([
        'PAYMENT ID',
        'BOOKING ID',
        'CUSTOMER',
        'DATE',
        'METHOD',
        'AMOUNT',
        'REFERENCE',
        'STATUS'

    ])
    for payments in payment_details:
        writer.writerow([
            payments.payment_id,
            payments.booking.booking_id,
            payments.booking.customer_name,
            payments.payment_date,
            payments.method,
            payments.amount,
            payments.refference_num,
            payments.payment_status
        ])
    return response

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
    confirm_status = ['Paid' ,'paid', 'advance']
    pending_status = ['pending','Pending']
    yearly_expenses = expense.objects.filter(date__year = current_year , status__in = confirm_status).aggregate(Sum('amount'))['amount__sum'] or 0
    yearly_expenses_previous = expense.objects.filter(date__year = previous_year , status__in = confirm_status).aggregate(Sum('amount'))['amount__sum'] or 0
    yearly_expenses_per = ((yearly_expenses-yearly_expenses_previous) / yearly_expenses_previous) * 100 or 0
    previous_month = current_month - 1
    monthly_expenses = expense.objects.filter(date__month = current_month, date__year = current_year, status__in = confirm_status).aggregate(Sum('amount'))['amount__sum'] or 0
    monthly_expenses_previous = expense.objects.filter(date__month = previous_month,date__year = current_year, status__in =confirm_status).aggregate(Sum('amount'))['amount__sum'] or 0
    monthly_expenses_per =(( monthly_expenses - monthly_expenses_previous) / monthly_expenses_previous) * 100 or 0
    monthly_expenses_pending = expense.objects.filter(date__month = current_month, status__in = pending_status).aggregate(Sum('amount'))['amount__sum'] or 0
    calculate_pending = expense.objects.filter(status__in = pending_status ).count()
    largest_expense = expense.objects.all().aggregate(Max('amount'))['amount__max'] or 0
    expense_list = expense.objects.all().order_by('-expense_id')
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
        paginator =Paginator(expense_obj , 10)
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
        expense_list = expense.objects.all().order_by('-expense_id')
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
        'current__month':current__month,
        'calculate_pending':calculate_pending,
    } 
    return render(request , 'expenses.html' , context)
@login_required(login_url='login')
def expense_data_download(request):
    data = expense.objects.all().order_by('-expense_id')
    today = datetime.now()
    current_date = today.strftime('%d %b %Y')
    current_time = today.strftime('%I:%M %p')
    response = HttpResponse(content_type = 'text/csv')
    response['content-Disposition'] = f'attachment; filename = Expense Records {current_time} {current_date}.csv'
    writer = csv.writer(response)
    #write row heading

    writer.writerow([
        'EXPENSE_ID',
        'TITLE',
        'CATEGORY',
        'DATE',
        'AMOUNT',
        'PAID BY',
        'STATUS'
    ])
    for download in data:
        writer.writerow([
            download.expense_id,
            download.expense_title,
            download.expense_category,
            download.date,
            download.amount,
            download.paid_by,
            download.status
        ])
    return response
        

@login_required(login_url='login')
def Reports_view(request):
    today = timezone.localdate()
    current_month = today.strftime('%B')
    current__month = today.month
    previous_month_date = today.replace(day=1) - timedelta(days=1)
    previous_month = previous_month_date.month
    previous__month = previous_month_date.strftime('%B')
    current_year = today.year
    previous_year = current_year - 1
    status_confirmed = ['confirmed', 'Confirmed', 'confirm', 'Confirm' , 'Comfirmed']
    status_advance = ['advance', 'Advance']
    status_pending = ['Pending', 'pending','unpaid','not paid' , 'Unpaid','Notpaid']
    status_cancelled = ['cancelled', 'Cancelled', 'Cancel', 'Cancel']
    #Dashboard report backend logic starts here
    booking_count = newbooking.objects.filter(event_date__month=current__month, event_date__year=current_year).count()
    bookingcount_previous = newbooking.objects.filter(event_date__month=previous_month, event_date__year=previous_month_date.year).count()
    if bookingcount_previous <= 0:
        booking_count_percentage = 100
    if booking_count <= 0:
        booking_count_percentage = 0
    else:
        booking_count_percentage = ((booking_count - bookingcount_previous) / bookingcount_previous) * 100
    booking_created_count = newbooking.objects.filter(created_at__month=current__month, created_at__year=current_year).count()
    booking_created_count_previous = newbooking.objects.filter(created_at__month=previous_month, created_at__year=previous_month_date.year).count()
    total_revenue_current_month = newbooking.objects.filter( event_date__month=current__month, event_date__year=current_year).aggregate(Sum('hall_price'))['hall_price__sum'] or 0
    current_month_revenue_display = format_report_payment_amount(total_revenue_current_month)
    previous_month_revenue = newbooking.objects.filter(event_date__month=previous_month, event_date__year=previous_month_date.year).aggregate(Sum('hall_price'))['hall_price__sum'] or 0
    if previous_month_revenue == 0:
        total_revenue_percentage = 100
    elif total_revenue_current_month == 0:
        total_revenue_percentage = 0
    else:
        total_revenue_percentage = ((total_revenue_current_month - previous_month_revenue) / previous_month_revenue) * 100 
    status_confirm = ['confirmed', 'Confirmed', 'confirm', 'Confirm' , 'Comfirmed' , 'Advance' , 'advance']
    received_payment_current_month = newbooking.objects.filter(status__in  =status_confirm, event_date__month=current__month, event_date__year=current_year).aggregate(Sum('hall_price'))['hall_price__sum'] or 0
    received_payment_current_month_display = format_report_payment_amount(received_payment_current_month)
    received_payment_percentage = (received_payment_current_month / total_revenue_current_month) * 100 if total_revenue_current_month else 0
    current_month_expense = expense.objects.filter(date__month=current__month, date__year=current_year, status__in = ['Paid' ,'paid', 'advance']).aggregate(Sum('amount'))['amount__sum'] or 0
    current_month_expense_display = format_report_payment_amount(current_month_expense)
    previous_month_expense = expense.objects.filter(date__month=previous_month, date__year=previous_month_date.year, status__in = ['Paid' ,'paid', 'advance']).aggregate(Sum('amount'))['amount__sum'] or 0
    if previous_month_expense == 0:
        current_month_expense_percentage = 100
    elif current_month_expense == 0:
        current_month_expense_percentage = -100
    else:
        current_month_expense_percentage = ((current_month_expense - previous_month_expense) / previous_month_expense) * 100
    net_profit_current_month = received_payment_current_month - current_month_expense
    net_profit_current_month_display = format_report_payment_amount(net_profit_current_month)
    protif_margin = (net_profit_current_month / received_payment_current_month) * 100 if received_payment_current_month else 0

    staff_salary_status = staff.objects.aggregate(
        paid_count=Count('staff_id', filter=Q(Salary_status__iexact='Paid')),
        unpaid_count=Count('staff_id', filter=Q(Salary_status__iexact='Unpaid')),
    )
    salary_record_count = staff_salary_status['paid_count'] + staff_salary_status['unpaid_count']
    salary_completion_percentage = (
        staff_salary_status['paid_count'] / salary_record_count * 100
        if salary_record_count else 0
    )
    staff_salary_by_category = staff.objects.values('category').annotate(
        paid_count=Count('staff_id', filter=Q(Salary_status__iexact='Paid')),
        unpaid_count=Count('staff_id', filter=Q(Salary_status__iexact='Unpaid')),
        record_count=Count(
            'staff_id',
            filter=Q(Salary_status__iexact='Paid') | Q(Salary_status__iexact='Unpaid'),
        ),
    ).order_by('category')



    total_booking = newbooking.objects.filter(event_date__year = current_year).count()
    yearly_booking_confirm_count = newbooking.objects.filter(status__in = status_confirmed , event_date__year = current_year).count()
    yearly_booking_advance_count = newbooking.objects.filter(status__in = status_advance , event_date__year = current_year).count()
    yearly_booking_pending_count = newbooking.objects.filter(status__in = status_pending , event_date__year = current_year).count()
    yearly_booking_cancelled_count = newbooking.objects.filter(status__in = status_cancelled , event_date__year = current_year).count()
    yearly_confirm_booking_precentage = (yearly_booking_confirm_count/total_booking) * 100 if total_booking else 0
    yearly_advance_booking_precentage = (yearly_booking_advance_count/total_booking) * 100 if total_booking else 0
    yearly_pending_booking_precentage = (yearly_booking_pending_count/total_booking) * 100 if total_booking else 0
    yearly_canceled_booking_precentage = (yearly_booking_cancelled_count/total_booking) * 100 if total_booking else 0
    previous_yearly_booking_count = newbooking.objects.filter(event_date__year = previous_year).count()
    previous_yearly_booking_confirm_count = newbooking.objects.filter(status__in = status_confirmed , event_date__year = previous_year).count()
    previous_yearly_booking_advance_count = newbooking.objects.filter(status__in = status_advance , event_date__year = previous_year).count()
    previous_yearly_booking_pending_count = newbooking.objects.filter(status__in = status_pending , event_date__year = previous_year).count()
    previous_yearly_booking_cancelled_count = newbooking.objects.filter(status__in = status_cancelled , event_date__year = previous_year).count()
    previous_yearly_confirm_booking_precentage = (previous_yearly_booking_confirm_count/previous_yearly_booking_count) * 100 if previous_yearly_booking_count else 0
    previous_yearly_advance_booking_precentage = (previous_yearly_booking_advance_count/previous_yearly_booking_count) * 100 if previous_yearly_booking_count else 0
    previous_yearly_pending_booking_precentage = (previous_yearly_booking_pending_count/previous_yearly_booking_count) * 100 if previous_yearly_booking_count else 0
    previous_yearly_canceled_booking_precentage = (previous_yearly_booking_cancelled_count/previous_yearly_booking_count) * 100 if previous_yearly_booking_count else 0

    booking_confirm_count = newbooking.objects.filter(status__in = status_confirmed , event_date__month = current__month , event_date__year = current_year).count()
    booking_advance_count = newbooking.objects.filter(status__in = status_advance , event_date__month = current__month , event_date__year = current_year).count()
    booking_pending_count = newbooking.objects.filter(status__in = status_pending , event_date__month = current__month , event_date__year = current_year).count()
    booking_cancelled_count = newbooking.objects.filter(status__in = status_cancelled , event_date__month = current__month , event_date__year = current_year).count()
    confirm_booking_precentage = (booking_confirm_count/booking_count) * 100 if booking_count else 0
    advance_booking_precentage = (booking_advance_count/booking_count) * 100 if booking_count else 0
    pending_booking_precentage = (booking_pending_count/booking_count) * 100 if booking_count else 0
    canceled_booking_precentage = (booking_cancelled_count/booking_count) * 100 if booking_count else 0
    monthly_booking_status_segments, monthly_booking_status_donut = build_booking_status_donut(
        booking_count,
        {
            'confirmed': booking_confirm_count,
            'pending': booking_pending_count,
            'cancelled': booking_cancelled_count,
            'advance': booking_advance_count,
        },
    )
    yearly_booking_status_segments, yearly_booking_status_donut = build_booking_status_donut(
        total_booking,
        {
            'confirmed': yearly_booking_confirm_count,
            'pending': yearly_booking_pending_count,
            'cancelled': yearly_booking_cancelled_count,
            'advance': yearly_booking_advance_count,
        },
    )
    previous_year_booking_status_segments, previous_year_booking_status_donut = build_booking_status_donut(
        previous_yearly_booking_count,
        {
            'confirmed': previous_yearly_booking_confirm_count,
            'pending': previous_yearly_booking_pending_count,
            'cancelled': previous_yearly_booking_cancelled_count,
            'advance': previous_yearly_booking_advance_count,
        },
    )

    #Payment method distribution count code
    total_revenue= payment.objects.filter(payment_date__year = current_year).aggregate(Sum('amount'))['amount__sum'] or 0
    cash_payment = payment.objects.filter(method__in = ['cash','Cash'] , payment_date__year = current_year).aggregate(Sum('amount'))['amount__sum'] or 0
    card_payment = payment.objects.filter(method__in = ['card','Card'] , payment_date__year = current_year).aggregate(Sum('amount'))['amount__sum'] or 0
    online_payment = payment.objects.filter(method__in = ['online','Online'] , payment_date__year = current_year).aggregate(Sum('amount'))['amount__sum'] or 0
    bank_transfer_payment = payment.objects.filter(method__in = ['bank transfer','Bank Transfer'] , payment_date__year = current_year).aggregate(Sum('amount'))['amount__sum'] or 0
    cash_payment_display = format_report_payment_amount(cash_payment)
    card_payment_display = format_report_payment_amount(card_payment)
    online_payment_display = format_report_payment_amount(online_payment)
    bank_transfer_payment_display = format_report_payment_amount(bank_transfer_payment)
    total_payment_display = format_report_payment_amount(total_revenue)
    cash_payment_percentage = (cash_payment/total_revenue) * 100 if total_revenue else 0
    card_payment_percentage = (card_payment/total_revenue) * 100 if total_revenue else 0
    online_payment_percentage = (online_payment/total_revenue) * 100 if total_revenue else 0
    bank_transfer_payment_percentage = (bank_transfer_payment/total_revenue) * 100 if total_revenue else 0

    #Hall performance backend logic starts here
    portion_a = newbooking.objects.filter(event_hall = 'A' , event_date__month = current__month , event_date__year = current_year).count()
    portion_b = newbooking.objects.filter(event_hall = 'B' , event_date__month = current__month , event_date__year = current_year).count()
    portion_c = newbooking.objects.filter(event_hall = 'C' , event_date__month = current__month , event_date__year = current_year).count()
    portion_A_b = newbooking.objects.filter(event_hall = 'A and B' , event_date__month = current__month , event_date__year = current_year).count()
    portion_b_c = newbooking.objects.filter(event_hall = 'B and C' , event_date__month = current__month , event_date__year = current_year).count()
    portion_a_price = newbooking.objects.filter(event_hall = 'A' , event_date__month = current__month , event_date__year = current_year).aggregate(Sum('hall_price'))['hall_price__sum'] or 0
    portion_b_price = newbooking.objects.filter(event_hall = 'B' , event_date__month = current__month , event_date__year = current_year).aggregate(Sum('hall_price'))['hall_price__sum'] or 0
    portion_c_price = newbooking.objects.filter(event_hall = 'C' , event_date__month = current__month , event_date__year = current_year).aggregate(Sum('hall_price'))['hall_price__sum'] or 0
    portion_A_b_price = newbooking.objects.filter(event_hall = 'A and B' , event_date__month = current__month , event_date__year = current_year).aggregate(Sum('hall_price'))['hall_price__sum'] or 0
    portion_b_c_price = newbooking.objects.filter(event_hall = 'B and C' , event_date__month = current__month , event_date__year = current_year).aggregate(Sum('hall_price'))['hall_price__sum'] or 0
    portion_a_display = format_report_payment_amount(portion_a_price)
    portion_b_display = format_report_payment_amount(portion_b_price)
    portion_c_display = format_report_payment_amount(portion_c_price)
    portion_A_b_display = format_report_payment_amount(portion_A_b_price)
    portion_b_c_display = format_report_payment_amount(portion_b_c_price)
    portions = {
        'Hall A': portion_a,
        'Hall B': portion_b,
        'Hall C': portion_c,
        'Hall A and B': portion_A_b,
        'Hall B and C': portion_b_c,
    }
    top_hall_portion = max(portions, key=portions.get) if portions else None

    #Financial performance backend logic starts here
    Received_amount = payment.objects.filter(payment_date__year = current_year , payment_status__in = ['paid' , 'Paid' , 'advance', 'Advance']).aggregate(Sum('amount'))['amount__sum'] or 0
    Received_amount_display = format_report_payment_amount(Received_amount)
    total_expenses = expense.objects.filter(date__year = current_year , status__in = ['paid' , 'Paid']).aggregate(Sum('amount'))['amount__sum'] or 0
    total_expenses_display = format_report_payment_amount(total_expenses)
    net_profit = Received_amount - total_expenses
    net_profit_display = format_report_payment_amount(net_profit)
    recieved_amount_percentage = (Received_amount/total_revenue) * 100 if total_revenue else 0

    # START: Build the annual financial report chart through the current year.
    financial_year_start = current_year - 4
    annual_received_amounts = {
        row['year']: float(row['total'] or 0)
        for row in payment.objects.filter(
            payment_date__year__gte=financial_year_start,
            payment_date__year__lte=current_year,
        ).filter(
            Q(payment_status__iexact='Paid') | Q(payment_status__iexact='Advance'),
        ).annotate(
            year=ExtractYear('payment_date'),
        ).values('year').annotate(
            total=Sum('amount'),
        )
    }
    annual_paid_expenses = {
        row['year']: row['total'] or 0
        for row in expense.objects.filter(
            date__year__gte=financial_year_start,
            date__year__lte=current_year,
            status__iexact='Paid',
        ).annotate(
            year=ExtractYear('date'),
        ).values('year').annotate(
            total=Sum('amount'),
        )
    }
    financial_periods = [
        {
            'year': year,
            'revenue': annual_received_amounts.get(year, 0),
            'expenses': annual_paid_expenses.get(year, 0),
        }
        for year in range(financial_year_start, current_year + 1)
    ]
    for period in financial_periods:
        period['profit'] = period['revenue'] - period['expenses']

    financial_values = [
        value
        for period in financial_periods
        for value in (period['revenue'], period['profit'])
    ]
    financial_minimum = min([0, *financial_values])
    financial_maximum = max([0, *financial_values])
    raw_axis_step = (financial_maximum - financial_minimum) / 4
    if raw_axis_step:
        axis_magnitude = 10 ** math.floor(math.log10(raw_axis_step))
        normalized_axis_step = raw_axis_step / axis_magnitude
        if normalized_axis_step <= 1:
            financial_axis_step = axis_magnitude
        elif normalized_axis_step <= 2:
            financial_axis_step = 2 * axis_magnitude
        elif normalized_axis_step <= 5:
            financial_axis_step = 5 * axis_magnitude
        else:
            financial_axis_step = 10 * axis_magnitude
    else:
        financial_axis_step = 1

    financial_axis_minimum = math.floor(financial_minimum / financial_axis_step) * financial_axis_step
    financial_axis_maximum = math.ceil(financial_maximum / financial_axis_step) * financial_axis_step
    if financial_axis_minimum == financial_axis_maximum:
        financial_axis_maximum = financial_axis_minimum + financial_axis_step

    financial_expense_maximum = max(period['expenses'] for period in financial_periods)
    if financial_expense_maximum:
        raw_expense_axis_step = financial_expense_maximum / 4
        expense_axis_magnitude = 10 ** math.floor(math.log10(raw_expense_axis_step))
        normalized_expense_axis_step = raw_expense_axis_step / expense_axis_magnitude
        if normalized_expense_axis_step <= 1:
            financial_expense_axis_step = expense_axis_magnitude
        elif normalized_expense_axis_step <= 2:
            financial_expense_axis_step = 2 * expense_axis_magnitude
        elif normalized_expense_axis_step <= 5:
            financial_expense_axis_step = 5 * expense_axis_magnitude
        else:
            financial_expense_axis_step = 10 * expense_axis_magnitude
        financial_expense_axis_maximum = (
            math.ceil(financial_expense_maximum / financial_expense_axis_step)
            * financial_expense_axis_step
        )
    else:
        financial_expense_axis_step = 1
        financial_expense_axis_maximum = 4

    chart_top = 22
    chart_bottom = 198
    chart_height = chart_bottom - chart_top
    financial_axis_ticks = []
    tick_value = financial_axis_minimum
    while tick_value <= financial_axis_maximum + financial_axis_step / 1000:
        tick_y = chart_bottom - (
            (tick_value - financial_axis_minimum)
            / (financial_axis_maximum - financial_axis_minimum)
            * chart_height
        )
        financial_axis_ticks.append({
            'value': tick_value,
            'label': format_report_chart_axis_label(tick_value),
            'y': f'{tick_y:.2f}',
            'label_y': f'{tick_y + 4:.2f}',
        })
        tick_value += financial_axis_step

    financial_expense_axis_ticks = []
    tick_value = 0
    while tick_value <= financial_expense_axis_maximum + financial_expense_axis_step / 1000:
        tick_y = chart_bottom - (
            tick_value / financial_expense_axis_maximum * chart_height
        )
        financial_expense_axis_ticks.append({
            'label': format_report_chart_axis_label(tick_value),
            'y': f'{tick_y:.2f}',
            'label_y': f'{tick_y + 4:.2f}',
        })
        tick_value += financial_expense_axis_step

    zero_y = chart_bottom - (
        (0 - financial_axis_minimum)
        / (financial_axis_maximum - financial_axis_minimum)
        * chart_height
    )
    for index, period in enumerate(financial_periods):
        baseline_x = 68 + index * 150
        period['revenue_x'] = f'{baseline_x:.1f}'
        period['expenses_x'] = f'{baseline_x + 38:.1f}'
        period['profit_x'] = f'{baseline_x + 66:.1f}'
        period['label_x'] = f'{baseline_x + 25:.1f}'
        for key in ('revenue', 'profit'):
            value_y = chart_bottom - (
                (period[key] - financial_axis_minimum)
                / (financial_axis_maximum - financial_axis_minimum)
                * chart_height
            )
            period[f'{key}_y'] = f'{min(value_y, zero_y):.2f}'
            period[f'{key}_height'] = f'{abs(value_y - zero_y):.2f}'
        expense_y = chart_bottom - (
            period['expenses'] / financial_expense_axis_maximum * chart_height
        )
        period['expenses_y'] = f'{expense_y:.2f}'
        period['expenses_height'] = f'{chart_bottom - expense_y:.2f}'

    financial_zero_y = f'{zero_y:.2f}'
    # END: Annual financial chart data and dynamic axis are ready for the report template.

    # Compare monthly booking creation dates with scheduled event dates.
    month_labels = [date(current_year, month, 1).strftime('%B') for month in range(1, 13)]
    event_bookings_by_month = {
        row['month']: row['total']
        for row in newbooking.objects.filter(event_date__year=current_year)
        .annotate(month=ExtractMonth('event_date'))
        .values('month')
        .annotate(total=Count('booking_id'))
    }
    created_bookings_by_month = {
        row['month']: row['total']
        for row in newbooking.objects.filter(created_at__year=current_year)
        .annotate(month=ExtractMonth('created_at'))
        .values('month')
        .annotate(total=Count('booking_id'))
    }
    booking_chart_data = {
        'labels': month_labels,
        'datasets': [
            {
                'label': 'Booking created',
                'data': [created_bookings_by_month.get(month, 0) for month in range(1, 13)],
            },
            {
                'label': 'Event this Month',
                'data': [event_bookings_by_month.get(month, 0) for month in range(1, 13)],
            },
        ],
    }
    booking_chart_aria_label = (
        f"Monthly bookings created and event dates for {current_year}."
    )

    context = {
        'current_month': current_month,
        'current__month': current__month,
        'previous__month': previous__month,
        'previous_month_year': previous_month_date.year,
        'current_year': current_year,
        'previous_year': previous_year,
        'booking_count':booking_count,
        'booking_count_percentage':booking_count_percentage,
        'received_payment_current_month_display':received_payment_current_month_display,
        'current_month_expense_display':current_month_expense_display,
        'current_month_expense_percentage':current_month_expense_percentage,
        'net_profit_current_month_display':net_profit_current_month_display,
        'protif_margin':protif_margin,
        'staff_salary_paid_count':staff_salary_status['paid_count'],
        'staff_salary_unpaid_count':staff_salary_status['unpaid_count'],
        'salary_completion_percentage':salary_completion_percentage,
        'staff_salary_by_category':staff_salary_by_category,
        'received_payment_percentage':received_payment_percentage,
        'total_revenue_percentage':total_revenue_percentage,
        'current_month_revenue_display':current_month_revenue_display,
        'bookingcount_previous':bookingcount_previous,
        'booking_created_count':booking_created_count,
        'booking_created_count_previous':booking_created_count_previous,
        'booking_chart_data': booking_chart_data,
        'booking_chart_aria_label': booking_chart_aria_label,
        'total_booking':total_booking,
        'booking_confirm_count':booking_confirm_count,
        'booking_advance_count':booking_advance_count,
        'booking_pending_count':booking_pending_count,
        'booking_cancelled_count':booking_cancelled_count,
        'monthly_booking_status_segments':monthly_booking_status_segments,
        'monthly_booking_status_donut':monthly_booking_status_donut,
        'yearly_booking_status_segments':yearly_booking_status_segments,
        'yearly_booking_status_donut':yearly_booking_status_donut,
        'previous_year_booking_status_segments':previous_year_booking_status_segments,
        'previous_year_booking_status_donut':previous_year_booking_status_donut,
        'confirm_booking_precentage':confirm_booking_precentage,
        'advance_booking_precentage':advance_booking_precentage,
        'pending_booking_precentage':pending_booking_precentage,
        'canceled_booking_precentage':canceled_booking_precentage,
        'yearly_booking_confirm_count':yearly_booking_confirm_count,
        'yearly_booking_advance_count':yearly_booking_advance_count,
        'yearly_booking_pending_count':yearly_booking_pending_count,
        'yearly_booking_cancelled_count':yearly_booking_cancelled_count,
        'yearly_confirm_booking_precentage':yearly_confirm_booking_precentage,
        'yearly_advance_booking_precentage':yearly_advance_booking_precentage,
        'yearly_pending_booking_precentage':yearly_pending_booking_precentage,
        'yearly_canceled_booking_precentage':yearly_canceled_booking_precentage,
        'previous_yearly_booking_count':previous_yearly_booking_count,
        'previous_yearly_booking_confirm_count':previous_yearly_booking_confirm_count,
        'previous_yearly_booking_advance_count':previous_yearly_booking_advance_count,
        'previous_yearly_booking_pending_count':previous_yearly_booking_pending_count,
        'previous_yearly_booking_cancelled_count':previous_yearly_booking_cancelled_count,
        'previous_yearly_confirm_booking_precentage':previous_yearly_confirm_booking_precentage,
        'previous_yearly_advance_booking_precentage':previous_yearly_advance_booking_precentage,
        'previous_yearly_pending_booking_precentage':previous_yearly_pending_booking_precentage,
        'previous_yearly_canceled_booking_precentage':previous_yearly_canceled_booking_precentage,
        'cash_payment':cash_payment,
        'card_payment':card_payment,
        'online_payment':online_payment,
        'bank_transfer_payment':bank_transfer_payment,
        'cash_payment_display':cash_payment_display,
        'card_payment_display':card_payment_display,
        'online_payment_display':online_payment_display,
        'bank_transfer_payment_display':bank_transfer_payment_display,
        'total_payment_display':total_payment_display,
        'cash_payment_percentage':cash_payment_percentage,
        'card_payment_percentage':card_payment_percentage,
        'online_payment_percentage':online_payment_percentage,
        'bank_transfer_payment_percentage':bank_transfer_payment_percentage,
        #hall performance context data
        'portion_a':portion_a,
        'portion_b':portion_b,
        'portion_c':portion_c,
        'portion_A_b':portion_A_b,
        'portion_b_c':portion_b_c,
        'portion_a_display':portion_a_display,
        'portion_b_display':portion_b_display,
        'portion_c_display':portion_c_display,
        'portion_A_b_display':portion_A_b_display,
        'portion_b_c_display':portion_b_c_display,
        'top_hall_portion':top_hall_portion,
        #financial performance context data
        'received_amount_display':Received_amount_display,
        'total_expenses_display':total_expenses_display,
        'net_profit_display':net_profit_display,
        'recieved_amount_percentage':recieved_amount_percentage,
        'financial_year_start':financial_year_start,
        'financial_periods':financial_periods,
        'financial_axis_ticks':financial_axis_ticks,
        'financial_expense_axis_ticks':financial_expense_axis_ticks,
        'financial_zero_y':financial_zero_y,
    }
    return render(request , 'reports.html' , context)


@login_required(login_url='login')
def export_reports_csv(request):
    today = timezone.localdate()
    current_year = today.year
    current_month = today.month
    previous_month_date = today.replace(day=1) - timedelta(days=1)

    def safe_csv_text(value):
        value = str(value)
        if value.lstrip(' \t\r\n').startswith(('=', '+', '-', '@')):
            return f"'{value}"
        return value

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response.write('\ufeff')
    response['Content-Disposition'] = (
        f'attachment; filename="hallmaster-report-{current_year}.csv"'
    )
    writer = csv.writer(response)
    writer.writerow(['Section', 'Period', 'Metric', 'Value'])

    current_month_bookings = newbooking.objects.filter(
        event_date__year=current_year,
        event_date__month=current_month,
    )
    previous_month_bookings = newbooking.objects.filter(
        event_date__year=previous_month_date.year,
        event_date__month=previous_month_date.month,
    )
    current_month_created = newbooking.objects.filter(
        created_at__year=current_year,
        created_at__month=current_month,
    )
    previous_month_created = newbooking.objects.filter(
        created_at__year=previous_month_date.year,
        created_at__month=previous_month_date.month,
    )
    writer.writerow(['Bookings', today.strftime('%B %Y'), 'Bookings by event date', current_month_bookings.count()])
    writer.writerow(['Bookings', today.strftime('%B %Y'), 'Bookings created', current_month_created.count()])
    writer.writerow(['Bookings', previous_month_date.strftime('%B %Y'), 'Bookings by event date', previous_month_bookings.count()])
    writer.writerow(['Bookings', previous_month_date.strftime('%B %Y'), 'Bookings created', previous_month_created.count()])

    yearly_bookings = newbooking.objects.filter(event_date__year=current_year)
    writer.writerow(['Bookings', current_year, 'Total bookings', yearly_bookings.count()])
    for row in yearly_bookings.values('status').annotate(total=Count('booking_id')).order_by('status'):
        writer.writerow(['Booking status', current_year, safe_csv_text(row['status']), row['total']])

    yearly_payments = payment.objects.filter(payment_date__year=current_year)
    total_payments = yearly_payments.aggregate(total=Sum('amount'))['total'] or 0
    yearly_expenses = expense.objects.filter(date__year=current_year)
    paid_expenses = yearly_expenses.filter(status__iexact='Paid')
    paid_expense_total = paid_expenses.aggregate(total=Sum('amount'))['total'] or 0
    writer.writerow(['Financials', current_year, 'Payments recorded', total_payments])
    writer.writerow(['Financials', current_year, 'Paid expenses', paid_expense_total])
    writer.writerow(['Financials', current_year, 'Net after paid expenses', total_payments - paid_expense_total])

    for row in yearly_payments.values('method').annotate(
        payment_count=Count('payment_id'),
        total=Sum('amount'),
    ).order_by('method'):
        method_label = safe_csv_text(f"{row['method']} ({row['payment_count']} payments)")
        writer.writerow(['Payment method', current_year, method_label, row['total'] or 0])

    for row in yearly_expenses.values('expense_category').annotate(
        expense_count=Count('expense_id'),
        total=Sum('amount'),
    ).order_by('expense_category'):
        category_label = safe_csv_text(f"{row['expense_category']} ({row['expense_count']} expenses)")
        writer.writerow(['Expense category', current_year, category_label, row['total'] or 0])

    monthly_halls = current_month_bookings.values('event_hall').annotate(
        booking_count=Count('booking_id'),
        revenue=Sum('hall_price'),
    ).order_by('event_hall')
    for row in monthly_halls:
        writer.writerow([
            'Hall performance',
            today.strftime('%B %Y'),
            f"{safe_csv_text(row['event_hall'])} bookings",
            row['booking_count'],
        ])
        writer.writerow([
            'Hall performance',
            today.strftime('%B %Y'),
            f"{safe_csv_text(row['event_hall'])} revenue",
            row['revenue'] or 0,
        ])

    salary_totals = staff.objects.aggregate(
        paid=Count('staff_id', filter=Q(Salary_status__iexact='Paid')),
        unpaid=Count('staff_id', filter=Q(Salary_status__iexact='Unpaid')),
    )
    writer.writerow(['Staff salaries', 'All records', 'Paid staff', salary_totals['paid']])
    writer.writerow(['Staff salaries', 'All records', 'Unpaid staff', salary_totals['unpaid']])
    for row in staff.objects.values('category').annotate(
        paid=Count('staff_id', filter=Q(Salary_status__iexact='Paid')),
        unpaid=Count('staff_id', filter=Q(Salary_status__iexact='Unpaid')),
    ).order_by('category'):
        category = safe_csv_text(row['category'])
        writer.writerow(['Staff salaries', category, 'Paid staff', row['paid']])
        writer.writerow(['Staff salaries', category, 'Unpaid staff', row['unpaid']])

    return response

@login_required(login_url='login')
def Staff_view(request):
    total_staff = staff.objects.all().count()
    active_staff = staff.objects.filter(staff_status = 'active').count()
    manager_count = staff.objects.filter(staff_role = 'manager').count()
    search = request.GET.get('search' , '')
    status_filter = request.GET.get('status', '')
    staff_list = staff.objects.all().order_by('-staff_id')
    if search:
        staff_list = staff_list.filter(
            Q(staff_id__icontains = search)|
            Q(staff_name__icontains = search)|
            Q(staff_email__icontains = search)|
            Q(staff_number__icontains = search)|
            Q(staff_role__icontains = search)|
            Q(staff_join_date__icontains = search)|
            Q(staff_nic_num__icontains = search)
        )
    if status_filter:
        staff_list = staff_list.filter(staff_status__iexact=status_filter)
    paginator = Paginator(staff_list, 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    context={
        'staff_list': staff_list,
        'page_obj': page_obj,
        'total_staff': total_staff,
        'active_staff': active_staff,
        'manager_count': manager_count,
        'search': search,
        'status_filter': status_filter,
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
    inventory_categories = InventoryCategory.objects.all()

    if request.method =='POST':
        form = new_inventory(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request , "Inventory created successfully.")
            return redirect('inventoryform')
        else:
            messages.error(request , "Please correct the errors below.")
    else:
        form  = new_inventory()
    context = {'form' : form,
               'inventory_categories':inventory_categories
               }
    return render(request , 'addinventory.html' , context)
@login_required(login_url='login')
def New_inventory_category(request):
    if request.method =='POST':
        form = new_inventory_category(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request , "Inventory category created successfully.")
            return redirect('inventory')
        else:
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
        today = timezone.now()
        month = today.month
        pre = today.strftime('%b')
        next = month + 1
        todays = datetime.now().month
        previous_month = today +1
        previous_month_name = today.strftime("%b")
        print(previous_month_name)
        context = {
            'pre':pre,
            'next':next,
            'today':today,
        }
        return render(request , "testerbase.html" ,context)

# Create your views here
