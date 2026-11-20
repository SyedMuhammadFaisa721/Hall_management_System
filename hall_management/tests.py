import re
from io import BytesIO
from datetime import date, timedelta
from decimal import Decimal
from smtplib import SMTPException
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from django.test import override_settings
from django.urls import reverse
from pypdf import PdfReader
from urllib.parse import urlparse

from .models import Hall_portion, Inventory, InventoryCategory, expense, newbooking, payment, staff
from .views import _build_invoice, _build_invoice_pdf


class BookingFormTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username='booking-form-test',
            password='test-password',
        )
        self.client.force_login(self.user)
        self.portion = Hall_portion.objects.create(
            portion_name='A',
            portion_capacity=200,
        )

    def valid_booking_data(self, **overrides):
        data = {
            'customer_name': 'Booking Form Customer',
            'phone_number': '03001234567',
            'nic_number': '12345-1234567-1',
            'customer_email': 'booking@example.com',
            'event_name': 'Wedding Reception',
            'event_type': 'Wedding',
            'event_date': '2026-12-20',
            'event_time': 'Day',
            'event_guest': '120',
            'event_hall': [str(self.portion.pk)],
            'special_req': 'Stage setup',
            'hall_price': '75000',
            'status': 'Confirmed',
            'service': 'Buffet Service',
            'payment_method': 'Bank Transfer',
        }
        data.update(overrides)
        return data

    def invoice_url_for(self, booking):
        invoice_id = booking.booking_id.replace('BK-', 'INV-', 1)
        return f"{reverse('invoice_detail', args=[invoice_id])}?popup=1"

    def test_booking_form_renders_payment_methods_from_payment_model(self):
        response = self.client.get(reverse('bookingform'))

        self.assertEqual(response.status_code, 200)
        for value, label in payment._meta.get_field('method').choices:
            self.assertContains(response, f'value="{value}"')
            self.assertContains(response, label)

    def test_booking_form_saves_booking_halls_event_shift_and_payment_method(self):
        with patch('hall_management.views._send_invoice_email') as send_invoice:
            response = self.client.post(
                reverse('bookingform'),
                self.valid_booking_data(),
            )

        booking = newbooking.objects.get(customer_email='booking@example.com')
        send_invoice.assert_called_once()
        self.assertEqual(send_invoice.call_args.args[1], booking)
        self.assertRedirects(
            response,
            self.invoice_url_for(booking),
            fetch_redirect_response=False,
        )
        invoice_response = self.client.get(response.url)
        self.assertEqual(invoice_response.status_code, 200)
        self.assertContains(invoice_response, booking.customer_name)
        self.assertContains(invoice_response, booking.event_name)
        self.assertEqual(booking.event_time, 'Day')
        self.assertEqual(booking.payment_method, 'Bank Transfer')
        self.assertEqual(booking.service, 'Buffet Service')
        self.assertEqual(list(booking.event_hall.all()), [self.portion])
        saved_payment = payment.objects.get(booking=booking)
        self.assertEqual(saved_payment.amount, Decimal('75000.00'))
        self.assertEqual(saved_payment.payment_status, 'Pending')

    def test_booking_form_rejects_same_portion_date_and_event_time(self):
        existing_booking = newbooking.objects.create(
            customer_name='Existing Customer',
            phone_number='03001234567',
            nic_number='12345-1234567-9',
            customer_email='existing@example.com',
            event_name='Existing Wedding',
            event_type='Wedding',
            event_date=date(2026, 12, 20),
            event_guest=100,
            hall_price=75000,
            status='Confirmed',
            event_time='Day',
            payment_status='Pending',
        )
        existing_booking.event_hall.add(self.portion)

        response = self.client.post(
            reverse('bookingform'),
            self.valid_booking_data(),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'already have a booking')
        self.assertContains(response, 'View availability calendar for this date')
        self.assertContains(response, '?date=2026-12-20#availability-calendar')
        self.assertEqual(newbooking.objects.count(), 1)

    def test_booking_form_allows_same_date_and_time_for_different_portion(self):
        other_portion = Hall_portion.objects.create(
            portion_name='B',
            portion_capacity=200,
        )
        existing_booking = newbooking.objects.create(
            customer_name='Existing Customer',
            phone_number='03001234567',
            nic_number='12345-1234567-9',
            customer_email='existing@example.com',
            event_name='Existing Wedding',
            event_type='Wedding',
            event_date=date(2026, 12, 20),
            event_guest=100,
            hall_price=75000,
            status='Confirmed',
            event_time='Day',
            payment_status='Pending',
        )
        existing_booking.event_hall.add(self.portion)

        response = self.client.post(
            reverse('bookingform'),
            self.valid_booking_data(event_hall=[str(other_portion.pk)]),
        )

        booking = newbooking.objects.get(customer_email='booking@example.com')
        self.assertRedirects(
            response,
            self.invoice_url_for(booking),
            fetch_redirect_response=False,
        )
        self.assertEqual(newbooking.objects.count(), 2)

    def test_booking_form_rejects_past_event_date(self):
        with patch('hall_management.form.timezone.localdate', return_value=date(2026, 12, 21)):
            response = self.client.post(
                reverse('bookingform'),
                self.valid_booking_data(event_date='2026-12-20'),
            )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Past dates cannot be booked.')
        self.assertEqual(newbooking.objects.count(), 0)

    def test_booking_form_date_picker_starts_at_today(self):
        with patch('hall_management.views.timezone.localdate', return_value=date(2026, 12, 21)):
            response = self.client.get(reverse('bookingform'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'min="2026-12-21"')

    def test_advance_booking_saves_amount_within_hall_price(self):
        response = self.client.post(
            reverse('bookingform'),
            self.valid_booking_data(status='Advance', advance_amount='25000'),
        )

        booking = newbooking.objects.get(customer_email='booking@example.com')
        self.assertRedirects(
            response,
            self.invoice_url_for(booking),
            fetch_redirect_response=False,
        )
        self.assertEqual(booking.advance_amount, 25000)
        saved_payment = payment.objects.get(booking=booking)
        self.assertEqual(saved_payment.method, 'Bank Transfer')
        self.assertEqual(saved_payment.amount, Decimal('75000.00'))
        self.assertEqual(saved_payment.refference_num, 'None')
        self.assertEqual(saved_payment.payment_status, 'Advance')
        self.assertEqual(saved_payment.remaining_amount, Decimal('50000.00'))

    def test_advance_amount_greater_than_hall_price_is_rejected(self):
        response = self.client.post(
            reverse('bookingform'),
            self.valid_booking_data(status='Advance', advance_amount='75001'),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Advance amount cannot exceed hall price.')
        self.assertEqual(newbooking.objects.count(), 0)

    def test_advance_status_requires_an_amount(self):
        response = self.client.post(
            reverse('bookingform'),
            self.valid_booking_data(status='Advance'),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Enter the advance amount.')
        self.assertEqual(newbooking.objects.count(), 0)

    def test_invalid_booking_form_renders_errors_without_creating_booking(self):
        response = self.client.post(reverse('bookingform'), {'customer_name': ''})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'This field is required.')
        self.assertEqual(newbooking.objects.count(), 0)


class BookingSearchTests(TestCase):
    def test_booking_search_matches_payment_status(self):
        user_model = get_user_model()
        user = user_model.objects.create_user(
            username='booking-search-test',
            password='test-password',
        )
        self.client.force_login(user)
        today = date.today()
        current_date = today.replace(day=15)
        previous_month_end = today.replace(day=1) - timedelta(days=1)
        previous_date = previous_month_end.replace(day=15)
        portion = Hall_portion.objects.create(portion_name='A', portion_capacity=100)

        def create_booking(event_date, status, customer_name):
            return newbooking.objects.create(
                customer_name=customer_name,
                phone_number='03001234567',
                nic_number=f'NIC-{customer_name}',
                customer_email=f'{customer_name.replace(" ", "").lower()}@example.com',
                event_name='Search Test Event',
                event_type='Wedding',
                event_date=event_date,
                event_guest=50,
                hall_price=50000,
                status=status,
                event_time='Day',
                payment_status='Pending',
            )

        create_booking(previous_date, 'Confirmed', 'Previous Confirmed')
        create_booking(previous_date, 'Pending', 'Previous Pending')
        create_booking(previous_date, 'cancelled', 'Previous Cancelled')
        target = create_booking(current_date, 'Confirmed', 'Payment Status Match')
        target.payment_status = 'Advance'
        target.save(update_fields=['payment_status'])
        target.event_hall.add(portion)

        response = self.client.get(reverse('bookings'), {'search': 'Advance'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context['page_obj'].object_list), [target])


class BookingPaginationTests(TestCase):
    def test_booking_tables_use_independent_pagination(self):
        user_model = get_user_model()
        user = user_model.objects.create_user(
            username='booking-pagination-test',
            password='test-password',
        )
        self.client.force_login(user)
        today = date.today()
        previous_month_date = (today.replace(day=1) - timedelta(days=1)).replace(day=15)

        def create_booking(index, event_date, status):
            return newbooking.objects.create(
                customer_name=f'Paginator Customer {index}',
                phone_number=f'0300{index:07d}',
                nic_number=f'PAG-{index:04d}',
                customer_email=f'paginator-{index}@example.com',
                event_name='Paginator Event',
                event_type='Wedding',
                event_date=event_date,
                event_guest=50,
                hall_price=1000,
                status=status,
                event_time='Day',
                payment_status='Pending',
            )

        for index, status in enumerate(('Confirmed', 'Pending', 'cancelled'), start=1):
            booking = create_booking(index, previous_month_date, status)
            newbooking.objects.filter(pk=booking.pk).update(created_at=previous_month_date)
        for index in range(4, 16):
            create_booking(index, today, 'Pending')

        all_bookings_page = self.client.get(reverse('bookings'), {'page': 2})
        self.assertEqual(all_bookings_page.status_code, 200)
        self.assertEqual(all_bookings_page.context['page_obj'].number, 2)
        self.assertEqual(all_bookings_page.context['today_page_obj'].number, 1)

        today_bookings_page = self.client.get(
            reverse('bookings'),
            {'page': 2, 'today_page': 2},
        )
        self.assertEqual(today_bookings_page.status_code, 200)
        self.assertEqual(today_bookings_page.context['page_obj'].number, 2)
        self.assertEqual(today_bookings_page.context['today_page_obj'].number, 2)


class AvailabilityEventsTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username='calendar-test',
            password='test-password',
        )
        self.portion = Hall_portion.objects.create(
            portion_name='A',
            portion_capacity=100,
        )
        self.booking = newbooking.objects.create(
            customer_name='Test Customer',
            phone_number='03001234567',
            nic_number='12345-1234567-1',
            customer_email='customer@example.com',
            event_name='Test Wedding',
            event_type='Wedding',
            event_date=date(2026, 11, 9),
            event_guest=80,
            hall_price=50000,
            status='confirmed',
            event_time='Night',
            payment_status='Pending',
        )
        self.booking.event_hall.add(self.portion)

    def test_availability_page_uses_database_portions_and_event_endpoint(self):
        self.client.force_login(self.user)

        with patch('hall_management.views.timezone.localdate', return_value=date(2026, 11, 9)):
            response = self.client.get(reverse('availability'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-events-url="/availability/events/"')
        self.assertContains(response, 'id="availability-portions-data"')
        self.assertContains(response, '"portion_name": "A"')

    def test_available_dates_count_future_dates_with_an_unbooked_active_portion(self):
        self.client.force_login(self.user)
        second_portion = Hall_portion.objects.create(
            portion_name='B',
            portion_capacity=100,
        )
        fully_booked_date = newbooking.objects.create(
            customer_name='Second Customer',
            phone_number='03001234568',
            nic_number='12345-1234567-2',
            customer_email='second@example.com',
            event_name='Second Wedding',
            event_type='Wedding',
            event_date=date(2026, 11, 9),
            event_guest=80,
            hall_price=50000,
            status='confirmed',
            event_time='Night',
            payment_status='Pending',
        )
        fully_booked_date.event_hall.add(second_portion)

        with patch('hall_management.views.timezone.localdate', return_value=date(2026, 11, 9)):
            response = self.client.get(reverse('availability'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['available_dates'], 21)

    def test_calendar_events_include_booking_and_portion_details(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse('availability_events'),
            {'start': '2026-11-01', 'end': '2026-12-01'},
        )

        self.assertEqual(response.status_code, 200)
        event = response.json()['events'][0]
        self.assertEqual(event['start'], '2026-11-09')
        self.assertEqual(event['title'], 'Test Wedding')
        self.assertEqual(event['extendedProps']['customerName'], 'Test Customer')
        self.assertEqual(event['extendedProps']['guestCount'], 80)
        self.assertEqual(event['extendedProps']['halls'], [
            {'id': self.portion.pk, 'name': 'A'},
        ])

    def test_calendar_events_reject_invalid_date_ranges(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse('availability_events'),
            {'start': 'not-a-date', 'end': '2026-12-01'},
        )

        self.assertEqual(response.status_code, 400)


class ReportsViewTests(TestCase):
    def test_booking_history_page_renders_twenty_years_of_sample_data(self):
        user_model = get_user_model()
        user = user_model.objects.create_user(
            username='booking-history-test',
            password='test-password',
        )
        self.client.force_login(user)

        response = self.client.get(reverse('booking_history'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['page'], 'booking-history')
        self.assertContains(response, 'Annual booking history')
        self.assertContains(response, 'Sample data')
        self.assertEqual(response.content.count(b'data-history-year='), 20)

    def test_reports_page_handles_portion_name_filters(self):
        user_model = get_user_model()
        user = user_model.objects.create_user(
            username='reports-test',
            password='test-password',
        )
        self.client.force_login(user)

        response = self.client.get(reverse('reports'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['portion_a'], 0)

    def test_reports_hall_metrics_use_exact_portion_combinations(self):
        user_model = get_user_model()
        user = user_model.objects.create_user(
            username='reports-combination-test',
            password='test-password',
        )
        self.client.force_login(user)
        portion_a = Hall_portion.objects.create(portion_name='A', portion_capacity=100)
        portion_b = Hall_portion.objects.create(portion_name='B', portion_capacity=100)

        previous_booking = newbooking.objects.create(
            customer_name='Previous Customer',
            phone_number='03001234567',
            nic_number='12345-1234567-3',
            customer_email='previous@example.com',
            event_name='Previous Event',
            event_type='Wedding',
            event_date=date(2026, 10, 15),
            event_guest=50,
            hall_price=10000,
            status='Confirmed',
            event_time='Day',
        )
        previous_booking.event_hall.add(portion_a)
        current_booking = newbooking.objects.create(
            customer_name='Current Customer',
            phone_number='03001234568',
            nic_number='12345-1234567-4',
            customer_email='current@example.com',
            event_name='Current Event',
            event_type='Wedding',
            event_date=date(2026, 11, 15),
            event_guest=80,
            hall_price=50000,
            status='Confirmed',
            event_time='Night',
        )
        current_booking.event_hall.add(portion_a, portion_b)

        with patch('hall_management.views.timezone.localdate', return_value=date(2026, 11, 18)):
            response = self.client.get(reverse('reports'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['portion_a'], 0)
        self.assertEqual(response.context['portion_A_b'], 1)
        self.assertEqual(response.context['portion_A_b_display'], '50,000')
        self.assertEqual(response.context['overall_occupancy'], 2)
        self.assertEqual(response.context['portion_A_b_occupancy'], 2)
        self.assertEqual(response.context['portion_a_occupancy'], 0)


class DashboardAvailabilityTests(TestCase):
    def test_dashboard_hall_availability_uses_current_month_bookings(self):
        user_model = get_user_model()
        user = user_model.objects.create_user(
            username='dashboard-availability-test',
            password='test-password',
        )
        self.client.force_login(user)
        portion_a = Hall_portion.objects.create(portion_name='A', portion_capacity=100)
        portion_b = Hall_portion.objects.create(portion_name='B', portion_capacity=100)
        today = date.today()

        confirmed_booking = newbooking.objects.create(
            customer_name='Confirmed Dashboard Customer',
            phone_number='03001234567',
            nic_number='12345-1234567-5',
            customer_email='confirmed-dashboard@example.com',
            event_name='Confirmed Dashboard Event',
            event_type='Wedding',
            event_date=today,
            event_guest=50,
            hall_price=0,
            status='Confirmed',
            event_time='Day',
        )
        confirmed_booking.event_hall.add(portion_a)
        pending_booking = newbooking.objects.create(
            customer_name='Pending Dashboard Customer',
            phone_number='03001234568',
            nic_number='12345-1234567-6',
            customer_email='pending-dashboard@example.com',
            event_name='Pending Dashboard Event',
            event_type='Wedding',
            event_date=today,
            event_guest=50,
            hall_price=0,
            status='Pending',
            event_time='Night',
        )
        pending_booking.event_hall.add(portion_b)

        response = self.client.get(reverse('dashboard'))
        remaining_days = (today.replace(day=1) + timedelta(days=32)).replace(day=1)
        remaining_days = (remaining_days - today).days

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['dashboard_confirmed_bookings'], 1)
        self.assertEqual(response.context['dashboard_pending_bookings'], 1)
        self.assertEqual(response.context['booked_capacity_percentage'], round(100 / remaining_days))
        self.assertEqual(response.context['available_dates'], max(remaining_days - 1, 0))


class InventoryCategoryFormTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username='category-test',
            password='test-password',
        )
        self.client.force_login(self.user)

    def test_category_form_saves_category_and_returns_to_form(self):
        response = self.client.post(
            reverse('inventorycategoryform'),
            {'category_name': 'Seating'},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.redirect_chain, [(reverse('inventorycategoryform'), 302)])
        self.assertContains(response, 'Inventory category created successfully.')
        self.assertNotContains(response, 'Frontend preview only')
        self.assertTrue(InventoryCategory.objects.filter(category_name='Seating').exists())

    def test_category_form_displays_validation_errors_without_saving(self):
        response = self.client.post(
            reverse('inventorycategoryform'),
            {'category_name': 'This category name is too long'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ensure this value has at most 20 characters')
        self.assertEqual(InventoryCategory.objects.count(), 0)


class ExpenseFormTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username='expense-test',
            password='test-password',
        )
        self.client.force_login(self.user)

    def test_expense_form_saves_and_confirms_creation(self):
        response = self.client.post(
            reverse('expensesform'),
            {
                'expense_title': 'Generator fuel',
                'expense_category': 'Electricity',
                'date': '2026-11-14',
                'amount': '2500',
                'paid_by': 'Hall manager',
                'status': 'Pending',
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.redirect_chain, [(reverse('expensesform'), 302)])
        self.assertContains(response, 'Expense created successfully.')
        saved_expense = expense.objects.get(expense_title='Generator fuel')
        self.assertEqual(saved_expense.expense_category, 'Electricity')
        self.assertEqual(saved_expense.amount, 2500)
        self.assertEqual(saved_expense.status, 'Pending')

    def test_expense_form_rejects_invalid_category_and_nonpositive_amount(self):
        response = self.client.post(
            reverse('expensesform'),
            {
                'expense_title': 'Water bill',
                'expense_category': 'Invalid category',
                'date': '2026-11-14',
                'amount': '0',
                'paid_by': 'Hall manager',
                'status': 'Paid',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Select a valid choice')
        self.assertContains(response, 'Ensure this value is greater than or equal to 1.')
        self.assertContains(response, 'value="Water bill"')
        self.assertEqual(expense.objects.count(), 0)


class PaymentFormTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username='payment-test',
            password='test-password',
        )
        self.client.force_login(self.user)
        self.booking = newbooking.objects.create(
            customer_name='Payment Customer',
            phone_number='03001234567',
            nic_number='12345-1234567-1',
            customer_email='payment@example.com',
            event_name='Wedding',
            event_type='Wedding',
            event_date=date(2026, 12, 20),
            event_guest=100,
            hall_price=100000,
            status='confirmed',
            event_time='Night',
            payment_status='Pending',
        )

    def test_payment_form_lists_bookings_and_default_payment_date(self):
        response = self.client.get(reverse('paymentform'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.booking.booking_id)
        self.assertContains(response, 'type="date"')
        self.assertContains(response, 'name="csrfmiddlewaretoken"')

    def test_payment_form_saves_payment_and_redirects_to_ledger(self):
        response = self.client.post(
            reverse('paymentform'),
            {
                'booking': self.booking.booking_id,
                'payment_date': '2026-11-14',
                'method': 'Bank Transfer',
                'amount': '25000.50',
                'refference_num': 'BANK-REF-001',
                'payment_status': 'advance',
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.redirect_chain, [(reverse('payments'), 302)])
        self.assertContains(response, 'Payment recorded successfully.')
        saved_payment = payment.objects.get(refference_num='BANK-REF-001')
        self.assertEqual(saved_payment.booking, self.booking)
        self.assertEqual(saved_payment.amount, 25000.50)
        self.assertTrue(saved_payment.payment_id)

    def test_payment_form_shows_selected_booking_details(self):
        response = self.client.get(reverse('paymentform'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'BOOKING SUMMARY')
        self.assertContains(response, 'Payment Customer')
        self.assertContains(response, 'event_type_status')
        self.assertContains(response, 'remaining_balance')

    def test_payment_form_rejects_amount_above_balance_after_advance_and_payments(self):
        self.booking.advance_amount = 20000
        self.booking.save(update_fields=['advance_amount'])
        payment.objects.create(
            booking=self.booking,
            method='cash',
            amount=Decimal('30000.00'),
            refference_num='EXISTING-001',
            payment_status='paid',
        )

        response = self.client.post(
            reverse('paymentform'),
            {
                'booking': self.booking.booking_id,
                'payment_date': '2026-11-14',
                'method': 'cash',
                'amount': '50000.01',
                'refference_num': 'OVER-BALANCE',
                'payment_status': 'paid',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Amount cannot exceed the remaining balance of PKR 50,000.00.')
        self.assertFalse(payment.objects.filter(refference_num='OVER-BALANCE').exists())

    def test_payment_form_balance_ignores_booking_total_placeholder_payment(self):
        self.booking.advance_amount = 20000
        self.booking.save(update_fields=['advance_amount'])
        payment.objects.create(
            booking=self.booking,
            method='cash',
            amount=Decimal('100000.00'),
            refference_num='None',
            payment_status='Advance',
        )

        response = self.client.post(
            reverse('paymentform'),
            {
                'booking': self.booking.booking_id,
                'payment_date': '2026-11-14',
                'method': 'cash',
                'amount': '80000',
                'refference_num': 'REMAINING-BALANCE',
                'payment_status': 'paid',
            },
        )

        self.assertRedirects(response, reverse('payments'), fetch_redirect_response=False)
        saved_payment = payment.objects.get(refference_num='REMAINING-BALANCE')
        self.assertEqual(saved_payment.amount, Decimal('80000.00'))

    def test_payment_form_rejects_nonpositive_amount_and_invalid_method(self):
        response = self.client.post(
            reverse('paymentform'),
            {
                'booking': self.booking.booking_id,
                'payment_date': '2026-11-14',
                'method': 'Unknown',
                'amount': '0',
                'refference_num': 'INVALID-REF',
                'payment_status': 'advance',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ensure this value is greater than or equal to 0.01.')
        self.assertContains(response, 'Select a valid choice')
        self.assertEqual(payment.objects.count(), 0)

    def test_payments_page_renders_remaining_amount_without_template_arithmetic(self):
        self.booking.advance_amount = 20000
        self.booking.save(update_fields=['advance_amount'])
        payment.objects.create(
            booking=self.booking,
            payment_date=date(2026, 11, 14),
            method='cash',
            amount=Decimal('25000.00'),
            refference_num='REMAINING-001',
            payment_status='advance',
        )

        response = self.client.get(reverse('payments'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['page_obj'][0].remaining_amount, Decimal('5000.00'))


class InventoryFormTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username='inventory-test',
            password='test-password',
        )
        self.client.force_login(self.user)
        self.category = InventoryCategory.objects.create(category_name='Seating')

    def test_inventory_form_saves_and_redirects_to_inventory_list(self):
        response = self.client.post(
            reverse('inventoryform'),
            {
                'inventory_name': 'Banquet chair',
                'category': str(self.category.pk),
                'inventory_quantity': '10',
                'available_quantity': '10',
                'damage_quantity': '0',
            },
        )

        self.assertRedirects(response, reverse('inventory'))
        item = Inventory.objects.get(inventory_name='Banquet chair')
        self.assertEqual(item.category, self.category)
        self.assertEqual(item.damage_quantity, 0)

    def test_inventory_form_shows_invalid_quantity_error_on_damaged_field(self):
        response = self.client.post(
            reverse('inventoryform'),
            {
                'inventory_name': 'Banquet chair',
                'category': str(self.category.pk),
                'inventory_quantity': '10',
                'available_quantity': '8',
                'damage_quantity': '3',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Available and damaged quantities cannot exceed total quantity.')
        self.assertContains(response, 'id="inventory-damaged-errors"')
        self.assertContains(response, 'value="8"')
        self.assertContains(response, f'<option value="{self.category.pk}" selected>')
        self.assertEqual(Inventory.objects.count(), 0)

    def test_inventory_form_shows_invalid_category_error_on_category_field(self):
        response = self.client.post(
            reverse('inventoryform'),
            {
                'inventory_name': 'Banquet chair',
                'category': 'not-a-category-id',
                'inventory_quantity': '10',
                'available_quantity': '8',
                'damage_quantity': '2',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="inventory-category-errors"')
        self.assertContains(response, 'Select a valid choice')
        self.assertEqual(Inventory.objects.count(), 0)

    def test_inventory_form_shows_negative_quantity_errors_on_each_quantity_field(self):
        response = self.client.post(
            reverse('inventoryform'),
            {
                'inventory_name': 'Banquet chair',
                'category': str(self.category.pk),
                'inventory_quantity': '-1',
                'available_quantity': '-2',
                'damage_quantity': '-3',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="inventory-total-errors"')
        self.assertContains(response, 'id="inventory-available-errors"')
        self.assertContains(response, 'id="inventory-damaged-errors"')
        self.assertContains(response, 'Quantity cannot be negative.')
        self.assertEqual(Inventory.objects.count(), 0)


@override_settings(MAILERS={
    'default': {
        'BACKEND': 'django.core.mail.backends.locmem.EmailBackend',
        'OPTIONS': {},
    },
})
class StaffManagerVerificationTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username='staff-verification-test',
            password='test-password',
        )
        self.client.force_login(self.user)

    def valid_staff_data(self, **overrides):
        data = {
            'staff_name': 'Manager Test',
            'staff_email': 'manager@example.com',
            'staff_number': '03001234567',
            'staff_role': 'Manager',
            'staff_nic_num': '12345-1234567-1',
            'staff_status': 'Active',
            'staff_join_date': '2026-11-19',
            'category': 'worker',
            'Salary_status': 'Unpaid',
        }
        data.update(overrides)
        return data

    def test_manager_gets_verification_then_credentials_only_after_confirmation(self):
        response = self.client.post(
            reverse('staffform'),
            self.valid_staff_data(),
        )

        self.assertRedirects(response, reverse('staffform'), fetch_redirect_response=False)
        self.assertContains(self.client.get(response['Location']), 'verification email has been sent')
        manager = staff.objects.get(staff_email='manager@example.com')
        self.assertFalse(manager.manager_email_verified)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['manager@example.com'])
        verification_html = next(
            content
            for content, mimetype in mail.outbox[0].alternatives
            if mimetype == 'text/html'
        )
        verification_path = urlparse(
            re.search(r'href="([^"]+)"', verification_html).group(1)
        ).path

        confirmation_page = self.client.get(verification_path)
        self.assertEqual(confirmation_page.status_code, 200)
        self.assertContains(confirmation_page, 'Confirm your manager email')
        self.assertFalse(get_user_model().objects.filter(email='manager@example.com').exists())

        response = self.client.post(verification_path)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Email confirmed')
        manager.refresh_from_db()
        self.assertTrue(manager.manager_email_verified)
        self.assertEqual(len(mail.outbox), 2)

        credentials = mail.outbox[1].body
        username = re.search(r'Username\s+(\S+)', credentials).group(1)
        password = re.search(r'Temporary password\s+(\S+)', credentials).group(1)
        self.assertRegex(username, r'^managertest\d{4}$')
        self.assertEqual(len(password), 8)
        self.assertTrue(any(character.islower() for character in password))
        self.assertTrue(any(character.isupper() for character in password))
        self.assertTrue(any(character.isdigit() for character in password))
        self.assertTrue(any(not character.isalnum() for character in password))

        manager_user = get_user_model().objects.get(email='manager@example.com')
        self.assertTrue(manager_user.is_staff)
        self.assertTrue(manager_user.check_password(password))
        login_response = self.client.post(
            reverse('login'),
            {'username': username, 'password': password},
        )
        self.assertRedirects(
            login_response,
            reverse('dashboard'),
            fetch_redirect_response=False,
        )
        self.assertEqual(mail.outbox[1].to, ['manager@example.com'])
        self.assertTrue(manager_user.groups.filter(name='Manager').exists())

        self.client.post(verification_path)
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(get_user_model().objects.filter(email='manager@example.com').count(), 1)

    def test_non_manager_is_saved_without_verification_email_or_login_account(self):
        response = self.client.post(
            reverse('staffform'),
            self.valid_staff_data(
                staff_name='Receptionist Test',
                staff_email='',
                staff_role='Receptionist',
                staff_nic_num='12345-1234567-2',
            ),
        )

        self.assertRedirects(response, reverse('staffform'), fetch_redirect_response=False)
        self.assertEqual(staff.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 0)
        self.assertFalse(get_user_model().objects.filter(first_name='Receptionist Test').exists())

    def test_manager_without_email_is_rejected(self):
        response = self.client.post(
            reverse('staffform'),
            self.valid_staff_data(staff_email=''),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'An email address is required for a manager.')
        self.assertEqual(staff.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)

    @patch(
        'hall_management.views._send_template_email',
        side_effect=SMTPException('mail unavailable'),
    )
    def test_manager_record_is_rolled_back_when_verification_email_fails(self, send_email):
        response = self.client.post(
            reverse('staffform'),
            self.valid_staff_data(),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'The verification email could not be sent.')
        self.assertEqual(staff.objects.count(), 0)
        send_email.assert_called_once()


class InvoiceTemplateTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username='invoice-template-test',
            password='test-password',
        )
        self.client.force_login(self.user)

    def create_booking(self, **overrides):
        booking_data = {
            'customer_name': 'Invoice Customer',
            'phone_number': '03001234567',
            'nic_number': '12345-1234567-1',
            'customer_email': 'invoice@example.com',
            'event_name': 'Wedding Reception',
            'event_type': 'Wedding',
            'event_date': date.today() + timedelta(days=30),
            'event_guest': 120,
            'hall_price': 100000,
            'status': 'Confirmed',
            'event_time': 'Day',
        }
        booking_data.update(overrides)
        booking = newbooking.objects.create(**booking_data)
        hall = Hall_portion.objects.create(
            portion_name=f'H{newbooking.objects.count()}',
            portion_capacity=200,
        )
        booking.event_hall.add(hall)
        return booking

    def test_invoices_page_renders_booking_and_calculates_paid_and_balance(self):
        booking = self.create_booking(advance_amount=20000)
        payment.objects.create(
            booking=booking,
            method='cash',
            amount=Decimal('100000.00'),
            refference_num='None',
            payment_status='Advance',
        )
        payment.objects.create(
            booking=booking,
            method='cash',
            amount=Decimal('30000.00'),
            refference_num='INVOICE-PAID',
            payment_status='paid',
        )
        payment.objects.create(
            booking=booking,
            method='cash',
            amount=Decimal('10000.00'),
            refference_num='INVOICE-PENDING',
            payment_status='pending',
        )

        response = self.client.get(reverse('invoices'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, booking.booking_id.replace('BK-', 'INV-', 1))
        self.assertContains(response, 'Invoice Customer')
        self.assertContains(response, 'Rs 100,000')
        self.assertContains(response, 'Rs 50,000')
        self.assertNotContains(response, 'Venue and event package')
        self.assertContains(response, 'invoice-template.css')
        self.assertContains(response, 'Invoice register')
        self.assertContains(response, 'See invoice')
        self.assertContains(
            response,
            f'href="{reverse("invoice_detail", args=[booking.booking_id.replace("BK-", "INV-", 1)])}?popup=1"',
        )

    def test_invoice_register_filters_database_invoices(self):
        paid_booking = self.create_booking(
            customer_name='Paid Invoice Customer',
            customer_email='paid-invoice@example.com',
            hall_price=50000,
        )
        payment.objects.create(
            booking=paid_booking,
            method='cash',
            amount=Decimal('50000.00'),
            refference_num='PAID-INVOICE',
            payment_status='paid',
        )
        self.create_booking(
            customer_name='Pending Invoice Customer',
            customer_email='pending-invoice@example.com',
        )

        response = self.client.get(
            reverse('invoices'),
            {'search': 'Paid Invoice Customer', 'status': 'paid'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['page_obj'].paginator.count, 1)
        self.assertEqual(response.context['invoice_list'][0]['booking'], paid_booking.booking_id)

    def test_invoice_register_paginates_and_preserves_filters(self):
        for index in range(11):
            self.create_booking(customer_name=f'Pagination Customer {index}')

        response = self.client.get(
            reverse('invoices'),
            {'search': 'Pagination Customer', 'status': 'pending', 'page': 2},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['page_obj'].number, 2)
        self.assertEqual(len(response.context['invoice_list']), 1)
        self.assertContains(response, 'search=Pagination%20Customer&amp;status=pending&amp;page=1')

    def test_invoice_register_marks_past_unpaid_bookings_overdue(self):
        overdue_booking = self.create_booking(
            event_date=date.today() - timedelta(days=1),
        )

        response = self.client.get(reverse('invoices'), {'status': 'overdue'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['invoice_list'][0]['booking'], overdue_booking.booking_id)
        self.assertEqual(response.context['invoice_list'][0]['status'], 'overdue')

    def test_invoice_detail_uses_current_booking_and_payments(self):
        booking = self.create_booking(advance_amount=25000)
        invoice_id = booking.booking_id.replace('BK-', 'INV-', 1)

        response = self.client.get(f'{reverse("invoice_detail", args=[invoice_id])}?popup=1')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, invoice_id)
        self.assertContains(response, 'Invoice Customer')
        self.assertContains(response, 'H1')
        self.assertContains(response, 'Rs 25,000')
        self.assertContains(response, 'Rs 75,000')
        self.assertContains(response, 'TERMS &amp; CONDITIONS')
        self.assertContains(response, 'window.print()')
        self.assertNotContains(response, 'Main navigation')

    def test_generated_invoice_pdf_has_complete_single_page_layout(self):
        booking = self.create_booking(advance_amount=25000)
        invoice_id = booking.booking_id.replace('BK-', 'INV-', 1)
        pdf = _build_invoice_pdf(_build_invoice(booking), invoice_id)
        reader = PdfReader(BytesIO(pdf))

        self.assertEqual(len(reader.pages), 1)
        page_text = reader.pages[0].extract_text()
        for expected_text in (
            'ROYAL PALACE HALL',
            invoice_id,
            booking.customer_email,
            'PAYMENT NOTE',
            'Balance due',
            'TERMS & CONDITIONS',
            'Karachi, Pakistan',
        ):
            self.assertIn(expected_text, page_text)

    def test_invoice_detail_returns_404_for_unknown_invoice(self):
        response = self.client.get(reverse('invoice_detail', args=['INV-2099-999']))

        self.assertEqual(response.status_code, 404)

    def test_invoice_register_has_no_fake_invoice_when_no_bookings_exist(self):
        response = self.client.get(reverse('invoices'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No invoices yet.')
        self.assertNotContains(response, 'INV-2026-126')
