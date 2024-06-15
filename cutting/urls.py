from django.urls import path

from cutting.views import cutting_visualization_view, cutting_form_manual_view, cutting_form_file_view, \
    cutting_form_view

urlpatterns = [
    path('cutting-form/', cutting_form_view, name='cutting_form'),
    path('cutting-form/manual/', cutting_form_manual_view, name='cutting_form_manual'),
    path('cutting-form/file/', cutting_form_file_view, name='cutting_form_file'),
    path('cutting-visualization/<int:request_id>/', cutting_visualization_view, name='cutting_visualization'),
]
