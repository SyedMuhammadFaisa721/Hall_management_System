from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Hall_portion, Inventory, InventoryCategory, newbooking


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
