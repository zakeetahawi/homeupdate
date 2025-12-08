from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.models import Permission
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import UserSerializer, RoleSerializer, RoleDetailSerializer, UserRoleSerializer, PermissionSerializer
from .models import Role, UserRole, BranchDevice
from .services.dashboard_service import DashboardService
import json

User = get_user_model()

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_user(request):
    """
    نقطة نهاية للحصول على معلومات المستخدم الحالي المصادق
    تستخدم مع نظام المصادقة JWT
    """
    user = request.user
    serializer = UserSerializer(user)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_info(request):
    """
    نقطة نهاية للحصول على معلومات إضافية عن المستخدم الحالي
    مثل الإشعارات غير المقروءة والصلاحيات
    """
    user = request.user
    
    # استرجاع معلومات المستخدم الأساسية
    user_data = UserSerializer(user).data
    
    # إضافة معلومات إضافية
    # user_data['unread_notifications_count'] = getattr(user, 'notifications', []).filter(is_read=False).count()  # تم إزالة نظام الإشعارات
    
    # إضافة الصلاحيات والمجموعات
    permissions = list(user.get_all_permissions())
    user_data['permissions'] = permissions
    user_data['groups'] = list(user.groups.values_list('name', flat=True))
    
    return Response({
        'user': user_data,
        'is_authenticated': True,
        'token_valid': True
    })

@api_view(['POST'])
@permission_classes([AllowAny])
def login_api(request):
    username = request.data.get('username')
    password = request.data.get('password')
    
    if not username or not password:
        return Response({'error': 'يرجى إدخال اسم المستخدم وكلمة المرور'}, status=status.HTTP_400_BAD_REQUEST)
    
    user = authenticate(username=username, password=password)
    
    if user is not None:
        refresh = RefreshToken.for_user(user)
        return Response({
            'token': str(refresh.access_token),
            'refresh': str(refresh),
            'user': {
                'username': user.username,
                'id': user.id,
                'is_staff': user.is_staff
            }
        })
    else:
        return Response(
            {'error': 'اسم المستخدم أو كلمة المرور غير صحيحة'}, 
            status=status.HTTP_401_UNAUTHORIZED
        )

# API views for Role Management
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def role_list_api(request):
    """قائمة الأدوار المتاحة في النظام"""
    roles = Role.objects.all()
    
    # تصفية الأدوار حسب النوع
    role_type = request.query_params.get('type')
    if role_type == 'system':
        roles = roles.filter(is_system_role=True)
    elif role_type == 'custom':
        roles = roles.filter(is_system_role=False)
    
    # البحث عن الأدوار
    search = request.query_params.get('search')
    if search:
        roles = roles.filter(name__icontains=search)
    
    serializer = RoleSerializer(roles, many=True)
    return Response(serializer.data)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated, IsAdminUser])
def role_create_api(request):
    """إنشاء دور جديد"""
    if request.method == 'POST':
        serializer = RoleDetailSerializer(data=request.data)
        if serializer.is_valid():
            role = serializer.save()
            
            # إضافة الصلاحيات إذا تم تحديدها
            permissions_ids = request.data.get('permissions_ids', [])
            if permissions_ids:
                permissions = Permission.objects.filter(id__in=permissions_ids)
                role.permissions.set(permissions)
            
            return Response(RoleDetailSerializer(role).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    return Response({'message': 'استخدم طريقة POST لإنشاء دور جديد'})


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated, IsAdminUser])
def role_detail_api(request, pk):
    """تفاصيل وتعديل وحذف دور"""
    try:
        role = Role.objects.get(pk=pk)
    except Role.DoesNotExist:
        return Response({'error': 'الدور غير موجود'}, status=status.HTTP_404_NOT_FOUND)
    
    # التحقق من أنه لا يمكن حذف أدوار النظام إلا بواسطة المدير العام
    if role.is_system_role and not request.user.is_superuser and request.method == 'DELETE':
        return Response({'error': 'لا يمكن حذف أدوار النظام إلا بواسطة المدير العام'}, status=status.HTTP_403_FORBIDDEN)
    
    if request.method == 'GET':
        serializer = RoleDetailSerializer(role)
        return Response(serializer.data)
    
    elif request.method == 'PUT':
        serializer = RoleDetailSerializer(role, data=request.data, partial=True)
        if serializer.is_valid():
            updated_role = serializer.save()
            
            # تحديث الصلاحيات إذا تم تحديدها
            permissions_ids = request.data.get('permissions_ids')
            if permissions_ids is not None:
                permissions = Permission.objects.filter(id__in=permissions_ids)
                updated_role.permissions.set(permissions)
            
            # تحديث صلاحيات المستخدمين الذين لديهم هذا الدور
            for user_role in UserRole.objects.filter(role=updated_role):
                user = user_role.user
                # إعادة تعيين الصلاحيات من الأدوار
                user_roles = user.user_roles.all()
                # إعادة تعيين صلاحيات المستخدم
                user.user_permissions.clear()
                for ur in user_roles:
                    for permission in ur.role.permissions.all():
                        user.user_permissions.add(permission)
            
            return Response(RoleDetailSerializer(updated_role).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        # حذف علاقات الدور بالمستخدمين
        UserRole.objects.filter(role=role).delete()
        
        # حذف الدور
        role.delete()
        
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_roles_api(request, user_id):
    """الحصول على قائمة أدوار مستخدم معين"""
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return Response({'error': 'المستخدم غير موجود'}, status=status.HTTP_404_NOT_FOUND)
    
    user_roles = UserRole.objects.filter(user=user)
    serializer = UserRoleSerializer(user_roles, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminUser])
def add_user_role_api(request, user_id):
    """إضافة دور لمستخدم معين"""
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return Response({'error': 'المستخدم غير موجود'}, status=status.HTTP_404_NOT_FOUND)
    
    role_id = request.data.get('role_id')
    if not role_id:
        return Response({'error': 'يرجى تحديد الدور'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        role = Role.objects.get(pk=role_id)
    except Role.DoesNotExist:
        return Response({'error': 'الدور غير موجود'}, status=status.HTTP_404_NOT_FOUND)
    
    # التحقق من أن الدور غير مسند بالفعل للمستخدم
    if UserRole.objects.filter(user=user, role=role).exists():
        return Response({'error': 'الدور مسند بالفعل لهذا المستخدم'}, status=status.HTTP_400_BAD_REQUEST)
    
    # إنشاء علاقة بين الدور والمستخدم
    user_role = UserRole.objects.create(user=user, role=role)
    
    # إضافة صلاحيات الدور للمستخدم
    for permission in role.permissions.all():
        user.user_permissions.add(permission)
    
    serializer = UserRoleSerializer(user_role)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated, IsAdminUser])
def remove_user_role_api(request, user_id, role_id):
    """إزالة دور من مستخدم معين"""
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return Response({'error': 'المستخدم غير موجود'}, status=status.HTTP_404_NOT_FOUND)
    
    try:
        role = Role.objects.get(pk=role_id)
    except Role.DoesNotExist:
        return Response({'error': 'الدور غير موجود'}, status=status.HTTP_404_NOT_FOUND)
    
    try:
        user_role = UserRole.objects.get(user=user, role=role)
    except UserRole.DoesNotExist:
        return Response({'error': 'الدور غير مسند لهذا المستخدم'}, status=status.HTTP_404_NOT_FOUND)
    
    # حذف العلاقة بين الدور والمستخدم
    user_role.delete()
    
    # إزالة صلاحيات الدور من المستخدم (التي لا تنتمي لأدوار أخرى)
    for permission in role.permissions.all():
        if not UserRole.objects.filter(user=user, role__permissions=permission).exists():
            user.user_permissions.remove(permission)
    
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_permissions(request):
    """الحصول على قائمة صلاحيات المستخدم الحالي"""
    user = request.user
    
    # الحصول على الصلاحيات المباشرة من المستخدم
    direct_permissions = user.user_permissions.all()
    
    # الحصول على الصلاحيات من الأدوار المسندة للمستخدم
    roles_permissions = Permission.objects.filter(
        role__user_roles__user=user
    ).distinct()
    
    # دمج الصلاحيات المباشرة وصلاحيات الأدوار
    all_permissions = direct_permissions | roles_permissions
    
    serializer = PermissionSerializer(all_permissions, many=True)
    return Response(serializer.data)

@login_required
def dashboard_stats(request):
    """
    Return dashboard statistics
    """
    stats = DashboardService.get_cached_stats(request.user)
    return JsonResponse(stats)

@login_required
def dashboard_activities(request):
    """
    Return recent activities
    """
    activities = DashboardService.get_recent_activities(
        user=request.user,
        limit=request.GET.get('limit', 10)
    )
    return JsonResponse({'activities': activities})

@login_required
def dashboard_orders(request):
    """
    Return recent orders
    """
    orders = DashboardService.get_recent_orders(
        user=request.user,
        limit=request.GET.get('limit', 5)
    )
    return JsonResponse({'orders': orders})

@login_required
def dashboard_trends(request):
    """
    Return trends data for charts
    """
    days = int(request.GET.get('days', 30))
    data = DashboardService.get_trends_data(days=days)
    return JsonResponse(data)

@require_http_methods(["POST"])
@csrf_exempt
def check_device_api(request):
    """
    API للتحقق من تسجيل جهاز بناءً على بصمته أو معرفه الثابت
    """
    try:
        data = json.loads(request.body)
        device_fingerprint = data.get('device_fingerprint')
        hardware_serial = data.get('hardware_serial')
        
        if not device_fingerprint and not hardware_serial:
            return JsonResponse({
                'registered': False,
                'error': 'البصمة أو المعرف الثابت مطلوب'
            }, status=400)
        
        device = None
        found_by = None
        
        # البحث أولاً بالـ hardware_serial (أكثر استقراراً)
        if hardware_serial:
            try:
                device = BranchDevice.objects.get(hardware_serial=hardware_serial)
                found_by = 'hardware_serial'
            except BranchDevice.DoesNotExist:
                pass
        
        # إذا لم يُعثر عليه، البحث بالـ fingerprint
        if not device and device_fingerprint:
            try:
                device = BranchDevice.objects.get(device_fingerprint=device_fingerprint)
                found_by = 'fingerprint'
            except BranchDevice.DoesNotExist:
                pass
        
        if device:
            return JsonResponse({
                'registered': True,
                'device_name': device.device_name,
                'branch_name': device.branch.name,
                'branch_id': device.branch.id,
                'is_active': device.is_active,
                'is_blocked': device.is_blocked,
                'blocked_reason': device.blocked_reason if device.is_blocked else None,
                'last_used': device.last_used.strftime('%Y-%m-%d %H:%M') if device.last_used else None,
                'last_used_by': device.last_used_by.username if device.last_used_by else None,
                'found_by': found_by,
                'hardware_serial': device.hardware_serial,
                'device_fingerprint': device.device_fingerprint[:16] + '...' if device.device_fingerprint else None,
            })
        else:
            return JsonResponse({
                'registered': False,
                'message': 'الجهاز غير مسجل في النظام',
                'searched_serial': hardware_serial,
                'searched_fingerprint': device_fingerprint[:16] + '...' if device_fingerprint else None,
            })
            
    except json.JSONDecodeError:
        return JsonResponse({
            'registered': False,
            'error': 'خطأ في البيانات المرسلة'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'registered': False,
            'error': str(e)
        }, status=500)
