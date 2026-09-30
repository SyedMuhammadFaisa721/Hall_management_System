from django.shortcuts import render , redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm

def login(request):
    if request.method == "GET":
        return render(request, 'login.html')
    if request.method == "POST":
        form = AuthenticationForm(data= request.data)
        if form.is_valid():
            user = form.get_user
            login(request , user)
            return redirect("dashboard")
        else:
            form = AuthenticationForm()
        return render(request , 'login.html', {'form':form})
HALLMASTER_TEMPLATES = {
    'dashboard': 'dashboard.html',
    'bookings': 'bookings.html',
    'bookingform': 'bookingform.html',
    'availability': 'availability.html',
    'customers': 'customers.html',
    'packages': 'packages.html',
    'payments': 'payments.html',
    'invoices': 'invoices.html',
    'expenses': 'expenses.html',
    'reports': 'reports.html',
    'staff': 'staff.html',
    'notifications': 'notifications.html',
    'settings': 'settings.html',
}


def hallmaster_page(request, page='dashboard'):
    return render(request, HALLMASTER_TEMPLATES[page], {'page': page})


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
    return render(request, 'inventory.html')

# Create your views here.
