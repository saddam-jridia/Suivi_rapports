from .models import RegistrationRequest


def pending_requests(request):
    if request.user.is_authenticated and (request.user.is_superuser or request.user.is_staff):
        return {
            'pending_count_global': RegistrationRequest.objects.filter(status='pending').count()
        }
    return {}