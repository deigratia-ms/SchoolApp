from django.urls import path
from . import views
from . import views_career

app_name = 'website'

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('academics/', views.academics, name='academics'),
    path('admissions/', views.admissions, name='admissions'),
    path('contact/', views.contact, name='contact'),
    path('virtual-tour/', views.virtual_tour, name='virtual-tour'),
    path('virtual-tour/<int:pk>/', views.tour_location_detail, name='tour-location-detail'),
    path('events/', views.EventListView.as_view(), name='events'),
    path('events/<str:pk>/', views.EventDetailView.as_view(), name='event-detail'),
    path('news/', views.AnnouncementListView.as_view(), name='news'),
    path('news/category/<slug:category_slug>/', views.AnnouncementListView.as_view(), name='news-category'),
    path('news/archive/<int:year>/<int:month>/', views.AnnouncementArchiveView.as_view(), name='news-archive'),
    path('news/<slug:slug>/', views.AnnouncementDetailView.as_view(), name='announcement-detail'),
    path('newsletter/subscribe/', views.subscribe_newsletter, name='newsletter-subscribe'),
    path('gallery/', views.GalleryListView.as_view(), name='gallery'),
    path('gallery/<int:pk>/', views.GalleryDetailView.as_view(), name='gallery-detail'),

    # Staff URLs
    path('staff/', views.StaffListView.as_view(), name='staff-list'),
    path('staff/<int:pk>/', views.StaffDetailView.as_view(), name='staff-detail'),
    path('api/staff/<int:pk>/', views.get_staff_details, name='staff-details-api'),

    # Career URLs
    path('careers/', views_career.career_list, name='careers'),
    path('api/job/<int:pk>/', views_career.job_detail, name='job-details-api'),
    path('careers/apply/<int:pk>/', views_career.submit_application, name='submit-application'),

    # Quick Links URLs
    path('calendar/', views_career.school_calendar, name='school-calendar'),
    path('privacy-policy/', views_career.privacy_policy, name='privacy-policy'),
    path('terms-of-service/', views_career.terms_of_service, name='terms-of-service'),
    path('faqs/', views_career.faq_page, name='faqs'),

    # Admin-specific AJAX endpoints
    path('admin/website/get-page-content/', views.get_page_content, name='get-page-content'),
    path('admin/website/get-page-faqs/', views.get_page_faqs, name='get-page-faqs'),
]