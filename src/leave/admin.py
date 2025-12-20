from django.contrib import admin
from .models import Leave
from .forms import LeaveAdminForm
# from .models import Comment


class LeaveAdmin(admin.ModelAdmin):
    form = LeaveAdminForm
    fieldsets = (
        (None, {
            'fields': ('user', 'startdate', 'enddate', 'leavetype', 'reason', 'defaultdays', 'status', 'is_approved', 'is_rejected')
        }),
    )
    list_display = ('user', 'startdate', 'enddate', 'leavetype', 'status', 'is_approved', 'is_rejected')
    list_filter = ('status', 'is_approved', 'is_rejected')
    search_fields = ('user__username', 'leavetype')

    class Media:
        js = ('leave/admin/js/admin.js',)

admin.site.register(Leave, LeaveAdmin)
# admin.site.register(Comment)
