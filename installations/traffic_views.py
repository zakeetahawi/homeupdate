from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import (
    login_required,
    permission_required,
    user_passes_test,
)
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .forms import DriverForm, VehicleForm
from .models import (
    Driver,
    InstallationSchedule,
    Vehicle,
    VehicleMission,
    VehicleRequest,
)


def is_traffic_manager_or_superuser(user):
    return user.is_superuser or user.is_traffic_manager


@login_required
@user_passes_test(is_traffic_manager_or_superuser)
def traffic_dashboard(request):
    """لوحة تحكم إدارة الحركة (المحسنة)"""

    # تحديد التاريخ (اليوم افتراضياً)
    selected_date_str = request.GET.get(
        "date", timezone.now().date().strftime("%Y-%m-%d")
    )
    try:
        selected_date = timezone.datetime.strptime(selected_date_str, "%Y-%m-%d").date()
    except ValueError:
        selected_date = timezone.now().date()

    # الإحصائيات العامة
    drivers_count = Driver.objects.filter(is_active=True).count()
    vehicles_count = Vehicle.objects.filter(status="active").count()
    vehicles_maintenance = Vehicle.objects.filter(status="maintenance").count()

    # 1. جدول المهام اليومي (Daily Schedule)
    # يشمل التركيبات + المهام الخاصة لهذا اليوم

    # التركيبات المجدولة لهذا اليوم
    daily_installations = InstallationSchedule.objects.filter(
        scheduled_date=selected_date,
        status__in=[
            "scheduled",
            "in_installation",
            "modification_in_progress",
            "completed",
        ],
    ).select_related("order", "driver", "order__customer", "team")

    # المهام المعينة لهذا اليوم (ب بجميع أنواعها: تركيب، خاصة، صيانة)
    daily_missions = VehicleMission.objects.filter(date=selected_date).select_related(
        "vehicle", "driver", "created_by"
    )

    # 2. المركبات والسائقين الشاغرين (Vacant Vehicles & Drivers)
    # المركبات والسائقين الذين ليسوا في مهمة نشطة حالياً
    busy_vehicles_ids = set()
    busy_drivers_ids = set()

    # نعتمد على جدول المهام (VehicleMission) لتحديد الانشغال حالياً
    # لأن مدير الحركة هو من يتحكم في بداية ونهاية هذه المهام
    for mission in daily_missions:
        if mission.status not in ["completed", "cancelled"]:
            if mission.vehicle_id:
                busy_vehicles_ids.add(mission.vehicle_id)
            if mission.driver_id:
                busy_drivers_ids.add(mission.driver_id)

    vacant_vehicles = (
        Vehicle.objects.filter(status="active")
        .exclude(id__in=busy_vehicles_ids)
        .order_by("name")
    )

    vacant_drivers = (
        Driver.objects.filter(is_active=True)
        .exclude(id__in=busy_drivers_ids)
        .order_by("name")
    )

    # 3. طلبات المركبات المعلقة
    pending_requests = (
        VehicleRequest.objects.filter(status="pending")
        .select_related("requester")
        .order_by("requested_date")
    )

    # إضافة إحصائيات المهام للسائقين (للتاريخ المحدد)
    # 1. التركيبات النشطة
    driver_active_inst = Count(
        "installations",
        filter=Q(
            installations__scheduled_date=selected_date,
            installations__status__in=[
                "scheduled",
                "in_installation",
                "modification_in_progress",
            ],
        ),
    )
    # 2. المهمات الخاصة النشطة
    driver_active_miss = Count(
        "missions",
        filter=Q(
            missions__date=selected_date,
            missions__status__in=["active", "pending"],
            missions__mission_type__in=["custom", "maintenance"],
        ),
    )
    # 3. إجمالي المهام (للمعلومات فقط)
    driver_total_tasks = Count(
        "installations", filter=Q(installations__scheduled_date=selected_date)
    ) + Count(
        "missions",
        filter=Q(
            missions__date=selected_date,
            missions__mission_type__in=["custom", "maintenance"],
        ),
    )

    drivers_with_stats = (
        Driver.objects.filter(is_active=True)
        .annotate(
            active_tasks=driver_active_inst + driver_active_miss,
            total_tasks=driver_total_tasks,
        )
        .order_by("name")
    )

    context = {
        "title": _("لوحة تحكم الحركة"),
        "selected_date": selected_date,
        "drivers_count": Driver.objects.filter(is_active=True).count(),
        "vacant_drivers_count": vacant_drivers.count(),
        "vehicles_count": Vehicle.objects.filter(status="active").count(),
        "vacant_vehicles_count": vacant_vehicles.count(),
        "vehicles_maintenance": vehicles_maintenance,
        "daily_installations": daily_installations,
        "daily_installations_count": daily_installations.count(),
        "daily_custom_missions_count": daily_missions.exclude(
            mission_type="installation"
        ).count(),
        "daily_missions": daily_missions,
        "vacant_vehicles": vacant_vehicles,
        "vacant_drivers": vacant_drivers,
        "pending_requests": pending_requests,
        "drivers": drivers_with_stats,
        "all_vehicles": Vehicle.objects.filter(status="active"),
        "all_drivers": Driver.objects.filter(is_active=True),
    }
    return render(request, "installations/traffic/dashboard.html", context)


@login_required
@user_passes_test(is_traffic_manager_or_superuser)
@require_http_methods(["POST"])
def assign_driver_to_installation(request, installation_id):
    """تخصيص سائق (ومركبة) لتركيب معين من لوحة الحركة"""
    installation = get_object_or_404(InstallationSchedule, id=installation_id)

    driver_id = request.POST.get("driver_id")

    if driver_id:
        driver = get_object_or_404(Driver, id=driver_id)
        installation.driver = driver

        # البحث عن مهمة موجودة لهذا السائق في هذا اليوم من نوع "تركيب"
        # إذا لم توجد، يتم إنشاء واحدة جديدة
        mission, created = VehicleMission.objects.get_or_create(
            driver=driver,
            date=installation.scheduled_date,
            mission_type="installation",
            status="active",
            defaults={
                "created_by": request.user,
                "vehicle": driver.vehicle,
                "start_time": (
                    timezone.localtime(timezone.now()).time()
                    if installation.scheduled_date == timezone.now().date()
                    else None
                ),
            },
        )
        # ربط التركيب بالمهمة
        installation.vehicle_mission = mission
        installation.save()

    else:
        # إلغاء التعيين
        if installation.vehicle_mission:
            mission = installation.vehicle_mission
            installation.driver = None
            installation.vehicle_mission = None
            installation.save()

            # إذا كانت هذه آخر عملية تركيب في هذه المهمة، فربما نريد حذف المهمة؟
            # أو نتركها كمدير حركة ليقرر. للتبسيط سنحذف المهمة إذا أصبحت فارغة وليس لها وصف خاص
            if mission.scheduled_installations.count() == 0 and not mission.description:
                mission.delete()

    installation.save()
    messages.success(request, _("تم تحديث تعيين السائق بنجاح"))
    return redirect("installations:traffic_dashboard")


@login_required
@user_passes_test(is_traffic_manager_or_superuser)
@require_http_methods(["POST"])
def create_custom_mission(request):
    """إنشاء مهمة خاصة لمركبة"""
    vehicle_id = request.POST.get("vehicle_id")
    driver_id = request.POST.get("driver_id")
    description = request.POST.get("description")
    date_str = request.POST.get("date", timezone.now().date().strftime("%Y-%m-%d"))

    if not vehicle_id or not driver_id:
        messages.error(request, _("المركبة والسائق مطلوبان"))
        return redirect("installations:traffic_dashboard")

    VehicleMission.objects.create(
        vehicle_id=vehicle_id,
        driver_id=driver_id,
        mission_type="custom",
        description=description,
        date=date_str,
        status="active",
        created_by=request.user,
        start_time=(
            timezone.localtime(timezone.now()).time()
            if date_str == timezone.now().date().strftime("%Y-%m-%d")
            else None
        ),
    )

    messages.success(request, _("تم إنشاء المهمة بنجاح"))
    return redirect("installations:traffic_dashboard")


@login_required
@user_passes_test(is_traffic_manager_or_superuser)
def handle_vehicle_request(request, request_id):
    """معالجة طلب مركبة (قبول/رفض)"""
    v_request = get_object_or_404(VehicleRequest, id=request_id)

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "approve":
            vehicle_id = request.POST.get("vehicle_id")
            driver_id = request.POST.get("driver_id")

            if not vehicle_id or not driver_id:
                messages.error(request, _("يجب تحديد مركبة وسائق للموافقة"))
                return redirect("installations:traffic_dashboard")

            # إنشاء المهمة
            mission = VehicleMission.objects.create(
                vehicle_id=vehicle_id,
                driver_id=driver_id,
                mission_type="custom",
                description=f"طلب من {v_request.requester.get_full_name()}: {v_request.purpose}",
                date=v_request.requested_date,
                status="active",
                created_by=request.user,
            )

            v_request.status = "approved"
            v_request.assigned_mission = mission
            v_request.save()
            messages.success(request, _("تمت الموافقة على الطلب وتخصيص المركبة"))

        elif action == "reject":
            reason = request.POST.get("rejection_reason", "")
            v_request.status = "rejected"
            v_request.rejection_reason = reason
            v_request.save()
            messages.info(request, _("تم رفض الطلب"))

    return redirect("installations:traffic_dashboard")


@login_required
@user_passes_test(is_traffic_manager_or_superuser)
def driver_list(request):
    """عرض قائمة السائقين مع إمكانية البحث والفلترة"""
    search_query = request.GET.get("q", "")
    status_filter = request.GET.get("status", "")

    drivers = Driver.objects.all().order_by("-is_active", "name")

    if search_query:
        drivers = drivers.filter(
            Q(name__icontains=search_query)
            | Q(phone__icontains=search_query)
            | Q(license_number__icontains=search_query)
        )

    if status_filter == "active":
        drivers = drivers.filter(is_active=True)
    elif status_filter == "inactive":
        drivers = drivers.filter(is_active=False)

    today = timezone.now().date()
    # إضافة إحصائيات المهام للسائقين (للتاريخ المحدد)
    # 1. عدد التركيبات النشطة فقط
    driver_installations_count = Count(
        "installations",
        filter=Q(
            installations__scheduled_date=today,
            installations__status__in=[
                "scheduled",
                "in_installation",
                "modification_scheduled",
                "modification_in_progress",
            ],
        ),
    )

    # 2. عدد المهام الخاصة النشطة فقط
    driver_missions_count = Count(
        "missions",
        filter=Q(missions__date=today, missions__status__in=["active", "pending"]),
    )

    drivers = drivers.annotate(
        daily_tasks=driver_installations_count + driver_missions_count
    )

    context = {
        "drivers": drivers,
        "search_query": search_query,
        "status_filter": status_filter,
        "title": _("إدارة السائقين"),
    }
    return render(request, "installations/traffic/driver_list.html", context)


@login_required
@user_passes_test(is_traffic_manager_or_superuser)
def vehicle_list(request):
    """عرض قائمة المركبات مع إمكانية البحث والفلترة"""
    search_query = request.GET.get("q", "")
    status_filter = request.GET.get("status", "")

    vehicles = Vehicle.objects.all().order_by("status", "name")

    if search_query:
        vehicles = vehicles.filter(
            Q(name__icontains=search_query)
            | Q(plate_number__icontains=search_query)
            | Q(model__icontains=search_query)
        )

    if status_filter:
        vehicles = vehicles.filter(status=status_filter)

    context = {
        "vehicles": vehicles,
        "search_query": search_query,
        "status_filter": status_filter,
        "title": _("إدارة المركبات"),
    }
    return render(request, "installations/traffic/vehicle_list.html", context)


@login_required
@user_passes_test(is_traffic_manager_or_superuser)
def mission_list(request):
    """عرض قائمة المهام مع فلترة متقدمة"""
    # الفلاتر
    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")
    driver_id = request.GET.get("driver")
    vehicle_id = request.GET.get("vehicle")
    status = request.GET.get("status")
    mission_type = request.GET.get("type")

    # جلب المهام (التي أنشئت يدوياً أو بواسطة مدير الحركة)
    missions = (
        VehicleMission.objects.select_related("vehicle", "driver", "created_by")
        .prefetch_related(
            "scheduled_installations",
            "scheduled_installations__order",
            "scheduled_installations__order__customer",
        )
        .order_by("-date", "-created_at")
    )

    # تطبيق الفلاتر
    if date_from:
        missions = missions.filter(date__gte=date_from)
    if date_to:
        missions = missions.filter(date__lte=date_to)
    if driver_id:
        missions = missions.filter(driver_id=driver_id)
    if vehicle_id:
        missions = missions.filter(vehicle_id=vehicle_id)
    if status:
        missions = missions.filter(status=status)
    if mission_type:
        missions = missions.filter(mission_type=mission_type)

    # الإحصائيات
    stats = {
        "total": missions.count(),
        "active": missions.filter(status="active").count(),
        "completed": missions.filter(status="completed").count(),
        "pending": missions.filter(status="pending").count(),
    }

    # التصفح (Pagination)
    paginator = Paginator(missions, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "missions": page_obj,
        "stats": stats,
        "drivers": Driver.objects.filter(is_active=True),
        "vehicles": Vehicle.objects.filter(status="active"),
        "title": _("سجل المهام والتحركات المعينة"),
        # الحفاظ على القيم في الفلتر
        "filters": {
            "date_from": date_from,
            "date_to": date_to,
            "driver_id": int(driver_id) if driver_id else "",
            "vehicle_id": int(vehicle_id) if vehicle_id else "",
            "status": status,
            "mission_type": mission_type,
        },
    }
    return render(request, "installations/traffic/mission_list.html", context)


@require_http_methods(["POST"])
@login_required
@user_passes_test(is_traffic_manager_or_superuser)
def complete_mission(request, pk):
    """إنهاء المهمة وتحديث حالتها"""
    mission = get_object_or_404(VehicleMission, pk=pk)

    if mission.status == "completed":
        messages.warning(request, _("هذه المهمة مكتملة بالفعل."))
        return redirect("installations:mission_list")

    # تحديث الحالة والوقت
    mission.status = "completed"

    # استخدام الوقت الحالي كنهاية للمهمة
    now = timezone.now()
    # تحويل الوقت المحلي إلى وقت فقط إذا كان الحقل TimeField
    local_now = timezone.localtime(now).time()

    # إذا لم يكن هناك وقت بدء، نستخدم الوقت الحالي كبداية ونهاية (للمهام الفورية)
    if not mission.start_time:
        mission.start_time = local_now

    mission.end_time = local_now

    # إضافة ملاحظات إن وجدت
    notes = request.POST.get("notes")
    if notes:
        current_desc = mission.description or ""
        mission.description = f"{current_desc}\n\n[تم الإكمال في {now.strftime('%H:%M')}]: {notes}".strip()

    mission.save()

    # تحديث حالة المركبة لتصبح شاغرة (نشطة)
    if mission.vehicle:
        mission.vehicle.status = "active"
        mission.vehicle.save()

    messages.success(request, _("تم إنهاء المهمة بنجاح والمركبة الآن شاغرة."))

    return redirect("installations:mission_list")


@login_required
@user_passes_test(is_traffic_manager_or_superuser)
def vehicle_detail(request, pk):
    """عرض تفاصيل المركبة وسجل حركتها"""
    vehicle = get_object_or_404(Vehicle, pk=pk)

    # جلب سجل المهام
    missions = vehicle.missions.select_related(
        "driver", "installation", "installation__order", "created_by"
    ).order_by("-date", "-start_time")

    context = {
        "vehicle": vehicle,
        "missions": missions,
        "title": f"{_('تفاصيل المركبة')}: {vehicle.name}",
    }
    return render(request, "installations/traffic/vehicle_detail.html", context)


# --- Views للمستخدمين العاديين ---


@login_required
def request_vehicle(request):
    """صفحة طلب مركبة للمستخدمين"""
    if request.method == "POST":
        date_str = request.POST.get("date")
        time_str = request.POST.get("time")
        purpose = request.POST.get("purpose")

        if date_str and purpose:
            VehicleRequest.objects.create(
                requester=request.user,
                requested_date=date_str,
                requested_time=time_str if time_str else None,
                purpose=purpose,
            )
            messages.success(request, _("تم إرسال طلب المركبة للإدارة"))
            return redirect("home")  # أو أي صفحة مناسبة

    return render(request, "installations/traffic/request_vehicle.html")


# --- CRUD Views القديمة (Drivers/Vehicles) ---
# (نحتفظ بها كما هي أو نعدلها إذا لزم الأمر)


@login_required
@user_passes_test(is_traffic_manager_or_superuser)
def driver_create(request):
    if request.method == "POST":
        form = DriverForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _("تم إضافة السائق بنجاح"))
            return redirect("installations:traffic_dashboard")
    else:
        form = DriverForm()

    context = {"form": form, "title": _("إضافة سائق جديد")}
    return render(request, "installations/traffic/driver_form.html", context)


@login_required
@user_passes_test(is_traffic_manager_or_superuser)
def driver_update(request, pk):
    driver = get_object_or_404(Driver, pk=pk)
    if request.method == "POST":
        form = DriverForm(request.POST, instance=driver)
        if form.is_valid():
            form.save()
            messages.success(request, _("تم تحديث بيانات السائق بنجاح"))
            return redirect("installations:traffic_dashboard")
    else:
        form = DriverForm(instance=driver)

    context = {"form": form, "title": _("تعديل بيانات السائق")}
    return render(request, "installations/traffic/driver_form.html", context)


@login_required
@user_passes_test(is_traffic_manager_or_superuser)
def driver_delete(request, pk):
    driver = get_object_or_404(Driver, pk=pk)
    if request.method == "POST":
        driver.delete()  # Soft delete
        messages.success(request, _("تم حذف السائق بنجاح"))
        return redirect("installations:traffic_dashboard")
    return redirect("installations:traffic_dashboard")


@login_required
@user_passes_test(is_traffic_manager_or_superuser)
def vehicle_create(request):
    if request.method == "POST":
        form = VehicleForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _("تم إضافة المركبة بنجاح"))
            return redirect("installations:traffic_dashboard")
    else:
        form = VehicleForm()

    context = {"form": form, "title": _("إضافة مركبة جديدة")}
    return render(request, "installations/traffic/vehicle_form.html", context)


@login_required
@user_passes_test(is_traffic_manager_or_superuser)
def vehicle_update(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk)
    if request.method == "POST":
        form = VehicleForm(request.POST, instance=vehicle)
        if form.is_valid():
            form.save()
            messages.success(request, _("تم تحديث بيانات المركبة بنجاح"))
            return redirect("installations:traffic_dashboard")
    else:
        form = VehicleForm(instance=vehicle)

    context = {"form": form, "title": _("تعديل بيانات المركبة")}
    return render(request, "installations/traffic/vehicle_form.html", context)


@login_required
@user_passes_test(is_traffic_manager_or_superuser)
def vehicle_delete(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk)
    if request.method == "POST":
        vehicle.delete()  # Soft delete
        messages.success(request, _("تم حذف المركبة بنجاح"))
        return redirect("installations:traffic_dashboard")
    return redirect("installations:traffic_dashboard")
