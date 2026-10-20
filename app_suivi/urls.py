from django.urls import path
from . import views

urlpatterns = [
    # Authentification
    path('',          views.home,                     name='home'),
    path('login/',    views.login_view,               name='login'),
    path('logout/',   views.logout_view,              name='logout'),

    # Inscription publique
    path('register/', views.register_delegate_public, name='register_delegate_public'),

    # Espace admin
    path('admin-space/',                              views.admin_dashboard,    name='admin_dashboard'),
    path('admin-space/users/',                        views.user_list,          name='user_list'),
    path('admin-space/users/new/',                    views.user_create,        name='user_create'),
    path('admin-space/users/<int:pk>/edit/',          views.user_update,        name='user_update'),
    path('admin-space/users/<int:pk>/delete/',        views.user_delete,        name='user_delete'),
    path('admin-space/users/<int:pk>/toggle/',        views.user_toggle_active, name='user_toggle_active'),

    # Demandes d'inscription
    path('admin-space/requests/',                    views.request_list,    name='request_list'),
    path('admin-space/requests/<int:pk>/approve/',   views.request_approve, name='request_approve'),
    path('admin-space/requests/<int:pk>/reject/',    views.request_reject,  name='request_reject'),

    # Délégués
    path('admin-space/delegates/new/',                views.register_delegate,      name='register_delegate'),

    # AJAX (public)
    path('ajax/next-delegate-id/',                    views.ajax_next_delegate_id,  name='ajax_next_delegate_id'),
    # روضتنا في حومتنا
    path('rawdhatna/',                   views.rawdhatna_list,   name='rawdhatna_list'),
    path('rawdhatna/new/',               views.rawdhatna_create, name='rawdhatna_create'),
    path('rawdhatna/<int:pk>/edit/',     views.rawdhatna_update, name='rawdhatna_update'),
    path('rawdhatna/<int:pk>/delete/',   views.rawdhatna_delete, name='rawdhatna_delete'),

    # أطفال طيف التوحد
    path('autism/',                  views.autism_list,   name='autism_list'),
    path('autism/new/',              views.autism_create, name='autism_create'),
    path('autism/<int:pk>/edit/',    views.autism_update, name='autism_update'),
    path('autism/<int:pk>/delete/',  views.autism_delete, name='autism_delete'),

    # الإيداع العائلي لكبار السن
    path('senior-family/',                  views.senior_family_list,   name='senior_family_list'),
    path('senior-family/new/',              views.senior_family_create, name='senior_family_create'),
    path('senior-family/<int:pk>/edit/',    views.senior_family_update, name='senior_family_update'),
    path('senior-family/<int:pk>/delete/',  views.senior_family_delete, name='senior_family_delete'),

    # الإدماج الاقتصادي للأسر
    path('family-integration/',                  views.family_integration_list,   name='family_integration_list'),
    path('family-integration/new/',              views.family_integration_create, name='family_integration_create'),
    path('family-integration/<int:pk>/edit/',    views.family_integration_update, name='family_integration_update'),
    path('family-integration/<int:pk>/delete/',  views.family_integration_delete, name='family_integration_delete'),

    # الإدماج الاقتصادي لأمهات التلاميذ
    path('mothers-dropout/',                  views.mothers_dropout_list,   name='mothers_dropout_list'),
    path('mothers-dropout/new/',              views.mothers_dropout_create, name='mothers_dropout_create'),
    path('mothers-dropout/<int:pk>/edit/',    views.mothers_dropout_update, name='mothers_dropout_update'),
    path('mothers-dropout/<int:pk>/delete/',  views.mothers_dropout_delete, name='mothers_dropout_delete'),

    # برنامج صامدة
    path('samda/',                  views.samda_list,   name='samda_list'),
    path('samda/new/',              views.samda_create, name='samda_create'),
    path('samda/<int:pk>/edit/',    views.samda_update, name='samda_update'),
    path('samda/<int:pk>/delete/',  views.samda_delete, name='samda_delete'),

    # النساء في الريف
    path('rural-women/',                  views.rural_women_list,   name='rural_women_list'),
    path('rural-women/new/',              views.rural_women_create, name='rural_women_create'),
    path('rural-women/<int:pk>/edit/',    views.rural_women_update, name='rural_women_update'),
    path('rural-women/<int:pk>/delete/',  views.rural_women_delete, name='rural_women_delete'),

    # خطة عمل لكل منطقة مشروع
    path('action-plan/',                  views.action_plan_list,   name='action_plan_list'),
    path('action-plan/new/',              views.action_plan_create, name='action_plan_create'),
    path('action-plan/<int:pk>/edit/',    views.action_plan_update, name='action_plan_update'),
    path('action-plan/<int:pk>/delete/',  views.action_plan_delete, name='action_plan_delete'),

    # برنامج رائدات
    path('raedat/',                  views.raedat_list,   name='raedat_list'),
    path('raedat/new/',              views.raedat_create, name='raedat_create'),
    path('raedat/<int:pk>/edit/',    views.raedat_update, name='raedat_update'),
    path('raedat/<int:pk>/delete/',  views.raedat_delete, name='raedat_delete'),

    # فضاءات المرافقة والتسويق
    path('accompagnement/',                  views.accompagnement_list,   name='accompagnement_list'),
    path('accompagnement/new/',              views.accompagnement_create, name='accompagnement_create'),
    path('accompagnement/<int:pk>/edit/',    views.accompagnement_update, name='accompagnement_update'),
    path('accompagnement/<int:pk>/delete/',  views.accompagnement_delete, name='accompagnement_delete'),

    # التمكين الاجتماعي للأسر
    path('family-cohesion/',                  views.family_cohesion_list,   name='family_cohesion_list'),
    path('family-cohesion/new/',              views.family_cohesion_create, name='family_cohesion_create'),
    path('family-cohesion/<int:pk>/edit/',    views.family_cohesion_update, name='family_cohesion_update'),
    path('family-cohesion/<int:pk>/delete/',  views.family_cohesion_delete, name='family_cohesion_delete'),

    # فضاءات الأسرة
    path('family-space/',                  views.family_space_list,   name='family_space_list'),
    path('family-space/new/',              views.family_space_create, name='family_space_create'),
    path('family-space/<int:pk>/edit/',    views.family_space_update, name='family_space_update'),
    path('family-space/<int:pk>/delete/',  views.family_space_delete, name='family_space_delete'),


    # مركز إرشاد وتوجيه أسري
    path('family-guidance/',                  views.family_guidance_list,   name='family_guidance_list'),
    path('family-guidance/new/',              views.family_guidance_create, name='family_guidance_create'),
    path('family-guidance/<int:pk>/edit/',    views.family_guidance_update, name='family_guidance_update'),
    path('family-guidance/<int:pk>/delete/',  views.family_guidance_delete, name='family_guidance_delete'),

    # وحدة مرافقة الأولياء
    path('parent-accompaniment/',                  views.parent_accompaniment_list,   name='parent_accompaniment_list'),
    path('parent-accompaniment/new/',              views.parent_accompaniment_create, name='parent_accompaniment_create'),
    path('parent-accompaniment/<int:pk>/edit/',    views.parent_accompaniment_update, name='parent_accompaniment_update'),
    path('parent-accompaniment/<int:pk>/delete/',  views.parent_accompaniment_delete, name='parent_accompaniment_delete'),

    # نوادي أطفال
    path('children-club/',                  views.children_club_list,   name='children_club_list'),
    path('children-club/new/',              views.children_club_create, name='children_club_create'),
    path('children-club/<int:pk>/edit/',    views.children_club_update, name='children_club_update'),
    path('children-club/<int:pk>/delete/',  views.children_club_delete, name='children_club_delete'),

    # المراكز المندمجة
    path('integrated-center/',                  views.integrated_center_list,   name='integrated_center_list'),
    path('integrated-center/new/',              views.integrated_center_create, name='integrated_center_create'),
    path('integrated-center/<int:pk>/edit/',    views.integrated_center_update, name='integrated_center_update'),
    path('integrated-center/<int:pk>/delete/',  views.integrated_center_delete, name='integrated_center_delete'),

    # مراكز المسنين
    path('elderly-center/',                  views.elderly_center_list,   name='elderly_center_list'),
    path('elderly-center/new/',              views.elderly_center_create, name='elderly_center_create'),
    path('elderly-center/<int:pk>/edit/',    views.elderly_center_update, name='elderly_center_update'),
    path('elderly-center/<int:pk>/delete/',  views.elderly_center_delete, name='elderly_center_delete'),

    # النوادي النهارية
    path('day-club/',                  views.day_club_list,   name='day_club_list'),
    path('day-club/new/',              views.day_club_create, name='day_club_create'),
    path('day-club/<int:pk>/edit/',    views.day_club_update, name='day_club_update'),
    path('day-club/<int:pk>/delete/',  views.day_club_delete, name='day_club_delete'),

    # مركبات الطفولة
    path('childhood-complex/',                  views.childhood_complex_list,   name='childhood_complex_list'),
    path('childhood-complex/new/',              views.childhood_complex_create, name='childhood_complex_create'),
    path('childhood-complex/<int:pk>/edit/',    views.childhood_complex_update, name='childhood_complex_update'),
    path('childhood-complex/<int:pk>/delete/',  views.childhood_complex_delete, name='childhood_complex_delete'),

    # مراكز الإعلامية الموجهة للطفل
    path('child-it-center/',                  views.child_it_center_list,   name='child_it_center_list'),
    path('child-it-center/new/',              views.child_it_center_create, name='child_it_center_create'),
    path('child-it-center/<int:pk>/edit/',    views.child_it_center_update, name='child_it_center_update'),
    path('child-it-center/<int:pk>/delete/',  views.child_it_center_delete, name='child_it_center_delete'),

    # روزنامة الأنشطة الأسبوعية
    path('weekly-activity/',                  views.weekly_activity_list,   name='weekly_activity_list'),
    path('weekly-activity/new/',              views.weekly_activity_create, name='weekly_activity_create'),
    path('weekly-activity/<int:pk>/edit/',    views.weekly_activity_update, name='weekly_activity_update'),
    path('weekly-activity/<int:pk>/delete/',  views.weekly_activity_delete, name='weekly_activity_delete'),

    # الاجتماعات وجلسات العمل
    path('meeting-session/',                  views.meeting_session_list,   name='meeting_session_list'),
    path('meeting-session/new/',              views.meeting_session_create, name='meeting_session_create'),
    path('meeting-session/<int:pk>/edit/',    views.meeting_session_update, name='meeting_session_update'),
    path('meeting-session/<int:pk>/delete/',  views.meeting_session_delete, name='meeting_session_delete'),

    # الزيارات
    path('visit/',                  views.visit_list,   name='visit_list'),
    path('visit/new/',              views.visit_create, name='visit_create'),
    path('visit/<int:pk>/edit/',    views.visit_update, name='visit_update'),
    path('visit/<int:pk>/delete/',  views.visit_delete, name='visit_delete'),

   
   # التظاهرات والاحتفالات
    path('celebration/',                  views.celebration_list,   name='celebration_list'),
    path('celebration/new/',              views.celebration_create, name='celebration_create'),
    path('celebration/<int:pk>/edit/',    views.celebration_update, name='celebration_update'),
    path('celebration/<int:pk>/delete/',  views.celebration_delete, name='celebration_delete'),

]