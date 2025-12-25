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
from leave.models import Leave, LEAVE_TYPE
from employee.models import *
from leave.forms import LeaveCreationForm
from collections import defaultdict
import calendar


def dashboard(request):
    """
    Enhanced dashboard with leave statistics and visualizations
    """
    dataset = dict()
    user = request.user

    if not request.user.is_authenticated:
        return redirect('accounts:login')

    if user.is_superuser and user.is_staff:
        # Super User Dashboard - Organization-wide statistics
        dataset = get_superuser_dashboard_data()
    else:
        # Regular User Dashboard - Personal leave statistics
        dataset = get_user_dashboard_data(user)
    
    dataset['title'] = 'Dashboard'
    return render(request,'dashboard/basic_dashboard.html',dataset)


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
    
    dataset['title'] = 'Enhanced Dashboard'
    return render(request,'dashboard/enhanced_dashboard.html',dataset)


def simple_dashboard(request):
    """
    Simple dashboard with basic statistics
    """
    user = request.user
    
    if not user.is_authenticated:
        return redirect('accounts:login')
    
    dataset = dict()
    
    if user.is_superuser and user.is_staff:
        # Super User Dashboard - Basic statistics
        all_leaves = Leave.objects.all()
        all_employees = Employee.objects.all()
        
        dataset.update({
            'total_employees': all_employees.count(),
            'total_leaves': all_leaves.count(),
            'pending_leaves': all_leaves.filter(status='pending').count(),
            'approved_leaves': all_leaves.filter(status='approved').count(),
            'rejected_leaves': all_leaves.filter(status='rejected').count(),
            'user_type': 'superuser'
        })
    else:
        # Regular User Dashboard - Basic personal statistics
        user_leaves = Leave.objects.filter(user=user)
        
        dataset.update({
            'total_leaves': user_leaves.count(),
            'approved_leaves': user_leaves.filter(status='approved').count(),
            'pending_leaves': user_leaves.filter(status='pending').count(),
            'rejected_leaves': user_leaves.filter(status='rejected').count(),
            'recent_leaves': user_leaves.order_by('-created')[:5],
            'user_type': 'regular'
        })
    
    dataset['title'] = 'Simple Dashboard'
    return render(request,'dashboard/simple_dashboard.html',dataset)


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
    for leave_type, _ in LEAVE_TYPE:
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
    
    # Calculate leave usage percentage
    leave_usage_percentage = (total_days_used / default_days * 100) if default_days > 0 else 0
    
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
        'leave_usage_percentage': min(leave_usage_percentage, 100),  # Cap at 100%
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
    for leave_type, display_name in LEAVE_TYPE:
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
        'leave_types': LEAVE_TYPE,
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
        'average_leave_duration': leaves.filter(status='approved').aggregate(avg_duration=Avg('leave_days'))['avg_duration'],
        'leaves': leaves.order_by('-created')[:20],
        'title': 'Leave Analytics'
    }
    
    return render(request, 'dashboard/simple_analytics.html', context)


def dashboard_employees(request):
    if not (request.user.is_authenticated and request.user.is_superuser and request.user.is_staff):
        return redirect('/')

    dataset = dict()
    departments = Department.objects.all()
    employees = Employee.objects.all()

    #pagination
    query = request.GET.get('search')
    if query:
        employees = employees.filter(
            Q(firstname__icontains = query) |
            Q(lastname__icontains = query)
        )

    paginator = Paginator(employees, 10) #show 10 employee lists per page

    page = request.GET.get('page')
    employees_paginated = paginator.get_page(page)

    blocked_employees = Employee.objects.all_blocked_employees()

    dataset['employees'] = employees_paginated
    dataset['departments'] = departments
    dataset['blocked_employees'] = blocked_employees

    return render(request,'dashboard/employee_app.html',dataset)


def dashboard_employees_create(request):
    if not (request.user.is_authenticated and request.user.is_superuser and request.user.is_staff):
        return redirect('/')

    if request.method == 'POST':
        form = EmployeeCreateForm(request.POST,request.FILES)
        if form.is_valid():
            instance = form.save(commit = False)
            user = request.POST.get('user')
            assigned_user = User.objects.get(id = user)

            instance.user = assigned_user

            instance.title = request.POST.get('title')
            instance.image = request.FILES.get('image')
            instance.firstname = request.POST.get('firstname')
            instance.lastname = request.POST.get('lastname')
            instance.othername = request.POST.get('othername')
            
            instance.birthday = request.POST.get('birthday')

            role = request.POST.get('role')
            role_instance = Role.objects.get(id = role)
            instance.role = role_instance

            instance.startdate = request.POST.get('startdate')
            instance.employeetype = request.POST.get('employeetype')
            instance.employeeid = request.POST.get('employeeid')
            instance.dateissued = request.POST.get('dateissued')

            instance.save()

            return  redirect('dashboard:employees')
        else:
            messages.error(request,'Trying to create dublicate employees with a single user account ',extra_tags = 'alert alert-warning alert-dismissible show')
            return redirect('dashboard:employeecreate')

    dataset = dict()
    form = EmployeeCreateForm()
    dataset['form'] = form
    dataset['title'] = 'register employee'
    return render(request,'dashboard/employee_create.html',dataset)


def employee_edit_data(request,id):
    if not (request.user.is_authenticated and request.user.is_superuser and request.user.is_staff):
        return redirect('/')
    employee = get_object_or_404(Employee, id = id)
    if request.method == 'POST':
        form = EmployeeCreateForm(request.POST or None,request.FILES or None,instance = employee)
        if form.is_valid():
            instance = form.save(commit = False)

            user = request.POST.get('user')
            assigned_user = User.objects.get(id = user)

            instance.user = assigned_user

            instance.image = request.FILES.get('image')
            instance.firstname = request.POST.get('firstname')
            instance.lastname = request.POST.get('lastname')
            instance.othername = request.POST.get('othername')
            
            instance.birthday = request.POST.get('birthday')

            religion_id = request.POST.get('religion')
            religion = Religion.objects.get(id = religion_id)
            instance.religion = religion

            nationality_id = request.POST.get('nationality')
            nationality = Nationality.objects.get(id = nationality_id)
            instance.nationality = nationality

            department_id = request.POST.get('department')
            department = Department.objects.get(id = department_id)
            instance.department = department

            instance.hometown = request.POST.get('hometown')
            instance.region = request.POST.get('region')
            instance.residence = request.POST.get('residence')
            instance.address = request.POST.get('address')
            instance.education = request.POST.get('education')
            instance.lastwork = request.POST.get('lastwork')
            instance.position = request.POST.get('position')
            instance.ssnitnumber = request.POST.get('ssnitnumber')
            instance.tinnumber = request.POST.get('tinnumber')

            role = request.POST.get('role')
            role_instance = Role.objects.get(id = role)
            instance.role = role_instance

            instance.startdate = request.POST.get('startdate')
            instance.employeetype = request.POST.get('employeetype')
            instance.employeeid = request.POST.get('employeeid')
            instance.dateissued = request.POST.get('dateissued')

            instance.save()
            messages.success(request,'Account Updated Successfully !!!',extra_tags = 'alert alert-success alert-dismissible show')
            return redirect('dashboard:employees')

        else:
            messages.error(request,'Error Updating account',extra_tags = 'alert alert-warning alert-dismissible show')
            return HttpResponse("Form data not valid")

    dataset = dict()
    form = EmployeeCreateForm(request.POST or None,request.FILES or None,instance = employee)
    dataset['form'] = form
    dataset['title'] = 'edit - {0}'.format(employee.get_full_name)
    return render(request,'dashboard/employee_create.html',dataset)


def dashboard_employee_info(request,id):
    if not request.user.is_authenticated:
        return redirect('/')
    
    employee = get_object_or_404(Employee, id = id)
    
    dataset = dict()
    dataset['employee'] = employee
    dataset['title'] = 'profile - {0}'.format(employee.get_full_name)
    return render(request,'dashboard/employee_detail.html',dataset)


# ---------------------LEAVE-------------------------------------------

def leave_creation(request):
    if not request.user.is_authenticated:
        return redirect('accounts:login')
    if request.method == 'POST':
        form = LeaveCreationForm(data = request.POST)
        if form.is_valid():
            instance = form.save(commit = False)
            user = request.user
            instance.user = user
            instance.save()

            messages.success(request,'Leave Request Sent,wait for Admins response',extra_tags = 'alert alert-success alert-dismissible show')
            return redirect('dashboard:createleave')

        messages.error(request,'failed to Request a Leave,please check entry dates',extra_tags = 'alert alert-warning alert-dismissible show')
        return redirect('dashboard:createleave')

    dataset = dict()
    form = LeaveCreationForm()
    dataset['form'] = form
    dataset['title'] = 'Apply for Leave'
    return render(request,'dashboard/create_leave.html',dataset)


def leaves_list(request):
    if not (request.user.is_staff and request.user.is_superuser):
        return redirect('/')
    leaves = Leave.objects.all_pending_leaves()
    return render(request,'dashboard/leaves_recent.html',{'leave_list':leaves,'title':'leaves list - pending'})


def leaves_approved_list(request):
    if not (request.user.is_superuser and request.user.is_staff):
        return redirect('/')
    leaves = Leave.objects.all_approved_leaves()
    return render(request,'dashboard/leaves_approved.html',{'leave_list':leaves,'title':'approved leave list'})


def leaves_view(request,id):
    if not (request.user.is_authenticated):
        return redirect('/')

    leave = get_object_or_404(Leave, id = id)
    employee = Employee.objects.filter(user = leave.user).first()
    if not employee:
        messages.error(request, 'No employee profile found for this user.', extra_tags='alert alert-warning alert-dismissible show')
        return redirect('dashboard:leaveslist')
    
    return render(request,'dashboard/leave_detail_view.html',{'leave':leave,'employee':employee,'title':'{0}-{1} leave'.format(leave.user.username,leave.status)})


def approve_leave(request,id):
    if request.method != 'POST':
        return redirect('dashboard:leaveslist')
    if not (request.user.is_superuser and request.user.is_authenticated):
        return redirect('/')
    leave = get_object_or_404(Leave, id = id)
    user = leave.user
    employee = Employee.objects.filter(user = user).first()
    if not employee:
        messages.error(request, 'No employee profile found for this user.', extra_tags='alert alert-warning alert-dismissible show')
        return redirect('dashboard:leaveslist')
    
    leave.approve_leave
    messages.success(request,'Leave successfully approved for {0}'.format(employee.get_full_name),extra_tags = 'alert alert-success alert-dismissible show')
    return redirect('dashboard:userleaveview', id = id)


def cancel_leaves_list(request):
    if not (request.user.is_superuser and request.user.is_authenticated):
        return redirect('/')
    leaves = Leave.objects.all_cancel_leaves()
    return render(request,'dashboard/leaves_cancel.html',{'leave_list_cancel':leaves,'title':'Cancel leave list'})


def unapprove_leave(request,id):
    if not (request.user.is_authenticated and request.user.is_superuser):
        return redirect('/')
    leave = get_object_or_404(Leave, id = id)
    leave.unapprove_leave
    return redirect('dashboard:leaveslist')


def cancel_leave(request,id):
    if not (request.user.is_superuser and request.user.is_authenticated):
        return redirect('/')
    leave = get_object_or_404(Leave, id = id)
    leave.leaves_cancel
    messages.success(request,'Leave is canceled',extra_tags = 'alert alert-success alert-dismissible show')
    return redirect('dashboard:canceleaveslist')


def uncancel_leave(request,id):
    if not (request.user.is_superuser and request.user.is_authenticated):
        return redirect('/')
    leave = get_object_or_404(Leave, id = id)
    leave.status = 'pending'
    leave.is_approved = False
    leave.save()
    messages.success(request,'Leave is uncanceled,now in pending list',extra_tags = 'alert alert-success alert-dismissible show')
    return redirect('dashboard:canceleaveslist')


def leave_rejected_list(request):
    dataset = dict()
    leave = Leave.objects.all_rejected_leaves()
    dataset['leave_list_rejected'] = leave
    return render(request,'dashboard/rejected_leaves_list.html',dataset)


def reject_leave(request,id):
    dataset = dict()
    leave = get_object_or_404(Leave, id = id)
    leave.reject_leave
    messages.success(request,'Leave is rejected',extra_tags = 'alert alert-success alert-dismissible show')
    return redirect('dashboard:leavesrejected')


def unreject_leave(request,id):
    leave = get_object_or_404(Leave, id = id)
    leave.status = 'pending'
    leave.is_approved = False
    leave.save()
    messages.success(request,'Leave is now in pending list ',extra_tags = 'alert alert-success alert-dismissible show')
    return redirect('dashboard:leavesrejected')


def view_my_leave_table(request):
    if request.user.is_authenticated:
        user = request.user
        leaves = Leave.objects.filter(user = user)
        employee = Employee.objects.filter(user = user).first()
        dataset = dict()
        dataset['leave_list'] = leaves
        dataset['employee'] = employee
        dataset['title'] = 'Leaves List'
    else:
        return redirect('accounts:login')
    return render(request,'dashboard/staff_leaves_table.html',dataset)
