from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.shortcuts import render,redirect,get_object_or_404
from django.http import HttpResponse,HttpResponseRedirect
from django.contrib.auth.models import User
from django.conf import settings
from django.db.models import Q, Count, Sum, Avg
import datetime
from django.core.mail import send_mail
from django.contrib import messages
from django.urls import reverse
from employee.forms import EmployeeCreateForm
from leave.models import Leave
from employee.models import *
from leave.forms import LeaveCreationForm
from collections import defaultdict
import calendar


def enhanced_dashboard(request):
    """
    Enhanced dashboard with leave statistics and visualizations
    """
    user = request.user
    
    if not user.is_authenticated:
        return redirect('accounts:login')
    
    dataset = dict()
    
    if user.is_superuser and user.is_staff:
        # Super User Dashboard - Organization-wide statistics
        dataset = get_superuser_dashboard_data()
    else:
        # Regular User Dashboard - Personal leave statistics
        dataset = get_user_dashboard_data(user)
    
    dataset['title'] = 'Dashboard'
    return render(request,'dashboard/enhanced_dashboard.html',dataset)


def get_user_dashboard_data(user):
    """Generate dashboard data for regular users"""
    dataset = dict()
    
    # Get user's leaves
    user_leaves = Leave.objects.filter(user=user)
    
    # Basic statistics
    total_leaves = user_leaves.count()
    approved_leaves = user_leaves.filter(status='approved').count()
    pending_leaves = user_leaves.filter(status='pending').count()
    rejected_leaves = user_leaves.filter(status='rejected').count()
    cancelled_leaves = user_leaves.filter(status='cancelled').count()
    
    # Leave statistics by type
    leave_types = {}
    for leave_type, _ in Leave.LEAVE_TYPE:
        count = user_leaves.filter(leavetype=leave_type).count()
        if count > 0:
            leave_types[leave_type] = count
    
    # Monthly leave statistics for current year
    current_year = datetime.datetime.now().year
    monthly_data = []
    for month in range(1, 13):
        month_name = calendar.month_abbr[month]
        count = user_leaves.filter(
            startdate__year=current_year,
            startdate__month=month
        ).count()
        monthly_data.append({'month': month_name, 'count': count})
    
    # Recent leave requests (last 5)
    recent_leaves = user_leaves.order_by('-created')[:5]
    
    # Calculate total leave days used
    approved_leaves_qs = user_leaves.filter(status='approved')
    total_days_used = 0
    for leave in approved_leaves_qs:
        if leave.leave_days:
            total_days_used += leave.leave_days + 1  # +1 to include both start and end dates
    
    # Default leave days per year (can be customized per user)
    default_days = 30
    days_remaining = default_days - total_days_used
    
    dataset.update({
        'total_leaves': total_leaves,
        'approved_leaves': approved_leaves,
        'pending_leaves': pending_leaves,
        'rejected_leaves': rejected_leaves,
        'cancelled_leaves': cancelled_leaves,
        'leave_types': leave_types,
        'monthly_data': monthly_data,
        'recent_leaves': recent_leaves,
        'total_days_used': total_days_used,
        'days_remaining': max(0, days_remaining),
        'default_days': default_days,
        'user_type': 'regular'
    })
    
    return dataset


def get_superuser_dashboard_data():
    """Generate dashboard data for super users"""
    dataset = dict()
    
    # Overall organization statistics
    all_leaves = Leave.objects.all()
    all_employees = Employee.objects.all()
    
    # Basic counts
    total_employees = all_employees.count()
    total_leaves = all_leaves.count()
    pending_leaves = all_leaves.filter(status='pending').count()
    approved_leaves = all_leaves.filter(status='approved').count()
    rejected_leaves = all_leaves.filter(status='rejected').count()
    
    # Leave status distribution for charts
    status_distribution = {
        'pending': pending_leaves,
        'approved': approved_leaves,
        'rejected': rejected_leaves,
        'cancelled': all_leaves.filter(status='cancelled').count()
    }
    
    # Department-wise leave statistics
    department_stats = []
    for department in Department.objects.all():
        dept_employees = all_employees.filter(department=department)
        dept_leaves = all_leaves.filter(user__employee__department=department)
        department_stats.append({
            'name': department.name,
            'employees': dept_employees.count(),
            'leaves': dept_leaves.count(),
            'pending': dept_leaves.filter(status='pending').count(),
            'approved': dept_leaves.filter(status='approved').count()
        })
    
    # Monthly leave trends (current year)
    current_year = datetime.datetime.now().year
    monthly_trends = []
    for month in range(1, 13):
        month_name = calendar.month_abbr[month]
        count = all_leaves.filter(
            startdate__year=current_year,
            startdate__month=month
        ).count()
        monthly_trends.append({'month': month_name, 'count': count})
    
    # Leave type distribution
    leave_type_stats = {}
    for leave_type, display_name in Leave.LEAVE_TYPE:
        count = all_leaves.filter(leavetype=leave_type).count()
        if count > 0:
            leave_type_stats[display_name] = count
    
    # Recent leave requests (last 10)
    recent_leaves = all_leaves.order_by('-created')[:10]
    
    # Top employees by leave requests
    top_leave_takers = User.objects.annotate(
        leave_count=Count('leave')
    ).filter(leave_count__gt=0).order_by('-leave_count')[:5]
    
    dataset.update({
        'total_employees': total_employees,
        'total_leaves': total_leaves,
        'pending_leaves': pending_leaves,
        'approved_leaves': approved_leaves,
        'rejected_leaves': rejected_leaves,
        'status_distribution': status_distribution,
        'department_stats': department_stats,
        'monthly_trends': monthly_trends,
        'leave_type_stats': leave_type_stats,
        'recent_leaves': recent_leaves,
        'top_leave_takers': top_leave_takers,
        'user_type': 'superuser'
    })
    
    return dataset


def leave_history(request):
    """Detailed leave history for users"""
    if not request.user.is_authenticated:
        return redirect('accounts:login')
    
    user_leaves = Leave.objects.filter(user=request.user).order_by('-created')
    
    # Filtering
    status_filter = request.GET.get('status', '')
    type_filter = request.GET.get('type', '')
    year_filter = request.GET.get('year', '')
    
    if status_filter:
        user_leaves = user_leaves.filter(status=status_filter)
    if type_filter:
        user_leaves = user_leaves.filter(leavetype=type_filter)
    if year_filter:
        user_leaves = user_leaves.filter(startdate__year=year_filter)
    
    # Pagination
    paginator = Paginator(user_leaves, 15)
    page = request.GET.get('page')
    leaves_paginated = paginator.get_page(page)
    
    # Calculate statistics for filtered results
    total_days = sum([(leave.leave_days + 1) if leave.leave_days else 0 for leave in user_leaves])
    
    context = {
        'leaves': leaves_paginated,
        'status_filter': status_filter,
        'type_filter': type_filter,
        'year_filter': year_filter,
        'total_days': total_days,
        'leave_types': Leave.LEAVE_TYPE,
        'title': 'Leave History'
    }
    
    return render(request, 'dashboard/leave_history.html', context)


def admin_leave_analytics(request):
    """Admin analytics dashboard"""
    if not (request.user.is_authenticated and request.user.is_superuser):
        return redirect('/')
    
    # Date range filtering
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    leaves = Leave.objects.all()
    if start_date and end_date:
        leaves = leaves.filter(startdate__range=[start_date, end_date])
    
    # Calculate various analytics
    context = {
        'total_leaves': leaves.count(),
        'approved_rate': (leaves.filter(status='approved').count() / leaves.count() * 100) if leaves.count() > 0 else 0,
        'most_common_leave_type': leaves.values('leavetype').annotate(count=Count('leavetype')).order_by('-count').first(),
        'average_leave_duration': leaves.filter(status='approved').aggregate(avg_duration=Avg('startdate'))['avg_duration'],
        'leaves': leaves.order_by('-created')[:20],
        'title': 'Leave Analytics'
    }
    
    return render(request, 'dashboard/admin_analytics.html', context)
