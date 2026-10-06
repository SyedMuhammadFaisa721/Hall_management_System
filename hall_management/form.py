from django import forms
from django.contrib.auth.models import Group
from .models import newbooking , staff , expense , Inventory, InventoryCategory
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
        
        
        
class new_booking(forms.ModelForm):
    class Meta:
        model = newbooking
        fields = ("customer_name" , "phone_number", "nic_number" , "customer_email" , "event_name","event_type","event_date", "event_guest" , "event_hall", "special_req", "hall_price", "status")
class new_staff(forms.ModelForm):
    class Meta:
        model = staff
        exclude = ["staff_id"]
class new_expense(forms.ModelForm):
    class Meta:
        model   = expense
        exclude = ["expense_id"]
class new_inventory(forms.ModelForm) :
    class Meta:
        model = Inventory
        fields = "__all__"
class new_inventory_category(forms.ModelForm):
    class Meta:
        model  = InventoryCategory
        fields = "__all__" 