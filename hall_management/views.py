import logging
import random
import secrets
import string
from decimal import Decimal
from html import unescape
from smtplib import SMTPException

from django.conf import settings
from django.shortcuts import get_object_or_404, render , redirect
from django.contrib.auth import login, logout
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied
from django.core import signing
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import EmailMultiAlternatives, get_connection
from django.core.signing import BadSignature
from django.db import transaction
from .form import hallmaster_user_creation, new_booking , new_expense ,new_inventory ,new_staff ,new_inventory_category, loginform , new_payment
from django.views.generic import ListView
from django.contrib import messages
from django.http import Http404, HttpResponse, JsonResponse
from django.template.loader import render_to_string
from django.urls import reverse
from django.db.models import Count, Q
from django.db.models.functions import ExtractMonth, ExtractYear
from django.core.paginator import Paginator
from .models import Hall_portion, newbooking , staff , expense , Inventory, InventoryCategory , payment
from django.db.models import Sum ,Max 
from datetime import date , datetime , timedelta
from django.utils.crypto import get_random_string
from django.utils.html import strip_tags
from django.utils.text import slugify
from django.views.decorators.http import require_http_methods, require_POST
import csv
import math
from io import BytesIO
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Flowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from django.utils.html import escape

logger = logging.getLogger(__name__)
MANAGER_EMAIL_VERIFICATION_SALT = 'hall_management.manager-email-verification'
MANAGER_EMAIL_VERIFICATION_MAX_AGE = 24 * 60 * 60


def _send_template_email(subject, template_name, context, recipient):
    mailers = getattr(settings, 'MAILERS', None)
    if not mailers or 'default' not in mailers:
        raise ImproperlyConfigured('Configure MAILERS["default"] before sending email.')

    mailer = mailers['default']
    options = mailer.get('OPTIONS', {})
    connection = get_connection(
        backend=mailer['BACKEND'],
        **options,
    )
    html_content = render_to_string(template_name, context)
    text_content = unescape(strip_tags(html_content)).strip()
    message = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=options.get('username') or settings.DEFAULT_FROM_EMAIL,
        to=[recipient],
        connection=connection,
    )
    message.attach_alternative(html_content, 'text/html')
    if message.send(fail_silently=False) != 1:
        raise SMTPException('The email backend did not send the message.')


class _InvoiceLogo(Flowable):
    def __init__(self):
        super().__init__()
        self.width = 46
        self.height = 46

    def draw(self):
        self.canv.setFillColor(colors.HexColor('#c7a864'))
        self.canv.roundRect(0, 0, self.width, self.height, 9, fill=1, stroke=0)
        self.canv.setFillColor(colors.HexColor('#241d10'))
        self.canv.setFont('Times-Bold', 16)
        self.canv.drawCentredString(self.width / 2, 15, 'HM')


def _invoice_paragraph(value, style):
    return Paragraph(escape(str(value)), style)


def _build_invoice_pdf(invoice, invoice_id):
    ink = colors.HexColor('#20211f')
    muted = colors.HexColor('#73736c')
    gold = colors.HexColor('#a9864b')
    cream = colors.HexColor('#fdfcf9')
    line = colors.HexColor('#e7e4de')
    page_width, page_height = A4
    content_width = page_width - 32 * mm
    output = BytesIO()

    def paint_page(canvas, document):
        canvas.saveState()
        canvas.setFillColor(cream)
        canvas.rect(0, 0, page_width, page_height, fill=1, stroke=0)
        canvas.setFillColor(gold)
        canvas.rect(0, page_height - 3, page_width, 3, fill=1, stroke=0)
        canvas.restoreState()

    doc = SimpleDocTemplate(
        output,
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=19 * mm,
        bottomMargin=12 * mm,
    )
    styles = {
        'brand': ParagraphStyle(
            'InvoiceBrand', fontName='Helvetica-Bold', fontSize=11,
            leading=14, textColor=ink,
        ),
        'brand_sub': ParagraphStyle(
            'InvoiceBrandSub', fontName='Helvetica', fontSize=7.5,
            leading=11, textColor=muted,
        ),
        'invoice_word': ParagraphStyle(
            'InvoiceWord', fontName='Times-Roman', fontSize=20,
            leading=23, textColor=gold, alignment=TA_RIGHT,
        ),
        'right': ParagraphStyle(
            'InvoiceRight', fontName='Helvetica-Bold', fontSize=9,
            leading=12, textColor=ink, alignment=TA_RIGHT,
        ),
        'status': ParagraphStyle(
            'InvoiceStatus', fontName='Helvetica', fontSize=8,
            leading=11, textColor=gold, alignment=TA_RIGHT,
        ),
        'label': ParagraphStyle(
            'InvoiceLabel', fontName='Helvetica-Bold', fontSize=9,
            leading=12, textColor=ink,
        ),
        'name': ParagraphStyle(
            'InvoiceCustomer', fontName='Times-Bold', fontSize=18,
            leading=22, textColor=ink,
        ),
        'body': ParagraphStyle(
            'InvoiceBody', fontName='Helvetica', fontSize=9.5,
            leading=14, textColor=ink,
        ),
        'muted': ParagraphStyle(
            'InvoiceMuted', fontName='Helvetica', fontSize=8.5,
            leading=12, textColor=muted,
        ),
        'meta_label': ParagraphStyle(
            'InvoiceMetaLabel', fontName='Helvetica-Bold', fontSize=8,
            leading=10, textColor=ink,
        ),
        'meta_value': ParagraphStyle(
            'InvoiceMetaValue', fontName='Helvetica-Bold', fontSize=9,
            leading=12, textColor=ink,
        ),
        'table_head': ParagraphStyle(
            'InvoiceTableHead', fontName='Helvetica-Bold', fontSize=8,
            leading=10, textColor=muted,
        ),
        'item': ParagraphStyle(
            'InvoiceItem', fontName='Helvetica-Bold', fontSize=9,
            leading=12, textColor=ink,
        ),
        'item_detail': ParagraphStyle(
            'InvoiceItemDetail', fontName='Helvetica', fontSize=8,
            leading=11, textColor=muted,
        ),
        'note': ParagraphStyle(
            'InvoiceNote', fontName='Helvetica', fontSize=8.5,
            leading=13, textColor=muted,
        ),
        'term': ParagraphStyle(
            'InvoiceTerm', fontName='Helvetica', fontSize=7.5,
            leading=10, textColor=muted,
        ),
        'footer': ParagraphStyle(
            'InvoiceFooter', fontName='Helvetica', fontSize=7.5,
            leading=10, textColor=muted,
        ),
    }

    def p(value, style):
        return _invoice_paragraph(value, styles[style])

    header_meta = [
        p('INVOICE', 'invoice_word'),
        p(invoice_id, 'right'),
        p(invoice['status'].capitalize(), 'status'),
    ]
    header = Table(
        [[
            _InvoiceLogo(),
            [
                p('ROYAL PALACE HALL', 'brand'),
                p('EVENTS & HOSPITALITY', 'brand_sub'),
            ],
            header_meta,
        ]],
        colWidths=[54, content_width - 54 - 125, 125],
    )
    header.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 14),
        ('LINEBELOW', (0, 0), (-1, -1), 0.7, line),
    ]))

    def meta_cell(label, value):
        return [p(label, 'meta_label'), p(value, 'meta_value')]

    meta = Table(
        [
            [meta_cell('BOOKING ID', invoice['booking']), meta_cell('EVENT DATE', invoice['event_date'])],
            [meta_cell('ISSUED ON', invoice['issued']), meta_cell('DUE DATE', invoice['due'])],
        ],
        colWidths=[content_width * .24, content_width * .23],
    )
    meta.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
    ]))
    customer = [
        p('BILLED TO', 'label'),
        Spacer(1, 6),
        p(invoice['customer'], 'name'),
        Spacer(1, 3),
        p(f'Email: {invoice["customer_email"]}', 'muted'),
        p(f'Event: {invoice["event"]}', 'muted'),
        p(f'Portion: {invoice["venue"]}', 'muted'),
    ]
    details = Table(
        [[customer, meta]],
        colWidths=[content_width * .53, content_width * .47],
    )
    details.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 19),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 19),
    ]))

    item_rows = [[
        p('SERVICE', 'table_head'),
        p('QTY', 'table_head'),
        p('RATE', 'table_head'),
        p('AMOUNT', 'table_head'),
    ]]
    for item in invoice['items']:
        item_rows.append([
            [p(item['description'], 'item'), p(item['detail'], 'item_detail')],
            p(item['quantity'], 'body'),
            p(f'Rs {item["rate"]}', 'body'),
            p(f'Rs {item["amount"]}', 'body'),
        ])
    item_widths = [
        content_width * .48,
        content_width * .10,
        content_width * .21,
        content_width * .21,
    ]
    items = Table(item_rows, colWidths=item_widths, repeatRows=1)
    items.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 9),
        ('TOPPADDING', (0, 1), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 12),
        ('LINEABOVE', (0, 0), (-1, 0), 0.7, line),
        ('LINEBELOW', (0, 0), (-1, 0), 0.7, line),
        ('LINEBELOW', (0, 1), (-1, -1), 0.6, colors.HexColor('#efede8')),
    ]))

    totals = Table([
        [p('Subtotal', 'muted'), p(f'Rs {invoice["total"]}', 'right')],
        [p('Amount paid', 'muted'), p(f'Rs {invoice["paid"]}', 'right')],
        [p('Balance due', 'label'), p(f'Rs {invoice["balance"]}', 'right')],
    ], colWidths=[content_width * .24, content_width * .20])
    totals.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, 1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, 1), 7),
        ('TEXTCOLOR', (1, 1), (1, 1), colors.HexColor('#42785e')),
        ('BACKGROUND', (0, 2), (-1, 2), colors.HexColor('#f7f2e8')),
        ('BOX', (0, 2), (-1, 2), 0.8, colors.HexColor('#e8dfcc')),
        ('TOPPADDING', (0, 2), (-1, 2), 11),
        ('BOTTOMPADDING', (0, 2), (-1, 2), 11),
    ]))
    summary = Table([[
        [
            p('PAYMENT NOTE', 'label'),
            Spacer(1, 8),
            Paragraph(
                f'Please include <b>{escape(invoice_id)}</b> as the payment reference.',
                styles['note'],
            ),
            Spacer(1, 6),
            p('Thank you for choosing Royal Palace Hall.', 'note'),
        ],
        totals,
    ]], colWidths=[content_width * .55, content_width * .45])
    summary.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (0, 0), 14),
        ('RIGHTPADDING', (1, 0), (1, 0), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 20),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 20),
    ]))

    terms = [
        'Please settle the outstanding balance by the due date shown on this invoice.',
        'Changes to guest count, event timing, venue setup, or selected services may affect the final amount.',
        'Additional services not listed on this invoice are not included and may be charged separately.',
        'Cancellation or rescheduling requests are handled under the terms agreed in the booking confirmation.',
        'Cancellation or rescheduling requests are handled under the terms agreed in the booking confirmation.',
        'Cancellation or rescheduling requests are handled under the terms agreed in the booking confirmation.',
        'Cancellation or rescheduling requests are handled under the terms agreed in the booking confirmation.',
    ]
    term_rows = []
    for index in range(0, len(terms), 2):
        term_rows.append([
            p(f'{index + 1}. {terms[index]}', 'term'),
            p(f'{index + 2}. {terms[index + 1]}', 'term') if index + 1 < len(terms) else '',
        ])
    terms_table = Table(term_rows, colWidths=[content_width * .5, content_width * .5])
    terms_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    terms_heading = Table([[
        p('TERMS & CONDITIONS', 'label'),
        p('Payment is due by the event date.', 'muted'),
    ]], colWidths=[content_width * .65, content_width * .35])
    terms_heading.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 15),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ('LINEABOVE', (0, 0), (-1, -1), 0.7, line),
    ]))
    footer = Table([
        [
            p('ROYAL PALACE HALL', 'footer'),
            p('Karachi, Pakistan', 'footer'),
            p(invoice_id, 'footer'),
        ],
        [
            p('HallMaster (C) 2026 - Secure Venue Management System.', 'footer'),
            '',
            p('Design and Developed by Syed Muhammad Faisal', 'footer'),
        ],
    ], colWidths=[content_width * .4, content_width * .3, content_width * .3])
    footer.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
        ('SPAN', (0, 1), (1, 1)),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 11),
        ('TOPPADDING', (0, 1), (-1, 1), 9),
        ('LINEABOVE', (0, 0), (-1, 0), 0.7, line),
        ('LINEABOVE', (0, 1), (-1, 1), 0.5, colors.HexColor('#efede8')),
    ]))

    story = [
        header,
        details,
        items,
        summary,
        terms_heading,
        terms_table,
        Spacer(1, 12),
        footer,
    ]
    doc.build(story, onFirstPage=paint_page, onLaterPages=paint_page)
    return output.getvalue()


def _send_invoice_email(request, booking):
    invoice_id = booking.booking_id.replace('BK-', 'INV-', 1)
    invoice = _build_invoice(booking)
    invoice_url = request.build_absolute_uri(
        reverse('invoice_detail', args=[invoice_id])
    )
    context = {
        'invoice': invoice,
        'invoice_id': invoice_id,
        'invoice_url': f'{invoice_url}?popup=1',
    }
    html_content = render_to_string('emails/invoice_sender.html', context)
    pdf_content = _build_invoice_pdf(invoice, invoice_id)

    mailers = getattr(settings, 'MAILERS', None)
    if not mailers or 'default' not in mailers:
        raise ImproperlyConfigured('Configure MAILERS["default"] before sending email.')

    mailer = mailers['default']
    options = mailer.get('OPTIONS', {})
    connection = get_connection(
        backend=mailer['BACKEND'],
        **options,
    )
    message = EmailMultiAlternatives(
        subject=f'Invoice {invoice_id} - Royal Palace Hall',
        body=unescape(strip_tags(html_content)).strip(),
        from_email=options.get('username') or settings.DEFAULT_FROM_EMAIL,
        to=[booking.customer_email],
        connection=connection,
    )
    message.attach_alternative(html_content, 'text/html')
    message.attach(f'{invoice_id}.pdf', pdf_content, 'application/pdf')
    if message.send(fail_silently=False) != 1:
        raise SMTPException('The invoice email did not send.')


def _manager_username(staff_name, user_model):
    username_base = slugify(staff_name).replace('-', '') or 'manager'
    username_field = user_model.USERNAME_FIELD
    for _ in range(10_000):
        username = f"{username_base}{get_random_string(4, allowed_chars=string.digits)}"
        if not user_model._default_manager.filter(
            **{f'{username_field}__iexact': username}
        ).exists():
            return username
    raise RuntimeError('Could not generate a unique manager username.')


def _manager_temporary_password():
    character_groups = (
        string.ascii_lowercase,
        string.ascii_uppercase,
        string.digits,
        '!#$%()*+,-./:;=?@[]^_{}~',
    )
    alphabet = ''.join(character_groups)
    characters = [secrets.choice(group) for group in character_groups]
    characters.extend(secrets.choice(alphabet) for _ in range(4))
    random.SystemRandom().shuffle(characters)
    return ''.join(characters)


def _manager_from_verification_token(staff_id, token):
    try:
        payload = signing.loads(
            token,
            salt=MANAGER_EMAIL_VERIFICATION_SALT,
            max_age=MANAGER_EMAIL_VERIFICATION_MAX_AGE,
        )
    except BadSignature:
        return None

    if not isinstance(payload, dict) or payload.get('staff_id') != staff_id:
        return None

    manager = staff.objects.filter(
        pk=staff_id,
        staff_role__iexact='manager',
    ).first()
    if not manager or payload.get('email') != manager.staff_email:
        return None
    return manager


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
    month_start = today.replace(day=1)
    next_month = (month_start + timedelta(days=32)).replace(day=1)
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

    availability_month_bookings = newbooking.objects.filter(
        event_date__month=today.month,
        event_date__year=today.year,
    )
    dashboard_confirmed_bookings = availability_month_bookings.filter(
        Q(status__iexact='confirmed') | Q(status__iexact='advance'),
    ).count()
    dashboard_pending_bookings = availability_month_bookings.filter(
        status__iexact='pending',
    ).count()
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

    remaining_month_days = (next_month - today).days
    available_dates = sum(
        1
        for day_offset in range(remaining_month_days)
        if active_portion_ids.difference(
            booked_portions_by_date.get(today + timedelta(days=day_offset), set())
        )
    )
    total_portion_days = len(active_portion_ids) * remaining_month_days
    booked_portion_days = sum(len(portions) for portions in booked_portions_by_date.values())
    booked_capacity_percentage = (
        round(booked_portion_days / total_portion_days * 100)
        if total_portion_days else 0
    )

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
        'availability_month': today.strftime('%B'),
        'booked_capacity_percentage': booked_capacity_percentage,
        'dashboard_confirmed_bookings': dashboard_confirmed_bookings,
        'dashboard_pending_bookings': dashboard_pending_bookings,
        'available_dates': available_dates,
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
    today_booking_list = newbooking.objects.filter(created_at=today).order_by('-booking_id')
    if search:
        search_filter = (
            Q(customer_name__icontains = search)|
            Q(booking_id__icontains = search)|
            Q(event_name__icontains = search)|
            Q(event_hall__portion_name__icontains = search)|
            Q(payment_status__icontains = search)|
            Q(status__icontains = search)
        )
        booking_list = booking_list.filter(search_filter)
        today_booking_list = today_booking_list.filter(search_filter)
    if booking_status_filter.lower() == 'confirmed':
        booking_list = booking_list.filter(status__in=booking_status)
        today_booking_list = today_booking_list.filter(status__in=booking_status)
    elif booking_status_filter.lower() == 'pending':
        booking_list = booking_list.filter(status__in=booking_status_pending)
        today_booking_list = today_booking_list.filter(status__in=booking_status_pending)
    elif booking_status_filter:
        booking_list = booking_list.filter(status__iexact=booking_status_filter)
        today_booking_list = today_booking_list.filter(status__iexact=booking_status_filter)
    if booking_date:
        booking_list = booking_list.filter(event_date=booking_date)
        today_booking_list = today_booking_list.filter(event_date=booking_date)

    paginator = Paginator(booking_list, 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    today_paginator = Paginator(today_booking_list, 10)
    today_page_obj = today_paginator.get_page(request.GET.get('today_page'))

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
                'today_page_obj': today_page_obj,
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
    payment_details = payment.objects.all().order_by('-created_at','-payment_id')
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
        ).order_by('-created_at','-payment_id')
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
        payment_obj = payment.objects.filter(method = payment_method).order_by('-created_at','-payment_id')
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

    booking_details = {}
    bookings = form.fields['booking'].queryset.prefetch_related('event_hall')
    for booking in bookings:
        booking_details[booking.booking_id] = {
            'booking_id': booking.booking_id,
            'customer_name': booking.customer_name,
            'phone_number': booking.phone_number,
            'customer_email': booking.customer_email,
            'event_name': booking.event_name,
            'event_type': booking.event_type,
            'event_date': booking.event_date.strftime('%d %b %Y'),
            'event_time': booking.event_time,
            'event_guest': booking.event_guest,
            'event_halls': ', '.join(hall.portion_name for hall in booking.event_hall.all()) or 'Not assigned',
            'service': booking.service,
            'status': booking.status,
            'hall_price': str(booking.hall_price),
            'advance_amount': str(booking.advance_amount or 0),
            'recorded_payment_total': str(booking.recorded_payment_total),
            'remaining_balance': str(booking.remaining_balance),
        }

    return render(request, 'addpaymentform.html', {
        'form': form,
        'page': 'payments',
        'booking_details': booking_details,
    })


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

# START: Invoice list and calculation backend
def _format_invoice_amount(amount):
    if amount == amount.to_integral_value():
        return f'{amount:,.0f}'
    return f'{amount:,.2f}'


def _build_invoice(booking, today=None):
    today = today or timezone.localdate()
    total = Decimal(booking.hall_price)
    posted_payments = sum(
        (
            recorded_payment.amount
            for recorded_payment in booking.payments.all()
            if recorded_payment.refference_num != 'None'
            and recorded_payment.payment_status.casefold() in {'paid', 'advance'}
        ),
        Decimal('0'),
    )
    paid = min(total, Decimal(booking.advance_amount or 0) + posted_payments)
    balance = max(total - paid, Decimal('0'))
    if balance == 0:
        status = 'paid'
    elif booking.event_date < today:
        status = 'overdue'
    else:
        status = 'pending'
    venues = ', '.join(hall.portion_name for hall in booking.event_hall.all())
    total_display = _format_invoice_amount(total)

    return {
        'invoice_id': booking.booking_id.replace('BK-', 'INV-', 1),
        'customer': booking.customer_name,
        'customer_email': booking.customer_email,
        'booking': booking.booking_id,
        'event': booking.event_name,
        'venue': venues or 'Not assigned',
        'event_date': booking.event_date.strftime('%d %b %Y'),
        'issued': booking.created_at.strftime('%d %b %Y'),
        'due': booking.event_date.strftime('%d %b %Y'),
        'total': total_display,
        'paid': _format_invoice_amount(paid),
        'balance': _format_invoice_amount(balance),
        'total_amount': total,
        'paid_amount': paid,
        'balance_amount': balance,
        'status': status,
        'items': [{
            'description': 'Venue and event package',
            'detail': f'{booking.event_name} · {booking.event_guest} guests',
            'quantity': 1,
            'rate': total_display,
            'amount': total_display,
        }],
    }


@login_required(login_url='login')
def Invoices_view(request):
    today = timezone.localdate()
    bookings = newbooking.objects.prefetch_related(
        'payments',
        'event_hall',
    ).order_by('-created_at', '-booking_id')
    invoices = [_build_invoice(booking, today) for booking in bookings]

    total_invoices = len(invoices)
    paid_amount = sum((invoice['paid_amount'] for invoice in invoices), Decimal('0'))
    pending_invoices = [invoice for invoice in invoices if invoice['status'] == 'pending']
    overdue_invoices = [invoice for invoice in invoices if invoice['status'] == 'overdue']
    total_amount = sum((invoice['total_amount'] for invoice in invoices), Decimal('0'))
    collected_percentage = round(paid_amount / total_amount * 100) if total_amount else 0

    search = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '').strip().lower()
    if search:
        search_value = search.casefold()
        invoices = [
            invoice for invoice in invoices
            if search_value in ' '.join((
                invoice['invoice_id'],
                invoice['booking'],
                invoice['customer'],
                invoice['customer_email'],
                invoice['event'],
                invoice['venue'],
            )).casefold()
        ]
    if status_filter in {'paid', 'pending', 'overdue'}:
        invoices = [invoice for invoice in invoices if invoice['status'] == status_filter]
    else:
        status_filter = ''

    page_obj = Paginator(invoices, 10).get_page(request.GET.get('page'))
    return render(request, 'invoices.html', {
        'page': 'invoices',
        'page_obj': page_obj,
        'invoice_list': page_obj.object_list,
        'search': search,
        'status_filter': status_filter,
        'total_invoices': total_invoices,
        'paid_amount': _format_invoice_amount(paid_amount),
        'collected_percentage': collected_percentage,
        'pending_amount': _format_invoice_amount(sum(
            (invoice['balance_amount'] for invoice in pending_invoices),
            Decimal('0'),
        )),
        'pending_count': len(pending_invoices),
        'overdue_amount': _format_invoice_amount(sum(
            (invoice['balance_amount'] for invoice in overdue_invoices),
            Decimal('0'),
        )),
        'overdue_count': len(overdue_invoices),
    })
# END: Invoice list and calculation backend


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
def Booking_history_view(request):
    return render(request, 'booking_history.html', {'page': 'booking-history'})


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
    def hall_bookings_for_portions(*portion_names):
        bookings = newbooking.objects.filter(
            event_date__month=current__month,
            event_date__year=current_year,
        ).annotate(
            portion_count=Count('event_hall', distinct=True),
        )
        for portion_name in portion_names:
            bookings = bookings.filter(event_hall__portion_name=portion_name)
        return list(bookings.filter(portion_count=len(portion_names)).distinct())

    portion_bookings = {
        'a': hall_bookings_for_portions('A'),
        'b': hall_bookings_for_portions('B'),
        'c': hall_bookings_for_portions('C'),
        'a_b': hall_bookings_for_portions('A', 'B'),
        'b_c': hall_bookings_for_portions('B', 'C'),
    }
    portion_a = len(portion_bookings['a'])
    portion_b = len(portion_bookings['b'])
    portion_c = len(portion_bookings['c'])
    portion_A_b = len(portion_bookings['a_b'])
    portion_b_c = len(portion_bookings['b_c'])
    portion_a_price = sum(booking.hall_price for booking in portion_bookings['a'])
    portion_b_price = sum(booking.hall_price for booking in portion_bookings['b'])
    portion_c_price = sum(booking.hall_price for booking in portion_bookings['c'])
    portion_A_b_price = sum(booking.hall_price for booking in portion_bookings['a_b'])
    portion_b_c_price = sum(booking.hall_price for booking in portion_bookings['b_c'])
    portion_a_display = format_report_payment_amount(portion_a_price)
    portion_b_display = format_report_payment_amount(portion_b_price)
    portion_c_display = format_report_payment_amount(portion_c_price)
    portion_A_b_display = format_report_payment_amount(portion_A_b_price)
    portion_b_c_display = format_report_payment_amount(portion_b_c_price)
    report_month_start = today.replace(day=1)
    report_next_month = (report_month_start + timedelta(days=32)).replace(day=1)
    report_month_days = (report_next_month - report_month_start).days
    monthly_shift_slots = report_month_days * 2
    active_portions = Hall_portion.objects.filter(portion_status__iexact='Active')
    active_portion_ids = set(active_portions.values_list('pk', flat=True))
    active_portion_names = set(active_portions.values_list('portion_name', flat=True))
    non_cancelled_month_bookings = newbooking.objects.filter(
        event_date__gte=report_month_start,
        event_date__lt=report_next_month,
    ).exclude(
        Q(status__iexact='cancel')
        | Q(status__iexact='cancelled')
        | Q(status__iexact='canceled')
    )
    occupied_portion_slots = non_cancelled_month_bookings.filter(
        event_hall__in=active_portion_ids,
    ).values(
        'event_date',
        'event_time',
        'event_hall',
    ).distinct().count()
    overall_occupancy = (
        round(occupied_portion_slots / (len(active_portion_ids) * monthly_shift_slots) * 100)
        if active_portion_ids and monthly_shift_slots else 0
    )

    def hall_occupancy_for_portions(*portion_names):
        if not portion_names or any(name not in active_portion_names for name in portion_names):
            return 0
        bookings = non_cancelled_month_bookings.annotate(
            portion_count=Count('event_hall', distinct=True),
        ).filter(portion_count=len(portion_names))
        for portion_name in portion_names:
            bookings = bookings.filter(event_hall__portion_name=portion_name)
        occupied_slots = bookings.values('event_date', 'event_time').distinct().count()
        return round(occupied_slots / monthly_shift_slots * 100) if monthly_shift_slots else 0

    portion_a_occupancy = hall_occupancy_for_portions('A')
    portion_b_occupancy = hall_occupancy_for_portions('B')
    portion_c_occupancy = hall_occupancy_for_portions('C')
    portion_A_b_occupancy = hall_occupancy_for_portions('A', 'B')
    portion_b_c_occupancy = hall_occupancy_for_portions('B', 'C')
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
        'overall_occupancy': overall_occupancy,
        'portion_a_occupancy': portion_a_occupancy,
        'portion_b_occupancy': portion_b_occupancy,
        'portion_c_occupancy': portion_c_occupancy,
        'portion_A_b_occupancy': portion_A_b_occupancy,
        'portion_b_c_occupancy': portion_b_c_occupancy,
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
    active_staff = staff.objects.filter(staff_status__iexact='active').count()
    manager_count = staff.objects.filter(staff_role__iexact='manager').count()
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
# START: Booking form backend
@login_required(login_url='login')
def New_booking(request):
    if request.method == 'POST':
        form = new_booking(request.POST)
        if form.is_valid():
            with transaction.atomic():
                booking = form.save()
                payment.objects.create(
                    booking=booking,
                    method=booking.payment_method,
                    amount=booking.hall_price,
                    refference_num='None',
                    payment_status='Advance' if booking.advance_amount else 'Pending',
                )
            messages.success(request, "Booking created successfully.")
            invoice_id = booking.booking_id.replace('BK-', 'INV-', 1)
            invoice_url = reverse('invoice_detail', args=[invoice_id])
            try:
                _send_invoice_email(request, booking)
                messages.success(request, f"Invoice sent to {booking.customer_email}.")
            except (SMTPException, ImproperlyConfigured) as error:
                logger.warning(
                    'Invoice email could not be sent for booking %s: %s',
                    booking.booking_id,
                    error,
                )
                messages.warning(
                    request,
                    f"Booking saved, but the invoice could not be emailed to {booking.customer_email}.",
                )
            return redirect(f'{invoice_url}?popup=1')

        messages.error(request, "Please correct the errors below.")
    else:
        form = new_booking()
    context = {
        'form': form,
        'booking_conflict_date': form.booking_conflict_date,
        'min_event_date': timezone.localdate().isoformat(),
    }
    return render(request , 'bookingform.html', context)
# END: Booking form backend

@login_required(login_url='login')
def Expense_form(request):
    if request.method == 'POST':
        form = new_expense(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Expense created successfully.")
            return redirect('expensesform')
        messages.error(request, "Please correct the errors below.")
    else:
        form = new_expense()
    return render(request, 'addexpense.html', {'form': form})
@login_required(login_url='login')
def New_staff(request):
    if request.method == 'POST':
        form = new_staff(request.POST)
        if form.is_valid():
            is_manager = form.cleaned_data['staff_role'].strip().casefold() == 'manager'
            try:
                with transaction.atomic():
                    staff_member = form.save(commit=False)
                    if is_manager:
                        staff_member.manager_email_verified = False
                    staff_member.save()

                    if is_manager:
                        token = signing.dumps(
                            {
                                'staff_id': staff_member.pk,
                                'email': staff_member.staff_email,
                            },
                            salt=MANAGER_EMAIL_VERIFICATION_SALT,
                        )
                        verification_url = request.build_absolute_uri(
                            reverse(
                                'verify_manager_email',
                                kwargs={
                                    'staff_id': staff_member.pk,
                                    'token': token,
                                },
                            )
                        )
                        _send_template_email(
                            'Confirm your HallMaster manager email',
                            'emails/manager_email_verification.html',
                            {
                                'manager_name': staff_member.staff_name,
                                'email': staff_member.staff_email,
                                'verification_url': verification_url,
                            },
                            staff_member.staff_email,
                        )
            except (SMTPException, OSError):
                logger.exception('Could not send manager verification email.')
                form.add_error(
                    None,
                    'The verification email could not be sent. The staff member was not saved; please try again.',
                )
            else:
                if is_manager:
                    messages.success(
                        request,
                        'Staff member saved. A verification email has been sent to the manager.',
                    )
                else:
                    messages.success(request, 'Staff member created successfully.')
                return redirect('staffform')
    else:
        form = new_staff()
    context = {'form': form}
    return render(request, 'addstaff.html', context)


@require_http_methods(['GET', 'POST'])
def verify_manager_email(request, staff_id, token):
    manager = _manager_from_verification_token(staff_id, token)
    if not manager:
        return render(
            request,
            'emails/manager_email_verification_confirm.html',
            {'state': 'invalid'},
            status=400,
        )

    if manager.manager_email_verified:
        return render(
            request,
            'emails/manager_email_verification_confirm.html',
            {'state': 'already_verified', 'manager_name': manager.staff_name},
        )

    if request.method == 'GET':
        return render(
            request,
            'emails/manager_email_verification_confirm.html',
            {'state': 'confirm', 'manager_name': manager.staff_name},
        )

    user_model = get_user_model()
    try:
        with transaction.atomic():
            manager = staff.objects.select_for_update().filter(
                pk=staff_id,
                staff_role__iexact='manager',
            ).first()
            signed_manager = _manager_from_verification_token(
                staff_id,
                token,
            )
            if (
                not manager
                or not signed_manager
                or manager.staff_email != signed_manager.staff_email
            ):
                state = 'invalid'
            elif manager.manager_email_verified:
                state = 'already_verified'
            elif user_model._default_manager.filter(
                email__iexact=manager.staff_email,
            ).exists():
                state = 'account_exists'
            else:
                username = _manager_username(manager.staff_name, user_model)
                temporary_password = _manager_temporary_password()
                manager_user = user_model._default_manager.create_user(
                    username=username,
                    email=manager.staff_email,
                    first_name=manager.staff_name,
                    password=temporary_password,
                    is_staff=True,
                    is_active=manager.staff_status.casefold() == 'active',
                )
                manager_group, _ = Group.objects.get_or_create(name='Manager')
                manager_user.groups.add(manager_group)
                _send_template_email(
                    'Your HallMaster manager sign-in details',
                    'emails/manager_credentials.html',
                    {
                        'manager_name': manager.staff_name,
                        'username': username,
                        'password': temporary_password,
                        'account_active': manager_user.is_active,
                        'login_url': request.build_absolute_uri(reverse('login')),
                    },
                    manager.staff_email,
                )
                manager.manager_email_verified = True
                manager.save(update_fields=['manager_email_verified'])
                state = 'complete'
    except (SMTPException, OSError):
        logger.exception('Could not send manager credentials email.')
        state = 'send_failed'

    status_codes = {
        'invalid': 400,
        'account_exists': 409,
        'send_failed': 503,
    }
    status_code = status_codes.get(state, 200)
    return render(
        request,
        'emails/manager_email_verification_confirm.html',
        {'state': state, 'manager_name': manager.staff_name if manager else ''},
        status=status_code,
    )
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


# START: Invoice detail backend
@login_required(login_url='login')
def invoice_detail(request, invoice_id):
    if not invoice_id.startswith('INV-'):
        raise Http404('Invoice not found')

    booking_id = invoice_id.replace('INV-', 'BK-', 1)
    booking = get_object_or_404(
        newbooking.objects.prefetch_related('payments', 'event_hall'),
        booking_id=booking_id,
    )
    invoice = _build_invoice(booking)
    return render(request, 'genrateinvoice.html', {
        'page': 'invoices',
        'invoice_id': invoice_id,
        'invoice': invoice,
        'layout_template': (
            'invoice_popup_base.html'
            if request.GET.get('popup') == '1'
            else 'base.html'
        ),
    })
# END: Invoice detail backend


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
