from django.shortcuts import render

def accounts_home(request):
    return render(request, 'accounts/admin_dashbord.html')