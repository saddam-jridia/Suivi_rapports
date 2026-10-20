from django import forms
from django.contrib.auth.models import User
from captcha.fields import CaptchaField


class UserForm(forms.ModelForm):
    # ... (ta classe existante pour l'admin) ...

    password = forms.CharField(
        label="كلمة السر",
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=False,
    )
    password_confirm = forms.CharField(
        label="تأكيد كلمة السر",
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=False,
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email',
                  'is_active', 'is_staff', 'is_superuser']
        widgets = {
            'username':   forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name':  forms.TextInput(attrs={'class': 'form-control'}),
            'email':      forms.EmailInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'username':     "اسم المستخدم",
            'first_name':   "الاسم",
            'last_name':    "اللقب",
            'email':        "البريد الإلكتروني",
            'is_active':    "نشط",
            'is_staff':     "موظف",
            'is_superuser': "مدير عام",
        }

    def __init__(self, *args, **kwargs):
        self.is_update = kwargs.get('instance') is not None
        super().__init__(*args, **kwargs)
        if not self.is_update:
            self.fields['password'].required = True
            self.fields['password_confirm'].required = True

    def clean(self):
        cleaned = super().clean()
        pwd  = cleaned.get('password')
        pwd2 = cleaned.get('password_confirm')
        if pwd or pwd2:
            if pwd != pwd2:
                raise forms.ValidationError("كلمتا السر غير متطابقتين")
            if len(pwd) < 8:
                raise forms.ValidationError("كلمة السر يجب أن تكون 8 أحرف على الأقل")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        pwd = self.cleaned_data.get('password')
        if pwd:
            user.set_password(pwd)
        if commit:
            user.save()
        return user


# =========================================================
# FORMULAIRE PUBLIC AVEC CAPTCHA
# =========================================================
class DelegateRegisterForm(forms.Form):
    """Formulaire d'inscription publique d'un délégué."""

    # ------------------- الولاية -------------------
    WILAYAS = [
        ('01', 'تونس'), ('02', 'أريانة'), ('03', 'بن عروس'),
        ('04', 'منوبة'), ('05', 'نابل'), ('06', 'زغوان'),
        ('07', 'بنزرت'), ('08', 'جندوبة'), ('09', 'الكاف'),
        ('10', 'سليانة'), ('11', 'القيروان'), ('12', 'القصرين'),
        ('13', 'سيدي بوزيد'), ('14', 'سوسة'), ('15', 'المنستير'),
        ('16', 'المهدية'), ('17', 'صفاقس'), ('18', 'قابس'),
        ('19', 'مدنين'), ('20', 'تطاوين'), ('21', 'قبلي'),
        ('22', 'توزر'), ('23', 'قفصة'), ('24', 'باجة'),
    ]

    ROLES = [
        ('central',  'المندوب العام'),
        ('regional', 'مندوب حماية الطفولة'),
        ('chef de bureau', 'Admin'),
    ]

    wilaya        = forms.ChoiceField(
        label="الولاية", choices=WILAYAS,
        widget=forms.Select(attrs={'class': 'form-select', 'required': True}),
    )
    role          = forms.ChoiceField(
        label="الصفة", choices=ROLES,
        widget=forms.Select(attrs={'class': 'form-select', 'required': True}),
    )
    delegate_code = forms.CharField(
        label="المعرّف الوحيد", max_length=10,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'placeholder': 'أدخل 10 أرقام',
            'maxlength': '10', 'required': True,
        }),
    )
    first_name    = forms.CharField(
        label="الاسم", max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'required': True}),
    )
    last_name     = forms.CharField(
        label="اللقب", max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'required': True}),
    )
    phone         = forms.CharField(
        label="الهاتف", max_length=8, required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'placeholder': '8 أرقام', 'maxlength': '8',
        }),
    )
    email         = forms.EmailField(
        label="البريد الإلكتروني", required=False,
        widget=forms.EmailInput(attrs={'class': 'form-control'}),
    )
    password      = forms.CharField(
        label="كلمة السر", min_length=8,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control', 'placeholder': '8 أحرف على الأقل',
            'required': True,
        }),
    )

    # ---------- CAPTCHA ----------
    captcha = CaptchaField(label="الرمز")

    # ---------- Validations ----------
    def clean_delegate_code(self):
        code = self.cleaned_data.get('delegate_code', '').strip()
        if not code.isdigit() or len(code) != 10:
            raise forms.ValidationError("المعرّف الوحيد يجب أن يكون 10 أرقام")
        if User.objects.filter(username=code).exists():
            raise forms.ValidationError("المعرّف الوحيد مستعمل بالفعل")
        return code

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip()
        if email and User.objects.filter(email=email).exists():
            raise forms.ValidationError("البريد الإلكتروني مستعمل بالفعل")
        return email