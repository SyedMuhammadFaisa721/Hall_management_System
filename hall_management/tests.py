from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Hall_portion, Inventory, InventoryCategory, expense, newbooking, payment


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
