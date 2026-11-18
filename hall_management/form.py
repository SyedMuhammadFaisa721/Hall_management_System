from decimal import Decimal

from django import forms
from django.contrib.auth.models import Group
from django.db.models import Q
from django.utils import timezone
from .models import newbooking , staff , expense , Inventory, InventoryCategory , payment
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

class loginform(AuthenticationForm):
        def __init__(self, *args, **kwargs):
            super(loginform, self).__init__(*args, **kwargs)
            self.fields['username'].widget.attrs.update({'placeholder': 'Enter your email' })
            self.fields['password'].widget.attrs.update({'placeholder': 'Enter your password'})


class hallmaster_user_creation(UserCreationForm):
    role = forms.ChoiceField(label='Workspace role', choices=())
    is_active = forms.BooleanField(label='Account is active', required=False, initial=True)

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ('first_name', 'last_name', 'username', 'email')

    def __init__(self, *args, can_create_admin=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.can_create_admin = can_create_admin
        self.fields['role'].choices = [
            ('member', 'Member'),
            ('staff', 'Staff'),
            ('manager', 'Manager'),
        ]
        if can_create_admin:
            self.fields['role'].choices.append(('administrator', 'Administrator'))

        self.fields['first_name'].label = 'First name'
        self.fields['last_name'].label = 'Last name'
        self.fields['username'].label = 'Username'
        self.fields['email'].label = 'Email address'
        self.fields['password1'].label = 'Password'
        self.fields['password2'].label = 'Confirm password'
        self.fields['password1'].help_text = 'Use at least 8 characters and avoid commonly used passwords.'

        for field in self.fields.values():
            field.widget.attrs['class'] = 'user-form-control'
        self.fields['is_active'].widget.attrs['class'] = 'user-form-checkbox'

    def save(self, commit=True):
        user = super().save(commit=False)
        role = self.cleaned_data['role']
        user.is_staff = role in ('staff', 'manager', 'administrator')
        user.is_superuser = role == 'administrator'
        user.is_active = self.cleaned_data['is_active']
        if commit:
            user.save()
            if role == 'manager':
                manager_group, _ = Group.objects.get_or_create(name='Manager')
                user.groups.add(manager_group)
        return user
        
        
        
# START: Booking form backend
class new_booking(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.booking_conflict_date = None

    event_type = forms.ChoiceField(choices=[
        ('Wedding', 'Wedding'),
        ('Engagement', 'Engagement'),
        ('Mehndi', 'Mehndi'),
        ('Corporate', 'Corporate'),
        ('Birthday', 'Birthday'),
    ])
    status = forms.ChoiceField(choices=[
        ('Confirmed', 'Confirmed'),
        ('Advance', 'Advance'),
        ('Pending', 'Pending'),
        ('Cancelled', 'Cancelled'),
    ], initial='Pending')
    payment_method = forms.ChoiceField(
        choices=payment._meta.get_field('method').choices,
        label='Payment method',
        initial='cash',
    )
    advance_amount = forms.IntegerField(
        required=False,
        min_value=1,
        label='Advance amount',
        widget=forms.NumberInput(attrs={'min': 1, 'step': 1, 'inputmode': 'numeric'}),
    )

    class Meta:
        model = newbooking
        fields = (
            "customer_name", "phone_number", "nic_number", "customer_email",
            "event_name", "event_type", "event_date", "event_time",
            "event_guest", "event_hall", "special_req", "hall_price",
            "status", "service", "payment_method", "advance_amount",
        )

    def clean(self):
        # START: Booking advance amount validation
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        advance_amount = cleaned_data.get('advance_amount')
        hall_price = cleaned_data.get('hall_price')

        if status == 'Advance':
            if advance_amount is None:
                self.add_error('advance_amount', 'Enter the advance amount.')
            elif hall_price is not None and advance_amount > hall_price:
                self.add_error('advance_amount', 'Advance amount cannot exceed hall price.')
        else:
            cleaned_data['advance_amount'] = None

        event_date = cleaned_data.get('event_date')
        event_time = cleaned_data.get('event_time')
        event_halls = cleaned_data.get('event_hall')
        booking_status = cleaned_data.get('status', '').strip().lower()
        today = timezone.localdate()
        if event_date and event_date < today:
            self.add_error('event_date', 'Past dates cannot be booked.')

        if (
            event_date
            and event_date >= today
            and event_time
            and event_halls
            and booking_status not in {'cancel', 'cancelled', 'canceled'}
        ):
            conflicting_bookings = newbooking.objects.filter(
                event_date=event_date,
                event_time=event_time,
                event_hall__in=event_halls,
            ).exclude(
                Q(status__iexact='cancel')
                | Q(status__iexact='cancelled')
                | Q(status__iexact='canceled')
            )
            if self.instance.pk:
                conflicting_bookings = conflicting_bookings.exclude(pk=self.instance.pk)

            if conflicting_bookings.exists():
                self.booking_conflict_date = event_date.isoformat()
                self.add_error(
                    None,
                    'This date and event time already have a booking for one or more selected hall portions.',
                )

        return cleaned_data
        # END: Booking advance amount validation
# END: Booking form backend
class new_staff(forms.ModelForm):
    class Meta:
        model = staff
        exclude = ["staff_id"]
class new_expense(forms.ModelForm):
    expense_category = forms.ChoiceField(choices=[
        ('Food', 'Food'),
        ('Decoration', 'Decoration'),
        ('Maintenance', 'Maintenance'),
        ('Staff', 'Staff'),
        ('Electricity', 'Electricity'),
        ('Marketing', 'Marketing'),
        ('Other', 'Other'),
    ])
    amount = forms.IntegerField(min_value=1)
    status = forms.ChoiceField(
        choices=[('Paid', 'Paid'), ('Pending', 'Pending')],
        initial='Paid',
    )

    class Meta:
        model   = expense
        exclude = ["expense_id"]
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }

class new_payment(forms.ModelForm):
    amount = forms.DecimalField(
        min_value=Decimal('0.01'),
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'min': '0.01',
            'step': '0.01',
            'inputmode': 'decimal',
        }),
    )
    booking = forms.ModelChoiceField(
        queryset=newbooking.objects.none(),
        label='Booking',
        empty_label='Choose a booking',
    )
    payment_status = forms.ChoiceField(
        choices=[
            ('paid', 'Paid'),
            ('advance', 'Advance'),
            ('pending', 'Pending'),
        ],
        initial='paid',
        label='Payment status',
    )

    class Meta:
        model = payment
        fields = ('booking', 'payment_date', 'method', 'amount', 'refference_num', 'payment_status')
        widgets = {
            'payment_date': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['booking'].queryset = newbooking.objects.all().order_by('-event_date')
        self.fields['booking'].label_from_instance = (
            lambda booking: f'{booking.booking_id} · {booking.customer_name} · {booking.event_date:%d %b %Y}'
        )
        self.fields['refference_num'].label = 'Reference number'
        self.fields['refference_num'].widget.attrs['maxlength'] = 40
        for field in self.fields.values():
            field.widget.attrs['class'] = 'payment-form-control'

    def clean(self):
        cleaned_data = super().clean()
        booking = cleaned_data.get('booking')
        amount = cleaned_data.get('amount')

        if booking is not None and amount is not None:
            remaining_balance = booking.remaining_balance
            if amount > remaining_balance:
                self.add_error(
                    'amount',
                    f'Amount cannot exceed the remaining balance of PKR {remaining_balance:,.2f}.',
                )

        return cleaned_data

class new_inventory(forms.ModelForm):
    class Meta:
        model = Inventory
        fields = "__all__"
        widgets = {
            'inventory_name': forms.TextInput(attrs={'class': 'input'}),
            'category': forms.Select(attrs={'class': 'select'}),
            'inventory_quantity': forms.NumberInput(attrs={'class': 'input inventory-quantity-input', 'min': 0}),
            'available_quantity': forms.NumberInput(attrs={'class': 'input inventory-quantity-input', 'min': 0}),
            'damage_quantity': forms.NumberInput(attrs={'class': 'input inventory-quantity-input', 'min': 0}),
        }

    def clean(self):
        cleaned_data = super().clean()
        total = cleaned_data.get('inventory_quantity')
        available = cleaned_data.get('available_quantity')
        damaged = cleaned_data.get('damage_quantity')

        for field_name in ('inventory_quantity', 'available_quantity', 'damage_quantity'):
            value = cleaned_data.get(field_name)
            if value is not None and value < 0:
                self.add_error(field_name, 'Quantity cannot be negative.')

        if total is not None and available is not None and damaged is not None:
            if available + damaged > total:
                self.add_error(
                    'damage_quantity',
                    'Available and damaged quantities cannot exceed total quantity.',
                )

        return cleaned_data


class new_inventory_category(forms.ModelForm):
    class Meta:
        model  = InventoryCategory
        fields = "__all__" 