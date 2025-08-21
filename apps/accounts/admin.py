from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import AdminUser, Customer

@admin.register(AdminUser)
class AdminUserAdmin(UserAdmin):
    # Fields to display in the list view
    list_display = ('email', 'is_staff', 'is_active', 'is_superuser')
    list_filter = ('is_staff', 'is_active', 'is_superuser', 'groups')
    search_fields = ('email',)
    ordering = ('email',)

    # Fields shown in the user detail page
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login',)}),
    )

    # Fields shown when creating a user
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'is_staff', 'is_active')}
        ),
    )

admin.site.register(Customer)