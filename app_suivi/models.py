from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import RegexValidator



# =========================================================
# CONSTANTES
# =========================================================

WILAYAS = [
    ('01', 'تونس'),       ('02', 'أريانة'),      ('03', 'بن عروس'),
    ('04', 'منوبة'),      ('05', 'نابل'),        ('06', 'زغوان'),
    ('07', 'بنزرت'),      ('08', 'جندوبة'),      ('09', 'الكاف'),
    ('10', 'سليانة'),     ('11', 'القيروان'),    ('12', 'القصرين'),
    ('13', 'سيدي بوزيد'), ('14', 'سوسة'),        ('15', 'المنستير'),
    ('16', 'المهدية'),    ('17', 'صفاقس'),       ('18', 'قابس'),
    ('19', 'مدنين'),      ('20', 'تطاوين'),      ('21', 'قبلي'),
    ('22', 'توزر'),       ('23', 'قفصة'),        ('24', 'باجة'),
]

ROLES = [
    ('central',        'المندوب العام'),
    ('regional',       'مندوب حماية الطفولة'),
    ('chef de bureau', 'Admin'),
]

REQUEST_STATUS = [
    ('pending',  'في الانتظار'),
    ('approved', 'تم القبول'),
    ('rejected', 'تم الرفض'),
]


# =========================================================
# VALIDATORS
# =========================================================

phone_validator = RegexValidator(
    regex=r'^\d{8}$',
    message="رقم الهاتف يجب أن يتكون من 8 أرقام"
)

code_validator = RegexValidator(
    regex=r'^\d{10}$',
    message="المعرّف الوحيد يجب أن يتكون من 10 أرقام"
)


# =========================================================
# PROFIL DÉLÉGUÉ
# =========================================================

class DelegateProfile(models.Model):
    """Profil étendu d'un délégué, lié au User Django natif."""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='delegate_profile',
        verbose_name="المستخدم",
    )
    wilaya = models.CharField(
        max_length=2,
        choices=WILAYAS,
        verbose_name="الولاية",
    )
    role = models.CharField(
        max_length=20,
        choices=ROLES,
        verbose_name="الصفة",
    )
    delegate_code = models.CharField(
        max_length=10,
        unique=True,
        validators=[code_validator],
        verbose_name="المعرّف الوحيد",
    )
    phone = models.CharField(
        max_length=8,
        blank=True,
        validators=[phone_validator],
        verbose_name="الهاتف",
    )
    is_validated = models.BooleanField(
        default=False,
        verbose_name="تم التحقق",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "مندوب"
        verbose_name_plural = "المناديب"
        ordering = ['-created_at']

    def __str__(self):
        return (
            f"{self.user.get_full_name() or self.user.username} "
            f"({self.get_wilaya_display()})"
        )

    def save(self, *args, **kwargs):
        # Sauvegarde initiale
        super().save(*args, **kwargs)

        # Synchronisation du username avec le delegate_code
        if self.delegate_code and self.user_id:
            if self.user.username != self.delegate_code:
                self.user.username = self.delegate_code
                self.user.save(update_fields=['username'])


# =========================================================
# DEMANDE D'INSCRIPTION (validation admin avant création User)
# =========================================================

class RegistrationRequest(models.Model):
    """
    Demande d'inscription d'un nouveau délégué (formulaire public).
    L'admin valide → création automatique du User + DelegateProfile.
    """

    # Données brutes saisies par le demandeur
    delegate_code = models.CharField(
        max_length=10,
        validators=[code_validator],
        verbose_name="المعرّف الوحيد",
    )
    first_name = models.CharField(max_length=100, verbose_name="الاسم")
    last_name = models.CharField(max_length=100, verbose_name="اللقب")
    email = models.EmailField(blank=True, verbose_name="البريد الإلكتروني")
    phone = models.CharField(
        max_length=8,
        blank=True,
        validators=[phone_validator],
        verbose_name="الهاتف",
    )
    wilaya = models.CharField(
        max_length=2,
        choices=WILAYAS,
        verbose_name="الولاية",
    )
    role = models.CharField(
        max_length=20,
        choices=ROLES,
        verbose_name="الصفة",
    )

    # ✅ Mot de passe haché fourni à l'inscription
    password_hash = models.CharField(
        max_length=128,
        blank=True,
        verbose_name="كلمة السر (مشفّرة)",
    )

    # Statut de la demande
    status = models.CharField(
        max_length=10,
        choices=REQUEST_STATUS,
        default='pending',
        verbose_name="الحالة",
    )
    admin_note = models.TextField(
        blank=True,
        verbose_name="ملاحظة الإدارة",
    )
    reviewed_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='reviewed_requests',
        verbose_name="تمت المراجعة بواسطة",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "طلب تسجيل"
        verbose_name_plural = "طلبات التسجيل"
        ordering = ['-created_at']

    def __str__(self):
        return (
            f"{self.first_name} {self.last_name} — "
            f"{self.delegate_code} [{self.get_status_display()}]"
        )

    def approve(self, admin_user):
        """Valide la demande et crée le User + DelegateProfile."""
        if self.status != 'pending':
            return None

        # Vérification : ne pas créer de doublon
        if User.objects.filter(username=self.delegate_code).exists():
            self.status = 'rejected'
            self.admin_note = "المعرّف الوحيد مستعمل بالفعل"
            self.reviewed_by = admin_user
            self.reviewed_at = timezone.now()
            self.save()
            return None

        # ✅ Création du User AVEC le mot de passe haché
        user = User.objects.create(
            username=self.delegate_code,
            email=self.email,
            first_name=self.first_name,
            last_name=self.last_name,
            is_active=True,
        )
        # On réinjecte le hash tel quel (déjà haché)
        if self.password_hash:
            user.password = self.password_hash
        else:
            user.set_unusable_password()
        user.save()

        # Création du profil
        DelegateProfile.objects.create(
            user=user,
            wilaya=self.wilaya,
            role=self.role,
            delegate_code=self.delegate_code,
            phone=self.phone,
            is_validated=True,
        )

        # Mise à jour de la demande
        self.status = 'approved'
        self.reviewed_by = admin_user
        self.reviewed_at = timezone.now()
        self.save()

        return user

    def reject(self, admin_user, note=''):
        """Refuse la demande."""
        self.status = 'rejected'
        self.admin_note = note
        self.reviewed_by = admin_user
        self.reviewed_at = timezone.now()
        self.save()


# =========================================================
# JOURNAL D'ACTIVITÉ
# =========================================================

class ActivityLog(models.Model):
    """Trace les actions importantes (création, modification, suppression)."""

    ACTION_CHOICES = [
        ('login',    'تسجيل دخول'),
        ('logout',   'تسجيل خروج'),
        ('create',   'إنشاء'),
        ('update',   'تحديث'),
        ('delete',   'حذف'),
        ('approve',  'قبول'),
        ('reject',   'رفض'),
    ]

    user = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='activities',
        verbose_name="المستخدم",
    )
    action = models.CharField(
        max_length=10,
        choices=ACTION_CHOICES,
        verbose_name="الإجراء",
    )
    target_model = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="الكيان",
    )
    target_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="رقم الكيان",
    )
    description = models.TextField(blank=True, verbose_name="الوصف")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "سجل نشاط"
        verbose_name_plural = "سجلات النشاط"
        ordering = ['-created_at']

    def __str__(self):
        return (
            f"[{self.created_at:%Y-%m-%d %H:%M}] "
            f"{self.user} — {self.get_action_display()}"
        )

# =========================================================
# PROGRAMME : روضتنا في حومتنا
# =========================================================

class Rawdhatna(models.Model):
    """متابعة برنامج روضتنا في حومتنا — رياض الأطفال."""

    # --- Identification ---
    wilaya = models.CharField(
        max_length=2,
        choices=WILAYAS,
        verbose_name="الولاية",
    )
    year = models.PositiveIntegerField(
        verbose_name="السنة",
        default=2026,
    )

    # --- فواضل السنوات السابقة  (Tranches antérieures) ---
    previous_credits_committed = models.DecimalField(
        max_digits=15, decimal_places=3, default=0,
        verbose_name="    فواضل السنوات السابقة - تعهدا",
    )
    previous_credits_paid = models.DecimalField(
        max_digits=15, decimal_places=3, default=0,
        verbose_name=" فواضل السنوات السابقة - دفعا",
    )

    # --- اعتمادات السنة الحالية (Crédits année en cours) ---
    current_credits_committed = models.DecimalField(
        max_digits=15, decimal_places=3, default=0,
        verbose_name="اعتمادات السنة الحالية - تعهدا",
    )
    current_credits_paid = models.DecimalField(
        max_digits=15, decimal_places=3, default=0,
        verbose_name="اعتمادات السنة الحالية - دفعا",
    )

    # --- مجموع الاعتمادات (Total des crédits) ---
    total_credits_committed = models.DecimalField(
        max_digits=15, decimal_places=3, default=0,
        verbose_name="مجموع الاعتمادات - تعهدا",
    )
    total_credits_paid = models.DecimalField(
        max_digits=15, decimal_places=3, default=0,
        verbose_name="مجموع الاعتمادات - دفعا",
    )

    # --- نسبة الاستهلاك (Taux de consommation) ---
    consumption_rate_committed = models.DecimalField(
        max_digits=8, decimal_places=2, default=0,
        verbose_name="نسبة الاستهلاك - تعهدا (%)",
    )
    consumption_rate_paid = models.DecimalField(
        max_digits=8, decimal_places=2, default=0,
        verbose_name="نسبة الاستهلاك - دفعا (%)",
    )

    # --- الاعتمادات المتبقية (Crédits restants) ---
    remaining_credits_committed = models.DecimalField(
        max_digits=15, decimal_places=3, default=0,
        verbose_name="الاعتمادات المتبقية - تعهدا",
    )
    remaining_credits_paid = models.DecimalField(
        max_digits=15, decimal_places=3, default=0,
        verbose_name="الاعتمادات المتبقية - دفعا",
    )

    # --- المستفيدون ---
    beneficiaries_female = models.PositiveIntegerField(
        default=0,
        verbose_name="عدد الإناث المستفيدات",
    )
    beneficiaries_male = models.PositiveIntegerField(
        default=0,
        verbose_name="عدد الذكور المستفيدين",
    )

    # --- رياض الأطفال ---
    kindergartens_count = models.PositiveIntegerField(
        default=0,
        verbose_name="عدد رياض الأطفال المنخرطة في البرنامج",
    )

    # --- Meta ---
    notes = models.TextField(
        blank=True,
        verbose_name="ملاحظات",
    )
    created_by = models.ForeignKey(
        User,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='rawdhatna_records',
        verbose_name="أُنشئ بواسطة",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "روضتنا في حومتنا"
        verbose_name_plural = "روضتنا في حومتنا"
        ordering = ['-year', 'wilaya']
        unique_together = [['wilaya', 'year']]

    def __str__(self):
        return f"روضتنا في حومتنا — {self.get_wilaya_display()} ({self.year})"

    @property
    def beneficiaries_total(self):
        return self.beneficiaries_female + self.beneficiaries_male

# =========================================================
# PROGRAMME : أطفال طيف التوحد
# =========================================================

class AutismProgram(models.Model):
    """متابعة برنامج أطفال طيف التوحد."""

    # --- Identification ---
    wilaya = models.CharField(
        max_length=2,
        choices=WILAYAS,
        verbose_name="الولاية",
    )
    year = models.PositiveIntegerField(
        verbose_name="السنة",
        default=2026,
    )

    # --- نوات السابقة ---
    previous_credits_committed = models.DecimalField(
        max_digits=15, decimal_places=3, default=0,
        verbose_name="نوات السابقة - تعهدا",
    )
    previous_credits_paid = models.DecimalField(
        max_digits=15, decimal_places=3, default=0,
        verbose_name="نوات السابقة - دفعا",
    )

    # --- اعتمادات السنة الحالية ---
    current_credits_committed = models.DecimalField(
        max_digits=15, decimal_places=3, default=0,
        verbose_name="اعتمادات السنة الحالية - تعهدا",
    )
    current_credits_paid = models.DecimalField(
        max_digits=15, decimal_places=3, default=0,
        verbose_name="اعتمادات السنة الحالية - دفعا",
    )

    # --- مجموع الاعتمادات ---
    total_credits_committed = models.DecimalField(
        max_digits=15, decimal_places=3, default=0,
        verbose_name="مجموع الاعتمادات - تعهدا",
    )
    total_credits_paid = models.DecimalField(
        max_digits=15, decimal_places=3, default=0,
        verbose_name="مجموع الاعتمادات - دفعا",
    )

    # --- نسبة الاستهلاك ---
    consumption_rate_committed = models.DecimalField(
        max_digits=8, decimal_places=2, default=0,
        verbose_name="نسبة الاستهلاك - تعهدا (%)",
    )
    consumption_rate_paid = models.DecimalField(
        max_digits=8, decimal_places=2, default=0,
        verbose_name="نسبة الاستهلاك - دفعا (%)",
    )

    # --- الاعتمادات المتبقية ---
    remaining_credits_committed = models.DecimalField(
        max_digits=15, decimal_places=3, default=0,
        verbose_name="الاعتمادات المتبقية - تعهدا",
    )
    remaining_credits_paid = models.DecimalField(
        max_digits=15, decimal_places=3, default=0,
        verbose_name="الاعتمادات المتبقية - دفعا",
    )

    # --- المستفيدون ---
    beneficiaries_female = models.PositiveIntegerField(
        default=0,
        verbose_name="عدد الإناث المستفيدات",
    )
    beneficiaries_male = models.PositiveIntegerField(
        default=0,
        verbose_name="عدد الذكور المستفيدين",
    )

    # --- المؤسسات والجمعيات ---
    associations_count = models.PositiveIntegerField(
        default=0,
        verbose_name="عدد الجمعيات والمراكز المعنية",
    )
    centers_count = models.PositiveIntegerField(
        default=0,
        verbose_name="عدد المراكز المتخصصة",
    )

    # --- Meta ---
    notes = models.TextField(
        blank=True,
        verbose_name="ملاحظات",
    )
    created_by = models.ForeignKey(
        User,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='autism_records',
        verbose_name="أُنشئ بواسطة",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "أطفال طيف التوحد"
        verbose_name_plural = "أطفال طيف التوحد"
        ordering = ['-year', 'wilaya']
        unique_together = [['wilaya', 'year']]

    def __str__(self):
        return f"أطفال طيف التوحد — {self.get_wilaya_display()} ({self.year})"

    @property
    def beneficiaries_total(self):
        return self.beneficiaries_female + self.beneficiaries_male

# =========================================================
# PROGRAMME : الإيداع العائلي لكبار السن
# =========================================================

class SeniorFamilyCare(models.Model):
    """متابعة برنامج الإيداع العائلي لكبار السن."""

    # --- Identification ---
    wilaya = models.CharField(
        max_length=2,
        choices=WILAYAS,
        verbose_name="الولاية",
    )
    year = models.PositiveIntegerField(
        verbose_name="السنة",
        default=2026,
    )

    # --- فواصل نوات السابقة ---
    previous_credits_committed = models.DecimalField(
        max_digits=15, decimal_places=3, default=0,
        verbose_name="فواصل نوات السابقة - تعهدا",
    )
    previous_credits_paid = models.DecimalField(
        max_digits=15, decimal_places=3, default=0,
        verbose_name="فواصل نوات السابقة - دفعا",
    )

    # --- اعتمادات سنة الحالية ---
    current_credits_committed = models.DecimalField(
        max_digits=15, decimal_places=3, default=0,
        verbose_name="اعتمادات سنة الحالية - تعهدا",
    )
    current_credits_paid = models.DecimalField(
        max_digits=15, decimal_places=3, default=0,
        verbose_name="اعتمادات سنة الحالية - دفعا",
    )

    # --- مجموع الاعتمادات ---
    total_credits_committed = models.DecimalField(
        max_digits=15, decimal_places=3, default=0,
        verbose_name="مجموع الاعتمادات - تعهدا",
    )
    total_credits_paid = models.DecimalField(
        max_digits=15, decimal_places=3, default=0,
        verbose_name="مجموع الاعتمادات - دفعا",
    )

    # --- نسبة الصرف ---
    consumption_rate_committed = models.DecimalField(
        max_digits=8, decimal_places=2, default=0,
        verbose_name="نسبة الصرف - تعهدا (%)",
    )
    consumption_rate_paid = models.DecimalField(
        max_digits=8, decimal_places=2, default=0,
        verbose_name="نسبة الصرف - دفعا (%)",
    )

    # --- المستفيدون ---
    beneficiaries_female = models.PositiveIntegerField(
        default=0,
        verbose_name="عدد كبار السن المستفيدين - إناث",
    )
    beneficiaries_male = models.PositiveIntegerField(
        default=0,
        verbose_name="عدد كبار السن المستفيدين - ذكور",
    )

    families_count = models.PositiveIntegerField(
        default=0,
        verbose_name="عدد الأسر المنتفعة بالبرنامج",
    )

    # --- Meta ---
    notes = models.TextField(
        blank=True,
        verbose_name="ملاحظات",
    )
    created_by = models.ForeignKey(
        User,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='senior_family_records',
        verbose_name="أُنشئ بواسطة",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "الإيداع العائلي لكبار السن"
        verbose_name_plural = "الإيداع العائلي لكبار السن"
        ordering = ['-year', 'wilaya']
        unique_together = [['wilaya', 'year']]

    def __str__(self):
        return f"الإيداع العائلي — {self.get_wilaya_display()} ({self.year})"

    @property
    def beneficiaries_total(self):
        return self.beneficiaries_female + self.beneficiaries_male

# =========================================================
# PROGRAMME : الإدماج الاقتصادي للأسر ذات الوضعيات الخاصة
# =========================================================

class FamilyEconomicIntegration(models.Model):
    """متابعة الإدماج الاقتصادي للأسر ذات الوضعيات الخاصة."""

    # --- Identification ---
    wilaya = models.CharField(
        max_length=2,
        choices=WILAYAS,
        verbose_name="الولاية",
    )
    year = models.PositiveIntegerField(
        verbose_name="السنة",
        default=2026,
    )

    # --- الفواصل والاعتمادات ---
    previous_credits_committed = models.DecimalField(
        max_digits=15, decimal_places=3, default=0, verbose_name="فواصل نوات السابقة - تعهدا"
    )
    previous_credits_paid = models.DecimalField(
        max_digits=15, decimal_places=3, default=0, verbose_name="فواصل نوات السابقة - دفعا"
    )
    current_credits_committed = models.DecimalField(
        max_digits=15, decimal_places=3, default=0, verbose_name="اعتمادات سنة الحالية - تعهدا"
    )
    current_credits_paid = models.DecimalField(
        max_digits=15, decimal_places=3, default=0, verbose_name="اعتمادات سنة الحالية - دفعا"
    )
    total_credits_committed = models.DecimalField(
        max_digits=15, decimal_places=3, default=0, verbose_name="مجموع الاعتمادات - تعهدا"
    )
    total_credits_paid = models.DecimalField(
        max_digits=15, decimal_places=3, default=0, verbose_name="مجموع الاعتمادات - دفعا"
    )
    consumption_rate_committed = models.DecimalField(
        max_digits=8, decimal_places=2, default=0, verbose_name="نسبة الصرف - تعهدا (%)"
    )
    consumption_rate_paid = models.DecimalField(
        max_digits=8, decimal_places=2, default=0, verbose_name="نسبة الصرف - دفعا (%)"
    )
    remaining_credits_committed = models.DecimalField(
        max_digits=15, decimal_places=3, default=0, verbose_name="الاعتمادات المتبقية - تعهدا"
    )
    remaining_credits_paid = models.DecimalField(
        max_digits=15, decimal_places=3, default=0, verbose_name="الاعتمادات المتبقية - دفعا"
    )

    # --- الأسر واللجان ---
    families_count = models.PositiveIntegerField(default=0, verbose_name="عدد الأسر المنتفعة بالبرنامج")
    committee_meetings_count = models.PositiveIntegerField(default=0, verbose_name="عدد جلسات عمل اللجنة الجهوية")

    # --- المطالب ---
    accepted_female = models.PositiveIntegerField(default=0, verbose_name="المطالب المقبولة - إناث")
    accepted_male = models.PositiveIntegerField(default=0, verbose_name="المطالب المقبولة - ذكور")
    rejected_female = models.PositiveIntegerField(default=0, verbose_name="المطالب المرفوضة - إناث")
    rejected_male = models.PositiveIntegerField(default=0, verbose_name="المطالب المرفوضة - ذكور")
    rejection_reasons = models.TextField(blank=True, verbose_name="أسباب الرفض")

    # --- المتابعة والتكوين ---
    field_visits_count = models.PositiveIntegerField(default=0, verbose_name="عدد الزيارات الميدانية للمتابعة")
    training_courses_count = models.PositiveIntegerField(default=0, verbose_name="عدد الدورات التدريبية")
    trainees_female = models.PositiveIntegerField(default=0, verbose_name="المشاركين في الدورات - إناث")
    trainees_male = models.PositiveIntegerField(default=0, verbose_name="المشاركين في الدورات - ذكور")

    # --- الإشكاليات ---
    obstacles = models.TextField(blank=True, verbose_name="الإشكاليات المعترضة")

    # --- Meta ---
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "الإدماج الاقتصادي للأسر"
        verbose_name_plural = "الإدماج الاقتصادي للأسر"
        ordering = ['-year', 'wilaya']
        unique_together = [['wilaya', 'year']]

    def __str__(self):
        return f"الإدماج الاقتصادي — {self.get_wilaya_display()} ({self.year})"

# =========================================================
# PROGRAMME : الإدماج الاقتصادي لأمهات التلاميذ المهددين
# =========================================================

class MothersSchoolDropout(models.Model):
    """متابعة الإدماج الاقتصادي لأمهات التلاميذ المهددين بالانقطاع المدرسي."""

    # --- Identification ---
    wilaya = models.CharField(
        max_length=2,
        choices=WILAYAS,
        verbose_name="الولاية",
    )
    year = models.PositiveIntegerField(
        verbose_name="السنة",
        default=2026,
    )

    # --- الفواصل والاعتمادات ---
    previous_credits_committed = models.DecimalField(
        max_digits=15, decimal_places=3, default=0, verbose_name="فواصل نوات السابقة - تعهدا"
    )
    previous_credits_paid = models.DecimalField(
        max_digits=15, decimal_places=3, default=0, verbose_name="فواصل نوات السابقة - دفعا"
    )
    current_credits_committed = models.DecimalField(
        max_digits=15, decimal_places=3, default=0, verbose_name="اعتمادات سنة الحالية - تعهدا"
    )
    current_credits_paid = models.DecimalField(
        max_digits=15, decimal_places=3, default=0, verbose_name="اعتمادات سنة الحالية - دفعا"
    )
    total_credits_committed = models.DecimalField(
        max_digits=15, decimal_places=3, default=0, verbose_name="مجموع الاعتمادات - تعهدا"
    )
    total_credits_paid = models.DecimalField(
        max_digits=15, decimal_places=3, default=0, verbose_name="مجموع الاعتمادات - دفعا"
    )
    consumption_rate_committed = models.DecimalField(
        max_digits=8, decimal_places=2, default=0, verbose_name="نسبة الصرف - تعهدا (%)"
    )
    consumption_rate_paid = models.DecimalField(
        max_digits=8, decimal_places=2, default=0, verbose_name="نسبة الصرف - دفعا (%)"
    )
    remaining_credits_committed = models.DecimalField(
        max_digits=15, decimal_places=3, default=0, verbose_name="الاعتمادات المتبقية - تعهدا"
    )
    remaining_credits_paid = models.DecimalField(
        max_digits=15, decimal_places=3, default=0, verbose_name="الاعتمادات المتبقية - دفعا"
    )

    # --- الأسر واللجان ---
    families_count = models.PositiveIntegerField(default=0, verbose_name="عدد الأسر المنتفعة بالبرنامج")
    committee_meetings_count = models.PositiveIntegerField(default=0, verbose_name="عدد جلسات عمل اللجنة الجهوية")

    # --- المطالب ---
    accepted_female = models.PositiveIntegerField(default=0, verbose_name="المطالب المقبولة - إناث")
    accepted_male = models.PositiveIntegerField(default=0, verbose_name="المطالب المقبولة - ذكور")
    rejected_female = models.PositiveIntegerField(default=0, verbose_name="المطالب المرفوضة - إناث")
    rejected_male = models.PositiveIntegerField(default=0, verbose_name="المطالب المرفوضة - ذكور")
    rejection_reasons = models.TextField(blank=True, verbose_name="أسباب الرفض")

    # --- المتابعة والتكوين ---
    field_visits_count = models.PositiveIntegerField(default=0, verbose_name="عدد الزيارات الميدانية للمتابعة")
    training_courses_count = models.PositiveIntegerField(default=0, verbose_name="عدد الدورات التدريبية")
    trainees_female = models.PositiveIntegerField(default=0, verbose_name="المشاركات في الدورات - إناث")
    trainees_male = models.PositiveIntegerField(default=0, verbose_name="المشاركين في الدورات - ذكور")

    # --- الإشكاليات ---
    obstacles = models.TextField(blank=True, verbose_name="الإشكاليات المعترضة")

    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "الإدماج الاقتصادي لأمهات التلاميذ"
        verbose_name_plural = "الإدماج الاقتصادي لأمهات التلاميذ"
        ordering = ['-year', 'wilaya']
        unique_together = [['wilaya', 'year']]

    def __str__(self):
        return f"أمهات التلاميذ المهددين — {self.get_wilaya_display()} ({self.year})"


# =========================================================
# PROGRAMME : صامدة (الإدماج الاقتصادي للنساء المعنفات)
# =========================================================

class SamdaProgram(models.Model):
    """متابعة برنامج صامدة للإدماج الاقتصادي للنساء المعنفات."""

    # --- Identification ---
    wilaya = models.CharField(
        max_length=2,
        choices=WILAYAS,
        verbose_name="الولاية",
    )
    year = models.PositiveIntegerField(
        verbose_name="السنة",
        default=2026,
    )

    # --- الفواصل والاعتمادات ---
    previous_credits_committed = models.DecimalField(
        max_digits=15, decimal_places=3, default=0, verbose_name="فواصل نوات السابقة - تعهدا"
    )
    previous_credits_paid = models.DecimalField(
        max_digits=15, decimal_places=3, default=0, verbose_name="فواصل نوات السابقة - دفعا"
    )
    current_credits_committed = models.DecimalField(
        max_digits=15, decimal_places=3, default=0, verbose_name="اعتمادات سنة الحالية - تعهدا"
    )
    current_credits_paid = models.DecimalField(
        max_digits=15, decimal_places=3, default=0, verbose_name="اعتمادات سنة الحالية - دفعا"
    )
    total_credits_committed = models.DecimalField(
        max_digits=15, decimal_places=3, default=0, verbose_name="مجموع الاعتمادات - تعهدا"
    )
    total_credits_paid = models.DecimalField(
        max_digits=15, decimal_places=3, default=0, verbose_name="مجموع الاعتمادات - دفعا"
    )
    consumption_rate_committed = models.DecimalField(
        max_digits=8, decimal_places=2, default=0, verbose_name="نسبة الصرف - تعهدا (%)"
    )
    consumption_rate_paid = models.DecimalField(
        max_digits=8, decimal_places=2, default=0, verbose_name="نسبة الصرف - دفعا (%)"
    )
    remaining_credits_committed = models.DecimalField(
        max_digits=15, decimal_places=3, default=0, verbose_name="الاعتمادات المتبقية - تعهدا"
    )
    remaining_credits_paid = models.DecimalField(
        max_digits=15, decimal_places=3, default=0, verbose_name="الاعتمادات المتبقية - دفعا"
    )

    # --- الأسر واللجان ---
    families_count = models.PositiveIntegerField(default=0, verbose_name="عدد الأسر المنتفعة بالبرنامج")
    committee_meetings_count = models.PositiveIntegerField(default=0, verbose_name="عدد جلسات عمل اللجنة الجهوية")

    # --- المطالب ---
    accepted_female = models.PositiveIntegerField(default=0, verbose_name="المطالب المقبولة - إناث")
    accepted_male = models.PositiveIntegerField(default=0, verbose_name="المطالب المقبولة - ذكور")
    rejected_female = models.PositiveIntegerField(default=0, verbose_name="المطالب المرفوضة - إناث")
    rejected_male = models.PositiveIntegerField(default=0, verbose_name="المطالب المرفوضة - ذكور")
    rejection_reasons = models.TextField(blank=True, verbose_name="أسباب الرفض")

    # --- المتابعة والتكوين ---
    field_visits_count = models.PositiveIntegerField(default=0, verbose_name="عدد الزيارات الميدانية للمتابعة")
    training_courses_count = models.PositiveIntegerField(default=0, verbose_name="عدد الدورات التدريبية")
    trainees_female = models.PositiveIntegerField(default=0, verbose_name="المشاركات في الدورات - إناث")
    trainees_male = models.PositiveIntegerField(default=0, verbose_name="المشاركين في الدورات - ذكور")

    # --- الإشكاليات ---
    obstacles = models.TextField(blank=True, verbose_name="الإشكاليات المعترضة")

    # --- Meta ---
    created_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='samda_records', verbose_name="أُنشئ بواسطة"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "برنامج صامدة"
        verbose_name_plural = "برنامج صامدة"
        ordering = ['-year', 'wilaya']
        unique_together = [['wilaya', 'year']]

    def __str__(self):
        return f"صامدة — {self.get_wilaya_display()} ({self.year})"

# =========================================================
# PROGRAMME : النساء في الريف (المجامع التنموية)
# =========================================================

class RuralWomenProgram(models.Model):
    """متابعة الإدماج الاقتصادي للنساء في الريف والمجامع التنموية."""

    # --- Identification ---
    wilaya = models.CharField(
        max_length=2,
        choices=WILAYAS,
        verbose_name="الولاية",
    )
    year = models.PositiveIntegerField(
        verbose_name="السنة",
        default=2026,
    )

    # --- الفواصل والاعتمادات ---
    previous_credits_committed = models.DecimalField(
        max_digits=15, decimal_places=3, default=0, verbose_name="فواصل نوات السابقة - تعهدا"
    )
    previous_credits_paid = models.DecimalField(
        max_digits=15, decimal_places=3, default=0, verbose_name="فواصل نوات السابقة - دفعا"
    )
    current_credits_committed = models.DecimalField(
        max_digits=15, decimal_places=3, default=0, verbose_name="اعتمادات سنة الحالية - تعهدا"
    )
    current_credits_paid = models.DecimalField(
        max_digits=15, decimal_places=3, default=0, verbose_name="اعتمادات سنة الحالية - دفعا"
    )
    total_credits_committed = models.DecimalField(
        max_digits=15, decimal_places=3, default=0, verbose_name="مجموع الاعتمادات - تعهدا"
    )
    total_credits_paid = models.DecimalField(
        max_digits=15, decimal_places=3, default=0, verbose_name="مجموع الاعتمادات - دفعا"
    )
    consumption_rate_committed = models.DecimalField(
        max_digits=8, decimal_places=2, default=0, verbose_name="نسبة الصرف - تعهدا (%)"
    )
    consumption_rate_paid = models.DecimalField(
        max_digits=8, decimal_places=2, default=0, verbose_name="نسبة الصرف - دفعا (%)"
    )
    remaining_credits_committed = models.DecimalField(
        max_digits=15, decimal_places=3, default=0, verbose_name="الاعتمادات المتبقية - تعهدا"
    )
    remaining_credits_paid = models.DecimalField(
        max_digits=15, decimal_places=3, default=0, verbose_name="الاعتمادات المتبقية - دفعا"
    )

    # --- الأسر واللجان ---
    families_count = models.PositiveIntegerField(default=0, verbose_name="عدد الأسر المنتفعة بالبرنامج")
    committee_meetings_count = models.PositiveIntegerField(default=0, verbose_name="عدد جلسات عمل اللجنة الجهوية")

    # --- المطالب ---
    accepted_female = models.PositiveIntegerField(default=0, verbose_name="المطالب المقبولة - إناث")
    accepted_male = models.PositiveIntegerField(default=0, verbose_name="المطالب المقبولة - ذكور")
    rejected_female = models.PositiveIntegerField(default=0, verbose_name="المطالب المرفوضة - إناث")
    rejected_male = models.PositiveIntegerField(default=0, verbose_name="المطالب المرفوضة - ذكور")
    rejection_reasons = models.TextField(blank=True, verbose_name="أسباب الرفض")

    # --- المتابعة والتكوين ---
    field_visits_count = models.PositiveIntegerField(default=0, verbose_name="عدد الزيارات الميدانية للمتابعة")
    training_courses_count = models.PositiveIntegerField(default=0, verbose_name="عدد الدورات التدريبية")
    trainees_female = models.PositiveIntegerField(default=0, verbose_name="المشاركات في الدورات - إناث")
    trainees_male = models.PositiveIntegerField(default=0, verbose_name="المشاركين في الدورات - ذكور")

    # --- الإشكاليات ---
    obstacles = models.TextField(blank=True, verbose_name="الإشكاليات المعترضة")

    # --- Meta ---
    created_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='rural_women_records', verbose_name="أُنشئ بواسطة"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "النساء في الريف"
        verbose_name_plural = "النساء في الريف"
        ordering = ['-year', 'wilaya']
        unique_together = [['wilaya', 'year']]

    def __str__(self):
        return f"النساء في الريف — {self.get_wilaya_display()} ({self.year})"

# =========================================================
# PROGRAMME : خطة عمل لكل منطقة مشروع
# =========================================================

class ActionPlanZone(models.Model):
    """متابعة خطة عمل لكل منطقة مشروع."""

    # --- Identification ---
    wilaya = models.CharField(
        max_length=2,
        choices=WILAYAS,
        verbose_name="الولاية",
    )
    year = models.PositiveIntegerField(
        verbose_name="السنة",
        default=2026,
    )

    # --- الفواصل والاعتمادات ---
    previous_credits_committed = models.DecimalField(
        max_digits=15, decimal_places=3, default=0, verbose_name="فواصل نوات السابقة - تعهدا"
    )
    previous_credits_paid = models.DecimalField(
        max_digits=15, decimal_places=3, default=0, verbose_name="فواصل نوات السابقة - دفعا"
    )
    current_credits_committed = models.DecimalField(
        max_digits=15, decimal_places=3, default=0, verbose_name="اعتمادات سنة الحالية - تعهدا"
    )
    current_credits_paid = models.DecimalField(
        max_digits=15, decimal_places=3, default=0, verbose_name="اعتمادات سنة الحالية - دفعا"
    )
    total_credits_committed = models.DecimalField(
        max_digits=15, decimal_places=3, default=0, verbose_name="مجموع الاعتمادات - تعهدا"
    )
    total_credits_paid = models.DecimalField(
        max_digits=15, decimal_places=3, default=0, verbose_name="مجموع الاعتمادات - دفعا"
    )
    consumption_rate_committed = models.DecimalField(
        max_digits=8, decimal_places=2, default=0, verbose_name="نسبة الصرف - تعهدا (%)"
    )
    consumption_rate_paid = models.DecimalField(
        max_digits=8, decimal_places=2, default=0, verbose_name="نسبة الصرف - دفعا (%)"
    )
    remaining_credits_committed = models.DecimalField(
        max_digits=15, decimal_places=3, default=0, verbose_name="الاعتمادات المتبقية - تعهدا"
    )
    remaining_credits_paid = models.DecimalField(
        max_digits=15, decimal_places=3, default=0, verbose_name="الاعتمادات المتبقية - دفعا"
    )

    # --- الأسر واللجان ---
    families_count = models.PositiveIntegerField(default=0, verbose_name="عدد المنتفعات بالبرنامج")
    committee_meetings_count = models.PositiveIntegerField(default=0, verbose_name="عدد جلسات عمل اللجنة الجهوية")

    # --- المطالب ---
    accepted_female = models.PositiveIntegerField(default=0, verbose_name="المطالب المقبولة - إناث")
    accepted_male = models.PositiveIntegerField(default=0, verbose_name="المطالب المقبولة - ذكور")
    rejected_female = models.PositiveIntegerField(default=0, verbose_name="المطالب المرفوضة - إناث")
    rejected_male = models.PositiveIntegerField(default=0, verbose_name="المطالب المرفوضة - ذكور")
    rejection_reasons = models.TextField(blank=True, verbose_name="أسباب الرفض")

    # --- المتابعة والتكوين ---
    field_visits_count = models.PositiveIntegerField(default=0, verbose_name="عدد الزيارات الميدانية للمتابعة")
    training_courses_count = models.PositiveIntegerField(default=0, verbose_name="عدد الدورات التدريبية")
    trainees_female = models.PositiveIntegerField(default=0, verbose_name="المشاركات في الدورات - إناث")
    trainees_male = models.PositiveIntegerField(default=0, verbose_name="المشاركين في الدورات - ذكور")

    # --- الإشكاليات ---
    obstacles = models.TextField(blank=True, verbose_name="الإشكاليات المعترضة")

    # --- Meta ---
    created_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='action_plan_records', verbose_name="أُنشئ بواسطة"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "خطة عمل لكل منطقة مشروع"
        verbose_name_plural = "خطة عمل لكل منطقة مشروع"
        ordering = ['-year', 'wilaya']
        unique_together = [['wilaya', 'year']]

    def __str__(self):
        return f"خطة عمل — {self.get_wilaya_display()} ({self.year})"

# =========================================================
# PROGRAMME : رائدات
# =========================================================

class RaedatProgram(models.Model):
    """متابعة برنامج رائدات لدعم المبادرة النسائية والقيادة."""

    # --- Identification ---
    wilaya = models.CharField(
        max_length=2,
        choices=WILAYAS,
        verbose_name="الولاية",
    )
    year = models.PositiveIntegerField(
        verbose_name="السنة",
        default=2026,
    )

    # --- الفواصل والاعتمادات ---
    previous_credits_committed = models.DecimalField(
        max_digits=15, decimal_places=3, default=0, verbose_name="فواصل نوات السابقة - تعهدا"
    )
    previous_credits_paid = models.DecimalField(
        max_digits=15, decimal_places=3, default=0, verbose_name="فواصل نوات السابقة - دفعا"
    )
    current_credits_committed = models.DecimalField(
        max_digits=15, decimal_places=3, default=0, verbose_name="اعتمادات سنة الحالية - تعهدا"
    )
    current_credits_paid = models.DecimalField(
        max_digits=15, decimal_places=3, default=0, verbose_name="اعتمادات سنة الحالية - دفعا"
    )
    total_credits_committed = models.DecimalField(
        max_digits=15, decimal_places=3, default=0, verbose_name="مجموع الاعتمادات - تعهدا"
    )
    total_credits_paid = models.DecimalField(
        max_digits=15, decimal_places=3, default=0, verbose_name="مجموع الاعتمادات - دفعا"
    )
    consumption_rate_committed = models.DecimalField(
        max_digits=8, decimal_places=2, default=0, verbose_name="نسبة الصرف - تعهدا (%)"
    )
    consumption_rate_paid = models.DecimalField(
        max_digits=8, decimal_places=2, default=0, verbose_name="نسبة الصرف - دفعا (%)"
    )
    remaining_credits_committed = models.DecimalField(
        max_digits=15, decimal_places=3, default=0, verbose_name="الاعتمادات المتبقية - تعهدا"
    )
    remaining_credits_paid = models.DecimalField(
        max_digits=15, decimal_places=3, default=0, verbose_name="الاعتمادات المتبقية - دفعا"
    )

    # --- المنتفعات ---
    beneficiaries_count = models.PositiveIntegerField(default=0, verbose_name="عدد النساء المنتفعات بالبرنامج")

    # --- المطالب ---
    accepted_female = models.PositiveIntegerField(default=0, verbose_name="المطالب المقبولة - إناث")
    accepted_male = models.PositiveIntegerField(default=0, verbose_name="المطالب المقبولة - ذكور")
    rejected_female = models.PositiveIntegerField(default=0, verbose_name="المطالب المرفوضة - إناث")
    rejected_male = models.PositiveIntegerField(default=0, verbose_name="المطالب المرفوضة - ذكور")
    rejection_reasons = models.TextField(blank=True, verbose_name="أسباب الرفض")

    # --- المتابعة والتكوين ---
    field_visits_count = models.PositiveIntegerField(default=0, verbose_name="عدد الزيارات الميدانية للمتابعة")
    training_courses_count = models.PositiveIntegerField(default=0, verbose_name="عدد الدورات التدريبية")
    trainees_count = models.PositiveIntegerField(default=0, verbose_name="عدد المشاركات في الدورات")

    # --- الإشكاليات ---
    obstacles = models.TextField(blank=True, verbose_name="الإشكاليات المعترضة")

    # --- Meta ---
    created_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='raedat_records', verbose_name="أُنشئ بواسطة"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "برنامج رائدات"
        verbose_name_plural = "برنامج رائدات"
        ordering = ['-year', 'wilaya']
        unique_together = [['wilaya', 'year']]

    def __str__(self):
        return f"رائدات — {self.get_wilaya_display()} ({self.year})"

# =========================================================
# PROGRAMME : فضاءات المرافقة والتسويق
# =========================================================

class AccompagnementSpace(models.Model):
    """متابعة فضاءات المرافقة والتسويق."""

    # --- Identification ---
    wilaya = models.CharField(
        max_length=2,
        choices=WILAYAS,
        verbose_name="الولاية",
    )
    year = models.PositiveIntegerField(
        verbose_name="السنة",
        default=2026,
    )

    # --- الفواصل والاعتمادات ---
    previous_credits_committed = models.DecimalField(
        max_digits=15, decimal_places=3, default=0, verbose_name="فواصل نوات السابقة - تعهدا"
    )
    previous_credits_paid = models.DecimalField(
        max_digits=15, decimal_places=3, default=0, verbose_name="فواصل نوات السابقة - دفعا"
    )
    current_credits_committed = models.DecimalField(
        max_digits=15, decimal_places=3, default=0, verbose_name="اعتمادات سنة الحالية - تعهدا"
    )
    current_credits_paid = models.DecimalField(
        max_digits=15, decimal_places=3, default=0, verbose_name="اعتمادات سنة الحالية - دفعا"
    )
    total_credits_committed = models.DecimalField(
        max_digits=15, decimal_places=3, default=0, verbose_name="مجموع الاعتمادات - تعهدا"
    )
    total_credits_paid = models.DecimalField(
        max_digits=15, decimal_places=3, default=0, verbose_name="مجموع الاعتمادات - دفعا"
    )
    consumption_rate_committed = models.DecimalField(
        max_digits=8, decimal_places=2, default=0, verbose_name="نسبة الصرف - تعهدا (%)"
    )
    consumption_rate_paid = models.DecimalField(
        max_digits=8, decimal_places=2, default=0, verbose_name="نسبة الصرف - دفعا (%)"
    )
    remaining_credits_committed = models.DecimalField(
        max_digits=15, decimal_places=3, default=0, verbose_name="الاعتمادات المتبقية - تعهدا"
    )
    remaining_credits_paid = models.DecimalField(
        max_digits=15, decimal_places=3, default=0, verbose_name="الاعتمادات المتبقية - دفعا"
    )

    # --- المنتفعون بالخدمات (كما في الوثيقة) ---
    beneficiaries_accompaniment = models.PositiveIntegerField(default=0, verbose_name="عدد المنتفعين بخدمات المرافقة")
    beneficiaries_training = models.PositiveIntegerField(default=0, verbose_name="عدد المنتفعين بخدمات التكوين")
    beneficiaries_marketing = models.PositiveIntegerField(default=0, verbose_name="عدد المنتفعين بخدمات التسويق")

    # --- الإشكاليات ---
    obstacles = models.TextField(blank=True, verbose_name="الإشكاليات المعترضة")

    # --- Meta ---
    created_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='accompagnement_records', verbose_name="أُنشئ بواسطة"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "فضاءات المرافقة والتسويق"
        verbose_name_plural = "فضاءات المرافقة والتسويق"
        ordering = ['-year', 'wilaya']
        unique_together = [['wilaya', 'year']]

    def __str__(self):
        return f"فضاءات المرافقة والتسويق — {self.get_wilaya_display()} ({self.year})"


# =========================================================
# PROGRAMME : التمكين الاجتماعي للأسر / الخطة الوطنية للتماسك الأسري
# =========================================================

class FamilyCohesionPlan(models.Model):
    """متابعة التمكين الاجتماعي للأسر والخطة الوطنية للتماسك الأسري."""

    PHASE_CHOICES = [
        ('1', 'المرحلة الأولى'),
        ('2', 'المرحلة الثانية'),
        ('3', 'المرحلة الثالثة'),
    ]

    # --- Identification ---
    wilaya = models.CharField(
        max_length=2,
        choices=WILAYAS,
        verbose_name="الولاية",
    )
    year = models.PositiveIntegerField(
        verbose_name="السنة",
        default=2026,
    )

    # --- الفواصل والاعتمادات ---
    previous_credits_committed = models.DecimalField(
        max_digits=15, decimal_places=3, default=0, verbose_name="فواصل نوات السابقة - تعهدا"
    )
    previous_credits_paid = models.DecimalField(
        max_digits=15, decimal_places=3, default=0, verbose_name="فواصل نوات السابقة - دفعا"
    )
    current_credits_committed = models.DecimalField(
        max_digits=15, decimal_places=3, default=0, verbose_name="اعتمادات سنة الحالية - تعهدا"
    )
    current_credits_paid = models.DecimalField(
        max_digits=15, decimal_places=3, default=0, verbose_name="اعتمادات سنة الحالية - دفعا"
    )
    total_credits_committed = models.DecimalField(
        max_digits=15, decimal_places=3, default=0, verbose_name="مجموع الاعتمادات - تعهدا"
    )
    total_credits_paid = models.DecimalField(
        max_digits=15, decimal_places=3, default=0, verbose_name="مجموع الاعتمادات - دفعا"
    )
    consumption_rate_committed = models.DecimalField(
        max_digits=8, decimal_places=2, default=0, verbose_name="نسبة الصرف - تعهدا (%)"
    )
    consumption_rate_paid = models.DecimalField(
        max_digits=8, decimal_places=2, default=0, verbose_name="نسبة الصرف - دفعا (%)"
    )
    remaining_credits_committed = models.DecimalField(
        max_digits=15, decimal_places=3, default=0, verbose_name="الاعتمادات المتبقية - تعهدا"
    )
    remaining_credits_paid = models.DecimalField(
        max_digits=15, decimal_places=3, default=0, verbose_name="الاعتمادات المتبقية - دفعا"
    )

    # --- المنتفعون والتنفيذ ---
    beneficiaries_count = models.PositiveIntegerField(default=0, verbose_name="عدد المنتفعين بخدمات")
    consulting_firm = models.CharField(max_length=255, blank=True, verbose_name="مكتب الدراسات المعني بالتنفيذ")
    implementation_phase = models.CharField(
        max_length=1, choices=PHASE_CHOICES, default='1', verbose_name="مرحلة التنفيذ"
    )

    # --- تركيبة فريق العمل ---
    team_sociologist = models.PositiveIntegerField(default=0, verbose_name="مختص في علم الاجتماع")
    team_legal = models.PositiveIntegerField(default=0, verbose_name="مختص في القانون")
    team_psychologist = models.PositiveIntegerField(default=0, verbose_name="مختص في علم النفس")
    team_health = models.PositiveIntegerField(default=0, verbose_name="مختص في الصحة")
    team_other_desc = models.CharField(max_length=255, blank=True, verbose_name="اختصاصات أخرى (اذكرها)")

    # --- Meta ---
    created_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='family_cohesion_records', verbose_name="أُنشئ بواسطة"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "التمكين الاجتماعي للأسر"
        verbose_name_plural = "التمكين الاجتماعي للأسر"
        ordering = ['-year', 'wilaya']
        unique_together = [['wilaya', 'year']]

    def __str__(self):
        return f"التماسك الأسري — {self.get_wilaya_display()} ({self.year})"


# =========================================================
# PROGRAMME : فضاءات الأسرة (5.1)
# =========================================================

class FamilySpace(models.Model):
    """متابعة فضاءات الأسرة (النشاط، الإطارات، المنتفعون، الاعتمادات، والبناء)."""

    # --- Identification ---
    wilaya = models.CharField(
        max_length=2,
        choices=WILAYAS,
        verbose_name="الولاية",
    )
    year = models.PositiveIntegerField(
        verbose_name="السنة",
        default=2026,
    )
    
    # --- الوضعية ---
    is_active = models.BooleanField(
        default=False, 
        verbose_name="في وضعية نشاط (نعم/لا)"
    )

    # --- الإطارات العاملة (إذا كان نشطاً) ---
    staff_legal = models.PositiveIntegerField(default=0, verbose_name="مختص في القانون")
    staff_psychology = models.PositiveIntegerField(default=0, verbose_name="مختص في علم النفس")
    staff_health = models.PositiveIntegerField(default=0, verbose_name="مختص في الصحة")
    staff_admin = models.PositiveIntegerField(default=0, verbose_name="متصرف")
    staff_educator = models.PositiveIntegerField(default=0, verbose_name="مربي")
    staff_other_desc = models.CharField(max_length=255, blank=True, verbose_name="اختصاصات أخرى (اذكرها)")
    staff_other_count = models.PositiveIntegerField(default=0, verbose_name="عدد الإطارات الأخرى")

    # --- المنتفعون ---
    beneficiaries_female = models.PositiveIntegerField(default=0, verbose_name="عدد الإناث")
    beneficiaries_male = models.PositiveIntegerField(default=0, verbose_name="عدد الذكور")
    beneficiaries_children = models.PositiveIntegerField(default=0, verbose_name="أطفال")
    beneficiaries_adults = models.PositiveIntegerField(default=0, verbose_name="كهول")
    beneficiaries_seniors = models.PositiveIntegerField(default=0, verbose_name="كبار سن")

    # --- الاعتمادات المخصصة لتسيير الفضاء ---
    previous_credits_committed = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="فواصل نوات السابقة - تعهدا")
    previous_credits_paid = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="فواصل نوات السابقة - دفعا")
    current_credits_committed = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="اعتمادات سنة الحالية - تعهدا")
    current_credits_paid = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="اعتمادات سنة الحالية - دفعا")
    total_credits_committed = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="مجموع الاعتمادات - تعهدا")
    total_credits_paid = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="مجموع الاعتمادات - دفعا")
    consumption_rate_committed = models.DecimalField(max_digits=8, decimal_places=2, default=0, verbose_name="نسبة الصرف - تعهدا (%)")
    consumption_rate_paid = models.DecimalField(max_digits=8, decimal_places=2, default=0, verbose_name="نسبة الصرف - دفعا (%)")
    remaining_credits_committed = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="الاعتمادات المتبقية - تعهدا")
    remaining_credits_paid = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="الاعتمادات المتبقية - دفعا")

    # --- إذا كان في طور البناء ---
    construction_start_year = models.PositiveIntegerField(null=True, blank=True, verbose_name="سنة الانطلاق")
    construction_total_credits = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="الاعتمادات الجملية")
    construction_progress = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="نسبة تقدم الإنجاز (%)")
    construction_delay_reasons = models.TextField(blank=True, verbose_name="أسباب تعطل الإنجاز")
    actual_operation_start_year = models.PositiveIntegerField(null=True, blank=True, verbose_name="سنة الانطلاق الفعلي للاستغلال")

    # --- Meta ---
    created_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='family_space_records', verbose_name="أُنشئ بواسطة"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "فضاء الأسرة"
        verbose_name_plural = "فضاءات الأسرة"
        ordering = ['-year', 'wilaya']
        unique_together = [['wilaya', 'year']]

    def __str__(self):
        return f"فضاء الأسرة — {self.get_wilaya_display()} ({self.year})"


# =========================================================
# PROGRAMME : مركز إرشاد وتوجيه أسري (5.2)
# =========================================================

class FamilyGuidanceCenter(models.Model):
    """متابعة مركز إرشاد وتوجيه أسري."""

    # --- Identification ---
    wilaya = models.CharField(
        max_length=2,
        choices=WILAYAS,
        verbose_name="الولاية",
    )
    year = models.PositiveIntegerField(
        verbose_name="السنة",
        default=2026,
    )
    
    # --- الوضعية ---
    is_active = models.BooleanField(
        default=False, 
        verbose_name="في وضعية نشاط (نعم/لا)"
    )

    # --- الإطارات العاملة (إذا كان نشطاً) ---
    staff_legal = models.PositiveIntegerField(default=0, verbose_name="مختص في القانون")
    staff_psychology = models.PositiveIntegerField(default=0, verbose_name="مختص في علم النفس")
    staff_health = models.PositiveIntegerField(default=0, verbose_name="مختص في الصحة")
    staff_admin = models.PositiveIntegerField(default=0, verbose_name="متصرف")
    staff_educator = models.PositiveIntegerField(default=0, verbose_name="مربي")
    staff_other_desc = models.CharField(max_length=255, blank=True, verbose_name="اختصاصات أخرى (اذكرها)")
    staff_other_count = models.PositiveIntegerField(default=0, verbose_name="عدد الإطارات الأخرى")

    # --- المنتفعون ---
    beneficiaries_female = models.PositiveIntegerField(default=0, verbose_name="عدد الإناث")
    beneficiaries_male = models.PositiveIntegerField(default=0, verbose_name="عدد الذكور")
    beneficiaries_children = models.PositiveIntegerField(default=0, verbose_name="أطفال")
    beneficiaries_youth = models.PositiveIntegerField(default=0, verbose_name="شبان")
    beneficiaries_adults = models.PositiveIntegerField(default=0, verbose_name="كهول")
    beneficiaries_seniors = models.PositiveIntegerField(default=0, verbose_name="كبار سن")

    # --- الاعتمادات المخصصة للتسيير ---
    previous_credits_committed = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="فواصل نوات السابقة - تعهدا")
    previous_credits_paid = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="فواصل نوات السابقة - دفعا")
    current_credits_committed = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="اعتمادات سنة الحالية - تعهدا")
    current_credits_paid = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="اعتمادات سنة الحالية - دفعا")
    total_credits_committed = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="مجموع الاعتمادات - تعهدا")
    total_credits_paid = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="مجموع الاعتمادات - دفعا")
    consumption_rate_committed = models.DecimalField(max_digits=8, decimal_places=2, default=0, verbose_name="نسبة الصرف - تعهدا (%)")
    consumption_rate_paid = models.DecimalField(max_digits=8, decimal_places=2, default=0, verbose_name="نسبة الصرف - دفعا (%)")
    remaining_credits_committed = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="الاعتمادات المتبقية - تعهدا")
    remaining_credits_paid = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="الاعتمادات المتبقية - دفعا")

    # --- إذا كان في طور البناء ---
    construction_start_year = models.PositiveIntegerField(null=True, blank=True, verbose_name="سنة الانطلاق")
    construction_total_credits = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="الاعتمادات الجملية")
    construction_progress = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="نسبة تقدم الإنجاز (%)")
    construction_delay_reasons = models.TextField(blank=True, verbose_name="أسباب تعطل الإنجاز")
    actual_operation_start_year = models.PositiveIntegerField(null=True, blank=True, verbose_name="سنة الانطلاق الفعلي للاستغلال")

    # --- Meta ---
    created_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='family_guidance_records', verbose_name="أُنشئ بواسطة"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "مركز إرشاد وتوجيه أسري"
        verbose_name_plural = "مراكز إرشاد وتوجيه أسري"
        ordering = ['-year', 'wilaya']
        unique_together = [['wilaya', 'year']]

    def __str__(self):
        return f"مركز إرشاد — {self.get_wilaya_display()} ({self.year})"



# =========================================================
# PROGRAMME : وحدة مرافقة الأولياء للتعهد ببنائهم ذوي اضطرابات التعلم (5.3)
# =========================================================

class ParentAccompanimentUnit(models.Model):
    """متابعة وحدة مرافقة الأولياء للتعهد ببنائهم ذوي اضطرابات التعلم."""

    # --- Identification ---
    wilaya = models.CharField(
        max_length=2,
        choices=WILAYAS,
        verbose_name="الولاية",
    )
    year = models.PositiveIntegerField(
        verbose_name="السنة",
        default=2026,
    )
    
    # --- الوضعية والإحصائيات ---
    learning_disabilities_cases = models.PositiveIntegerField(
        default=0, 
        verbose_name="عدد حالات اضطرابات التعلم"
    )
    is_active = models.BooleanField(
        default=False, 
        verbose_name="في وضعية نشاط (نعم/لا)"
    )

    # --- الإطارات العاملة (إذا كان نشطاً) ---
    staff_legal = models.PositiveIntegerField(default=0, verbose_name="مختص في القانون")
    staff_psychology = models.PositiveIntegerField(default=0, verbose_name="مختص في علم النفس")
    staff_health = models.PositiveIntegerField(default=0, verbose_name="مختص في الصحة")
    staff_admin = models.PositiveIntegerField(default=0, verbose_name="متصرف")
    staff_educator = models.PositiveIntegerField(default=0, verbose_name="مربي")
    staff_other_desc = models.CharField(max_length=255, blank=True, verbose_name="اختصاصات أخرى (اذكرها)")
    staff_other_count = models.PositiveIntegerField(default=0, verbose_name="عدد الإطارات الأخرى")

    # --- المنتفعون ---
    beneficiaries_female = models.PositiveIntegerField(default=0, verbose_name="عدد الإناث")
    beneficiaries_male = models.PositiveIntegerField(default=0, verbose_name="عدد الذكور")

    # --- الاعتمادات المخصصة للتسيير ---
    previous_credits_committed = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="فواصل نوات السابقة - تعهدا")
    previous_credits_paid = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="فواصل نوات السابقة - دفعا")
    current_credits_committed = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="اعتمادات سنة الحالية - تعهدا")
    current_credits_paid = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="اعتمادات سنة الحالية - دفعا")
    total_credits_committed = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="مجموع الاعتمادات - تعهدا")
    total_credits_paid = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="مجموع الاعتمادات - دفعا")
    consumption_rate_committed = models.DecimalField(max_digits=8, decimal_places=2, default=0, verbose_name="نسبة الصرف - تعهدا (%)")
    consumption_rate_paid = models.DecimalField(max_digits=8, decimal_places=2, default=0, verbose_name="نسبة الصرف - دفعا (%)")
    remaining_credits_committed = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="الاعتمادات المتبقية - تعهدا")
    remaining_credits_paid = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="الاعتمادات المتبقية - دفعا")

    # --- إذا كان في طور البناء ---
    construction_start_year = models.PositiveIntegerField(null=True, blank=True, verbose_name="سنة الانطلاق")
    construction_total_credits = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="الاعتمادات الجملية")
    construction_progress = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="نسبة تقدم الإنجاز (%)")
    construction_delay_reasons = models.TextField(blank=True, verbose_name="أسباب تعطل الإنجاز")
    actual_operation_start_year = models.PositiveIntegerField(null=True, blank=True, verbose_name="سنة الانطلاق الفعلي للاستغلال")

    # --- Meta ---
    created_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='parent_accompaniment_records', verbose_name="أُنشئ بواسطة"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "وحدة مرافقة الأولياء"
        verbose_name_plural = "وحدات مرافقة الأولياء"
        ordering = ['-year', 'wilaya']
        unique_together = [['wilaya', 'year']]

    def __str__(self):
        return f"وحدة مرافقة الأولياء — {self.get_wilaya_display()} ({self.year})"


# =========================================================
# PROGRAMME : نوادي أطفال (5.4)
# =========================================================

class ChildrenClub(models.Model):
    """متابعة نوادي الأطفال."""

    # --- Identification ---
    wilaya = models.CharField(
        max_length=2,
        choices=WILAYAS,
        verbose_name="الولاية",
    )
    year = models.PositiveIntegerField(
        verbose_name="السنة",
        default=2026,
    )
    
    # --- الوضعية ---
    is_active = models.BooleanField(
        default=False, 
        verbose_name="في وضعية نشاط (نعم/لا)"
    )

    # --- الإطارات العاملة (إذا كان نشطاً) ---
    staff_manager = models.PositiveIntegerField(default=0, verbose_name="مدير")
    staff_educator = models.PositiveIntegerField(default=0, verbose_name="مربي")
    staff_youth_teacher = models.PositiveIntegerField(default=0, verbose_name="أستاذ شباب")
    staff_childhood = models.PositiveIntegerField(default=0, verbose_name="طفولة")
    staff_other_desc = models.CharField(max_length=255, blank=True, verbose_name="اختصاصات أخرى (اذكرها)")
    staff_other_count = models.PositiveIntegerField(default=0, verbose_name="عدد الإطارات الأخرى")

    # --- المنتفعون ---
    beneficiaries_female = models.PositiveIntegerField(default=0, verbose_name="عدد الإناث")
    beneficiaries_male = models.PositiveIntegerField(default=0, verbose_name="عدد الذكور")

    # --- الاعتمادات المخصصة لتسيير النادي ---
    previous_credits_committed = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="فواصل نوات السابقة - تعهدا")
    previous_credits_paid = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="فواصل نوات السابقة - دفعا")
    current_credits_committed = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="اعتمادات سنة الحالية - تعهدا")
    current_credits_paid = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="اعتمادات سنة الحالية - دفعا")
    total_credits_committed = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="مجموع الاعتمادات - تعهدا")
    total_credits_paid = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="مجموع الاعتمادات - دفعا")
    consumption_rate_committed = models.DecimalField(max_digits=8, decimal_places=2, default=0, verbose_name="نسبة الصرف - تعهدا (%)")
    consumption_rate_paid = models.DecimalField(max_digits=8, decimal_places=2, default=0, verbose_name="نسبة الصرف - دفعا (%)")
    remaining_credits_committed = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="الاعتمادات المتبقية - تعهدا")
    remaining_credits_paid = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="الاعتمادات المتبقية - دفعا")

    # --- إذا كان في طور البناء ---
    construction_start_year = models.PositiveIntegerField(null=True, blank=True, verbose_name="سنة الانطلاق")
    construction_total_credits = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="الاعتمادات الجملية")
    construction_progress = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="نسبة تقدم الإنجاز (%)")
    construction_delay_reasons = models.TextField(blank=True, verbose_name="أسباب تعطل الإنجاز")
    actual_operation_start_year = models.PositiveIntegerField(null=True, blank=True, verbose_name="سنة الانطلاق الفعلي للاستغلال")

    # --- Meta ---
    created_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='children_club_records', verbose_name="أُنشئ بواسطة"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "نادي أطفال"
        verbose_name_plural = "نوادي أطفال"
        ordering = ['-year', 'wilaya']
        unique_together = [['wilaya', 'year']]

    def __str__(self):
        return f"نادي أطفال — {self.get_wilaya_display()} ({self.year})"


# =========================================================
# PROGRAMME : المراكز المندمجة (5.5)
# =========================================================

class IntegratedCenter(models.Model):
    """متابعة المراكز المندمجة."""

    # --- Identification ---
    wilaya = models.CharField(
        max_length=2,
        choices=WILAYAS,
        verbose_name="الولاية",
    )
    year = models.PositiveIntegerField(
        verbose_name="السنة",
        default=2026,
    )
    
    # --- الوضعية ---
    is_active = models.BooleanField(
        default=False, 
        verbose_name="في وضعية نشاط (نعم/لا)"
    )

    # --- الإطارات العاملة (إذا كان نشطاً) ---
    staff_manager = models.PositiveIntegerField(default=0, verbose_name="مدير")
    staff_educator = models.PositiveIntegerField(default=0, verbose_name="مربي")
    staff_youth_teacher = models.PositiveIntegerField(default=0, verbose_name="أستاذ شباب")
    staff_childhood = models.PositiveIntegerField(default=0, verbose_name="طفولة")
    staff_other_desc = models.CharField(max_length=255, blank=True, verbose_name="اختصاصات أخرى (اذكرها)")
    staff_other_count = models.PositiveIntegerField(default=0, verbose_name="عدد الإطارات الأخرى")

    # --- المنتفعون ---
    beneficiaries_female = models.PositiveIntegerField(default=0, verbose_name="عدد الإناث")
    beneficiaries_male = models.PositiveIntegerField(default=0, verbose_name="عدد الذكور")

    # --- الاعتمادات المخصصة للتسيير ---
    previous_credits_committed = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="فواصل نوات السابقة - تعهدا")
    previous_credits_paid = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="فواصل نوات السابقة - دفعا")
    current_credits_committed = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="اعتمادات سنة الحالية - تعهدا")
    current_credits_paid = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="اعتمادات سنة الحالية - دفعا")
    total_credits_committed = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="مجموع الاعتمادات - تعهدا")
    total_credits_paid = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="مجموع الاعتمادات - دفعا")
    consumption_rate_committed = models.DecimalField(max_digits=8, decimal_places=2, default=0, verbose_name="نسبة الصرف - تعهدا (%)")
    consumption_rate_paid = models.DecimalField(max_digits=8, decimal_places=2, default=0, verbose_name="نسبة الصرف - دفعا (%)")
    remaining_credits_committed = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="الاعتمادات المتبقية - تعهدا")
    remaining_credits_paid = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="الاعتمادات المتبقية - دفعا")

    # --- إذا كان في طور البناء ---
    construction_start_year = models.PositiveIntegerField(null=True, blank=True, verbose_name="سنة الانطلاق")
    construction_total_credits = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="الاعتمادات الجملية")
    construction_progress = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="نسبة تقدم الإنجاز (%)")
    construction_delay_reasons = models.TextField(blank=True, verbose_name="أسباب تعطل الإنجاز")
    actual_operation_start_year = models.PositiveIntegerField(null=True, blank=True, verbose_name="سنة الانطلاق الفعلي للاستغلال")

    # --- Meta ---
    created_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='integrated_center_records', verbose_name="أُنشئ بواسطة"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "مركز مندمج"
        verbose_name_plural = "المراكز المندمجة"
        ordering = ['-year', 'wilaya']
        unique_together = [['wilaya', 'year']]

    def __str__(self):
        return f"مركز مندمج — {self.get_wilaya_display()} ({self.year})"


# =========================================================
# PROGRAMME : مراكز المسنين (5.6)
# =========================================================

class ElderlyCenter(models.Model):
    """متابعة مراكز المسنين."""

    # --- Identification ---
    wilaya = models.CharField(
        max_length=2,
        choices=WILAYAS,
        verbose_name="الولاية",
    )
    year = models.PositiveIntegerField(
        verbose_name="السنة",
        default=2026,
    )
    
    # --- الوضعية ---
    is_active = models.BooleanField(
        default=False, 
        verbose_name="في وضعية نشاط (نعم/لا)"
    )

    # --- الإطارات العاملة (إذا كان نشطاً) ---
    staff_manager = models.PositiveIntegerField(default=0, verbose_name="مدير")
    staff_life_assistant = models.PositiveIntegerField(default=0, verbose_name="عون حياة")
    staff_health_assistant = models.PositiveIntegerField(default=0, verbose_name="عون صحة")

    # --- المنتفعون ---
    beneficiaries_female = models.PositiveIntegerField(default=0, verbose_name="عدد الإناث")
    beneficiaries_male = models.PositiveIntegerField(default=0, verbose_name="عدد الذكور")

    # --- الاعتمادات المخصصة للتسيير ---
    previous_credits_committed = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="فواصل نوات السابقة - تعهدا")
    previous_credits_paid = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="فواصل نوات السابقة - دفعا")
    current_credits_committed = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="اعتمادات سنة الحالية - تعهدا")
    current_credits_paid = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="اعتمادات سنة الحالية - دفعا")
    total_credits_committed = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="مجموع الاعتمادات - تعهدا")
    total_credits_paid = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="مجموع الاعتمادات - دفعا")
    consumption_rate_committed = models.DecimalField(max_digits=8, decimal_places=2, default=0, verbose_name="نسبة الصرف - تعهدا (%)")
    consumption_rate_paid = models.DecimalField(max_digits=8, decimal_places=2, default=0, verbose_name="نسبة الصرف - دفعا (%)")
    remaining_credits_committed = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="الاعتمادات المتبقية - تعهدا")
    remaining_credits_paid = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="الاعتمادات المتبقية - دفعا")

    # --- إذا كان في طور البناء ---
    construction_start_year = models.PositiveIntegerField(null=True, blank=True, verbose_name="سنة الانطلاق")
    construction_duration = models.CharField(max_length=100, blank=True, verbose_name="مدة الانجاز")
    construction_total_cost = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="الكلفة الجملية للانجاز")
    construction_progress = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="نسبة تقدم الإنجاز (%)")
    construction_delay_reasons = models.TextField(blank=True, verbose_name="أسباب تعطل الإنجاز")
    actual_operation_start_year = models.PositiveIntegerField(null=True, blank=True, verbose_name="سنة الانطلاق الفعلي للاستغلال")
    difficulties_obstacles = models.TextField(blank=True, verbose_name="الصعوبات والعراقيل")

    # --- Meta ---
    created_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='elderly_center_records', verbose_name="أُنشئ بواسطة"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "مركز مسنين"
        verbose_name_plural = "مراكز المسنين"
        ordering = ['-year', 'wilaya']
        unique_together = [['wilaya', 'year']]

    def __str__(self):
        return f"مركز مسنين — {self.get_wilaya_display()} ({self.year})"


# =========================================================
# PROGRAMME : النوادي النهارية (7.5)
# =========================================================

class DayClub(models.Model):
    """متابعة النوادي النهارية."""

    # --- Identification ---
    wilaya = models.CharField(
        max_length=2,
        choices=WILAYAS,
        verbose_name="الولاية",
    )
    year = models.PositiveIntegerField(
        verbose_name="السنة",
        default=2026,
    )
    
    # --- الوضعية ---
    is_active = models.BooleanField(
        default=False, 
        verbose_name="في وضعية نشاط (نعم/لا)"
    )

    # --- الإطارات العاملة (إذا كان نشطاً) ---
    staff_manager = models.PositiveIntegerField(default=0, verbose_name="مدير")
    staff_life_assistant = models.PositiveIntegerField(default=0, verbose_name="عون حياة")
    staff_health_assistant = models.PositiveIntegerField(default=0, verbose_name="عون صحة")

    # --- المنتفعون ---
    beneficiaries_female = models.PositiveIntegerField(default=0, verbose_name="عدد الإناث")
    beneficiaries_male = models.PositiveIntegerField(default=0, verbose_name="عدد الذكور")

    # --- الاعتمادات المخصصة للتسيير ---
    previous_credits_committed = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="فواصل نوات السابقة - تعهدا")
    previous_credits_paid = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="فواصل نوات السابقة - دفعا")
    current_credits_committed = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="اعتمادات سنة الحالية - تعهدا")
    current_credits_paid = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="اعتمادات سنة الحالية - دفعا")
    total_credits_committed = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="مجموع الاعتمادات - تعهدا")
    total_credits_paid = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="مجموع الاعتمادات - دفعا")
    consumption_rate_committed = models.DecimalField(max_digits=8, decimal_places=2, default=0, verbose_name="نسبة الصرف - تعهدا (%)")
    consumption_rate_paid = models.DecimalField(max_digits=8, decimal_places=2, default=0, verbose_name="نسبة الصرف - دفعا (%)")
    remaining_credits_committed = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="الاعتمادات المتبقية - تعهدا")
    remaining_credits_paid = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="الاعتمادات المتبقية - دفعا")

    # --- إذا كان في طور البناء ---
    construction_start_year = models.PositiveIntegerField(null=True, blank=True, verbose_name="سنة الانطلاق")
    construction_duration = models.CharField(max_length=100, blank=True, verbose_name="مدة الانجاز")
    construction_total_cost = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="الكلفة الجملية للانجاز")
    construction_progress = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="نسبة تقدم الإنجاز (%)")
    construction_delay_reasons = models.TextField(blank=True, verbose_name="أسباب تعطل الإنجاز")
    actual_operation_start_year = models.PositiveIntegerField(null=True, blank=True, verbose_name="سنة الانطلاق الفعلي للاستغلال")
    difficulties_obstacles = models.TextField(blank=True, verbose_name="الصعوبات والعراقيل")

    # --- Meta ---
    created_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='day_club_records', verbose_name="أُنشئ بواسطة"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "نادي نهاري"
        verbose_name_plural = "النوادي النهارية"
        ordering = ['-year', 'wilaya']
        unique_together = [['wilaya', 'year']]

    def __str__(self):
        return f"نادي نهاري — {self.get_wilaya_display()} ({self.year})"


# =========================================================
# PROGRAMME : مركبات الطفولة (8.5)
# =========================================================

class ChildhoodComplex(models.Model):
    """متابعة مركبات الطفولة."""

    # --- Identification ---
    wilaya = models.CharField(
        max_length=2,
        choices=WILAYAS,
        verbose_name="الولاية",
    )
    year = models.PositiveIntegerField(
        verbose_name="السنة",
        default=2026,
    )
    
    # --- الوضعية ---
    is_active = models.BooleanField(
        default=False, 
        verbose_name="في وضعية نشاط (نعم/لا)"
    )

    # --- الإطارات العاملة (إذا كان نشطاً) ---
    staff_manager = models.PositiveIntegerField(default=0, verbose_name="مدير")
    staff_educator = models.PositiveIntegerField(default=0, verbose_name="مربي")
    staff_youth_teacher = models.PositiveIntegerField(default=0, verbose_name="أستاذ شباب")
    staff_childhood = models.PositiveIntegerField(default=0, verbose_name="طفولة")
    staff_other_desc = models.CharField(max_length=255, blank=True, verbose_name="اختصاصات أخرى (اذكرها)")
    staff_other_count = models.PositiveIntegerField(default=0, verbose_name="عدد الإطارات الأخرى")

    # --- المنتفعون ---
    beneficiaries_female = models.PositiveIntegerField(default=0, verbose_name="عدد الإناث")
    beneficiaries_male = models.PositiveIntegerField(default=0, verbose_name="عدد الذكور")

    # --- الاعتمادات المخصصة للتسيير ---
    previous_credits_committed = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="فواصل نوات السابقة - تعهدا")
    previous_credits_paid = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="فواصل نوات السابقة - دفعا")
    current_credits_committed = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="اعتمادات سنة الحالية - تعهدا")
    current_credits_paid = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="اعتمادات سنة الحالية - دفعا")
    total_credits_committed = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="مجموع الاعتمادات - تعهدا")
    total_credits_paid = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="مجموع الاعتمادات - دفعا")
    consumption_rate_committed = models.DecimalField(max_digits=8, decimal_places=2, default=0, verbose_name="نسبة الصرف - تعهدا (%)")
    consumption_rate_paid = models.DecimalField(max_digits=8, decimal_places=2, default=0, verbose_name="نسبة الصرف - دفعا (%)")
    remaining_credits_committed = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="الاعتمادات المتبقية - تعهدا")
    remaining_credits_paid = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="الاعتمادات المتبقية - دفعا")

    # --- إذا كان في طور البناء أو التهيئة ---
    construction_start_year = models.PositiveIntegerField(null=True, blank=True, verbose_name="سنة الانطلاق")
    construction_duration = models.CharField(max_length=100, blank=True, verbose_name="مدة الانجاز")
    construction_total_cost = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="الكلفة الجملية للانجاز")
    construction_progress = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="نسبة تقدم الإنجاز (%)")
    construction_delay_reasons = models.TextField(blank=True, verbose_name="أسباب تعطل الإنجاز")
    actual_operation_start_year = models.PositiveIntegerField(null=True, blank=True, verbose_name="سنة الانطلاق الفعلي للاستغلال")
    difficulties_obstacles = models.TextField(blank=True, verbose_name="الصعوبات والعراقيل")

    # --- Meta ---
    created_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='childhood_complex_records', verbose_name="أُنشئ بواسطة"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "مركب طفولة"
        verbose_name_plural = "مركبات الطفولة"
        ordering = ['-year', 'wilaya']
        unique_together = [['wilaya', 'year']]

    def __str__(self):
        return f"مركب طفولة — {self.get_wilaya_display()} ({self.year})"


# =========================================================
# PROGRAMME : مراكز الإعلامية الموجهة للطفل (9.5)
# =========================================================

class ChildItCenter(models.Model):
    """متابعة مراكز الإعلامية الموجهة للطفل."""

    # --- Identification ---
    wilaya = models.CharField(
        max_length=2,
        choices=WILAYAS,
        verbose_name="الولاية",
    )
    year = models.PositiveIntegerField(
        verbose_name="السنة",
        default=2026,
    )
    
    # --- الوضعية ---
    is_active = models.BooleanField(
        default=False, 
        verbose_name="في وضعية نشاط (نعم/لا)"
    )

    # --- الإطارات العاملة (إذا كان نشطاً) ---
    staff_manager = models.PositiveIntegerField(default=0, verbose_name="مدير")
    staff_life_assistant = models.PositiveIntegerField(default=0, verbose_name="عون حياة")
    staff_health_assistant = models.PositiveIntegerField(default=0, verbose_name="عون صحة")

    # --- المنتفعون ---
    beneficiaries_female = models.PositiveIntegerField(default=0, verbose_name="عدد الإناث")
    beneficiaries_male = models.PositiveIntegerField(default=0, verbose_name="عدد الذكور")

    # --- الاعتمادات المخصصة للتسيير ---
    previous_credits_committed = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="فواصل نوات السابقة - تعهدا")
    previous_credits_paid = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="فواصل نوات السابقة - دفعا")
    current_credits_committed = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="اعتمادات سنة الحالية - تعهدا")
    current_credits_paid = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="اعتمادات سنة الحالية - دفعا")
    total_credits_committed = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="مجموع الاعتمادات - تعهدا")
    total_credits_paid = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="مجموع الاعتمادات - دفعا")
    consumption_rate_committed = models.DecimalField(max_digits=8, decimal_places=2, default=0, verbose_name="نسبة الصرف - تعهدا (%)")
    consumption_rate_paid = models.DecimalField(max_digits=8, decimal_places=2, default=0, verbose_name="نسبة الصرف - دفعا (%)")
    remaining_credits_committed = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="الاعتمادات المتبقية - تعهدا")
    remaining_credits_paid = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="الاعتمادات المتبقية - دفعا")

    # --- إذا كان في طور البناء أو التهيئة ---
    construction_start_year = models.PositiveIntegerField(null=True, blank=True, verbose_name="سنة الانطلاق")
    construction_duration = models.CharField(max_length=100, blank=True, verbose_name="مدة الانجاز")
    construction_total_cost = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="الكلفة الجملية للانجاز")
    construction_progress = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="نسبة تقدم الإنجاز (%)")
    construction_delay_reasons = models.TextField(blank=True, verbose_name="أسباب تعطل الإنجاز")
    actual_operation_start_year = models.PositiveIntegerField(null=True, blank=True, verbose_name="سنة الانطلاق الفعلي للاستغلال")
    difficulties_obstacles = models.TextField(blank=True, verbose_name="الصعوبات والعراقيل")

    # --- Meta ---
    created_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='child_it_center_records', verbose_name="أُنشئ بواسطة"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "مركز إعلامية للطفل"
        verbose_name_plural = "مراكز الإعلامية الموجهة للطفل"
        ordering = ['-year', 'wilaya']
        unique_together = [['wilaya', 'year']]

    def __str__(self):
        return f"مركز إعلامية — {self.get_wilaya_display()} ({self.year})"


# =========================================================
# PROGRAMME : روزنامة الأنشطة الأسبوعية
# =========================================================

class WeeklyActivity(models.Model):
    """متابعة روزنامة الأنشطة الأسبوعية."""

    DAY_CHOICES = [
        ('monday', 'الاثنين'),
        ('tuesday', 'الثلاثاء'),
        ('wednesday', 'الأربعاء'),
        ('thursday', 'الخميس'),
        ('friday', 'الجمعة'),
        ('saturday', 'السبت'),
        ('sunday', 'الأحد'),
    ]

    # --- Identification ---
    wilaya = models.CharField(
        max_length=2,
        choices=WILAYAS,
        verbose_name="الولاية",
    )
    day = models.CharField(
        max_length=10,
        choices=DAY_CHOICES,
        verbose_name="النهار",
    )
    date = models.DateField(
        null=True, blank=True, 
        verbose_name="التاريخ (اختياري)"
    )
    
    # --- Détails de l'activité ---
    time = models.TimeField(
        verbose_name="الساعة",
    )
    activity_name = models.CharField(
        max_length=255, 
        verbose_name="النشاط"
    )
    target_audience = models.CharField(
        max_length=255, 
        verbose_name="الفئات المعنية"
    )
    location = models.CharField(
        max_length=255, 
        verbose_name="المكان"
    )
    notes = models.TextField(
        blank=True, 
        verbose_name="الملاحظات"
    )

    # --- Meta ---
    created_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='weekly_activities', verbose_name="أُنشئ بواسطة"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "نشاط أسبوعي"
        verbose_name_plural = "روزنامة الأنشطة الأسبوعية"
        ordering = ['day', 'time']

    def __str__(self):
        return f"{self.get_day_display()} - {self.time} : {self.activity_name} ({self.get_wilaya_display()})"

        # =========================================================
        # PROGRAMME : الاجتماعات وجلسات العمل
        # =========================================================

class MeetingSession(models.Model):
    """متابعة الاجتماعات وجلسات العمل."""

    # --- Identification ---
    wilaya = models.CharField(
        max_length=2,
        choices=WILAYAS,
        verbose_name="الولاية",
    )
    year = models.PositiveIntegerField(
        verbose_name="السنة",
        default=2026,
    )
    
    # --- 1. داخل المندوبية ---
    inside_delegation_staff = models.BooleanField(default=False, verbose_name="داخل المندوبية - مع إطارات")
    inside_delegation_committees = models.BooleanField(default=False, verbose_name="داخل المندوبية - مدعوين في اطار لجان جهوية")

    # --- 2. خارج المندوبية ---
    outside_delegation = models.BooleanField(default=False, verbose_name="خارج المندوبية")

    # --- 3. في الولاية - هيكل عمومي ---
    in_public_structure = models.BooleanField(default=False, verbose_name="في الولاية - هيكل عمومي")
    public_structure_name = models.CharField(max_length=255, blank=True, verbose_name="اذكره (الهيكل العمومي)")
    public_structure_topic = models.CharField(max_length=255, blank=True, verbose_name="موضوع الاجتماع (الهيكل العمومي)")
    public_structure_date = models.CharField(max_length=100, blank=True, verbose_name="تاريخه (الهيكل العمومي)")

    # --- 4. في الولاية - مقر رئاسة ---
    in_presidency = models.BooleanField(default=False, verbose_name="في الولاية - مقر رئاسة")
    presidency_name = models.CharField(max_length=255, blank=True, verbose_name="اذكرها (مقر الرئاسة)")
    presidency_topic = models.CharField(max_length=255, blank=True, verbose_name="موضوع الاجتماع (مقر الرئاسة)")
    presidency_date = models.CharField(max_length=100, blank=True, verbose_name="تاريخه (مقر الرئاسة)")

    # --- Meta ---
    created_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='meeting_session_records', verbose_name="أُنشئ بواسطة"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "اجتماع / جلسة عمل"
        verbose_name_plural = "الاجتماعات وجلسات العمل"
        ordering = ['-year', 'wilaya']
        unique_together = [['wilaya', 'year']]

    def __str__(self):
        return f"اجتماع — {self.get_wilaya_display()} ({self.year})"


# =========================================================
# PROGRAMME : الزيارات
# =========================================================

class Visit(models.Model):
    """متابعة الزيارات (مؤسسات، هيكل عمومي، ميدانية)."""

    # --- Identification ---
    wilaya = models.CharField(
        max_length=2,
        choices=WILAYAS,
        verbose_name="الولاية",
    )
    year = models.PositiveIntegerField(
        verbose_name="السنة",
        default=2026,
    )
    
    # --- 1. مؤسسات خاضعة للإشراف ---
    has_supervised_institutions = models.BooleanField(default=False, verbose_name="مؤسسات خاضعة للإشراف")
    supervised_institutions = models.CharField(max_length=255, blank=True, verbose_name="i. اذكرها")
    supervised_topic = models.CharField(max_length=255, blank=True, verbose_name="ii. موضوع الزيارة")
    supervised_date = models.CharField(max_length=100, blank=True, verbose_name="iii. تاريخها")

    # --- 2. خارج الولاية ---
    has_outside_visits = models.BooleanField(default=False, verbose_name="خارج الولاية")

    # --- 3. في الولاية: في هيكل عمومي ---
    has_public_structure_visit = models.BooleanField(default=False, verbose_name="في الولاية: في هيكل عمومي")
    public_structure_name = models.CharField(max_length=255, blank=True, verbose_name="1. اذكره")
    public_structure_topic = models.CharField(max_length=255, blank=True, verbose_name="2. موضوع الاجتماع")
    public_structure_date = models.CharField(max_length=100, blank=True, verbose_name="وتاريخه")

    # --- 4. في الولاية: في مقر رئاسة ---
    has_presidency_visit = models.BooleanField(default=False, verbose_name="في الولاية: في مقر رئاسة")
    presidency_name = models.CharField(max_length=255, blank=True, verbose_name="i. اذكرها")
    presidency_topic = models.CharField(max_length=255, blank=True, verbose_name="ii. موضوع الاجتماع")
    presidency_date = models.CharField(max_length=100, blank=True, verbose_name="وتاريخه")

    # --- 5. زيارات ميدانية ---
    has_field_visits = models.BooleanField(default=False, verbose_name="زيارات ميدانية")
    field_visits_details = models.TextField(blank=True, verbose_name="تفاصيل الزيارات الميدانية (أشغال...)")

    # --- Meta ---
    created_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='visit_records', verbose_name="أُنشئ بواسطة"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "زيارة"
        verbose_name_plural = "الزيارات"
        ordering = ['-year', 'wilaya']
        unique_together = [['wilaya', 'year']]

    def __str__(self):
        return f"زيارات — {self.get_wilaya_display()} ({self.year})"

# =========================================================
# PROGRAMME : التظاهرات والاحتفالات (6.4)
# =========================================================

class CelebrationReport(models.Model):
    """تقرير التظاهرات والاحتفالات والاعتمادات المخصصة لها."""

    # --- Identification ---
    wilaya = models.CharField(
        max_length=2,
        choices=WILAYAS,
        verbose_name="الولاية",
    )
    year = models.PositiveIntegerField(
        verbose_name="السنة",
        default=2026,
    )

    # --- تحديد المناسبات (Cases à cocher) ---
    women_day = models.BooleanField(default=False, verbose_name="اليوم العالمي للمرأة (08 مارس)")
    human_rights_day = models.BooleanField(default=False, verbose_name="اليوم العربي لحقوق الإنسان (16 مارس)")
    productive_families_day = models.BooleanField(default=False, verbose_name="اليوم العربي للأسر المنتجة (15 مارس)")
    family_day = models.BooleanField(default=False, verbose_name="اليوم العالمي للأسرة (15 ماي)")
    mothers_day = models.BooleanField(default=False, verbose_name="عيد الأمهات (آخر أحد من شهر ماي)")
    elderly_abuse_day = models.BooleanField(default=False, verbose_name="اليوم العالمي حول الوقاية من الإساءة لكبار السن")
    elderly_day = models.BooleanField(default=False, verbose_name="01 أكتوبر اليوم العالمي لكبار السن")
    pink_october = models.BooleanField(default=False, verbose_name="شهر أكتوبر الوردي")
    rural_women_day = models.BooleanField(default=False, verbose_name="15 أكتوبر اليوم العالمي للمرأة في الريف")
    protection_month = models.BooleanField(default=False, verbose_name="شهر الحماية")
    violence_prevention_day = models.BooleanField(default=False, verbose_name="25 نوفمبر اليوم العالمي للوقاية من العنف")
    sixteen_days_activism = models.BooleanField(default=False, verbose_name="16 يوم من الأنشطة للوقاية من العنف (25 نوفمبر - 10 ديسمبر)")
    national_family_day = models.BooleanField(default=False, verbose_name="11 ديسمبر اليوم الوطني للأسرة")

    # --- الاعتمادات المخصصة ---
    previous_credits_committed = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="فواضل السنوات السابقة - تعهدا")
    previous_credits_paid = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="فواضل السنوات السابقة - دفعا")
    
    current_credits_committed = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="اعتمادات السنة الحالية - تعهدا")
    current_credits_paid = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="اعتمادات السنة الحالية - دفعا")
    
    total_credits_committed = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="مجموع الاعتمادات - تعهدا")
    total_credits_paid = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="مجموع الاعتمادات - دفعا")
    
    consumption_rate_committed = models.DecimalField(max_digits=8, decimal_places=2, default=0, verbose_name="نسبة الصرف - تعهدا (%)")
    consumption_rate_paid = models.DecimalField(max_digits=8, decimal_places=2, default=0, verbose_name="نسبة الصرف - دفعا (%)")
    
    remaining_credits_committed = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="الاعتمادات المتبقية - تعهدا")
    remaining_credits_paid = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name="الاعتمادات المتبقية - دفعا")

    # --- Meta ---
    created_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='celebration_records', verbose_name="أُنشئ بواسطة"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "تقرير تظاهرات واحتفالات"
        verbose_name_plural = "تقارير التظاهرات والاحتفالات"
        ordering = ['-year', 'wilaya']
        unique_together = [['wilaya', 'year']]

    def __str__(self):
        return f"تظاهرات — {self.get_wilaya_display()} ({self.year})"