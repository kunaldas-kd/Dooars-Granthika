"""
members/urls.py
"""

from django.urls import path
from . import views

app_name = "members"

urlpatterns = [
    # ── Dashboard ──────────────────────────────────────────────────────────────
    # path("dashboard/", views.members_dashboard, name="members_dashboard"),

    # ── Member list views ──────────────────────────────────────────────────────
    path("", views.members_list, name="members_list"),
    path("active/", views.members_active, name="members_active"),
    path("inactive/", views.members_inactive, name="members_inactive"),
    path("passout/", views.members_passout, name="members_passout"),

    # ── Member CRUD ────────────────────────────────────────────────────────────
    path("add/", views.member_add, name="member_add"),
    path("<int:pk>/", views.member_detail, name="member_detail"),
    path("<int:pk>/edit/", views.member_edit, name="member_edit"),
    path("<int:pk>/delete/", views.member_delete, name="member_delete"),
    path("<int:pk>/photo/", views.member_photo, name="member_photo"),

    # ── Member actions ─────────────────────────────────────────────────────────
    path("<int:pk>/reactivate/", views.member_reactivate, name="member_reactivate"),
    path("<int:pk>/mark-cleared/", views.member_mark_cleared, name="member_mark_cleared"),
    path("<int:pk>/send-reminder/", views.send_reminder, name="send_reminder"),

    # ── Clearance ──────────────────────────────────────────────────────────────
    path("clearance/check/", views.clearance_check, name="clearance_check"),
    path("clearance/cleared/", views.cleared_members, name="cleared_members"),
    path("clearance/pending/", views.pending_clearance, name="pending_clearance"),
    path("<int:pk>/clearance-certificate/", views.clearance_certificate, name="clearance_certificate"),
    path("<int:pk>/issue-clearance/", views.issue_clearance, name="issue_clearance"),

    # ── Lookup management (settings / admin-like pages) ────────────────────────
    path("settings/departments/", views.department_list, name="department_list"),
    path("settings/departments/<int:pk>/delete/", views.department_delete, name="department_delete"),

    path("settings/courses/", views.course_list, name="course_list"),
    path("settings/courses/<int:pk>/delete/", views.course_delete, name="course_delete"),

    path("settings/academic-years/", views.academic_year_list, name="academic_year_list"),
    path("settings/academic-years/<int:pk>/delete/", views.academic_year_delete, name="academic_year_delete"),

    path("settings/semesters/", views.semester_list, name="semester_list"),
    path("settings/semesters/<int:pk>/delete/", views.semester_delete, name="semester_delete"),
]