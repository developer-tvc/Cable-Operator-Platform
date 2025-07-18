from django.shortcuts import render, redirect, get_object_or_404
from .models import Plan
from .forms import PlanForm

def plan_list(request):
    plans = Plan.objects.all()
    return render(request, 'plans/plan_list.html', {'plans': plans})

def create_plan(request):
    if request.method == 'POST':
        form = PlanForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('plan_list')
    else:
        form = PlanForm()
    return render(request, 'plans/create_plan.html', {'form': form})

def update_plan(request, pk):
    plan = get_object_or_404(Plan, pk=pk)
    if request.method == 'POST':
        form = PlanForm(request.POST, instance=plan)
        if form.is_valid():
            form.save()
            return redirect('plan_list')
    else:
        form = PlanForm(instance=plan)
    return render(request, 'plans/update_plan.html', {'form': form, 'plan': plan})

def delete_plan(request, pk):
    plan = get_object_or_404(Plan, pk=pk)
    if request.method == 'POST':
        plan.delete()
        return redirect('plan_list')
    return render(request, 'plans/delete_plan.html', {'plan': plan})
