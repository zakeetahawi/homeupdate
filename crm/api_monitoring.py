"""
API endpoints لمراقبة النظام وقاعدة البيانات
"""

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from django.views import View
from django.utils import timezone
from crm.monitoring import performance_monitor, get_monitoring_status
from crm.db_pool import get_pool_statistics, cleanup_pool
import json
import logging

logger = logging.getLogger('api_monitoring')


@staff_member_required
@require_http_methods(["GET"])
def monitoring_status(request):
    """
    API endpoint للحصول على حالة المراقبة
    """
    try:
        status = get_monitoring_status()
        
        # إضافة معلومات إضافية
        status['timestamp'] = timezone.now().isoformat()
        status['server_time'] = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        
        return JsonResponse({
            'success': True,
            'data': status
        })
        
    except Exception as e:
        logger.error(f"Error getting monitoring status: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@staff_member_required
@require_http_methods(["GET"])
def database_stats(request):
    """
    API endpoint للحصول على إحصائيات قاعدة البيانات
    """
    try:
        db_stats = performance_monitor.db_monitor.get_connection_stats()
        
        if db_stats:
            # إضافة تحليل للحالة
            total = db_stats['total_connections']
            
            if total >= 120:
                status_level = 'emergency'
                status_color = 'red'
                status_message = 'حالة طوارئ - عدد الاتصالات مرتفع جداً'
            elif total >= 90:
                status_level = 'critical'
                status_color = 'orange'
                status_message = 'حالة حرجة - عدد الاتصالات مرتفع'
            elif total >= 70:
                status_level = 'warning'
                status_color = 'yellow'
                status_message = 'تحذير - عدد الاتصالات مرتفع نسبياً'
            else:
                status_level = 'normal'
                status_color = 'green'
                status_message = 'الحالة طبيعية'
            
            db_stats.update({
                'status_level': status_level,
                'status_color': status_color,
                'status_message': status_message,
                'timestamp': timezone.now().isoformat()
            })
            
            return JsonResponse({
                'success': True,
                'data': db_stats
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'فشل في الحصول على إحصائيات قاعدة البيانات'
            }, status=500)
            
    except Exception as e:
        logger.error(f"Error getting database stats: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@staff_member_required
@require_http_methods(["GET"])
def system_stats(request):
    """
    API endpoint للحصول على إحصائيات النظام
    """
    try:
        system_stats = performance_monitor.system_monitor.get_system_stats()
        
        if system_stats:
            return JsonResponse({
                'success': True,
                'data': system_stats
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'فشل في الحصول على إحصائيات النظام'
            }, status=500)
            
    except Exception as e:
        logger.error(f"Error getting system stats: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@staff_member_required
@require_http_methods(["GET"])
def pool_stats(request):
    """
    API endpoint للحصول على إحصائيات connection pool
    """
    try:
        pool_stats = get_pool_statistics()
        
        return JsonResponse({
            'success': True,
            'data': {
                'pool_stats': pool_stats,
                'timestamp': timezone.now().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting pool stats: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@method_decorator(staff_member_required, name='dispatch')
@method_decorator(csrf_exempt, name='dispatch')
class DatabaseActionsView(View):
    """
    API endpoint لتنفيذ إجراءات على قاعدة البيانات
    """
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            action = data.get('action')
            
            if action == 'cleanup':
                # تنظيف الاتصالات الخاملة
                force = data.get('force', False)
                cleaned = performance_monitor.db_monitor.cleanup_connections(force=force)
                
                return JsonResponse({
                    'success': True,
                    'message': f'تم تنظيف {cleaned} اتصال',
                    'data': {
                        'connections_cleaned': cleaned,
                        'cleanup_type': 'طوارئ' if force else 'عادي'
                    }
                })
                
            elif action == 'cleanup_pool':
                # تنظيف connection pool
                cleanup_pool()
                
                return JsonResponse({
                    'success': True,
                    'message': 'تم تنظيف connection pool',
                    'data': {
                        'action': 'pool_cleanup'
                    }
                })
                
            elif action == 'start_monitoring':
                # بدء المراقبة
                interval = data.get('interval', 30)
                performance_monitor.start_monitoring(interval)
                
                return JsonResponse({
                    'success': True,
                    'message': f'تم بدء المراقبة (كل {interval} ثانية)',
                    'data': {
                        'monitoring_interval': interval
                    }
                })
                
            elif action == 'stop_monitoring':
                # إيقاف المراقبة
                performance_monitor.stop_monitoring_service()
                
                return JsonResponse({
                    'success': True,
                    'message': 'تم إيقاف المراقبة',
                    'data': {
                        'action': 'monitoring_stopped'
                    }
                })
                
            else:
                return JsonResponse({
                    'success': False,
                    'error': f'إجراء غير معروف: {action}'
                }, status=400)
                
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'بيانات JSON غير صحيحة'
            }, status=400)
            
        except Exception as e:
            logger.error(f"Error in database action: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)


@staff_member_required
@require_http_methods(["GET"])
def health_check(request):
    """
    API endpoint لفحص صحة النظام
    """
    try:
        # فحص قاعدة البيانات
        db_stats = performance_monitor.db_monitor.get_connection_stats()
        db_healthy = db_stats is not None and db_stats['total_connections'] < 100
        
        # فحص النظام
        system_stats = performance_monitor.system_monitor.get_system_stats()
        system_healthy = (
            system_stats is not None and 
            system_stats['memory']['percent'] < 90 and
            system_stats['cpu']['percent'] < 90
        )
        
        # فحص المراقبة
        monitoring_status = get_monitoring_status()
        monitoring_healthy = monitoring_status.get('monitoring_active', False)
        
        overall_healthy = db_healthy and system_healthy
        
        health_data = {
            'overall_healthy': overall_healthy,
            'database_healthy': db_healthy,
            'system_healthy': system_healthy,
            'monitoring_active': monitoring_healthy,
            'timestamp': timezone.now().isoformat(),
            'checks': {
                'database_connections': db_stats['total_connections'] if db_stats else 'unknown',
                'memory_usage': f"{system_stats['memory']['percent']:.1f}%" if system_stats else 'unknown',
                'cpu_usage': f"{system_stats['cpu']['percent']:.1f}%" if system_stats else 'unknown',
            }
        }
        
        status_code = 200 if overall_healthy else 503
        
        return JsonResponse({
            'success': True,
            'data': health_data
        }, status=status_code)
        
    except Exception as e:
        logger.error(f"Error in health check: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e),
            'overall_healthy': False
        }, status=500)


@staff_member_required
@require_http_methods(["GET"])
def alerts(request):
    """
    API endpoint للحصول على التحذيرات النشطة
    """
    try:
        status = get_monitoring_status()
        alerts_data = status.get('alerts', {})
        
        # تنظيم التحذيرات
        active_alerts = []
        for alert_type, alert_info in alerts_data.items():
            if alert_info:
                active_alerts.append({
                    'type': alert_type,
                    'level': alert_info['level'],
                    'connections': alert_info['connections'],
                    'timestamp': alert_info['timestamp'],
                    'message': f"عدد الاتصالات: {alert_info['connections']} - مستوى {alert_info['level']}"
                })
        
        return JsonResponse({
            'success': True,
            'data': {
                'active_alerts': active_alerts,
                'total_alerts': len(active_alerts),
                'timestamp': timezone.now().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
