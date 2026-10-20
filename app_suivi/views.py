from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from .models import (
    RegistrationRequest, DelegateProfile, ActivityLog,
    WILAYAS, ROLES, Rawdhatna, AutismProgram, SeniorFamilyCare,
    FamilyEconomicIntegration, MothersSchoolDropout, SamdaProgram,
    RuralWomenProgram, ActionPlanZone, RaedatProgram, AccompagnementSpace,
    FamilyCohesionPlan, FamilySpace, FamilyGuidanceCenter, ParentAccompanimentUnit,
    ChildrenClub, IntegratedCenter, ElderlyCenter, DayClub, 
    ChildhoodComplex, ChildItCenter, WeeklyActivity, MeetingSession, Visit, CelebrationReport,  )
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User

from .forms import UserForm


# =====================================================
# AUTHENTIFICATION
# =====================================================

def login_view(request):
    """Page de connexion."""
    if request.user.is_authenticated:
        if request.user.is_superuser or request.user.is_staff:
            return redirect('request_list')
        return redirect('home')

    error = None
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            if not user.is_active:
                error = "حسابك في انتظار التفعيل من قبل الإدارة"
            else:
                login(request, user)
                # Redirect based on role
                if user.is_superuser or user.is_staff:
                    return redirect('request_list')
                else:
                    return redirect('home')
        else:
            error = "اسم المستخدم أو كلمة السر غير صحيحة"

    return render(request, 'accounts/login.html', {'error': error})


def logout_view(request):
    """Déconnexion."""
    logout(request)
    return redirect('login')


# =====================================================
# ACCUEIL
# =====================================================

@login_required
def home(request):
    """Page d'accueil après connexion."""
    return render(request, 'accounts/home.html')


# =====================================================
# INSCRIPTION PUBLIQUE DÉLÉGUÉ
# =====================================================

# Constantes de validation
VALID_WILAYAS = [f"{i:02d}" for i in range(1, 25)]   # 01..24
VALID_ROLES   = ['central', 'regional', 'chef de bureau']

def register_delegate_public(request):
    """
    Inscription publique d'un délégué (accessible sans être connecté).
    Crée une RegistrationRequest, PAS un User.
    """
    if request.user.is_authenticated:
        return redirect('home')

    error   = None
    success = None

    if request.method == 'POST':
        delegate_code = request.POST.get('delegate_code', '').strip()
        first_name    = request.POST.get('first_name', '').strip()
        last_name     = request.POST.get('last_name', '').strip()
        email         = request.POST.get('email', '').strip()
        password      = request.POST.get('password', '')
        wilaya        = request.POST.get('wilaya', '').strip()
        role          = request.POST.get('role', '').strip()
        phone         = request.POST.get('phone', '').strip()

        # -------- Validations --------
        if not delegate_code or not password or not first_name or not last_name:
            error = "يرجى تعبئة جميع الحقول المطلوبة"
        elif not delegate_code.isdigit() or len(delegate_code) != 10:
            error = "المعرّف الوحيد يجب أن يتكون من 10 أرقام"
        elif len(password) < 8:
            error = "كلمة السر يجب أن تكون 8 أحرف على الأقل"
        elif wilaya not in VALID_WILAYAS:
            error = "الولاية غير صحيحة"
        elif role not in VALID_ROLES:
            error = "الصفة غير صحيحة"
        elif phone and (not phone.isdigit() or len(phone) != 8):
            error = "رقم الهاتف يجب أن يتكون من 8 أرقام"
        elif User.objects.filter(username=delegate_code).exists():
            error = "المعرّف الوحيد مستعمل بالفعل"
        elif RegistrationRequest.objects.filter(
                delegate_code=delegate_code, status='pending').exists():
            error = "يوجد طلب قيد المراجعة بنفس المعرّف"
        elif email and User.objects.filter(email=email).exists():
            error = "البريد الإلكتروني مستعمل بالفعل"
        else:
            # ✅ Création d'une DEMANDE (pas d'un User)
            RegistrationRequest.objects.create(
                delegate_code=delegate_code,
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
                wilaya=wilaya,
                role=role,
                password_hash=make_password(password),
                status='pending',
            )
            success = "تم تسجيل طلبكم بنجاح. سيتم تفعيل حسابكم من قبل الإدارة."

    return render(request, 'admin/register_delegate.html', {
        'error':     error,
        'success':   success,
        'is_public': True,
    })

# =====================================================
# ESPACE ADMIN
# =====================================================

def is_admin(user):
    """Vérifie que l'utilisateur est staff ou superuser."""
    return user.is_authenticated and (user.is_superuser or user.is_staff)


# ---------- Dashboard ----------
@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    total_users     = User.objects.count()
    active_users    = User.objects.filter(is_active=True).count()
    inactive_users  = User.objects.filter(is_active=False).count()
    staff_users     = User.objects.filter(is_staff=True).count()
    recent_users    = User.objects.order_by('-date_joined')[:5]

    context = {
        'total_users':    total_users,
        'active_users':   active_users,
        'inactive_users': inactive_users,
        'staff_users':    staff_users,
        'recent_users':   recent_users,
    }
    return render(request, 'admin/dashboard.html', context)


# ---------- Liste des utilisateurs ----------
@login_required
@user_passes_test(is_admin)
def user_list(request):
    q     = request.GET.get('q', '').strip()
    users = User.objects.all().order_by('-date_joined')

    if q:
        users = users.filter(
            Q(username__icontains=q) |
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(email__icontains=q)
        )

    paginator = Paginator(users, 10)
    page_obj  = paginator.get_page(request.GET.get('page'))

    return render(request, 'admin/user_list.html', {
        'page_obj': page_obj,
        'q':        q,
    })


# ---------- Ajout utilisateur ----------
@login_required
@user_passes_test(is_admin)
def user_create(request):
    if request.method == 'POST':
        form = UserForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f"تم إنشاء المستخدم « {user.username} » بنجاح")
            return redirect('user_list')
        else:
            messages.error(request, "يرجى تصحيح الأخطاء أدناه")
    else:
        form = UserForm()

    return render(request, 'admin/user_form.html', {
        'form': form,
        'mode': 'create',
    })


# ---------- Modification utilisateur ----------
@login_required
@user_passes_test(is_admin)
def user_update(request, pk):
    user = get_object_or_404(User, pk=pk)

    if request.method == 'POST':
        form = UserForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, f"تم تحديث المستخدم « {user.username} » بنجاح")
            return redirect('user_list')
        else:
            messages.error(request, "يرجى تصحيح الأخطاء أدناه")
    else:
        form = UserForm(instance=user)

    return render(request, 'admin/user_form.html', {
        'form':     form,
        'mode':     'update',
        'user_obj': user,
    })


# ---------- Suppression utilisateur ----------
@login_required
@user_passes_test(is_admin)
def user_delete(request, pk):
    user = get_object_or_404(User, pk=pk)

    # Sécurité : ne pas se supprimer soi-même
    if user == request.user:
        messages.error(request, "لا يمكنك حذف حسابك الخاص")
        return redirect('user_list')

    if request.method == 'POST':
        username = user.username
        user.delete()
        messages.success(request, f"تم حذف المستخدم « {username} »")
        return redirect('user_list')

    return render(request, 'admin/user_confirm_delete.html', {'user_obj': user})


# ---------- Activation / Désactivation rapide ----------
@login_required
@user_passes_test(is_admin)
def user_toggle_active(request, pk):
    """Active ou désactive un utilisateur en un clic."""
    user = get_object_or_404(User, pk=pk)

    if user == request.user:
        messages.error(request, "لا يمكنك تعطيل حسابك الخاص")
        return redirect('user_list')

    user.is_active = not user.is_active
    user.save()

    state = "تفعيل" if user.is_active else "تعطيل"
    messages.success(request, f"تم {state} المستخدم « {user.username} »")
    return redirect('user_list')


# =====================================================
# DÉLÉGUÉS (ADMIN)
# =====================================================

@login_required
@user_passes_test(is_admin)
def register_delegate(request):
    """Formulaire admin pour créer un délégué (avec User Django)."""
    if request.method == 'POST':
        wilaya        = request.POST.get('wilaya', '').strip()
        role          = request.POST.get('role', '').strip()
        delegate_code = request.POST.get('delegate_code', '').strip()
        first_name    = request.POST.get('first_name', '').strip()
        last_name     = request.POST.get('last_name', '').strip()
        phone         = request.POST.get('phone', '').strip()
        email         = request.POST.get('email', '').strip()
        password      = request.POST.get('password', '')

        # Validation minimale
        if not (wilaya and role and delegate_code and first_name
                and last_name and password):
            messages.error(request, "يرجى تعبئة جميع الحقول المطلوبة")
            return render(request, 'admin/register_delegate.html')

        username = delegate_code
        if User.objects.filter(username=username).exists():
            messages.error(request, "المعرّف الوحيد مستعمل بالفعل")
            return render(request, 'admin/register_delegate.html')

        # Création du User (actif car créé par admin)
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
        )

        # Créer le Delegate si tu as un modèle :
        # from .models import Delegate
        # Delegate.objects.create(
        #     user=user,
        #     wilaya=wilaya,
        #     role=role,
        #     delegate_code=delegate_code,
        #     phone=phone,
        # )

        messages.success(
            request,
            f"تم تسجيل المندوب « {first_name} {last_name} » بنجاح"
        )
        return redirect('register_delegate')

    return render(request, 'admin/register_delegate.html')


# =====================================================
# AJAX — Prochain identifiant délégué
# =====================================================

def ajax_next_delegate_id(request):
    """
    Retourne le prochain identifiant délégué pour une wilaya donnée.
    Accessible publiquement (utilisé par /register/ ET par l'admin).
    Format : <code_wilaya><compteur sur 4 chiffres> (ex: 010001)
    """
    wilaya = request.GET.get('wilaya', '').strip()
    if not wilaya:
        return JsonResponse({'next_id': ''})

    # À adapter quand tu auras un modèle Delegate :
    # from .models import Delegate
    # count = Delegate.objects.filter(wilaya=wilaya).count() + 1

    count = 1  # temporaire — change-le quand tu auras un modèle
    next_id = f"{wilaya}{count:04d}"
    return JsonResponse({'next_id': next_id})

# =====================================================
# DEMANDES D'INSCRIPTION (ADMIN)
# =====================================================

@login_required
@user_passes_test(is_admin)
def request_list(request):
    """Liste toutes les demandes d'inscription."""
    status_filter = request.GET.get('status', 'pending')

    requests_qs = RegistrationRequest.objects.all().order_by('-created_at')
    if status_filter in ('pending', 'approved', 'rejected'):
        requests_qs = requests_qs.filter(status=status_filter)

    # Compteurs pour le badge
    pending_count  = RegistrationRequest.objects.filter(status='pending').count()
    approved_count = RegistrationRequest.objects.filter(status='approved').count()
    rejected_count = RegistrationRequest.objects.filter(status='rejected').count()

    return render(request, 'admin/request_list.html', {
        'requests':       requests_qs,
        'status_filter':  status_filter,
        'pending_count':  pending_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
    })


@login_required
@user_passes_test(is_admin)
def request_approve(request, pk):
    """Approuve une demande et crée le User + DelegateProfile."""
    req = get_object_or_404(RegistrationRequest, pk=pk)

    if req.status != 'pending':
        messages.warning(request, "هذا الطلب تمت معالجته مسبقاً")
        return redirect('request_list')

    user = req.approve(request.user)

    if user:
        ActivityLog.objects.create(
            user=request.user,
            action='approve',
            target_model='RegistrationRequest',
            target_id=req.pk,
            description=f"Approbation du délégué {req.delegate_code}",
        )
        messages.success(
            request,
            f"✅ تم قبول الطلب. المستخدم « {user.username} » جاهز للدخول."
        )
    else:
        messages.error(request, "❌ تعذّر قبول الطلب (المعرّف مستعمل)")

    return redirect('request_list')


@login_required
@user_passes_test(is_admin)
def request_reject(request, pk):
    """Refuse une demande."""
    req = get_object_or_404(RegistrationRequest, pk=pk)

    if req.status != 'pending':
        messages.warning(request, "هذا الطلب تمت معالجته مسبقاً")
        return redirect('request_list')

    note = request.POST.get('note', '').strip()
    req.reject(request.user, note=note)

    ActivityLog.objects.create(
        user=request.user,
        action='reject',
        target_model='RegistrationRequest',
        target_id=req.pk,
        description=f"Rejet du délégué {req.delegate_code} : {note}",
    )
    messages.success(request, "تم رفض الطلب")

    return redirect('request_list')



# =====================================================
# روضتنا في حومتنا (CRUD)
# =====================================================

@login_required
def rawdhatna_list(request):
    """Liste des enregistrements روضتنا في حومتنا."""
    records = Rawdhatna.objects.all()

    # Filtres
    wilaya_filter = request.GET.get('wilaya', '')
    year_filter   = request.GET.get('year', '')

    if wilaya_filter:
        records = records.filter(wilaya=wilaya_filter)
    if year_filter:
        records = records.filter(year=year_filter)

    # Années disponibles pour le filtre
    years = Rawdhatna.objects.values_list('year', flat=True).distinct().order_by('-year')

    return render(request, 'modules/rawdhatna_list.html', {
        'records': records,
        'years':   years,
        'wilaya_filter': wilaya_filter,
        'year_filter':   year_filter,
    })


@login_required
def rawdhatna_create(request):
    """Créer un enregistrement."""
    if request.method == 'POST':
        try:
            record = Rawdhatna(
                wilaya        = request.POST.get('wilaya'),
                year          = request.POST.get('year', 2026),

                previous_credits_committed  = request.POST.get('previous_credits_committed', 0) or 0,
                previous_credits_paid       = request.POST.get('previous_credits_paid', 0) or 0,
                current_credits_committed   = request.POST.get('current_credits_committed', 0) or 0,
                current_credits_paid        = request.POST.get('current_credits_paid', 0) or 0,
                total_credits_committed     = request.POST.get('total_credits_committed', 0) or 0,
                total_credits_paid          = request.POST.get('total_credits_paid', 0) or 0,
                consumption_rate_committed  = request.POST.get('consumption_rate_committed', 0) or 0,
                consumption_rate_paid       = request.POST.get('consumption_rate_paid', 0) or 0,
                remaining_credits_committed = request.POST.get('remaining_credits_committed', 0) or 0,
                remaining_credits_paid      = request.POST.get('remaining_credits_paid', 0) or 0,

                beneficiaries_female = request.POST.get('beneficiaries_female', 0) or 0,
                beneficiaries_male   = request.POST.get('beneficiaries_male', 0) or 0,
                kindergartens_count  = request.POST.get('kindergartens_count', 0) or 0,

                notes      = request.POST.get('notes', '').strip(),
                created_by = request.user,
            )
            record.save()
            messages.success(request, "✅ تم إضافة السجل بنجاح")
            return redirect('rawdhatna_list')

        except Exception as e:
            messages.error(request, f"❌ خطأ : {e}")

    return render(request, 'modules/rawdhatna_form.html', {
        'mode': 'create',
        'wilayas': WILAYAS,
    })


@login_required
def rawdhatna_update(request, pk):
    """Modifier un enregistrement."""
    record = get_object_or_404(Rawdhatna, pk=pk)

    if request.method == 'POST':
        try:
            record.wilaya = request.POST.get('wilaya')
            record.year   = request.POST.get('year', 2026)

            record.previous_credits_committed  = request.POST.get('previous_credits_committed', 0) or 0
            record.previous_credits_paid       = request.POST.get('previous_credits_paid', 0) or 0
            record.current_credits_committed   = request.POST.get('current_credits_committed', 0) or 0
            record.current_credits_paid        = request.POST.get('current_credits_paid', 0) or 0
            record.total_credits_committed     = request.POST.get('total_credits_committed', 0) or 0
            record.total_credits_paid          = request.POST.get('total_credits_paid', 0) or 0
            record.consumption_rate_committed  = request.POST.get('consumption_rate_committed', 0) or 0
            record.consumption_rate_paid       = request.POST.get('consumption_rate_paid', 0) or 0
            record.remaining_credits_committed = request.POST.get('remaining_credits_committed', 0) or 0
            record.remaining_credits_paid      = request.POST.get('remaining_credits_paid', 0) or 0

            record.beneficiaries_female = request.POST.get('beneficiaries_female', 0) or 0
            record.beneficiaries_male   = request.POST.get('beneficiaries_male', 0) or 0
            record.kindergartens_count  = request.POST.get('kindergartens_count', 0) or 0

            record.notes = request.POST.get('notes', '').strip()
            record.save()

            messages.success(request, "✅ تم تحديث السجل بنجاح")
            return redirect('rawdhatna_list')

        except Exception as e:
            messages.error(request, f"❌ خطأ : {e}")

    return render(request, 'modules/rawdhatna_form.html', {
        'mode':   'update',
        'record': record,
        'wilayas': WILAYAS,
    })


@login_required
def rawdhatna_delete(request, pk):
    """Supprimer un enregistrement."""
    record = get_object_or_404(Rawdhatna, pk=pk)

    if request.method == 'POST':
        record.delete()
        messages.success(request, "🗑️ تم حذف السجل")
        return redirect('rawdhatna_list')

    return render(request, 'modules/rawdhatna_confirm_delete.html', {'record': record})

# =====================================================
# أطفال طيف التوحد (CRUD)
# =====================================================

@login_required
def autism_list(request):
    """Liste des enregistrements أطفال طيف التوحد."""
    records = AutismProgram.objects.all()

    wilaya_filter = request.GET.get('wilaya', '')
    year_filter   = request.GET.get('year', '')

    if wilaya_filter:
        records = records.filter(wilaya=wilaya_filter)
    if year_filter:
        records = records.filter(year=year_filter)

    years = AutismProgram.objects.values_list('year', flat=True).distinct().order_by('-year')

    return render(request, 'modules/autism_list.html', {
        'records': records,
        'years':   years,
        'wilaya_filter': wilaya_filter,
        'year_filter':   year_filter,
        'wilayas': WILAYAS,
    })


@login_required
def autism_create(request):
    """Créer un enregistrement."""
    if request.method == 'POST':
        try:
            record = AutismProgram(
                wilaya = request.POST.get('wilaya'),
                year   = request.POST.get('year', 2026),

                previous_credits_committed  = request.POST.get('previous_credits_committed', 0) or 0,
                previous_credits_paid       = request.POST.get('previous_credits_paid', 0) or 0,
                current_credits_committed   = request.POST.get('current_credits_committed', 0) or 0,
                current_credits_paid        = request.POST.get('current_credits_paid', 0) or 0,
                total_credits_committed     = request.POST.get('total_credits_committed', 0) or 0,
                total_credits_paid          = request.POST.get('total_credits_paid', 0) or 0,
                consumption_rate_committed  = request.POST.get('consumption_rate_committed', 0) or 0,
                consumption_rate_paid       = request.POST.get('consumption_rate_paid', 0) or 0,
                remaining_credits_committed = request.POST.get('remaining_credits_committed', 0) or 0,
                remaining_credits_paid      = request.POST.get('remaining_credits_paid', 0) or 0,

                beneficiaries_female = request.POST.get('beneficiaries_female', 0) or 0,
                beneficiaries_male   = request.POST.get('beneficiaries_male', 0) or 0,
                associations_count   = request.POST.get('associations_count', 0) or 0,
                centers_count        = request.POST.get('centers_count', 0) or 0,

                notes      = request.POST.get('notes', '').strip(),
                created_by = request.user,
            )
            record.save()
            messages.success(request, "✅ تم إضافة السجل بنجاح")
            return redirect('autism_list')

        except Exception as e:
            messages.error(request, f"❌ خطأ : {e}")

    return render(request, 'modules/autism_form.html', {
        'mode': 'create',
        'wilayas': WILAYAS,
    })


@login_required
def autism_update(request, pk):
    """Modifier un enregistrement."""
    record = get_object_or_404(AutismProgram, pk=pk)

    if request.method == 'POST':
        try:
            record.wilaya = request.POST.get('wilaya')
            record.year   = request.POST.get('year', 2026)

            record.previous_credits_committed  = request.POST.get('previous_credits_committed', 0) or 0
            record.previous_credits_paid       = request.POST.get('previous_credits_paid', 0) or 0
            record.current_credits_committed   = request.POST.get('current_credits_committed', 0) or 0
            record.current_credits_paid        = request.POST.get('current_credits_paid', 0) or 0
            record.total_credits_committed     = request.POST.get('total_credits_committed', 0) or 0
            record.total_credits_paid          = request.POST.get('total_credits_paid', 0) or 0
            record.consumption_rate_committed  = request.POST.get('consumption_rate_committed', 0) or 0
            record.consumption_rate_paid       = request.POST.get('consumption_rate_paid', 0) or 0
            record.remaining_credits_committed = request.POST.get('remaining_credits_committed', 0) or 0
            record.remaining_credits_paid      = request.POST.get('remaining_credits_paid', 0) or 0

            record.beneficiaries_female = request.POST.get('beneficiaries_female', 0) or 0
            record.beneficiaries_male   = request.POST.get('beneficiaries_male', 0) or 0
            record.associations_count   = request.POST.get('associations_count', 0) or 0
            record.centers_count        = request.POST.get('centers_count', 0) or 0

            record.notes = request.POST.get('notes', '').strip()
            record.save()

            messages.success(request, "✅ تم تحديث السجل بنجاح")
            return redirect('autism_list')

        except Exception as e:
            messages.error(request, f"❌ خطأ : {e}")

    return render(request, 'modules/autism_form.html', {
        'mode':   'update',
        'record': record,
        'wilayas': WILAYAS,
    })


@login_required
def autism_delete(request, pk):
    """Supprimer un enregistrement."""
    record = get_object_or_404(AutismProgram, pk=pk)

    if request.method == 'POST':
        record.delete()
        messages.success(request, "🗑️ تم حذف السجل")
        return redirect('autism_list')

    return render(request, 'modules/autism_confirm_delete.html', {'record': record})

# =====================================================
# الإيداع العائلي لكبار السن (CRUD)
# =====================================================

@login_required
def senior_family_list(request):
    """Liste des enregistrements الإيداع العائلي."""
    records = SeniorFamilyCare.objects.all()

    wilaya_filter = request.GET.get('wilaya', '')
    year_filter   = request.GET.get('year', '')

    if wilaya_filter:
        records = records.filter(wilaya=wilaya_filter)
    if year_filter:
        records = records.filter(year=year_filter)

    years = SeniorFamilyCare.objects.values_list('year', flat=True).distinct().order_by('-year')

    return render(request, 'modules/senior_family_list.html', {
        'records': records,
        'years':   years,
        'wilaya_filter': wilaya_filter,
        'year_filter':   year_filter,
        'wilayas': WILAYAS,
    })


@login_required
def senior_family_create(request):
    """Créer un enregistrement."""
    if request.method == 'POST':
        try:
            record = SeniorFamilyCare(
                wilaya = request.POST.get('wilaya'),
                year   = request.POST.get('year', 2026),

                previous_credits_committed  = request.POST.get('previous_credits_committed', 0) or 0,
                previous_credits_paid       = request.POST.get('previous_credits_paid', 0) or 0,
                current_credits_committed   = request.POST.get('current_credits_committed', 0) or 0,
                current_credits_paid        = request.POST.get('current_credits_paid', 0) or 0,
                total_credits_committed     = request.POST.get('total_credits_committed', 0) or 0,
                total_credits_paid          = request.POST.get('total_credits_paid', 0) or 0,
                consumption_rate_committed  = request.POST.get('consumption_rate_committed', 0) or 0,
                consumption_rate_paid       = request.POST.get('consumption_rate_paid', 0) or 0,

                beneficiaries_female = request.POST.get('beneficiaries_female', 0) or 0,
                beneficiaries_male   = request.POST.get('beneficiaries_male', 0) or 0,
                families_count       = request.POST.get('families_count', 0) or 0,

                notes      = request.POST.get('notes', '').strip(),
                created_by = request.user,
            )
            record.save()
            messages.success(request, "✅ تم إضافة السجل بنجاح")
            return redirect('senior_family_list')

        except Exception as e:
            messages.error(request, f"❌ خطأ : {e}")

    return render(request, 'modules/senior_family_form.html', {
        'mode': 'create',
        'wilayas': WILAYAS,
    })


@login_required
def senior_family_update(request, pk):
    """Modifier un enregistrement."""
    record = get_object_or_404(SeniorFamilyCare, pk=pk)

    if request.method == 'POST':
        try:
            record.wilaya = request.POST.get('wilaya')
            record.year   = request.POST.get('year', 2026)

            record.previous_credits_committed  = request.POST.get('previous_credits_committed', 0) or 0
            record.previous_credits_paid       = request.POST.get('previous_credits_paid', 0) or 0
            record.current_credits_committed   = request.POST.get('current_credits_committed', 0) or 0
            record.current_credits_paid        = request.POST.get('current_credits_paid', 0) or 0
            record.total_credits_committed     = request.POST.get('total_credits_committed', 0) or 0
            record.total_credits_paid          = request.POST.get('total_credits_paid', 0) or 0
            record.consumption_rate_committed  = request.POST.get('consumption_rate_committed', 0) or 0
            record.consumption_rate_paid       = request.POST.get('consumption_rate_paid', 0) or 0

            record.beneficiaries_female = request.POST.get('beneficiaries_female', 0) or 0
            record.beneficiaries_male   = request.POST.get('beneficiaries_male', 0) or 0
            record.families_count       = request.POST.get('families_count', 0) or 0

            record.notes = request.POST.get('notes', '').strip()
            record.save()

            messages.success(request, "✅ تم تحديث السجل بنجاح")
            return redirect('senior_family_list')

        except Exception as e:
            messages.error(request, f"❌ خطأ : {e}")

    return render(request, 'modules/senior_family_form.html', {
        'mode':   'update',
        'record': record,
        'wilayas': WILAYAS,
    })


@login_required
def senior_family_delete(request, pk):
    """Supprimer un enregistrement."""
    record = get_object_or_404(SeniorFamilyCare, pk=pk)

    if request.method == 'POST':
        record.delete()
        messages.success(request, "🗑️ تم حذف السجل")
        return redirect('senior_family_list')

    return render(request, 'modules/senior_family_confirm_delete.html', {'record': record})

# =====================================================
# الإدماج الاقتصادي للأسر (CRUD)
# =====================================================

@login_required
def family_integration_list(request):
    records = FamilyEconomicIntegration.objects.all()
    
    wilaya_filter = request.GET.get('wilaya', '')
    year_filter   = request.GET.get('year', '')

    if wilaya_filter: records = records.filter(wilaya=wilaya_filter)
    if year_filter: records = records.filter(year=year_filter)

    years = FamilyEconomicIntegration.objects.values_list('year', flat=True).distinct().order_by('-year')

    return render(request, 'modules/family_integration_list.html', {
        'records': records, 'years': years,
        'wilaya_filter': wilaya_filter, 'year_filter': year_filter, 'wilayas': WILAYAS,
    })


@login_required
def family_integration_create(request):
    if request.method == 'POST':
        try:
            record = FamilyEconomicIntegration(
                wilaya = request.POST.get('wilaya'),
                year   = request.POST.get('year', 2026),
                
                # Credits
                previous_credits_committed  = request.POST.get('previous_credits_committed', 0) or 0,
                previous_credits_paid       = request.POST.get('previous_credits_paid', 0) or 0,
                current_credits_committed   = request.POST.get('current_credits_committed', 0) or 0,
                current_credits_paid        = request.POST.get('current_credits_paid', 0) or 0,
                total_credits_committed     = request.POST.get('total_credits_committed', 0) or 0,
                total_credits_paid          = request.POST.get('total_credits_paid', 0) or 0,
                consumption_rate_committed  = request.POST.get('consumption_rate_committed', 0) or 0,
                consumption_rate_paid       = request.POST.get('consumption_rate_paid', 0) or 0,
                remaining_credits_committed = request.POST.get('remaining_credits_committed', 0) or 0,
                remaining_credits_paid      = request.POST.get('remaining_credits_paid', 0) or 0,

                # Stats
                families_count = request.POST.get('families_count', 0) or 0,
                committee_meetings_count = request.POST.get('committee_meetings_count', 0) or 0,
                
                # Requests
                accepted_female = request.POST.get('accepted_female', 0) or 0,
                accepted_male   = request.POST.get('accepted_male', 0) or 0,
                rejected_female = request.POST.get('rejected_female', 0) or 0,
                rejected_male   = request.POST.get('rejected_male', 0) or 0,
                rejection_reasons = request.POST.get('rejection_reasons', '').strip(),

                # Training & Field
                field_visits_count = request.POST.get('field_visits_count', 0) or 0,
                training_courses_count = request.POST.get('training_courses_count', 0) or 0,
                trainees_female = request.POST.get('trainees_female', 0) or 0,
                trainees_male   = request.POST.get('trainees_male', 0) or 0,

                # Texts
                obstacles = request.POST.get('obstacles', '').strip(),
                notes     = request.POST.get('notes', '').strip(),
                created_by = request.user,
            )
            record.save()
            messages.success(request, "✅ تم إضافة السجل بنجاح")
            return redirect('family_integration_list')
        except Exception as e:
            messages.error(request, f"❌ خطأ : {e}")

    return render(request, 'modules/family_integration_form.html', {
        'mode': 'create', 'wilayas': WILAYAS,
    })


@login_required
def family_integration_update(request, pk):
    record = get_object_or_404(FamilyEconomicIntegration, pk=pk)
    
    if request.method == 'POST':
        try:
            record.wilaya = request.POST.get('wilaya')
            record.year   = request.POST.get('year', 2026)
            
            # Credits
            record.previous_credits_committed  = request.POST.get('previous_credits_committed', 0) or 0
            record.previous_credits_paid       = request.POST.get('previous_credits_paid', 0) or 0
            record.current_credits_committed   = request.POST.get('current_credits_committed', 0) or 0
            record.current_credits_paid        = request.POST.get('current_credits_paid', 0) or 0
            record.total_credits_committed     = request.POST.get('total_credits_committed', 0) or 0
            record.total_credits_paid          = request.POST.get('total_credits_paid', 0) or 0
            record.consumption_rate_committed  = request.POST.get('consumption_rate_committed', 0) or 0
            record.consumption_rate_paid       = request.POST.get('consumption_rate_paid', 0) or 0
            record.remaining_credits_committed = request.POST.get('remaining_credits_committed', 0) or 0
            record.remaining_credits_paid      = request.POST.get('remaining_credits_paid', 0) or 0

            # Stats
            record.families_count = request.POST.get('families_count', 0) or 0
            record.committee_meetings_count = request.POST.get('committee_meetings_count', 0) or 0
            
            # Requests
            record.accepted_female = request.POST.get('accepted_female', 0) or 0
            record.accepted_male   = request.POST.get('accepted_male', 0) or 0
            record.rejected_female = request.POST.get('rejected_female', 0) or 0
            record.rejected_male   = request.POST.get('rejected_male', 0) or 0
            record.rejection_reasons = request.POST.get('rejection_reasons', '').strip()

            # Training & Field
            record.field_visits_count = request.POST.get('field_visits_count', 0) or 0
            record.training_courses_count = request.POST.get('training_courses_count', 0) or 0
            record.trainees_female = request.POST.get('trainees_female', 0) or 0
            record.trainees_male   = request.POST.get('trainees_male', 0) or 0

            # Texts
            record.obstacles = request.POST.get('obstacles', '').strip()
            record.notes     = request.POST.get('notes', '').strip()
            
            record.save()
            messages.success(request, "✅ تم تحديث السجل بنجاح")
            return redirect('family_integration_list')
        except Exception as e:
            messages.error(request, f"❌ خطأ : {e}")

    return render(request, 'modules/family_integration_form.html', {
        'mode': 'update', 'record': record, 'wilayas': WILAYAS,
    })


@login_required
def family_integration_delete(request, pk):
    record = get_object_or_404(FamilyEconomicIntegration, pk=pk)
    if request.method == 'POST':
        record.delete()
        messages.success(request, "🗑️ تم حذف السجل")
        return redirect('family_integration_list')
    return render(request, 'modules/family_integration_confirm_delete.html', {'record': record})

# =====================================================
# الإدماج الاقتصادي لأمهات التلاميذ المهددين (CRUD)
# =====================================================

@login_required
def mothers_dropout_list(request):
    records = MothersSchoolDropout.objects.all()
    
    wilaya_filter = request.GET.get('wilaya', '')
    year_filter   = request.GET.get('year', '')

    if wilaya_filter: records = records.filter(wilaya=wilaya_filter)
    if year_filter: records = records.filter(year=year_filter)

    years = MothersSchoolDropout.objects.values_list('year', flat=True).distinct().order_by('-year')

    return render(request, 'modules/mothers_dropout_list.html', {
        'records': records, 'years': years,
        'wilaya_filter': wilaya_filter, 'year_filter': year_filter, 'wilayas': WILAYAS,
    })


@login_required
def mothers_dropout_create(request):
    if request.method == 'POST':
        try:
            record = MothersSchoolDropout(
                wilaya = request.POST.get('wilaya'),
                year   = request.POST.get('year', 2026),
                
                # Credits
                previous_credits_committed  = request.POST.get('previous_credits_committed', 0) or 0,
                previous_credits_paid       = request.POST.get('previous_credits_paid', 0) or 0,
                current_credits_committed   = request.POST.get('current_credits_committed', 0) or 0,
                current_credits_paid        = request.POST.get('current_credits_paid', 0) or 0,
                total_credits_committed     = request.POST.get('total_credits_committed', 0) or 0,
                total_credits_paid          = request.POST.get('total_credits_paid', 0) or 0,
                consumption_rate_committed  = request.POST.get('consumption_rate_committed', 0) or 0,
                consumption_rate_paid       = request.POST.get('consumption_rate_paid', 0) or 0,
                remaining_credits_committed = request.POST.get('remaining_credits_committed', 0) or 0,
                remaining_credits_paid      = request.POST.get('remaining_credits_paid', 0) or 0,

                # Stats
                families_count = request.POST.get('families_count', 0) or 0,
                committee_meetings_count = request.POST.get('committee_meetings_count', 0) or 0,
                
                # Requests
                accepted_female = request.POST.get('accepted_female', 0) or 0,
                accepted_male   = request.POST.get('accepted_male', 0) or 0,
                rejected_female = request.POST.get('rejected_female', 0) or 0,
                rejected_male   = request.POST.get('rejected_male', 0) or 0,
                rejection_reasons = request.POST.get('rejection_reasons', '').strip(),

                # Training & Field
                field_visits_count = request.POST.get('field_visits_count', 0) or 0,
                training_courses_count = request.POST.get('training_courses_count', 0) or 0,
                trainees_female = request.POST.get('trainees_female', 0) or 0,
                trainees_male   = request.POST.get('trainees_male', 0) or 0,

                # Texts
                obstacles = request.POST.get('obstacles', '').strip(),
                notes     = request.POST.get('notes', '').strip(),
                created_by = request.user,
            )
            record.save()
            messages.success(request, "✅ تم إضافة السجل بنجاح")
            return redirect('mothers_dropout_list')
        except Exception as e:
            messages.error(request, f"❌ خطأ : {e}")

    return render(request, 'modules/mothers_dropout_form.html', {
        'mode': 'create', 'wilayas': WILAYAS,
    })


@login_required
def mothers_dropout_update(request, pk):
    record = get_object_or_404(MothersSchoolDropout, pk=pk)
    
    if request.method == 'POST':
        try:
            record.wilaya = request.POST.get('wilaya')
            record.year   = request.POST.get('year', 2026)
            
            # Credits
            record.previous_credits_committed  = request.POST.get('previous_credits_committed', 0) or 0
            record.previous_credits_paid       = request.POST.get('previous_credits_paid', 0) or 0
            record.current_credits_committed   = request.POST.get('current_credits_committed', 0) or 0
            record.current_credits_paid        = request.POST.get('current_credits_paid', 0) or 0
            record.total_credits_committed     = request.POST.get('total_credits_committed', 0) or 0
            record.total_credits_paid          = request.POST.get('total_credits_paid', 0) or 0
            record.consumption_rate_committed  = request.POST.get('consumption_rate_committed', 0) or 0
            record.consumption_rate_paid       = request.POST.get('consumption_rate_paid', 0) or 0
            record.remaining_credits_committed = request.POST.get('remaining_credits_committed', 0) or 0
            record.remaining_credits_paid      = request.POST.get('remaining_credits_paid', 0) or 0

            # Stats
            record.families_count = request.POST.get('families_count', 0) or 0
            record.committee_meetings_count = request.POST.get('committee_meetings_count', 0) or 0
            
            # Requests
            record.accepted_female = request.POST.get('accepted_female', 0) or 0
            record.accepted_male   = request.POST.get('accepted_male', 0) or 0
            record.rejected_female = request.POST.get('rejected_female', 0) or 0
            record.rejected_male   = request.POST.get('rejected_male', 0) or 0
            record.rejection_reasons = request.POST.get('rejection_reasons', '').strip()

            # Training & Field
            record.field_visits_count = request.POST.get('field_visits_count', 0) or 0
            record.training_courses_count = request.POST.get('training_courses_count', 0) or 0
            record.trainees_female = request.POST.get('trainees_female', 0) or 0
            record.trainees_male   = request.POST.get('trainees_male', 0) or 0

            # Texts
            record.obstacles = request.POST.get('obstacles', '').strip()
            record.notes     = request.POST.get('notes', '').strip()
            
            record.save()
            messages.success(request, "✅ تم تحديث السجل بنجاح")
            return redirect('mothers_dropout_list')
        except Exception as e:
            messages.error(request, f"❌ خطأ : {e}")

    return render(request, 'modules/mothers_dropout_form.html', {
        'mode': 'update', 'record': record, 'wilayas': WILAYAS,
    })


@login_required
def mothers_dropout_delete(request, pk):
    record = get_object_or_404(MothersSchoolDropout, pk=pk)
    if request.method == 'POST':
        record.delete()
        messages.success(request, "🗑️ تم حذف السجل")
        return redirect('mothers_dropout_list')
    return render(request, 'modules/mothers_dropout_confirm_delete.html', {'record': record})


# =====================================================
# برنامج صامدة (CRUD)
# =====================================================

@login_required
def samda_list(request):
    records = SamdaProgram.objects.all()
    
    wilaya_filter = request.GET.get('wilaya', '')
    year_filter   = request.GET.get('year', '')

    if wilaya_filter: records = records.filter(wilaya=wilaya_filter)
    if year_filter: records = records.filter(year=year_filter)

    years = SamdaProgram.objects.values_list('year', flat=True).distinct().order_by('-year')

    return render(request, 'modules/samda_list.html', {
        'records': records, 'years': years,
        'wilaya_filter': wilaya_filter, 'year_filter': year_filter, 'wilayas': WILAYAS,
    })


@login_required
def samda_create(request):
    if request.method == 'POST':
        try:
            record = SamdaProgram(
                wilaya = request.POST.get('wilaya'),
                year   = request.POST.get('year', 2026),
                
                # Credits
                previous_credits_committed  = request.POST.get('previous_credits_committed', 0) or 0,
                previous_credits_paid       = request.POST.get('previous_credits_paid', 0) or 0,
                current_credits_committed   = request.POST.get('current_credits_committed', 0) or 0,
                current_credits_paid        = request.POST.get('current_credits_paid', 0) or 0,
                total_credits_committed     = request.POST.get('total_credits_committed', 0) or 0,
                total_credits_paid          = request.POST.get('total_credits_paid', 0) or 0,
                consumption_rate_committed  = request.POST.get('consumption_rate_committed', 0) or 0,
                consumption_rate_paid       = request.POST.get('consumption_rate_paid', 0) or 0,
                remaining_credits_committed = request.POST.get('remaining_credits_committed', 0) or 0,
                remaining_credits_paid      = request.POST.get('remaining_credits_paid', 0) or 0,

                # Stats
                families_count = request.POST.get('families_count', 0) or 0,
                committee_meetings_count = request.POST.get('committee_meetings_count', 0) or 0,
                
                # Requests
                accepted_female = request.POST.get('accepted_female', 0) or 0,
                accepted_male   = request.POST.get('accepted_male', 0) or 0,
                rejected_female = request.POST.get('rejected_female', 0) or 0,
                rejected_male   = request.POST.get('rejected_male', 0) or 0,
                rejection_reasons = request.POST.get('rejection_reasons', '').strip(),

                # Training & Field
                field_visits_count = request.POST.get('field_visits_count', 0) or 0,
                training_courses_count = request.POST.get('training_courses_count', 0) or 0,
                trainees_female = request.POST.get('trainees_female', 0) or 0,
                trainees_male   = request.POST.get('trainees_male', 0) or 0,

                # Texts
                obstacles = request.POST.get('obstacles', '').strip(),
                created_by = request.user,
            )
            record.save()
            messages.success(request, "✅ تم إضافة السجل بنجاح")
            return redirect('samda_list')
        except Exception as e:
            messages.error(request, f"❌ خطأ : {e}")

    return render(request, 'modules/samda_form.html', {
        'mode': 'create', 'wilayas': WILAYAS,
    })


@login_required
def samda_update(request, pk):
    record = get_object_or_404(SamdaProgram, pk=pk)
    
    if request.method == 'POST':
        try:
            record.wilaya = request.POST.get('wilaya')
            record.year   = request.POST.get('year', 2026)
            
            # Credits
            record.previous_credits_committed  = request.POST.get('previous_credits_committed', 0) or 0
            record.previous_credits_paid       = request.POST.get('previous_credits_paid', 0) or 0
            record.current_credits_committed   = request.POST.get('current_credits_committed', 0) or 0
            record.current_credits_paid        = request.POST.get('current_credits_paid', 0) or 0
            record.total_credits_committed     = request.POST.get('total_credits_committed', 0) or 0
            record.total_credits_paid          = request.POST.get('total_credits_paid', 0) or 0
            record.consumption_rate_committed  = request.POST.get('consumption_rate_committed', 0) or 0
            record.consumption_rate_paid       = request.POST.get('consumption_rate_paid', 0) or 0
            record.remaining_credits_committed = request.POST.get('remaining_credits_committed', 0) or 0
            record.remaining_credits_paid      = request.POST.get('remaining_credits_paid', 0) or 0

            # Stats
            record.families_count = request.POST.get('families_count', 0) or 0
            record.committee_meetings_count = request.POST.get('committee_meetings_count', 0) or 0
            
            # Requests
            record.accepted_female = request.POST.get('accepted_female', 0) or 0
            record.accepted_male   = request.POST.get('accepted_male', 0) or 0
            record.rejected_female = request.POST.get('rejected_female', 0) or 0
            record.rejected_male   = request.POST.get('rejected_male', 0) or 0
            record.rejection_reasons = request.POST.get('rejection_reasons', '').strip()

            # Training & Field
            record.field_visits_count = request.POST.get('field_visits_count', 0) or 0
            record.training_courses_count = request.POST.get('training_courses_count', 0) or 0
            record.trainees_female = request.POST.get('trainees_female', 0) or 0
            record.trainees_male   = request.POST.get('trainees_male', 0) or 0

            # Texts
            record.obstacles = request.POST.get('obstacles', '').strip()
            
            record.save()
            messages.success(request, "✅ تم تحديث السجل بنجاح")
            return redirect('samda_list')
        except Exception as e:
            messages.error(request, f"❌ خطأ : {e}")

    return render(request, 'modules/samda_form.html', {
        'mode': 'update', 'record': record, 'wilayas': WILAYAS,
    })


@login_required
def samda_delete(request, pk):
    record = get_object_or_404(SamdaProgram, pk=pk)
    if request.method == 'POST':
        record.delete()
        messages.success(request, "🗑️ تم حذف السجل")
        return redirect('samda_list')
    return render(request, 'modules/samda_confirm_delete.html', {'record': record})


# =====================================================
# النساء في الريف (CRUD)
# =====================================================

@login_required
def rural_women_list(request):
    records = RuralWomenProgram.objects.all()
    
    wilaya_filter = request.GET.get('wilaya', '')
    year_filter   = request.GET.get('year', '')

    if wilaya_filter: records = records.filter(wilaya=wilaya_filter)
    if year_filter: records = records.filter(year=year_filter)

    years = RuralWomenProgram.objects.values_list('year', flat=True).distinct().order_by('-year')

    return render(request, 'modules/rural_women_list.html', {
        'records': records, 'years': years,
        'wilaya_filter': wilaya_filter, 'year_filter': year_filter, 'wilayas': WILAYAS,
    })


@login_required
def rural_women_create(request):
    if request.method == 'POST':
        try:
            record = RuralWomenProgram(
                wilaya = request.POST.get('wilaya'),
                year   = request.POST.get('year', 2026),
                
                # Credits
                previous_credits_committed  = request.POST.get('previous_credits_committed', 0) or 0,
                previous_credits_paid       = request.POST.get('previous_credits_paid', 0) or 0,
                current_credits_committed   = request.POST.get('current_credits_committed', 0) or 0,
                current_credits_paid        = request.POST.get('current_credits_paid', 0) or 0,
                total_credits_committed     = request.POST.get('total_credits_committed', 0) or 0,
                total_credits_paid          = request.POST.get('total_credits_paid', 0) or 0,
                consumption_rate_committed  = request.POST.get('consumption_rate_committed', 0) or 0,
                consumption_rate_paid       = request.POST.get('consumption_rate_paid', 0) or 0,
                remaining_credits_committed = request.POST.get('remaining_credits_committed', 0) or 0,
                remaining_credits_paid      = request.POST.get('remaining_credits_paid', 0) or 0,

                # Stats
                families_count = request.POST.get('families_count', 0) or 0,
                committee_meetings_count = request.POST.get('committee_meetings_count', 0) or 0,
                
                # Requests
                accepted_female = request.POST.get('accepted_female', 0) or 0,
                accepted_male   = request.POST.get('accepted_male', 0) or 0,
                rejected_female = request.POST.get('rejected_female', 0) or 0,
                rejected_male   = request.POST.get('rejected_male', 0) or 0,
                rejection_reasons = request.POST.get('rejection_reasons', '').strip(),

                # Training & Field
                field_visits_count = request.POST.get('field_visits_count', 0) or 0,
                training_courses_count = request.POST.get('training_courses_count', 0) or 0,
                trainees_female = request.POST.get('trainees_female', 0) or 0,
                trainees_male   = request.POST.get('trainees_male', 0) or 0,

                # Texts
                obstacles = request.POST.get('obstacles', '').strip(),
                created_by = request.user,
            )
            record.save()
            messages.success(request, "✅ تم إضافة السجل بنجاح")
            return redirect('rural_women_list')
        except Exception as e:
            messages.error(request, f"❌ خطأ : {e}")

    return render(request, 'modules/rural_women_form.html', {
        'mode': 'create', 'wilayas': WILAYAS,
    })


@login_required
def rural_women_update(request, pk):
    record = get_object_or_404(RuralWomenProgram, pk=pk)
    
    if request.method == 'POST':
        try:
            record.wilaya = request.POST.get('wilaya')
            record.year   = request.POST.get('year', 2026)
            
            # Credits
            record.previous_credits_committed  = request.POST.get('previous_credits_committed', 0) or 0
            record.previous_credits_paid       = request.POST.get('previous_credits_paid', 0) or 0
            record.current_credits_committed   = request.POST.get('current_credits_committed', 0) or 0
            record.current_credits_paid        = request.POST.get('current_credits_paid', 0) or 0
            record.total_credits_committed     = request.POST.get('total_credits_committed', 0) or 0
            record.total_credits_paid          = request.POST.get('total_credits_paid', 0) or 0
            record.consumption_rate_committed  = request.POST.get('consumption_rate_committed', 0) or 0
            record.consumption_rate_paid       = request.POST.get('consumption_rate_paid', 0) or 0
            record.remaining_credits_committed = request.POST.get('remaining_credits_committed', 0) or 0
            record.remaining_credits_paid      = request.POST.get('remaining_credits_paid', 0) or 0

            # Stats
            record.families_count = request.POST.get('families_count', 0) or 0
            record.committee_meetings_count = request.POST.get('committee_meetings_count', 0) or 0
            
            # Requests
            record.accepted_female = request.POST.get('accepted_female', 0) or 0
            record.accepted_male   = request.POST.get('accepted_male', 0) or 0
            record.rejected_female = request.POST.get('rejected_female', 0) or 0
            record.rejected_male   = request.POST.get('rejected_male', 0) or 0
            record.rejection_reasons = request.POST.get('rejection_reasons', '').strip()

            # Training & Field
            record.field_visits_count = request.POST.get('field_visits_count', 0) or 0
            record.training_courses_count = request.POST.get('training_courses_count', 0) or 0
            record.trainees_female = request.POST.get('trainees_female', 0) or 0
            record.trainees_male   = request.POST.get('trainees_male', 0) or 0

            # Texts
            record.obstacles = request.POST.get('obstacles', '').strip()
            
            record.save()
            messages.success(request, "✅ تم تحديث السجل بنجاح")
            return redirect('rural_women_list')
        except Exception as e:
            messages.error(request, f"❌ خطأ : {e}")

    return render(request, 'modules/rural_women_form.html', {
        'mode': 'update', 'record': record, 'wilayas': WILAYAS,
    })


@login_required
def rural_women_delete(request, pk):
    record = get_object_or_404(RuralWomenProgram, pk=pk)
    if request.method == 'POST':
        record.delete()
        messages.success(request, "🗑️ تم حذف السجل")
        return redirect('rural_women_list')
    return render(request, 'modules/rural_women_confirm_delete.html', {'record': record})

# =====================================================
# خطة عمل لكل منطقة مشروع (CRUD)
# =====================================================

@login_required
def action_plan_list(request):
    records = ActionPlanZone.objects.all()
    
    wilaya_filter = request.GET.get('wilaya', '')
    year_filter   = request.GET.get('year', '')

    if wilaya_filter: records = records.filter(wilaya=wilaya_filter)
    if year_filter: records = records.filter(year=year_filter)

    years = ActionPlanZone.objects.values_list('year', flat=True).distinct().order_by('-year')

    return render(request, 'modules/action_plan_list.html', {
        'records': records, 'years': years,
        'wilaya_filter': wilaya_filter, 'year_filter': year_filter, 'wilayas': WILAYAS,
    })


@login_required
def action_plan_create(request):
    if request.method == 'POST':
        try:
            record = ActionPlanZone(
                wilaya = request.POST.get('wilaya'),
                year   = request.POST.get('year', 2026),
                
                # Credits
                previous_credits_committed  = request.POST.get('previous_credits_committed', 0) or 0,
                previous_credits_paid       = request.POST.get('previous_credits_paid', 0) or 0,
                current_credits_committed   = request.POST.get('current_credits_committed', 0) or 0,
                current_credits_paid        = request.POST.get('current_credits_paid', 0) or 0,
                total_credits_committed     = request.POST.get('total_credits_committed', 0) or 0,
                total_credits_paid          = request.POST.get('total_credits_paid', 0) or 0,
                consumption_rate_committed  = request.POST.get('consumption_rate_committed', 0) or 0,
                consumption_rate_paid       = request.POST.get('consumption_rate_paid', 0) or 0,
                remaining_credits_committed = request.POST.get('remaining_credits_committed', 0) or 0,
                remaining_credits_paid      = request.POST.get('remaining_credits_paid', 0) or 0,

                # Stats
                families_count = request.POST.get('families_count', 0) or 0,
                committee_meetings_count = request.POST.get('committee_meetings_count', 0) or 0,
                
                # Requests
                accepted_female = request.POST.get('accepted_female', 0) or 0,
                accepted_male   = request.POST.get('accepted_male', 0) or 0,
                rejected_female = request.POST.get('rejected_female', 0) or 0,
                rejected_male   = request.POST.get('rejected_male', 0) or 0,
                rejection_reasons = request.POST.get('rejection_reasons', '').strip(),

                # Training & Field
                field_visits_count = request.POST.get('field_visits_count', 0) or 0,
                training_courses_count = request.POST.get('training_courses_count', 0) or 0,
                trainees_female = request.POST.get('trainees_female', 0) or 0,
                trainees_male   = request.POST.get('trainees_male', 0) or 0,

                # Texts
                obstacles = request.POST.get('obstacles', '').strip(),
                created_by = request.user,
            )
            record.save()
            messages.success(request, "✅ تم إضافة السجل بنجاح")
            return redirect('action_plan_list')
        except Exception as e:
            messages.error(request, f"❌ خطأ : {e}")

    return render(request, 'modules/action_plan_form.html', {
        'mode': 'create', 'wilayas': WILAYAS,
    })


@login_required
def action_plan_update(request, pk):
    record = get_object_or_404(ActionPlanZone, pk=pk)
    
    if request.method == 'POST':
        try:
            record.wilaya = request.POST.get('wilaya')
            record.year   = request.POST.get('year', 2026)
            
            # Credits
            record.previous_credits_committed  = request.POST.get('previous_credits_committed', 0) or 0
            record.previous_credits_paid       = request.POST.get('previous_credits_paid', 0) or 0
            record.current_credits_committed   = request.POST.get('current_credits_committed', 0) or 0
            record.current_credits_paid        = request.POST.get('current_credits_paid', 0) or 0
            record.total_credits_committed     = request.POST.get('total_credits_committed', 0) or 0
            record.total_credits_paid          = request.POST.get('total_credits_paid', 0) or 0
            record.consumption_rate_committed  = request.POST.get('consumption_rate_committed', 0) or 0
            record.consumption_rate_paid       = request.POST.get('consumption_rate_paid', 0) or 0
            record.remaining_credits_committed = request.POST.get('remaining_credits_committed', 0) or 0
            record.remaining_credits_paid      = request.POST.get('remaining_credits_paid', 0) or 0

            # Stats
            record.families_count = request.POST.get('families_count', 0) or 0
            record.committee_meetings_count = request.POST.get('committee_meetings_count', 0) or 0
            
            # Requests
            record.accepted_female = request.POST.get('accepted_female', 0) or 0
            record.accepted_male   = request.POST.get('accepted_male', 0) or 0
            record.rejected_female = request.POST.get('rejected_female', 0) or 0
            record.rejected_male   = request.POST.get('rejected_male', 0) or 0
            record.rejection_reasons = request.POST.get('rejection_reasons', '').strip()

            # Training & Field
            record.field_visits_count = request.POST.get('field_visits_count', 0) or 0
            record.training_courses_count = request.POST.get('training_courses_count', 0) or 0
            record.trainees_female = request.POST.get('trainees_female', 0) or 0
            record.trainees_male   = request.POST.get('trainees_male', 0) or 0

            # Texts
            record.obstacles = request.POST.get('obstacles', '').strip()
            
            record.save()
            messages.success(request, "✅ تم تحديث السجل بنجاح")
            return redirect('action_plan_list')
        except Exception as e:
            messages.error(request, f"❌ خطأ : {e}")

    return render(request, 'modules/action_plan_form.html', {
        'mode': 'update', 'record': record, 'wilayas': WILAYAS,
    })


@login_required
def action_plan_delete(request, pk):
    record = get_object_or_404(ActionPlanZone, pk=pk)
    if request.method == 'POST':
        record.delete()
        messages.success(request, "🗑️ تم حذف السجل")
        return redirect('action_plan_list')
    return render(request, 'modules/action_plan_confirm_delete.html', {'record': record})


# =====================================================
# برنامج رائدات (CRUD)
# =====================================================

@login_required
def raedat_list(request):
    records = RaedatProgram.objects.all()
    
    wilaya_filter = request.GET.get('wilaya', '')
    year_filter   = request.GET.get('year', '')

    if wilaya_filter: records = records.filter(wilaya=wilaya_filter)
    if year_filter: records = records.filter(year=year_filter)

    years = RaedatProgram.objects.values_list('year', flat=True).distinct().order_by('-year')

    return render(request, 'modules/raedat_list.html', {
        'records': records, 'years': years,
        'wilaya_filter': wilaya_filter, 'year_filter': year_filter, 'wilayas': WILAYAS,
    })


@login_required
def raedat_create(request):
    if request.method == 'POST':
        try:
            record = RaedatProgram(
                wilaya = request.POST.get('wilaya'),
                year   = request.POST.get('year', 2026),
                
                # Credits
                previous_credits_committed  = request.POST.get('previous_credits_committed', 0) or 0,
                previous_credits_paid       = request.POST.get('previous_credits_paid', 0) or 0,
                current_credits_committed   = request.POST.get('current_credits_committed', 0) or 0,
                current_credits_paid        = request.POST.get('current_credits_paid', 0) or 0,
                total_credits_committed     = request.POST.get('total_credits_committed', 0) or 0,
                total_credits_paid          = request.POST.get('total_credits_paid', 0) or 0,
                consumption_rate_committed  = request.POST.get('consumption_rate_committed', 0) or 0,
                consumption_rate_paid       = request.POST.get('consumption_rate_paid', 0) or 0,
                remaining_credits_committed = request.POST.get('remaining_credits_committed', 0) or 0,
                remaining_credits_paid      = request.POST.get('remaining_credits_paid', 0) or 0,

                # Stats
                beneficiaries_count = request.POST.get('beneficiaries_count', 0) or 0,
                
                # Requests
                accepted_female = request.POST.get('accepted_female', 0) or 0,
                accepted_male   = request.POST.get('accepted_male', 0) or 0,
                rejected_female = request.POST.get('rejected_female', 0) or 0,
                rejected_male   = request.POST.get('rejected_male', 0) or 0,
                rejection_reasons = request.POST.get('rejection_reasons', '').strip(),

                # Training & Field
                field_visits_count = request.POST.get('field_visits_count', 0) or 0,
                training_courses_count = request.POST.get('training_courses_count', 0) or 0,
                trainees_count = request.POST.get('trainees_count', 0) or 0,

                # Texts
                obstacles = request.POST.get('obstacles', '').strip(),
                created_by = request.user,
            )
            record.save()
            messages.success(request, "✅ تم إضافة السجل بنجاح")
            return redirect('raedat_list')
        except Exception as e:
            messages.error(request, f"❌ خطأ : {e}")

    return render(request, 'modules/raedat_form.html', {
        'mode': 'create', 'wilayas': WILAYAS,
    })


@login_required
def raedat_update(request, pk):
    record = get_object_or_404(RaedatProgram, pk=pk)
    
    if request.method == 'POST':
        try:
            record.wilaya = request.POST.get('wilaya')
            record.year   = request.POST.get('year', 2026)
            
            # Credits
            record.previous_credits_committed  = request.POST.get('previous_credits_committed', 0) or 0
            record.previous_credits_paid       = request.POST.get('previous_credits_paid', 0) or 0
            record.current_credits_committed   = request.POST.get('current_credits_committed', 0) or 0
            record.current_credits_paid        = request.POST.get('current_credits_paid', 0) or 0
            record.total_credits_committed     = request.POST.get('total_credits_committed', 0) or 0
            record.total_credits_paid          = request.POST.get('total_credits_paid', 0) or 0
            record.consumption_rate_committed  = request.POST.get('consumption_rate_committed', 0) or 0
            record.consumption_rate_paid       = request.POST.get('consumption_rate_paid', 0) or 0
            record.remaining_credits_committed = request.POST.get('remaining_credits_committed', 0) or 0
            record.remaining_credits_paid      = request.POST.get('remaining_credits_paid', 0) or 0

            # Stats
            record.beneficiaries_count = request.POST.get('beneficiaries_count', 0) or 0
            
            # Requests
            record.accepted_female = request.POST.get('accepted_female', 0) or 0
            record.accepted_male   = request.POST.get('accepted_male', 0) or 0
            record.rejected_female = request.POST.get('rejected_female', 0) or 0
            record.rejected_male   = request.POST.get('rejected_male', 0) or 0
            record.rejection_reasons = request.POST.get('rejection_reasons', '').strip()

            # Training & Field
            record.field_visits_count = request.POST.get('field_visits_count', 0) or 0
            record.training_courses_count = request.POST.get('training_courses_count', 0) or 0
            record.trainees_count = request.POST.get('trainees_count', 0) or 0

            # Texts
            record.obstacles = request.POST.get('obstacles', '').strip()
            
            record.save()
            messages.success(request, "✅ تم تحديث السجل بنجاح")
            return redirect('raedat_list')
        except Exception as e:
            messages.error(request, f"❌ خطأ : {e}")

    return render(request, 'modules/raedat_form.html', {
        'mode': 'update', 'record': record, 'wilayas': WILAYAS,
    })


@login_required
def raedat_delete(request, pk):
    record = get_object_or_404(RaedatProgram, pk=pk)
    if request.method == 'POST':
        record.delete()
        messages.success(request, "🗑️ تم حذف السجل")
        return redirect('raedat_list')
    return render(request, 'modules/raedat_confirm_delete.html', {'record': record})


# =====================================================
# فضاءات المرافقة والتسويق (CRUD)
# =====================================================

@login_required
def accompagnement_list(request):
    records = AccompagnementSpace.objects.all()
    
    wilaya_filter = request.GET.get('wilaya', '')
    year_filter   = request.GET.get('year', '')

    if wilaya_filter: records = records.filter(wilaya=wilaya_filter)
    if year_filter: records = records.filter(year=year_filter)

    years = AccompagnementSpace.objects.values_list('year', flat=True).distinct().order_by('-year')

    return render(request, 'modules/accompagnement_list.html', {
        'records': records, 'years': years,
        'wilaya_filter': wilaya_filter, 'year_filter': year_filter, 'wilayas': WILAYAS,
    })


@login_required
def accompagnement_create(request):
    if request.method == 'POST':
        try:
            record = AccompagnementSpace(
                wilaya = request.POST.get('wilaya'),
                year   = request.POST.get('year', 2026),
                
                # Credits
                previous_credits_committed  = request.POST.get('previous_credits_committed', 0) or 0,
                previous_credits_paid       = request.POST.get('previous_credits_paid', 0) or 0,
                current_credits_committed   = request.POST.get('current_credits_committed', 0) or 0,
                current_credits_paid        = request.POST.get('current_credits_paid', 0) or 0,
                total_credits_committed     = request.POST.get('total_credits_committed', 0) or 0,
                total_credits_paid          = request.POST.get('total_credits_paid', 0) or 0,
                consumption_rate_committed  = request.POST.get('consumption_rate_committed', 0) or 0,
                consumption_rate_paid       = request.POST.get('consumption_rate_paid', 0) or 0,
                remaining_credits_committed = request.POST.get('remaining_credits_committed', 0) or 0,
                remaining_credits_paid      = request.POST.get('remaining_credits_paid', 0) or 0,

                # Beneficiaries
                beneficiaries_accompaniment = request.POST.get('beneficiaries_accompaniment', 0) or 0,
                beneficiaries_training      = request.POST.get('beneficiaries_training', 0) or 0,
                beneficiaries_marketing     = request.POST.get('beneficiaries_marketing', 0) or 0,

                # Texts
                obstacles = request.POST.get('obstacles', '').strip(),
                created_by = request.user,
            )
            record.save()
            messages.success(request, "✅ تم إضافة السجل بنجاح")
            return redirect('accompagnement_list')
        except Exception as e:
            messages.error(request, f"❌ خطأ : {e}")

    return render(request, 'modules/accompagnement_form.html', {
        'mode': 'create', 'wilayas': WILAYAS,
    })


@login_required
def accompagnement_update(request, pk):
    record = get_object_or_404(AccompagnementSpace, pk=pk)
    
    if request.method == 'POST':
        try:
            record.wilaya = request.POST.get('wilaya')
            record.year   = request.POST.get('year', 2026)
            
            # Credits
            record.previous_credits_committed  = request.POST.get('previous_credits_committed', 0) or 0
            record.previous_credits_paid       = request.POST.get('previous_credits_paid', 0) or 0
            record.current_credits_committed   = request.POST.get('current_credits_committed', 0) or 0
            record.current_credits_paid        = request.POST.get('current_credits_paid', 0) or 0
            record.total_credits_committed     = request.POST.get('total_credits_committed', 0) or 0
            record.total_credits_paid          = request.POST.get('total_credits_paid', 0) or 0
            record.consumption_rate_committed  = request.POST.get('consumption_rate_committed', 0) or 0
            record.consumption_rate_paid       = request.POST.get('consumption_rate_paid', 0) or 0
            record.remaining_credits_committed = request.POST.get('remaining_credits_committed', 0) or 0
            record.remaining_credits_paid      = request.POST.get('remaining_credits_paid', 0) or 0

            # Beneficiaries
            record.beneficiaries_accompaniment = request.POST.get('beneficiaries_accompaniment', 0) or 0
            record.beneficiaries_training      = request.POST.get('beneficiaries_training', 0) or 0
            record.beneficiaries_marketing     = request.POST.get('beneficiaries_marketing', 0) or 0

            # Texts
            record.obstacles = request.POST.get('obstacles', '').strip()
            
            record.save()
            messages.success(request, "✅ تم تحديث السجل بنجاح")
            return redirect('accompagnement_list')
        except Exception as e:
            messages.error(request, f"❌ خطأ : {e}")

    return render(request, 'modules/accompagnement_form.html', {
        'mode': 'update', 'record': record, 'wilayas': WILAYAS,
    })


@login_required
def accompagnement_delete(request, pk):
    record = get_object_or_404(AccompagnementSpace, pk=pk)
    if request.method == 'POST':
        record.delete()
        messages.success(request, "🗑️ تم حذف السجل")
        return redirect('accompagnement_list')
    return render(request, 'modules/accompagnement_confirm_delete.html', {'record': record})


# =====================================================
# التمكين الاجتماعي للأسر (CRUD)
# =====================================================

@login_required
def family_cohesion_list(request):
    records = FamilyCohesionPlan.objects.all()
    
    wilaya_filter = request.GET.get('wilaya', '')
    year_filter   = request.GET.get('year', '')

    if wilaya_filter: records = records.filter(wilaya=wilaya_filter)
    if year_filter: records = records.filter(year=year_filter)

    years = FamilyCohesionPlan.objects.values_list('year', flat=True).distinct().order_by('-year')

    return render(request, 'modules/family_cohesion_list.html', {
        'records': records, 'years': years,
        'wilaya_filter': wilaya_filter, 'year_filter': year_filter, 'wilayas': WILAYAS,
    })


@login_required
def family_cohesion_create(request):
    if request.method == 'POST':
        try:
            record = FamilyCohesionPlan(
                wilaya = request.POST.get('wilaya'),
                year   = request.POST.get('year', 2026),
                
                # Credits
                previous_credits_committed  = request.POST.get('previous_credits_committed', 0) or 0,
                previous_credits_paid       = request.POST.get('previous_credits_paid', 0) or 0,
                current_credits_committed   = request.POST.get('current_credits_committed', 0) or 0,
                current_credits_paid        = request.POST.get('current_credits_paid', 0) or 0,
                total_credits_committed     = request.POST.get('total_credits_committed', 0) or 0,
                total_credits_paid          = request.POST.get('total_credits_paid', 0) or 0,
                consumption_rate_committed  = request.POST.get('consumption_rate_committed', 0) or 0,
                consumption_rate_paid       = request.POST.get('consumption_rate_paid', 0) or 0,
                remaining_credits_committed = request.POST.get('remaining_credits_committed', 0) or 0,
                remaining_credits_paid      = request.POST.get('remaining_credits_paid', 0) or 0,

                # Beneficiaries & Phase
                beneficiaries_count = request.POST.get('beneficiaries_count', 0) or 0,
                consulting_firm = request.POST.get('consulting_firm', '').strip(),
                implementation_phase = request.POST.get('implementation_phase', '1'),

                # Team
                team_sociologist = request.POST.get('team_sociologist', 0) or 0,
                team_legal = request.POST.get('team_legal', 0) or 0,
                team_psychologist = request.POST.get('team_psychologist', 0) or 0,
                team_health = request.POST.get('team_health', 0) or 0,
                team_other_desc = request.POST.get('team_other_desc', '').strip(),

                created_by = request.user,
            )
            record.save()
            messages.success(request, "✅ تم إضافة السجل بنجاح")
            return redirect('family_cohesion_list')
        except Exception as e:
            messages.error(request, f"❌ خطأ : {e}")

    return render(request, 'modules/family_cohesion_form.html', {
        'mode': 'create', 'wilayas': WILAYAS,
    })


@login_required
def family_cohesion_update(request, pk):
    record = get_object_or_404(FamilyCohesionPlan, pk=pk)
    
    if request.method == 'POST':
        try:
            record.wilaya = request.POST.get('wilaya')
            record.year   = request.POST.get('year', 2026)
            
            # Credits
            record.previous_credits_committed  = request.POST.get('previous_credits_committed', 0) or 0
            record.previous_credits_paid       = request.POST.get('previous_credits_paid', 0) or 0
            record.current_credits_committed   = request.POST.get('current_credits_committed', 0) or 0
            record.current_credits_paid        = request.POST.get('current_credits_paid', 0) or 0
            record.total_credits_committed     = request.POST.get('total_credits_committed', 0) or 0
            record.total_credits_paid          = request.POST.get('total_credits_paid', 0) or 0
            record.consumption_rate_committed  = request.POST.get('consumption_rate_committed', 0) or 0
            record.consumption_rate_paid       = request.POST.get('consumption_rate_paid', 0) or 0
            record.remaining_credits_committed = request.POST.get('remaining_credits_committed', 0) or 0
            record.remaining_credits_paid      = request.POST.get('remaining_credits_paid', 0) or 0

            # Beneficiaries & Phase
            record.beneficiaries_count = request.POST.get('beneficiaries_count', 0) or 0
            record.consulting_firm = request.POST.get('consulting_firm', '').strip()
            record.implementation_phase = request.POST.get('implementation_phase', '1')

            # Team
            record.team_sociologist = request.POST.get('team_sociologist', 0) or 0
            record.team_legal = request.POST.get('team_legal', 0) or 0
            record.team_psychologist = request.POST.get('team_psychologist', 0) or 0
            record.team_health = request.POST.get('team_health', 0) or 0
            record.team_other_desc = request.POST.get('team_other_desc', '').strip()
            
            record.save()
            messages.success(request, "✅ تم تحديث السجل بنجاح")
            return redirect('family_cohesion_list')
        except Exception as e:
            messages.error(request, f"❌ خطأ : {e}")

    return render(request, 'modules/family_cohesion_form.html', {
        'mode': 'update', 'record': record, 'wilayas': WILAYAS,
    })


@login_required
def family_cohesion_delete(request, pk):
    record = get_object_or_404(FamilyCohesionPlan, pk=pk)
    if request.method == 'POST':
        record.delete()
        messages.success(request, "🗑️ تم حذف السجل")
        return redirect('family_cohesion_list')
    return render(request, 'modules/family_cohesion_confirm_delete.html', {'record': record})


# =====================================================
# فضاءات الأسرة (CRUD)
# =====================================================

@login_required
def family_space_list(request):
    records = FamilySpace.objects.all()
    
    wilaya_filter = request.GET.get('wilaya', '')
    year_filter   = request.GET.get('year', '')

    if wilaya_filter: records = records.filter(wilaya=wilaya_filter)
    if year_filter: records = records.filter(year=year_filter)

    years = FamilySpace.objects.values_list('year', flat=True).distinct().order_by('-year')

    return render(request, 'modules/family_space_list.html', {
        'records': records, 'years': years,
        'wilaya_filter': wilaya_filter, 'year_filter': year_filter, 'wilayas': WILAYAS,
    })


@login_required
def family_space_create(request):
    if request.method == 'POST':
        try:
            record = FamilySpace(
                wilaya = request.POST.get('wilaya'),
                year   = request.POST.get('year', 2026),
                is_active = request.POST.get('is_active') == 'on',
                
                # Staff
                staff_legal = request.POST.get('staff_legal', 0) or 0,
                staff_psychology = request.POST.get('staff_psychology', 0) or 0,
                staff_health = request.POST.get('staff_health', 0) or 0,
                staff_admin = request.POST.get('staff_admin', 0) or 0,
                staff_educator = request.POST.get('staff_educator', 0) or 0,
                staff_other_desc = request.POST.get('staff_other_desc', '').strip(),
                staff_other_count = request.POST.get('staff_other_count', 0) or 0,

                # Beneficiaries
                beneficiaries_female = request.POST.get('beneficiaries_female', 0) or 0,
                beneficiaries_male = request.POST.get('beneficiaries_male', 0) or 0,
                beneficiaries_children = request.POST.get('beneficiaries_children', 0) or 0,
                beneficiaries_adults = request.POST.get('beneficiaries_adults', 0) or 0,
                beneficiaries_seniors = request.POST.get('beneficiaries_seniors', 0) or 0,

                # Credits
                previous_credits_committed  = request.POST.get('previous_credits_committed', 0) or 0,
                previous_credits_paid       = request.POST.get('previous_credits_paid', 0) or 0,
                current_credits_committed   = request.POST.get('current_credits_committed', 0) or 0,
                current_credits_paid        = request.POST.get('current_credits_paid', 0) or 0,
                total_credits_committed     = request.POST.get('total_credits_committed', 0) or 0,
                total_credits_paid          = request.POST.get('total_credits_paid', 0) or 0,
                consumption_rate_committed  = request.POST.get('consumption_rate_committed', 0) or 0,
                consumption_rate_paid       = request.POST.get('consumption_rate_paid', 0) or 0,
                remaining_credits_committed = request.POST.get('remaining_credits_committed', 0) or 0,
                remaining_credits_paid      = request.POST.get('remaining_credits_paid', 0) or 0,

                # Construction
                construction_start_year = request.POST.get('construction_start_year') or None,
                construction_total_credits = request.POST.get('construction_total_credits', 0) or 0,
                construction_progress = request.POST.get('construction_progress', 0) or 0,
                construction_delay_reasons = request.POST.get('construction_delay_reasons', '').strip(),
                actual_operation_start_year = request.POST.get('actual_operation_start_year') or None,

                created_by = request.user,
            )
            record.save()
            messages.success(request, "✅ تم إضافة السجل بنجاح")
            return redirect('family_space_list')
        except Exception as e:
            messages.error(request, f"❌ خطأ : {e}")

    return render(request, 'modules/family_space_form.html', {
        'mode': 'create', 'wilayas': WILAYAS,
    })


@login_required
def family_space_update(request, pk):
    record = get_object_or_404(FamilySpace, pk=pk)
    
    if request.method == 'POST':
        try:
            record.wilaya = request.POST.get('wilaya')
            record.year   = request.POST.get('year', 2026)
            record.is_active = request.POST.get('is_active') == 'on'
            
            # Staff
            record.staff_legal = request.POST.get('staff_legal', 0) or 0
            record.staff_psychology = request.POST.get('staff_psychology', 0) or 0
            record.staff_health = request.POST.get('staff_health', 0) or 0
            record.staff_admin = request.POST.get('staff_admin', 0) or 0
            record.staff_educator = request.POST.get('staff_educator', 0) or 0
            record.staff_other_desc = request.POST.get('staff_other_desc', '').strip()
            record.staff_other_count = request.POST.get('staff_other_count', 0) or 0

            # Beneficiaries
            record.beneficiaries_female = request.POST.get('beneficiaries_female', 0) or 0
            record.beneficiaries_male = request.POST.get('beneficiaries_male', 0) or 0
            record.beneficiaries_children = request.POST.get('beneficiaries_children', 0) or 0
            record.beneficiaries_adults = request.POST.get('beneficiaries_adults', 0) or 0
            record.beneficiaries_seniors = request.POST.get('beneficiaries_seniors', 0) or 0

            # Credits
            record.previous_credits_committed  = request.POST.get('previous_credits_committed', 0) or 0
            record.previous_credits_paid       = request.POST.get('previous_credits_paid', 0) or 0
            record.current_credits_committed   = request.POST.get('current_credits_committed', 0) or 0
            record.current_credits_paid        = request.POST.get('current_credits_paid', 0) or 0
            record.total_credits_committed     = request.POST.get('total_credits_committed', 0) or 0
            record.total_credits_paid          = request.POST.get('total_credits_paid', 0) or 0
            record.consumption_rate_committed  = request.POST.get('consumption_rate_committed', 0) or 0
            record.consumption_rate_paid       = request.POST.get('consumption_rate_paid', 0) or 0
            record.remaining_credits_committed = request.POST.get('remaining_credits_committed', 0) or 0
            record.remaining_credits_paid      = request.POST.get('remaining_credits_paid', 0) or 0

            # Construction
            record.construction_start_year = request.POST.get('construction_start_year') or None
            record.construction_total_credits = request.POST.get('construction_total_credits', 0) or 0
            record.construction_progress = request.POST.get('construction_progress', 0) or 0
            record.construction_delay_reasons = request.POST.get('construction_delay_reasons', '').strip()
            record.actual_operation_start_year = request.POST.get('actual_operation_start_year') or None
            
            record.save()
            messages.success(request, "✅ تم تحديث السجل بنجاح")
            return redirect('family_space_list')
        except Exception as e:
            messages.error(request, f"❌ خطأ : {e}")

    return render(request, 'modules/family_space_form.html', {
        'mode': 'update', 'record': record, 'wilayas': WILAYAS,
    })


@login_required
def family_space_delete(request, pk):
    record = get_object_or_404(FamilySpace, pk=pk)
    if request.method == 'POST':
        record.delete()
        messages.success(request, "🗑️ تم حذف السجل")
        return redirect('family_space_list')
    return render(request, 'modules/family_space_confirm_delete.html', {'record': record})


# =====================================================
# مركز إرشاد وتوجيه أسري (CRUD)
# =====================================================

@login_required
def family_guidance_list(request):
    records = FamilyGuidanceCenter.objects.all()
    
    wilaya_filter = request.GET.get('wilaya', '')
    year_filter   = request.GET.get('year', '')

    if wilaya_filter: records = records.filter(wilaya=wilaya_filter)
    if year_filter: records = records.filter(year=year_filter)

    years = FamilyGuidanceCenter.objects.values_list('year', flat=True).distinct().order_by('-year')

    return render(request, 'modules/family_guidance_list.html', {
        'records': records, 'years': years,
        'wilaya_filter': wilaya_filter, 'year_filter': year_filter, 'wilayas': WILAYAS,
    })


@login_required
def family_guidance_create(request):
    if request.method == 'POST':
        try:
            record = FamilyGuidanceCenter(
                wilaya = request.POST.get('wilaya'),
                year   = request.POST.get('year', 2026),
                is_active = request.POST.get('is_active') == 'on',
                
                # Staff
                staff_legal = request.POST.get('staff_legal', 0) or 0,
                staff_psychology = request.POST.get('staff_psychology', 0) or 0,
                staff_health = request.POST.get('staff_health', 0) or 0,
                staff_admin = request.POST.get('staff_admin', 0) or 0,
                staff_educator = request.POST.get('staff_educator', 0) or 0,
                staff_other_desc = request.POST.get('staff_other_desc', '').strip(),
                staff_other_count = request.POST.get('staff_other_count', 0) or 0,

                # Beneficiaries
                beneficiaries_female = request.POST.get('beneficiaries_female', 0) or 0,
                beneficiaries_male = request.POST.get('beneficiaries_male', 0) or 0,
                beneficiaries_children = request.POST.get('beneficiaries_children', 0) or 0,
                beneficiaries_youth = request.POST.get('beneficiaries_youth', 0) or 0,
                beneficiaries_adults = request.POST.get('beneficiaries_adults', 0) or 0,
                beneficiaries_seniors = request.POST.get('beneficiaries_seniors', 0) or 0,

                # Credits
                previous_credits_committed  = request.POST.get('previous_credits_committed', 0) or 0,
                previous_credits_paid       = request.POST.get('previous_credits_paid', 0) or 0,
                current_credits_committed   = request.POST.get('current_credits_committed', 0) or 0,
                current_credits_paid        = request.POST.get('current_credits_paid', 0) or 0,
                total_credits_committed     = request.POST.get('total_credits_committed', 0) or 0,
                total_credits_paid          = request.POST.get('total_credits_paid', 0) or 0,
                consumption_rate_committed  = request.POST.get('consumption_rate_committed', 0) or 0,
                consumption_rate_paid       = request.POST.get('consumption_rate_paid', 0) or 0,
                remaining_credits_committed = request.POST.get('remaining_credits_committed', 0) or 0,
                remaining_credits_paid      = request.POST.get('remaining_credits_paid', 0) or 0,

                # Construction
                construction_start_year = request.POST.get('construction_start_year') or None,
                construction_total_credits = request.POST.get('construction_total_credits', 0) or 0,
                construction_progress = request.POST.get('construction_progress', 0) or 0,
                construction_delay_reasons = request.POST.get('construction_delay_reasons', '').strip(),
                actual_operation_start_year = request.POST.get('actual_operation_start_year') or None,

                created_by = request.user,
            )
            record.save()
            messages.success(request, "✅ تم إضافة السجل بنجاح")
            return redirect('family_guidance_list')
        except Exception as e:
            messages.error(request, f"❌ خطأ : {e}")

    return render(request, 'modules/family_guidance_form.html', {
        'mode': 'create', 'wilayas': WILAYAS,
    })


@login_required
def family_guidance_update(request, pk):
    record = get_object_or_404(FamilyGuidanceCenter, pk=pk)
    
    if request.method == 'POST':
        try:
            record.wilaya = request.POST.get('wilaya')
            record.year   = request.POST.get('year', 2026)
            record.is_active = request.POST.get('is_active') == 'on'
            
            # Staff
            record.staff_legal = request.POST.get('staff_legal', 0) or 0
            record.staff_psychology = request.POST.get('staff_psychology', 0) or 0
            record.staff_health = request.POST.get('staff_health', 0) or 0
            record.staff_admin = request.POST.get('staff_admin', 0) or 0
            record.staff_educator = request.POST.get('staff_educator', 0) or 0
            record.staff_other_desc = request.POST.get('staff_other_desc', '').strip()
            record.staff_other_count = request.POST.get('staff_other_count', 0) or 0

            # Beneficiaries
            record.beneficiaries_female = request.POST.get('beneficiaries_female', 0) or 0
            record.beneficiaries_male = request.POST.get('beneficiaries_male', 0) or 0
            record.beneficiaries_children = request.POST.get('beneficiaries_children', 0) or 0
            record.beneficiaries_youth = request.POST.get('beneficiaries_youth', 0) or 0
            record.beneficiaries_adults = request.POST.get('beneficiaries_adults', 0) or 0
            record.beneficiaries_seniors = request.POST.get('beneficiaries_seniors', 0) or 0

            # Credits
            record.previous_credits_committed  = request.POST.get('previous_credits_committed', 0) or 0
            record.previous_credits_paid       = request.POST.get('previous_credits_paid', 0) or 0
            record.current_credits_committed   = request.POST.get('current_credits_committed', 0) or 0
            record.current_credits_paid        = request.POST.get('current_credits_paid', 0) or 0
            record.total_credits_committed     = request.POST.get('total_credits_committed', 0) or 0
            record.total_credits_paid          = request.POST.get('total_credits_paid', 0) or 0
            record.consumption_rate_committed  = request.POST.get('consumption_rate_committed', 0) or 0
            record.consumption_rate_paid       = request.POST.get('consumption_rate_paid', 0) or 0
            record.remaining_credits_committed = request.POST.get('remaining_credits_committed', 0) or 0
            record.remaining_credits_paid      = request.POST.get('remaining_credits_paid', 0) or 0

            # Construction
            record.construction_start_year = request.POST.get('construction_start_year') or None
            record.construction_total_credits = request.POST.get('construction_total_credits', 0) or 0
            record.construction_progress = request.POST.get('construction_progress', 0) or 0
            record.construction_delay_reasons = request.POST.get('construction_delay_reasons', '').strip()
            record.actual_operation_start_year = request.POST.get('actual_operation_start_year') or None
            
            record.save()
            messages.success(request, "✅ تم تحديث السجل بنجاح")
            return redirect('family_guidance_list')
        except Exception as e:
            messages.error(request, f"❌ خطأ : {e}")

    return render(request, 'modules/family_guidance_form.html', {
        'mode': 'update', 'record': record, 'wilayas': WILAYAS,
    })


@login_required
def family_guidance_delete(request, pk):
    record = get_object_or_404(FamilyGuidanceCenter, pk=pk)
    if request.method == 'POST':
        record.delete()
        messages.success(request, "🗑️ تم حذف السجل")
        return redirect('family_guidance_list')
    return render(request, 'modules/family_guidance_confirm_delete.html', {'record': record})


# =====================================================
# وحدة مرافقة الأولياء (CRUD)
# =====================================================

@login_required
def parent_accompaniment_list(request):
    records = ParentAccompanimentUnit.objects.all()
    
    wilaya_filter = request.GET.get('wilaya', '')
    year_filter   = request.GET.get('year', '')

    if wilaya_filter: records = records.filter(wilaya=wilaya_filter)
    if year_filter: records = records.filter(year=year_filter)

    years = ParentAccompanimentUnit.objects.values_list('year', flat=True).distinct().order_by('-year')

    return render(request, 'modules/parent_accompaniment_list.html', {
        'records': records, 'years': years,
        'wilaya_filter': wilaya_filter, 'year_filter': year_filter, 'wilayas': WILAYAS,
    })


@login_required
def parent_accompaniment_create(request):
    if request.method == 'POST':
        try:
            record = ParentAccompanimentUnit(
                wilaya = request.POST.get('wilaya'),
                year   = request.POST.get('year', 2026),
                learning_disabilities_cases = request.POST.get('learning_disabilities_cases', 0) or 0,
                is_active = request.POST.get('is_active') == 'on',
                
                # Staff
                staff_legal = request.POST.get('staff_legal', 0) or 0,
                staff_psychology = request.POST.get('staff_psychology', 0) or 0,
                staff_health = request.POST.get('staff_health', 0) or 0,
                staff_admin = request.POST.get('staff_admin', 0) or 0,
                staff_educator = request.POST.get('staff_educator', 0) or 0,
                staff_other_desc = request.POST.get('staff_other_desc', '').strip(),
                staff_other_count = request.POST.get('staff_other_count', 0) or 0,

                # Beneficiaries
                beneficiaries_female = request.POST.get('beneficiaries_female', 0) or 0,
                beneficiaries_male = request.POST.get('beneficiaries_male', 0) or 0,

                # Credits
                previous_credits_committed  = request.POST.get('previous_credits_committed', 0) or 0,
                previous_credits_paid       = request.POST.get('previous_credits_paid', 0) or 0,
                current_credits_committed   = request.POST.get('current_credits_committed', 0) or 0,
                current_credits_paid        = request.POST.get('current_credits_paid', 0) or 0,
                total_credits_committed     = request.POST.get('total_credits_committed', 0) or 0,
                total_credits_paid          = request.POST.get('total_credits_paid', 0) or 0,
                consumption_rate_committed  = request.POST.get('consumption_rate_committed', 0) or 0,
                consumption_rate_paid       = request.POST.get('consumption_rate_paid', 0) or 0,
                remaining_credits_committed = request.POST.get('remaining_credits_committed', 0) or 0,
                remaining_credits_paid      = request.POST.get('remaining_credits_paid', 0) or 0,

                # Construction
                construction_start_year = request.POST.get('construction_start_year') or None,
                construction_total_credits = request.POST.get('construction_total_credits', 0) or 0,
                construction_progress = request.POST.get('construction_progress', 0) or 0,
                construction_delay_reasons = request.POST.get('construction_delay_reasons', '').strip(),
                actual_operation_start_year = request.POST.get('actual_operation_start_year') or None,

                created_by = request.user,
            )
            record.save()
            messages.success(request, "✅ تم إضافة السجل بنجاح")
            return redirect('parent_accompaniment_list')
        except Exception as e:
            messages.error(request, f"❌ خطأ : {e}")

    return render(request, 'modules/parent_accompaniment_form.html', {
        'mode': 'create', 'wilayas': WILAYAS,
    })


@login_required
def parent_accompaniment_update(request, pk):
    record = get_object_or_404(ParentAccompanimentUnit, pk=pk)
    
    if request.method == 'POST':
        try:
            record.wilaya = request.POST.get('wilaya')
            record.year   = request.POST.get('year', 2026)
            record.learning_disabilities_cases = request.POST.get('learning_disabilities_cases', 0) or 0
            record.is_active = request.POST.get('is_active') == 'on'
            
            # Staff
            record.staff_legal = request.POST.get('staff_legal', 0) or 0
            record.staff_psychology = request.POST.get('staff_psychology', 0) or 0
            record.staff_health = request.POST.get('staff_health', 0) or 0
            record.staff_admin = request.POST.get('staff_admin', 0) or 0
            record.staff_educator = request.POST.get('staff_educator', 0) or 0
            record.staff_other_desc = request.POST.get('staff_other_desc', '').strip()
            record.staff_other_count = request.POST.get('staff_other_count', 0) or 0

            # Beneficiaries
            record.beneficiaries_female = request.POST.get('beneficiaries_female', 0) or 0
            record.beneficiaries_male = request.POST.get('beneficiaries_male', 0) or 0

            # Credits
            record.previous_credits_committed  = request.POST.get('previous_credits_committed', 0) or 0
            record.previous_credits_paid       = request.POST.get('previous_credits_paid', 0) or 0
            record.current_credits_committed   = request.POST.get('current_credits_committed', 0) or 0
            record.current_credits_paid        = request.POST.get('current_credits_paid', 0) or 0
            record.total_credits_committed     = request.POST.get('total_credits_committed', 0) or 0
            record.total_credits_paid          = request.POST.get('total_credits_paid', 0) or 0
            record.consumption_rate_committed  = request.POST.get('consumption_rate_committed', 0) or 0
            record.consumption_rate_paid       = request.POST.get('consumption_rate_paid', 0) or 0
            record.remaining_credits_committed = request.POST.get('remaining_credits_committed', 0) or 0
            record.remaining_credits_paid      = request.POST.get('remaining_credits_paid', 0) or 0

            # Construction
            record.construction_start_year = request.POST.get('construction_start_year') or None
            record.construction_total_credits = request.POST.get('construction_total_credits', 0) or 0
            record.construction_progress = request.POST.get('construction_progress', 0) or 0
            record.construction_delay_reasons = request.POST.get('construction_delay_reasons', '').strip()
            record.actual_operation_start_year = request.POST.get('actual_operation_start_year') or None
            
            record.save()
            messages.success(request, "✅ تم تحديث السجل بنجاح")
            return redirect('parent_accompaniment_list')
        except Exception as e:
            messages.error(request, f"❌ خطأ : {e}")

    return render(request, 'modules/parent_accompaniment_form.html', {
        'mode': 'update', 'record': record, 'wilayas': WILAYAS,
    })


@login_required
def parent_accompaniment_delete(request, pk):
    record = get_object_or_404(ParentAccompanimentUnit, pk=pk)
    if request.method == 'POST':
        record.delete()
        messages.success(request, "🗑️ تم حذف السجل")
        return redirect('parent_accompaniment_list')
    return render(request, 'modules/parent_accompaniment_confirm_delete.html', {'record': record})


# =====================================================
# نوادي أطفال (CRUD)
# =====================================================

@login_required
def children_club_list(request):
    records = ChildrenClub.objects.all()
    
    wilaya_filter = request.GET.get('wilaya', '')
    year_filter   = request.GET.get('year', '')

    if wilaya_filter: records = records.filter(wilaya=wilaya_filter)
    if year_filter: records = records.filter(year=year_filter)

    years = ChildrenClub.objects.values_list('year', flat=True).distinct().order_by('-year')

    return render(request, 'modules/children_club_list.html', {
        'records': records, 'years': years,
        'wilaya_filter': wilaya_filter, 'year_filter': year_filter, 'wilayas': WILAYAS,
    })


@login_required
def children_club_create(request):
    if request.method == 'POST':
        try:
            record = ChildrenClub(
                wilaya = request.POST.get('wilaya'),
                year   = request.POST.get('year', 2026),
                is_active = request.POST.get('is_active') == 'on',
                
                # Staff
                staff_manager = request.POST.get('staff_manager', 0) or 0,
                staff_educator = request.POST.get('staff_educator', 0) or 0,
                staff_youth_teacher = request.POST.get('staff_youth_teacher', 0) or 0,
                staff_childhood = request.POST.get('staff_childhood', 0) or 0,
                staff_other_desc = request.POST.get('staff_other_desc', '').strip(),
                staff_other_count = request.POST.get('staff_other_count', 0) or 0,

                # Beneficiaries
                beneficiaries_female = request.POST.get('beneficiaries_female', 0) or 0,
                beneficiaries_male = request.POST.get('beneficiaries_male', 0) or 0,

                # Credits
                previous_credits_committed  = request.POST.get('previous_credits_committed', 0) or 0,
                previous_credits_paid       = request.POST.get('previous_credits_paid', 0) or 0,
                current_credits_committed   = request.POST.get('current_credits_committed', 0) or 0,
                current_credits_paid        = request.POST.get('current_credits_paid', 0) or 0,
                total_credits_committed     = request.POST.get('total_credits_committed', 0) or 0,
                total_credits_paid          = request.POST.get('total_credits_paid', 0) or 0,
                consumption_rate_committed  = request.POST.get('consumption_rate_committed', 0) or 0,
                consumption_rate_paid       = request.POST.get('consumption_rate_paid', 0) or 0,
                remaining_credits_committed = request.POST.get('remaining_credits_committed', 0) or 0,
                remaining_credits_paid      = request.POST.get('remaining_credits_paid', 0) or 0,

                # Construction
                construction_start_year = request.POST.get('construction_start_year') or None,
                construction_total_credits = request.POST.get('construction_total_credits', 0) or 0,
                construction_progress = request.POST.get('construction_progress', 0) or 0,
                construction_delay_reasons = request.POST.get('construction_delay_reasons', '').strip(),
                actual_operation_start_year = request.POST.get('actual_operation_start_year') or None,

                created_by = request.user,
            )
            record.save()
            messages.success(request, "✅ تم إضافة السجل بنجاح")
            return redirect('children_club_list')
        except Exception as e:
            messages.error(request, f"❌ خطأ : {e}")

    return render(request, 'modules/children_club_form.html', {
        'mode': 'create', 'wilayas': WILAYAS,
    })


@login_required
def children_club_update(request, pk):
    record = get_object_or_404(ChildrenClub, pk=pk)
    
    if request.method == 'POST':
        try:
            record.wilaya = request.POST.get('wilaya')
            record.year   = request.POST.get('year', 2026)
            record.is_active = request.POST.get('is_active') == 'on'
            
            # Staff
            record.staff_manager = request.POST.get('staff_manager', 0) or 0
            record.staff_educator = request.POST.get('staff_educator', 0) or 0
            record.staff_youth_teacher = request.POST.get('staff_youth_teacher', 0) or 0
            record.staff_childhood = request.POST.get('staff_childhood', 0) or 0
            record.staff_other_desc = request.POST.get('staff_other_desc', '').strip()
            record.staff_other_count = request.POST.get('staff_other_count', 0) or 0

            # Beneficiaries
            record.beneficiaries_female = request.POST.get('beneficiaries_female', 0) or 0
            record.beneficiaries_male = request.POST.get('beneficiaries_male', 0) or 0

            # Credits
            record.previous_credits_committed  = request.POST.get('previous_credits_committed', 0) or 0
            record.previous_credits_paid       = request.POST.get('previous_credits_paid', 0) or 0
            record.current_credits_committed   = request.POST.get('current_credits_committed', 0) or 0
            record.current_credits_paid        = request.POST.get('current_credits_paid', 0) or 0
            record.total_credits_committed     = request.POST.get('total_credits_committed', 0) or 0
            record.total_credits_paid          = request.POST.get('total_credits_paid', 0) or 0
            record.consumption_rate_committed  = request.POST.get('consumption_rate_committed', 0) or 0
            record.consumption_rate_paid       = request.POST.get('consumption_rate_paid', 0) or 0
            record.remaining_credits_committed = request.POST.get('remaining_credits_committed', 0) or 0
            record.remaining_credits_paid      = request.POST.get('remaining_credits_paid', 0) or 0

            # Construction
            record.construction_start_year = request.POST.get('construction_start_year') or None
            record.construction_total_credits = request.POST.get('construction_total_credits', 0) or 0
            record.construction_progress = request.POST.get('construction_progress', 0) or 0
            record.construction_delay_reasons = request.POST.get('construction_delay_reasons', '').strip()
            record.actual_operation_start_year = request.POST.get('actual_operation_start_year') or None
            
            record.save()
            messages.success(request, "✅ تم تحديث السجل بنجاح")
            return redirect('children_club_list')
        except Exception as e:
            messages.error(request, f"❌ خطأ : {e}")

    return render(request, 'modules/children_club_form.html', {
        'mode': 'update', 'record': record, 'wilayas': WILAYAS,
    })


@login_required
def children_club_delete(request, pk):
    record = get_object_or_404(ChildrenClub, pk=pk)
    if request.method == 'POST':
        record.delete()
        messages.success(request, "🗑️ تم حذف السجل")
        return redirect('children_club_list')
    return render(request, 'modules/children_club_confirm_delete.html', {'record': record})


# =====================================================
# المراكز المندمجة (CRUD)
# =====================================================

@login_required
def integrated_center_list(request):
    records = IntegratedCenter.objects.all()
    
    wilaya_filter = request.GET.get('wilaya', '')
    year_filter   = request.GET.get('year', '')

    if wilaya_filter: records = records.filter(wilaya=wilaya_filter)
    if year_filter: records = records.filter(year=year_filter)

    years = IntegratedCenter.objects.values_list('year', flat=True).distinct().order_by('-year')

    return render(request, 'modules/integrated_center_list.html', {
        'records': records, 'years': years,
        'wilaya_filter': wilaya_filter, 'year_filter': year_filter, 'wilayas': WILAYAS,
    })


@login_required
def integrated_center_create(request):
    if request.method == 'POST':
        try:
            record = IntegratedCenter(
                wilaya = request.POST.get('wilaya'),
                year   = request.POST.get('year', 2026),
                is_active = request.POST.get('is_active') == 'on',
                
                # Staff
                staff_manager = request.POST.get('staff_manager', 0) or 0,
                staff_educator = request.POST.get('staff_educator', 0) or 0,
                staff_youth_teacher = request.POST.get('staff_youth_teacher', 0) or 0,
                staff_childhood = request.POST.get('staff_childhood', 0) or 0,
                staff_other_desc = request.POST.get('staff_other_desc', '').strip(),
                staff_other_count = request.POST.get('staff_other_count', 0) or 0,

                # Beneficiaries
                beneficiaries_female = request.POST.get('beneficiaries_female', 0) or 0,
                beneficiaries_male = request.POST.get('beneficiaries_male', 0) or 0,

                # Credits
                previous_credits_committed  = request.POST.get('previous_credits_committed', 0) or 0,
                previous_credits_paid       = request.POST.get('previous_credits_paid', 0) or 0,
                current_credits_committed   = request.POST.get('current_credits_committed', 0) or 0,
                current_credits_paid        = request.POST.get('current_credits_paid', 0) or 0,
                total_credits_committed     = request.POST.get('total_credits_committed', 0) or 0,
                total_credits_paid          = request.POST.get('total_credits_paid', 0) or 0,
                consumption_rate_committed  = request.POST.get('consumption_rate_committed', 0) or 0,
                consumption_rate_paid       = request.POST.get('consumption_rate_paid', 0) or 0,
                remaining_credits_committed = request.POST.get('remaining_credits_committed', 0) or 0,
                remaining_credits_paid      = request.POST.get('remaining_credits_paid', 0) or 0,

                # Construction
                construction_start_year = request.POST.get('construction_start_year') or None,
                construction_total_credits = request.POST.get('construction_total_credits', 0) or 0,
                construction_progress = request.POST.get('construction_progress', 0) or 0,
                construction_delay_reasons = request.POST.get('construction_delay_reasons', '').strip(),
                actual_operation_start_year = request.POST.get('actual_operation_start_year') or None,

                created_by = request.user,
            )
            record.save()
            messages.success(request, "✅ تم إضافة السجل بنجاح")
            return redirect('integrated_center_list')
        except Exception as e:
            messages.error(request, f"❌ خطأ : {e}")

    return render(request, 'modules/integrated_center_form.html', {
        'mode': 'create', 'wilayas': WILAYAS,
    })


@login_required
def integrated_center_update(request, pk):
    record = get_object_or_404(IntegratedCenter, pk=pk)
    
    if request.method == 'POST':
        try:
            record.wilaya = request.POST.get('wilaya')
            record.year   = request.POST.get('year', 2026)
            record.is_active = request.POST.get('is_active') == 'on'
            
            # Staff
            record.staff_manager = request.POST.get('staff_manager', 0) or 0
            record.staff_educator = request.POST.get('staff_educator', 0) or 0
            record.staff_youth_teacher = request.POST.get('staff_youth_teacher', 0) or 0
            record.staff_childhood = request.POST.get('staff_childhood', 0) or 0
            record.staff_other_desc = request.POST.get('staff_other_desc', '').strip()
            record.staff_other_count = request.POST.get('staff_other_count', 0) or 0

            # Beneficiaries
            record.beneficiaries_female = request.POST.get('beneficiaries_female', 0) or 0
            record.beneficiaries_male = request.POST.get('beneficiaries_male', 0) or 0

            # Credits
            record.previous_credits_committed  = request.POST.get('previous_credits_committed', 0) or 0
            record.previous_credits_paid       = request.POST.get('previous_credits_paid', 0) or 0
            record.current_credits_committed   = request.POST.get('current_credits_committed', 0) or 0
            record.current_credits_paid        = request.POST.get('current_credits_paid', 0) or 0
            record.total_credits_committed     = request.POST.get('total_credits_committed', 0) or 0
            record.total_credits_paid          = request.POST.get('total_credits_paid', 0) or 0
            record.consumption_rate_committed  = request.POST.get('consumption_rate_committed', 0) or 0
            record.consumption_rate_paid       = request.POST.get('consumption_rate_paid', 0) or 0
            record.remaining_credits_committed = request.POST.get('remaining_credits_committed', 0) or 0
            record.remaining_credits_paid      = request.POST.get('remaining_credits_paid', 0) or 0

            # Construction
            record.construction_start_year = request.POST.get('construction_start_year') or None
            record.construction_total_credits = request.POST.get('construction_total_credits', 0) or 0
            record.construction_progress = request.POST.get('construction_progress', 0) or 0
            record.construction_delay_reasons = request.POST.get('construction_delay_reasons', '').strip()
            record.actual_operation_start_year = request.POST.get('actual_operation_start_year') or None
            
            record.save()
            messages.success(request, "✅ تم تحديث السجل بنجاح")
            return redirect('integrated_center_list')
        except Exception as e:
            messages.error(request, f"❌ خطأ : {e}")

    return render(request, 'modules/integrated_center_form.html', {
        'mode': 'update', 'record': record, 'wilayas': WILAYAS,
    })


@login_required
def integrated_center_delete(request, pk):
    record = get_object_or_404(IntegratedCenter, pk=pk)
    if request.method == 'POST':
        record.delete()
        messages.success(request, "🗑️ تم حذف السجل")
        return redirect('integrated_center_list')
    return render(request, 'modules/integrated_center_confirm_delete.html', {'record': record})


# =====================================================
# مراكز المسنين (CRUD)
# =====================================================

@login_required
def elderly_center_list(request):
    records = ElderlyCenter.objects.all()
    
    wilaya_filter = request.GET.get('wilaya', '')
    year_filter   = request.GET.get('year', '')

    if wilaya_filter: records = records.filter(wilaya=wilaya_filter)
    if year_filter: records = records.filter(year=year_filter)

    years = ElderlyCenter.objects.values_list('year', flat=True).distinct().order_by('-year')

    return render(request, 'modules/elderly_center_list.html', {
        'records': records, 'years': years,
        'wilaya_filter': wilaya_filter, 'year_filter': year_filter, 'wilayas': WILAYAS,
    })


@login_required
def elderly_center_create(request):
    if request.method == 'POST':
        try:
            record = ElderlyCenter(
                wilaya = request.POST.get('wilaya'),
                year   = request.POST.get('year', 2026),
                is_active = request.POST.get('is_active') == 'on',
                
                # Staff
                staff_manager = request.POST.get('staff_manager', 0) or 0,
                staff_life_assistant = request.POST.get('staff_life_assistant', 0) or 0,
                staff_health_assistant = request.POST.get('staff_health_assistant', 0) or 0,

                # Beneficiaries
                beneficiaries_female = request.POST.get('beneficiaries_female', 0) or 0,
                beneficiaries_male = request.POST.get('beneficiaries_male', 0) or 0,

                # Credits
                previous_credits_committed  = request.POST.get('previous_credits_committed', 0) or 0,
                previous_credits_paid       = request.POST.get('previous_credits_paid', 0) or 0,
                current_credits_committed   = request.POST.get('current_credits_committed', 0) or 0,
                current_credits_paid        = request.POST.get('current_credits_paid', 0) or 0,
                total_credits_committed     = request.POST.get('total_credits_committed', 0) or 0,
                total_credits_paid          = request.POST.get('total_credits_paid', 0) or 0,
                consumption_rate_committed  = request.POST.get('consumption_rate_committed', 0) or 0,
                consumption_rate_paid       = request.POST.get('consumption_rate_paid', 0) or 0,
                remaining_credits_committed = request.POST.get('remaining_credits_committed', 0) or 0,
                remaining_credits_paid      = request.POST.get('remaining_credits_paid', 0) or 0,

                # Construction
                construction_start_year = request.POST.get('construction_start_year') or None,
                construction_duration = request.POST.get('construction_duration', '').strip(),
                construction_total_cost = request.POST.get('construction_total_cost', 0) or 0,
                construction_progress = request.POST.get('construction_progress', 0) or 0,
                construction_delay_reasons = request.POST.get('construction_delay_reasons', '').strip(),
                actual_operation_start_year = request.POST.get('actual_operation_start_year') or None,
                difficulties_obstacles = request.POST.get('difficulties_obstacles', '').strip(),

                created_by = request.user,
            )
            record.save()
            messages.success(request, "✅ تم إضافة السجل بنجاح")
            return redirect('elderly_center_list')
        except Exception as e:
            messages.error(request, f"❌ خطأ : {e}")

    return render(request, 'modules/elderly_center_form.html', {
        'mode': 'create', 'wilayas': WILAYAS,
    })


@login_required
def elderly_center_update(request, pk):
    record = get_object_or_404(ElderlyCenter, pk=pk)
    
    if request.method == 'POST':
        try:
            record.wilaya = request.POST.get('wilaya')
            record.year   = request.POST.get('year', 2026)
            record.is_active = request.POST.get('is_active') == 'on'
            
            # Staff
            record.staff_manager = request.POST.get('staff_manager', 0) or 0
            record.staff_life_assistant = request.POST.get('staff_life_assistant', 0) or 0
            record.staff_health_assistant = request.POST.get('staff_health_assistant', 0) or 0

            # Beneficiaries
            record.beneficiaries_female = request.POST.get('beneficiaries_female', 0) or 0
            record.beneficiaries_male = request.POST.get('beneficiaries_male', 0) or 0

            # Credits
            record.previous_credits_committed  = request.POST.get('previous_credits_committed', 0) or 0
            record.previous_credits_paid       = request.POST.get('previous_credits_paid', 0) or 0
            record.current_credits_committed   = request.POST.get('current_credits_committed', 0) or 0
            record.current_credits_paid        = request.POST.get('current_credits_paid', 0) or 0
            record.total_credits_committed     = request.POST.get('total_credits_committed', 0) or 0
            record.total_credits_paid          = request.POST.get('total_credits_paid', 0) or 0
            record.consumption_rate_committed  = request.POST.get('consumption_rate_committed', 0) or 0
            record.consumption_rate_paid       = request.POST.get('consumption_rate_paid', 0) or 0
            record.remaining_credits_committed = request.POST.get('remaining_credits_committed', 0) or 0
            record.remaining_credits_paid      = request.POST.get('remaining_credits_paid', 0) or 0

            # Construction
            record.construction_start_year = request.POST.get('construction_start_year') or None
            record.construction_duration = request.POST.get('construction_duration', '').strip()
            record.construction_total_cost = request.POST.get('construction_total_cost', 0) or 0
            record.construction_progress = request.POST.get('construction_progress', 0) or 0
            record.construction_delay_reasons = request.POST.get('construction_delay_reasons', '').strip()
            record.actual_operation_start_year = request.POST.get('actual_operation_start_year') or None
            record.difficulties_obstacles = request.POST.get('difficulties_obstacles', '').strip()
            
            record.save()
            messages.success(request, "✅ تم تحديث السجل بنجاح")
            return redirect('elderly_center_list')
        except Exception as e:
            messages.error(request, f"❌ خطأ : {e}")

    return render(request, 'modules/elderly_center_form.html', {
        'mode': 'update', 'record': record, 'wilayas': WILAYAS,
    })


@login_required
def elderly_center_delete(request, pk):
    record = get_object_or_404(ElderlyCenter, pk=pk)
    if request.method == 'POST':
        record.delete()
        messages.success(request, "🗑️ تم حذف السجل")
        return redirect('elderly_center_list')
    return render(request, 'modules/elderly_center_confirm_delete.html', {'record': record})



# =====================================================
# النوادي النهارية (CRUD)
# =====================================================

@login_required
def day_club_list(request):
    records = DayClub.objects.all()
    
    wilaya_filter = request.GET.get('wilaya', '')
    year_filter   = request.GET.get('year', '')

    if wilaya_filter: records = records.filter(wilaya=wilaya_filter)
    if year_filter: records = records.filter(year=year_filter)

    years = DayClub.objects.values_list('year', flat=True).distinct().order_by('-year')

    return render(request, 'modules/day_club_list.html', {
        'records': records, 'years': years,
        'wilaya_filter': wilaya_filter, 'year_filter': year_filter, 'wilayas': WILAYAS,
    })


@login_required
def day_club_create(request):
    if request.method == 'POST':
        try:
            record = DayClub(
                wilaya = request.POST.get('wilaya'),
                year   = request.POST.get('year', 2026),
                is_active = request.POST.get('is_active') == 'on',
                
                # Staff
                staff_manager = request.POST.get('staff_manager', 0) or 0,
                staff_life_assistant = request.POST.get('staff_life_assistant', 0) or 0,
                staff_health_assistant = request.POST.get('staff_health_assistant', 0) or 0,

                # Beneficiaries
                beneficiaries_female = request.POST.get('beneficiaries_female', 0) or 0,
                beneficiaries_male = request.POST.get('beneficiaries_male', 0) or 0,

                # Credits
                previous_credits_committed  = request.POST.get('previous_credits_committed', 0) or 0,
                previous_credits_paid       = request.POST.get('previous_credits_paid', 0) or 0,
                current_credits_committed   = request.POST.get('current_credits_committed', 0) or 0,
                current_credits_paid        = request.POST.get('current_credits_paid', 0) or 0,
                total_credits_committed     = request.POST.get('total_credits_committed', 0) or 0,
                total_credits_paid          = request.POST.get('total_credits_paid', 0) or 0,
                consumption_rate_committed  = request.POST.get('consumption_rate_committed', 0) or 0,
                consumption_rate_paid       = request.POST.get('consumption_rate_paid', 0) or 0,
                remaining_credits_committed = request.POST.get('remaining_credits_committed', 0) or 0,
                remaining_credits_paid      = request.POST.get('remaining_credits_paid', 0) or 0,

                # Construction
                construction_start_year = request.POST.get('construction_start_year') or None,
                construction_duration = request.POST.get('construction_duration', '').strip(),
                construction_total_cost = request.POST.get('construction_total_cost', 0) or 0,
                construction_progress = request.POST.get('construction_progress', 0) or 0,
                construction_delay_reasons = request.POST.get('construction_delay_reasons', '').strip(),
                actual_operation_start_year = request.POST.get('actual_operation_start_year') or None,
                difficulties_obstacles = request.POST.get('difficulties_obstacles', '').strip(),

                created_by = request.user,
            )
            record.save()
            messages.success(request, "✅ تم إضافة السجل بنجاح")
            return redirect('day_club_list')
        except Exception as e:
            messages.error(request, f"❌ خطأ : {e}")

    return render(request, 'modules/day_club_form.html', {
        'mode': 'create', 'wilayas': WILAYAS,
    })


@login_required
def day_club_update(request, pk):
    record = get_object_or_404(DayClub, pk=pk)
    
    if request.method == 'POST':
        try:
            record.wilaya = request.POST.get('wilaya')
            record.year   = request.POST.get('year', 2026)
            record.is_active = request.POST.get('is_active') == 'on'
            
            # Staff
            record.staff_manager = request.POST.get('staff_manager', 0) or 0
            record.staff_life_assistant = request.POST.get('staff_life_assistant', 0) or 0
            record.staff_health_assistant = request.POST.get('staff_health_assistant', 0) or 0

            # Beneficiaries
            record.beneficiaries_female = request.POST.get('beneficiaries_female', 0) or 0
            record.beneficiaries_male = request.POST.get('beneficiaries_male', 0) or 0

            # Credits
            record.previous_credits_committed  = request.POST.get('previous_credits_committed', 0) or 0
            record.previous_credits_paid       = request.POST.get('previous_credits_paid', 0) or 0
            record.current_credits_committed   = request.POST.get('current_credits_committed', 0) or 0
            record.current_credits_paid        = request.POST.get('current_credits_paid', 0) or 0
            record.total_credits_committed     = request.POST.get('total_credits_committed', 0) or 0
            record.total_credits_paid          = request.POST.get('total_credits_paid', 0) or 0
            record.consumption_rate_committed  = request.POST.get('consumption_rate_committed', 0) or 0
            record.consumption_rate_paid       = request.POST.get('consumption_rate_paid', 0) or 0
            record.remaining_credits_committed = request.POST.get('remaining_credits_committed', 0) or 0
            record.remaining_credits_paid      = request.POST.get('remaining_credits_paid', 0) or 0

            # Construction
            record.construction_start_year = request.POST.get('construction_start_year') or None
            record.construction_duration = request.POST.get('construction_duration', '').strip()
            record.construction_total_cost = request.POST.get('construction_total_cost', 0) or 0
            record.construction_progress = request.POST.get('construction_progress', 0) or 0
            record.construction_delay_reasons = request.POST.get('construction_delay_reasons', '').strip()
            record.actual_operation_start_year = request.POST.get('actual_operation_start_year') or None
            record.difficulties_obstacles = request.POST.get('difficulties_obstacles', '').strip()
            
            record.save()
            messages.success(request, "✅ تم تحديث السجل بنجاح")
            return redirect('day_club_list')
        except Exception as e:
            messages.error(request, f"❌ خطأ : {e}")

    return render(request, 'modules/day_club_form.html', {
        'mode': 'update', 'record': record, 'wilayas': WILAYAS,
    })


@login_required
def day_club_delete(request, pk):
    record = get_object_or_404(DayClub, pk=pk)
    if request.method == 'POST':
        record.delete()
        messages.success(request, "🗑️ تم حذف السجل")
        return redirect('day_club_list')
    return render(request, 'modules/day_club_confirm_delete.html', {'record': record})


# =====================================================
# مركبات الطفولة (CRUD)
# =====================================================

@login_required
def childhood_complex_list(request):
    records = ChildhoodComplex.objects.all()
    
    wilaya_filter = request.GET.get('wilaya', '')
    year_filter   = request.GET.get('year', '')

    if wilaya_filter: records = records.filter(wilaya=wilaya_filter)
    if year_filter: records = records.filter(year=year_filter)

    years = ChildhoodComplex.objects.values_list('year', flat=True).distinct().order_by('-year')

    return render(request, 'modules/childhood_complex_list.html', {
        'records': records, 'years': years,
        'wilaya_filter': wilaya_filter, 'year_filter': year_filter, 'wilayas': WILAYAS,
    })


@login_required
def childhood_complex_create(request):
    if request.method == 'POST':
        try:
            record = ChildhoodComplex(
                wilaya = request.POST.get('wilaya'),
                year   = request.POST.get('year', 2026),
                is_active = request.POST.get('is_active') == 'on',
                
                # Staff
                staff_manager = request.POST.get('staff_manager', 0) or 0,
                staff_educator = request.POST.get('staff_educator', 0) or 0,
                staff_youth_teacher = request.POST.get('staff_youth_teacher', 0) or 0,
                staff_childhood = request.POST.get('staff_childhood', 0) or 0,
                staff_other_desc = request.POST.get('staff_other_desc', '').strip(),
                staff_other_count = request.POST.get('staff_other_count', 0) or 0,

                # Beneficiaries
                beneficiaries_female = request.POST.get('beneficiaries_female', 0) or 0,
                beneficiaries_male = request.POST.get('beneficiaries_male', 0) or 0,

                # Credits
                previous_credits_committed  = request.POST.get('previous_credits_committed', 0) or 0,
                previous_credits_paid       = request.POST.get('previous_credits_paid', 0) or 0,
                current_credits_committed   = request.POST.get('current_credits_committed', 0) or 0,
                current_credits_paid        = request.POST.get('current_credits_paid', 0) or 0,
                total_credits_committed     = request.POST.get('total_credits_committed', 0) or 0,
                total_credits_paid          = request.POST.get('total_credits_paid', 0) or 0,
                consumption_rate_committed  = request.POST.get('consumption_rate_committed', 0) or 0,
                consumption_rate_paid       = request.POST.get('consumption_rate_paid', 0) or 0,
                remaining_credits_committed = request.POST.get('remaining_credits_committed', 0) or 0,
                remaining_credits_paid      = request.POST.get('remaining_credits_paid', 0) or 0,

                # Construction
                construction_start_year = request.POST.get('construction_start_year') or None,
                construction_duration = request.POST.get('construction_duration', '').strip(),
                construction_total_cost = request.POST.get('construction_total_cost', 0) or 0,
                construction_progress = request.POST.get('construction_progress', 0) or 0,
                construction_delay_reasons = request.POST.get('construction_delay_reasons', '').strip(),
                actual_operation_start_year = request.POST.get('actual_operation_start_year') or None,
                difficulties_obstacles = request.POST.get('difficulties_obstacles', '').strip(),

                created_by = request.user,
            )
            record.save()
            messages.success(request, "✅ تم إضافة السجل بنجاح")
            return redirect('childhood_complex_list')
        except Exception as e:
            messages.error(request, f"❌ خطأ : {e}")

    return render(request, 'modules/childhood_complex_form.html', {
        'mode': 'create', 'wilayas': WILAYAS,
    })


@login_required
def childhood_complex_update(request, pk):
    record = get_object_or_404(ChildhoodComplex, pk=pk)
    
    if request.method == 'POST':
        try:
            record.wilaya = request.POST.get('wilaya')
            record.year   = request.POST.get('year', 2026)
            record.is_active = request.POST.get('is_active') == 'on'
            
            # Staff
            record.staff_manager = request.POST.get('staff_manager', 0) or 0
            record.staff_educator = request.POST.get('staff_educator', 0) or 0
            record.staff_youth_teacher = request.POST.get('staff_youth_teacher', 0) or 0
            record.staff_childhood = request.POST.get('staff_childhood', 0) or 0
            record.staff_other_desc = request.POST.get('staff_other_desc', '').strip()
            record.staff_other_count = request.POST.get('staff_other_count', 0) or 0

            # Beneficiaries
            record.beneficiaries_female = request.POST.get('beneficiaries_female', 0) or 0
            record.beneficiaries_male = request.POST.get('beneficiaries_male', 0) or 0

            # Credits
            record.previous_credits_committed  = request.POST.get('previous_credits_committed', 0) or 0
            record.previous_credits_paid       = request.POST.get('previous_credits_paid', 0) or 0
            record.current_credits_committed   = request.POST.get('current_credits_committed', 0) or 0
            record.current_credits_paid        = request.POST.get('current_credits_paid', 0) or 0
            record.total_credits_committed     = request.POST.get('total_credits_committed', 0) or 0
            record.total_credits_paid          = request.POST.get('total_credits_paid', 0) or 0
            record.consumption_rate_committed  = request.POST.get('consumption_rate_committed', 0) or 0
            record.consumption_rate_paid       = request.POST.get('consumption_rate_paid', 0) or 0
            record.remaining_credits_committed = request.POST.get('remaining_credits_committed', 0) or 0
            record.remaining_credits_paid      = request.POST.get('remaining_credits_paid', 0) or 0

            # Construction
            record.construction_start_year = request.POST.get('construction_start_year') or None
            record.construction_duration = request.POST.get('construction_duration', '').strip()
            record.construction_total_cost = request.POST.get('construction_total_cost', 0) or 0
            record.construction_progress = request.POST.get('construction_progress', 0) or 0
            record.construction_delay_reasons = request.POST.get('construction_delay_reasons', '').strip()
            record.actual_operation_start_year = request.POST.get('actual_operation_start_year') or None
            record.difficulties_obstacles = request.POST.get('difficulties_obstacles', '').strip()
            
            record.save()
            messages.success(request, "✅ تم تحديث السجل بنجاح")
            return redirect('childhood_complex_list')
        except Exception as e:
            messages.error(request, f"❌ خطأ : {e}")

    return render(request, 'modules/childhood_complex_form.html', {
        'mode': 'update', 'record': record, 'wilayas': WILAYAS,
    })


@login_required
def childhood_complex_delete(request, pk):
    record = get_object_or_404(ChildhoodComplex, pk=pk)
    if request.method == 'POST':
        record.delete()
        messages.success(request, "🗑️ تم حذف السجل")
        return redirect('childhood_complex_list')
    return render(request, 'modules/childhood_complex_confirm_delete.html', {'record': record})


# =====================================================
# مراكز الإعلامية الموجهة للطفل (CRUD)
# =====================================================

@login_required
def child_it_center_list(request):
    records = ChildItCenter.objects.all()
    
    wilaya_filter = request.GET.get('wilaya', '')
    year_filter   = request.GET.get('year', '')

    if wilaya_filter: records = records.filter(wilaya=wilaya_filter)
    if year_filter: records = records.filter(year=year_filter)

    years = ChildItCenter.objects.values_list('year', flat=True).distinct().order_by('-year')

    return render(request, 'modules/child_it_center_list.html', {
        'records': records, 'years': years,
        'wilaya_filter': wilaya_filter, 'year_filter': year_filter, 'wilayas': WILAYAS,
    })


@login_required
def child_it_center_create(request):
    if request.method == 'POST':
        try:
            record = ChildItCenter(
                wilaya = request.POST.get('wilaya'),
                year   = request.POST.get('year', 2026),
                is_active = request.POST.get('is_active') == 'on',
                
                # Staff
                staff_manager = request.POST.get('staff_manager', 0) or 0,
                staff_life_assistant = request.POST.get('staff_life_assistant', 0) or 0,
                staff_health_assistant = request.POST.get('staff_health_assistant', 0) or 0,

                # Beneficiaries
                beneficiaries_female = request.POST.get('beneficiaries_female', 0) or 0,
                beneficiaries_male = request.POST.get('beneficiaries_male', 0) or 0,

                # Credits
                previous_credits_committed  = request.POST.get('previous_credits_committed', 0) or 0,
                previous_credits_paid       = request.POST.get('previous_credits_paid', 0) or 0,
                current_credits_committed   = request.POST.get('current_credits_committed', 0) or 0,
                current_credits_paid        = request.POST.get('current_credits_paid', 0) or 0,
                total_credits_committed     = request.POST.get('total_credits_committed', 0) or 0,
                total_credits_paid          = request.POST.get('total_credits_paid', 0) or 0,
                consumption_rate_committed  = request.POST.get('consumption_rate_committed', 0) or 0,
                consumption_rate_paid       = request.POST.get('consumption_rate_paid', 0) or 0,
                remaining_credits_committed = request.POST.get('remaining_credits_committed', 0) or 0,
                remaining_credits_paid      = request.POST.get('remaining_credits_paid', 0) or 0,

                # Construction
                construction_start_year = request.POST.get('construction_start_year') or None,
                construction_duration = request.POST.get('construction_duration', '').strip(),
                construction_total_cost = request.POST.get('construction_total_cost', 0) or 0,
                construction_progress = request.POST.get('construction_progress', 0) or 0,
                construction_delay_reasons = request.POST.get('construction_delay_reasons', '').strip(),
                actual_operation_start_year = request.POST.get('actual_operation_start_year') or None,
                difficulties_obstacles = request.POST.get('difficulties_obstacles', '').strip(),

                created_by = request.user,
            )
            record.save()
            messages.success(request, "✅ تم إضافة السجل بنجاح")
            return redirect('child_it_center_list')
        except Exception as e:
            messages.error(request, f"❌ خطأ : {e}")

    return render(request, 'modules/child_it_center_form.html', {
        'mode': 'create', 'wilayas': WILAYAS,
    })


@login_required
def child_it_center_update(request, pk):
    record = get_object_or_404(ChildItCenter, pk=pk)
    
    if request.method == 'POST':
        try:
            record.wilaya = request.POST.get('wilaya')
            record.year   = request.POST.get('year', 2026)
            record.is_active = request.POST.get('is_active') == 'on'
            
            # Staff
            record.staff_manager = request.POST.get('staff_manager', 0) or 0
            record.staff_life_assistant = request.POST.get('staff_life_assistant', 0) or 0
            record.staff_health_assistant = request.POST.get('staff_health_assistant', 0) or 0

            # Beneficiaries
            record.beneficiaries_female = request.POST.get('beneficiaries_female', 0) or 0
            record.beneficiaries_male = request.POST.get('beneficiaries_male', 0) or 0

            # Credits
            record.previous_credits_committed  = request.POST.get('previous_credits_committed', 0) or 0
            record.previous_credits_paid       = request.POST.get('previous_credits_paid', 0) or 0
            record.current_credits_committed   = request.POST.get('current_credits_committed', 0) or 0
            record.current_credits_paid        = request.POST.get('current_credits_paid', 0) or 0
            record.total_credits_committed     = request.POST.get('total_credits_committed', 0) or 0
            record.total_credits_paid          = request.POST.get('total_credits_paid', 0) or 0
            record.consumption_rate_committed  = request.POST.get('consumption_rate_committed', 0) or 0
            record.consumption_rate_paid       = request.POST.get('consumption_rate_paid', 0) or 0
            record.remaining_credits_committed = request.POST.get('remaining_credits_committed', 0) or 0
            record.remaining_credits_paid      = request.POST.get('remaining_credits_paid', 0) or 0

            # Construction
            record.construction_start_year = request.POST.get('construction_start_year') or None
            record.construction_duration = request.POST.get('construction_duration', '').strip()
            record.construction_total_cost = request.POST.get('construction_total_cost', 0) or 0
            record.construction_progress = request.POST.get('construction_progress', 0) or 0
            record.construction_delay_reasons = request.POST.get('construction_delay_reasons', '').strip()
            record.actual_operation_start_year = request.POST.get('actual_operation_start_year') or None
            record.difficulties_obstacles = request.POST.get('difficulties_obstacles', '').strip()
            
            record.save()
            messages.success(request, "✅ تم تحديث السجل بنجاح")
            return redirect('child_it_center_list')
        except Exception as e:
            messages.error(request, f"❌ خطأ : {e}")

    return render(request, 'modules/child_it_center_form.html', {
        'mode': 'update', 'record': record, 'wilayas': WILAYAS,
    })


@login_required
def child_it_center_delete(request, pk):
    record = get_object_or_404(ChildItCenter, pk=pk)
    if request.method == 'POST':
        record.delete()
        messages.success(request, "🗑️ تم حذف السجل")
        return redirect('child_it_center_list')
    return render(request, 'modules/child_it_center_confirm_delete.html', {'record': record})


# =====================================================
# روزنامة الأنشطة الأسبوعية (CRUD)
# =====================================================

@login_required
def weekly_activity_list(request):
    records = WeeklyActivity.objects.all()
    
    wilaya_filter = request.GET.get('wilaya', '')
    day_filter = request.GET.get('day', '')

    if wilaya_filter: records = records.filter(wilaya=wilaya_filter)
    if day_filter: records = records.filter(day=day_filter)

    return render(request, 'modules/weekly_activity_list.html', {
        'records': records,
        'wilaya_filter': wilaya_filter, 
        'day_filter': day_filter,
        'wilayas': WILAYAS,
        'days': WeeklyActivity.DAY_CHOICES,
    })


@login_required
def weekly_activity_create(request):
    if request.method == 'POST':
        try:
            record = WeeklyActivity(
                wilaya = request.POST.get('wilaya'),
                day = request.POST.get('day'),
                date = request.POST.get('date') or None,
                time = request.POST.get('time'),
                activity_name = request.POST.get('activity_name', '').strip(),
                target_audience = request.POST.get('target_audience', '').strip(),
                location = request.POST.get('location', '').strip(),
                notes = request.POST.get('notes', '').strip(),
                created_by = request.user,
            )
            record.save()
            messages.success(request, "✅ تم إضافة النشاط بنجاح")
            return redirect('weekly_activity_list')
        except Exception as e:
            messages.error(request, f"❌ خطأ : {e}")

    return render(request, 'modules/weekly_activity_form.html', {
        'mode': 'create', 
        'wilayas': WILAYAS,
        'days': WeeklyActivity.DAY_CHOICES,
    })


@login_required
def weekly_activity_update(request, pk):
    record = get_object_or_404(WeeklyActivity, pk=pk)
    
    if request.method == 'POST':
        try:
            record.wilaya = request.POST.get('wilaya')
            record.day = request.POST.get('day')
            record.date = request.POST.get('date') or None
            record.time = request.POST.get('time')
            record.activity_name = request.POST.get('activity_name', '').strip()
            record.target_audience = request.POST.get('target_audience', '').strip()
            record.location = request.POST.get('location', '').strip()
            record.notes = request.POST.get('notes', '').strip()
            
            record.save()
            messages.success(request, "✅ تم تحديث النشاط بنجاح")
            return redirect('weekly_activity_list')
        except Exception as e:
            messages.error(request, f"❌ خطأ : {e}")

    return render(request, 'modules/weekly_activity_form.html', {
        'mode': 'update', 
        'record': record, 
        'wilayas': WILAYAS,
        'days': WeeklyActivity.DAY_CHOICES,
    })


@login_required
def weekly_activity_delete(request, pk):
    record = get_object_or_404(WeeklyActivity, pk=pk)
    if request.method == 'POST':
        record.delete()
        messages.success(request, "🗑️ تم حذف النشاط")
        return redirect('weekly_activity_list')
    return render(request, 'modules/weekly_activity_confirm_delete.html', {'record': record})


# =====================================================
# الاجتماعات وجلسات العمل (CRUD)
# =====================================================

@login_required
def meeting_session_list(request):
    records = MeetingSession.objects.all()
    
    wilaya_filter = request.GET.get('wilaya', '')
    year_filter   = request.GET.get('year', '')

    if wilaya_filter: records = records.filter(wilaya=wilaya_filter)
    if year_filter: records = records.filter(year=year_filter)

    years = MeetingSession.objects.values_list('year', flat=True).distinct().order_by('-year')

    return render(request, 'modules/meeting_session_list.html', {
        'records': records, 'years': years,
        'wilaya_filter': wilaya_filter, 'year_filter': year_filter, 'wilayas': WILAYAS,
    })


@login_required
def meeting_session_create(request):
    if request.method == 'POST':
        try:
            record = MeetingSession(
                wilaya = request.POST.get('wilaya'),
                year   = request.POST.get('year', 2026),
                
                # Inside Delegation
                inside_delegation_staff = request.POST.get('inside_delegation_staff') == 'on',
                inside_delegation_committees = request.POST.get('inside_delegation_committees') == 'on',

                # Outside Delegation
                outside_delegation = request.POST.get('outside_delegation') == 'on',

                # Public Structure
                in_public_structure = request.POST.get('in_public_structure') == 'on',
                public_structure_name = request.POST.get('public_structure_name', '').strip(),
                public_structure_topic = request.POST.get('public_structure_topic', '').strip(),
                public_structure_date = request.POST.get('public_structure_date', '').strip(),

                # Presidency
                in_presidency = request.POST.get('in_presidency') == 'on',
                presidency_name = request.POST.get('presidency_name', '').strip(),
                presidency_topic = request.POST.get('presidency_topic', '').strip(),
                presidency_date = request.POST.get('presidency_date', '').strip(),

                created_by = request.user,
            )
            record.save()
            messages.success(request, "✅ تم إضافة السجل بنجاح")
            return redirect('meeting_session_list')
        except Exception as e:
            messages.error(request, f"❌ خطأ : {e}")

    return render(request, 'modules/meeting_session_form.html', {
        'mode': 'create', 'wilayas': WILAYAS,
    })


@login_required
def meeting_session_update(request, pk):
    record = get_object_or_404(MeetingSession, pk=pk)
    
    if request.method == 'POST':
        try:
            record.wilaya = request.POST.get('wilaya')
            record.year   = request.POST.get('year', 2026)
            
            # Inside Delegation
            record.inside_delegation_staff = request.POST.get('inside_delegation_staff') == 'on'
            record.inside_delegation_committees = request.POST.get('inside_delegation_committees') == 'on'

            # Outside Delegation
            record.outside_delegation = request.POST.get('outside_delegation') == 'on'

            # Public Structure
            record.in_public_structure = request.POST.get('in_public_structure') == 'on'
            record.public_structure_name = request.POST.get('public_structure_name', '').strip()
            record.public_structure_topic = request.POST.get('public_structure_topic', '').strip()
            record.public_structure_date = request.POST.get('public_structure_date', '').strip()

            # Presidency
            record.in_presidency = request.POST.get('in_presidency') == 'on'
            record.presidency_name = request.POST.get('presidency_name', '').strip()
            record.presidency_topic = request.POST.get('presidency_topic', '').strip()
            record.presidency_date = request.POST.get('presidency_date', '').strip()
            
            record.save()
            messages.success(request, "✅ تم تحديث السجل بنجاح")
            return redirect('meeting_session_list')
        except Exception as e:
            messages.error(request, f"❌ خطأ : {e}")

    return render(request, 'modules/meeting_session_form.html', {
        'mode': 'update', 'record': record, 'wilayas': WILAYAS,
    })

@login_required
def meeting_session_delete(request, pk):
    record = get_object_or_404(MeetingSession, pk=pk)
    if request.method == 'POST':
        record.delete()
        messages.success(request, "🗑️ تم حذف السجل")
        return redirect('meeting_session_list')
    return render(request, 'modules/meeting_session_confirm_delete.html', {'record': record})


# =====================================================
# الزيارات (CRUD)
# =====================================================

@login_required
def visit_list(request):
    records = Visit.objects.all()
    
    wilaya_filter = request.GET.get('wilaya', '')
    year_filter   = request.GET.get('year', '')

    if wilaya_filter: records = records.filter(wilaya=wilaya_filter)
    if year_filter: records = records.filter(year=year_filter)

    years = Visit.objects.values_list('year', flat=True).distinct().order_by('-year')

    return render(request, 'modules/visit_list.html', {
        'records': records, 'years': years,
        'wilaya_filter': wilaya_filter, 'year_filter': year_filter, 'wilayas': WILAYAS,
    })


@login_required
def visit_create(request):
    if request.method == 'POST':
        try:
            record = Visit(
                wilaya = request.POST.get('wilaya'),
                year   = request.POST.get('year', 2026),
                
                # 1. Supervised
                has_supervised_institutions = request.POST.get('has_supervised_institutions') == 'on',
                supervised_institutions = request.POST.get('supervised_institutions', '').strip(),
                supervised_topic = request.POST.get('supervised_topic', '').strip(),
                supervised_date = request.POST.get('supervised_date', '').strip(),

                # 2. Outside
                has_outside_visits = request.POST.get('has_outside_visits') == 'on',

                # 3. Public Structure
                has_public_structure_visit = request.POST.get('has_public_structure_visit') == 'on',
                public_structure_name = request.POST.get('public_structure_name', '').strip(),
                public_structure_topic = request.POST.get('public_structure_topic', '').strip(),
                public_structure_date = request.POST.get('public_structure_date', '').strip(),

                # 4. Presidency
                has_presidency_visit = request.POST.get('has_presidency_visit') == 'on',
                presidency_name = request.POST.get('presidency_name', '').strip(),
                presidency_topic = request.POST.get('presidency_topic', '').strip(),
                presidency_date = request.POST.get('presidency_date', '').strip(),

                # 5. Field Visits
                has_field_visits = request.POST.get('has_field_visits') == 'on',
                field_visits_details = request.POST.get('field_visits_details', '').strip(),

                created_by = request.user,
            )
            record.save()
            messages.success(request, "✅ تم إضافة السجل بنجاح")
            return redirect('visit_list')
        except Exception as e:
            messages.error(request, f"❌ خطأ : {e}")

    return render(request, 'modules/visit_form.html', {
        'mode': 'create', 'wilayas': WILAYAS,
    })


@login_required
def visit_update(request, pk):
    record = get_object_or_404(Visit, pk=pk)
    
    if request.method == 'POST':
        try:
            record.wilaya = request.POST.get('wilaya')
            record.year   = request.POST.get('year', 2026)
            
            # 1. Supervised
            record.has_supervised_institutions = request.POST.get('has_supervised_institutions') == 'on'
            record.supervised_institutions = request.POST.get('supervised_institutions', '').strip()
            record.supervised_topic = request.POST.get('supervised_topic', '').strip()
            record.supervised_date = request.POST.get('supervised_date', '').strip()

            # 2. Outside
            record.has_outside_visits = request.POST.get('has_outside_visits') == 'on'

            # 3. Public Structure
            record.has_public_structure_visit = request.POST.get('has_public_structure_visit') == 'on'
            record.public_structure_name = request.POST.get('public_structure_name', '').strip()
            record.public_structure_topic = request.POST.get('public_structure_topic', '').strip()
            record.public_structure_date = request.POST.get('public_structure_date', '').strip()

            # 4. Presidency
            record.has_presidency_visit = request.POST.get('has_presidency_visit') == 'on'
            record.presidency_name = request.POST.get('presidency_name', '').strip()
            record.presidency_topic = request.POST.get('presidency_topic', '').strip()
            record.presidency_date = request.POST.get('presidency_date', '').strip()

            # 5. Field Visits
            record.has_field_visits = request.POST.get('has_field_visits') == 'on'
            record.field_visits_details = request.POST.get('field_visits_details', '').strip()
            
            record.save()
            messages.success(request, "✅ تم تحديث السجل بنجاح")
            return redirect('visit_list')
        except Exception as e:
            messages.error(request, f"❌ خطأ : {e}")

    return render(request, 'modules/visit_form.html', {
        'mode': 'update', 'record': record, 'wilayas': WILAYAS,
    })


@login_required
def visit_delete(request, pk):
    record = get_object_or_404(Visit, pk=pk)
    if request.method == 'POST':
        record.delete()
        messages.success(request, "🗑️ تم حذف السجل")
        return redirect('visit_list')
    return render(request, 'modules/visit_confirm_delete.html', {'record': record})


# =====================================================
# التظاهرات والاحتفالات (CRUD)
# =====================================================

@login_required
def celebration_list(request):
    records = CelebrationReport.objects.all()
    
    wilaya_filter = request.GET.get('wilaya', '')
    year_filter   = request.GET.get('year', '')

    if wilaya_filter: records = records.filter(wilaya=wilaya_filter)
    if year_filter: records = records.filter(year=year_filter)

    years = CelebrationReport.objects.values_list('year', flat=True).distinct().order_by('-year')

    return render(request, 'modules/celebration_list.html', {
        'records': records, 'years': years,
        'wilaya_filter': wilaya_filter, 'year_filter': year_filter, 'wilayas': WILAYAS,
    })


@login_required
def celebration_create(request):
    if request.method == 'POST':
        try:
            record = CelebrationReport(
                wilaya = request.POST.get('wilaya'),
                year   = request.POST.get('year', 2026),

                # Checkboxes
                women_day = request.POST.get('women_day') == 'on',
                human_rights_day = request.POST.get('human_rights_day') == 'on',
                productive_families_day = request.POST.get('productive_families_day') == 'on',
                family_day = request.POST.get('family_day') == 'on',
                mothers_day = request.POST.get('mothers_day') == 'on',
                elderly_abuse_day = request.POST.get('elderly_abuse_day') == 'on',
                elderly_day = request.POST.get('elderly_day') == 'on',
                pink_october = request.POST.get('pink_october') == 'on',
                rural_women_day = request.POST.get('rural_women_day') == 'on',
                protection_month = request.POST.get('protection_month') == 'on',
                violence_prevention_day = request.POST.get('violence_prevention_day') == 'on',
                sixteen_days_activism = request.POST.get('sixteen_days_activism') == 'on',
                national_family_day = request.POST.get('national_family_day') == 'on',

                # Credits
                previous_credits_committed  = request.POST.get('previous_credits_committed', 0) or 0,
                previous_credits_paid       = request.POST.get('previous_credits_paid', 0) or 0,
                current_credits_committed   = request.POST.get('current_credits_committed', 0) or 0,
                current_credits_paid        = request.POST.get('current_credits_paid', 0) or 0,
                total_credits_committed     = request.POST.get('total_credits_committed', 0) or 0,
                total_credits_paid          = request.POST.get('total_credits_paid', 0) or 0,
                consumption_rate_committed  = request.POST.get('consumption_rate_committed', 0) or 0,
                consumption_rate_paid       = request.POST.get('consumption_rate_paid', 0) or 0,
                remaining_credits_committed = request.POST.get('remaining_credits_committed', 0) or 0,
                remaining_credits_paid      = request.POST.get('remaining_credits_paid', 0) or 0,

                created_by = request.user,
            )
            record.save()
            messages.success(request, "✅ تم إضافة التقرير بنجاح")
            return redirect('celebration_list')
        except Exception as e:
            messages.error(request, f"❌ خطأ : {e}")

    return render(request, 'modules/celebration_form.html', {
        'mode': 'create', 'wilayas': WILAYAS,
    })


@login_required
def celebration_update(request, pk):
    record = get_object_or_404(CelebrationReport, pk=pk)
    
    if request.method == 'POST':
        try:
            record.wilaya = request.POST.get('wilaya')
            record.year   = request.POST.get('year', 2026)

            # Checkboxes
            record.women_day = request.POST.get('women_day') == 'on'
            record.human_rights_day = request.POST.get('human_rights_day') == 'on'
            record.productive_families_day = request.POST.get('productive_families_day') == 'on'
            record.family_day = request.POST.get('family_day') == 'on'
            record.mothers_day = request.POST.get('mothers_day') == 'on'
            record.elderly_abuse_day = request.POST.get('elderly_abuse_day') == 'on'
            record.elderly_day = request.POST.get('elderly_day') == 'on'
            record.pink_october = request.POST.get('pink_october') == 'on'
            record.rural_women_day = request.POST.get('rural_women_day') == 'on'
            record.protection_month = request.POST.get('protection_month') == 'on'
            record.violence_prevention_day = request.POST.get('violence_prevention_day') == 'on'
            record.sixteen_days_activism = request.POST.get('sixteen_days_activism') == 'on'
            record.national_family_day = request.POST.get('national_family_day') == 'on'

            # Credits
            record.previous_credits_committed  = request.POST.get('previous_credits_committed', 0) or 0
            record.previous_credits_paid       = request.POST.get('previous_credits_paid', 0) or 0
            record.current_credits_committed   = request.POST.get('current_credits_committed', 0) or 0
            record.current_credits_paid        = request.POST.get('current_credits_paid', 0) or 0
            record.total_credits_committed     = request.POST.get('total_credits_committed', 0) or 0
            record.total_credits_paid          = request.POST.get('total_credits_paid', 0) or 0
            record.consumption_rate_committed  = request.POST.get('consumption_rate_committed', 0) or 0
            record.consumption_rate_paid       = request.POST.get('consumption_rate_paid', 0) or 0
            record.remaining_credits_committed = request.POST.get('remaining_credits_committed', 0) or 0
            record.remaining_credits_paid      = request.POST.get('remaining_credits_paid', 0) or 0
            
            record.save()
            messages.success(request, "✅ تم تحديث التقرير بنجاح")
            return redirect('celebration_list')
        except Exception as e:
            messages.error(request, f"❌ خطأ : {e}")

    return render(request, 'modules/celebration_form.html', {
        'mode': 'update', 'record': record, 'wilayas': WILAYAS,
    })


@login_required
def celebration_delete(request, pk):
    record = get_object_or_404(CelebrationReport, pk=pk)
    if request.method == 'POST':
        record.delete()
        messages.success(request, "🗑️ تم حذف التقرير")
        return redirect('celebration_list')
    return render(request, 'modules/celebration_confirm_delete.html', {'record': record})