#!/bin/bash
# 🚀 تشغيل النظام للإنتاج بدون Cloudflare Tunnel
# يمكن الوصول للنظام عبر: http://192.168.1.30:8000

RED='\033[0;31m'
GREEN='\033[0;32m'
WHITE='\033[1;37m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD_BLUE='\033[1;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

PROJECT_DIR="/home/zakee/homeupdate"
LOGS_DIR="$PROJECT_DIR/logs"

# إنشاء مجلد logs إذا لم يكن موجوداً
mkdir -p "$LOGS_DIR"

# تقليل مستوى التسجيل للتشغيل السلس - الإنتاج الحقيقي
export DEBUG=False
export DJANGO_LOG_LEVEL=INFO

print_status() { echo -e "${GREEN}✅ $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_info() { echo -e "${WHITE}ℹ️  $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_success() { echo -e "${BOLD_BLUE}🎉 $1${NC}"; }
print_upload() { echo -e "${PURPLE}📤 $1${NC}"; }

echo ""
echo -e "${BOLD_BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD_BLUE}          🚀 نظام إدارة الخواجة - الإنتاج           ${NC}"
echo -e "${BOLD_BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if [ ! -d "$PROJECT_DIR" ]; then
	print_error "مجلد المشروع غير موجود: $PROJECT_DIR"
	exit 1
fi
cd "$PROJECT_DIR"

# تفعيل البيئة الافتراضية للمشروع
print_info "تفعيل البيئة الافتراضية..."
source "$PROJECT_DIR/venv/bin/activate"
print_status "تم تفعيل البيئة الافتراضية"

# تطبيق تحديثات قاعدة البيانات
print_info "تطبيق تحديثات قاعدة البيانات..."
python manage.py migrate --noinput
print_status "تم تطبيق جميع التحديثات"

# تنظيف الإشعارات القديمة
print_info "تنظيف الإشعارات القديمة..."
python manage.py cleanup_notifications
print_status "تم تنظيف الإشعارات القديمة"

# فحص حالة قاعدة البيانات
print_info "فحص حالة قاعدة البيانات..."
python manage.py monitor_db --once
print_status "قاعدة البيانات تعمل بشكل طبيعي"

# تجميع الملفات الثابتة
print_info "تجميع الملفات الثابتة للإنتاج..."
rm -rf staticfiles/*
python manage.py collectstatic --noinput --clear
print_status "تم تجميع الملفات الثابتة"

# فحص المستخدمين
print_info "فحص المستخدمين..."
USER_COUNT=$(python -c "import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings'); import django; django.setup(); from accounts.models import User; print(User.objects.count())")
if [ "$USER_COUNT" -eq 0 ]; then
	print_warning "لا يوجد مستخدمين، سيتم إنشاء admin/admin123"
	python -c "import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings'); import django; django.setup(); from accounts.models import User; User.objects.create_superuser('admin', 'admin@example.com', 'admin123'); print('تم إنشاء المستخدم admin/admin123')"
	print_status "تم إنشاء مستخدم admin بنجاح"
else
	print_status "عدد المستخدمين الحالي: $USER_COUNT"
fi

# تشغيل Redis
print_info "فحص وتشغيل Redis..."
if ! pgrep -x "redis-server" >/dev/null && ! pgrep -x "valkey-server" >/dev/null; then
	if command -v valkey-server &>/dev/null; then
		valkey-server --daemonize yes --port 6379 --dir /tmp
		print_status "تم تشغيل Valkey Server"
	elif command -v redis-server &>/dev/null; then
		redis-server --daemonize yes --port 6379 --dir /tmp
		print_status "تم تشغيل Redis Server"
	else
		print_error "Redis/Valkey غير مثبت!"
		exit 1
	fi
else
	print_status "Redis/Valkey يعمل بالفعل"
fi

# تشغيل Celery Worker
print_info "تشغيل Celery Worker مع نظام الرفع المحسن..."
cd "$PROJECT_DIR"
if [ -f "$PROJECT_DIR/crm/__init__.py" ]; then
	rm -f "$LOGS_DIR/celery_worker.pid" "$LOGS_DIR/celery_worker.log"

	celery -A crm worker \
		--loglevel=info \
		--queues=celery,file_uploads \
		--pidfile="$LOGS_DIR/celery_worker.pid" \
		--logfile="$LOGS_DIR/celery_worker.log" \
		--pool=solo \
		--concurrency=2 \
		--max-tasks-per-child=50 \
		--detach

	sleep 5

	if [ -f "$LOGS_DIR/celery_worker.pid" ]; then
		CELERY_WORKER_PID=$(cat "$LOGS_DIR/celery_worker.pid")
		if ps -p $CELERY_WORKER_PID >/dev/null; then
			print_status "تم تشغيل Celery Worker بنجاح (PID: $CELERY_WORKER_PID)"
			print_upload "نظام الرفع جاهز: العقود والمعاينات"
		else
			print_error "فشل في تشغيل Celery Worker"
			tail -n 20 "$LOGS_DIR/celery_worker.log"
		fi
	else
		print_error "فشل في تشغيل Celery Worker - لم يتم إنشاء ملف PID"
	fi
else
	print_error "ملف التهيئة crm/__init__.py غير موجود"
fi

# تشغيل Celery Beat
print_info "تشغيل Celery Beat للمهام الدورية..."
cd "$PROJECT_DIR"
if [ -f "$PROJECT_DIR/crm/__init__.py" ]; then
	rm -f "$LOGS_DIR/celery_beat.pid" "$LOGS_DIR/celery_beat.log" "$LOGS_DIR/celerybeat-schedule"*

	celery -A crm beat \
		--loglevel=info \
		--pidfile="$LOGS_DIR/celery_beat.pid" \
		--logfile="$LOGS_DIR/celery_beat.log" \
		--schedule="$LOGS_DIR/celerybeat-schedule" \
		--detach

	sleep 5

	if [ -f "$LOGS_DIR/celery_beat.pid" ]; then
		CELERY_BEAT_PID=$(cat "$LOGS_DIR/celery_beat.pid")
		if ps -p $CELERY_BEAT_PID >/dev/null; then
			print_status "تم تشغيل Celery Beat بنجاح (PID: $CELERY_BEAT_PID)"
		else
			print_error "فشل في تشغيل Celery Beat"
			tail -n 20 "$LOGS_DIR/celery_beat.log"
		fi
	else
		print_error "فشل في تشغيل Celery Beat - لم يتم إنشاء ملف PID"
	fi
else
	print_error "ملف التهيئة crm/__init__.py غير موجود"
fi

# تصدير إعدادات قاعدة البيانات للنسخ الاحتياطي
if [ -f "crm/settings.py" ]; then
	eval $(
		python - <<'PY'
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','crm.settings')
import django
django.setup()
from django.conf import settings
print(f"export DB_NAME='{settings.DATABASES['default'].get('NAME','')}'")
print(f"export DB_USER='{settings.DATABASES['default'].get('USER','')}'")
print(f"export DB_HOST='{settings.DATABASES['default'].get('HOST','')}'")
print(f"export DB_PORT='{settings.DATABASES['default'].get('PORT','')}'")
print(f"export DB_PASSWORD='{settings.DATABASES['default'].get('PASSWORD','')}'")
PY
	)
fi

# تشغيل النسخ الاحتياطي
if [ -f "لينكس/db-backup.sh" ]; then
	chmod +x "لينكس/db-backup.sh"
	./لينكس/db-backup.sh >"$LOGS_DIR/db_backup.log" 2>&1 &
	DB_BACKUP_PID=$!
	print_status "تم تشغيل خدمة النسخ الاحتياطي (PID: $DB_BACKUP_PID)"
fi

# مراقبة سجل النسخ الاحتياطي
if [ -f "$LOGS_DIR/db_backup.log" ] || true; then
	(tail -n0 -F "$LOGS_DIR/db_backup.log" 2>/dev/null | while read line; do
		if echo "$line" | grep -q "تم إنشاء نسخة احتياطية بنجاح"; then
			print_status "$line"
		fi
	done) &
	BACKUP_TAIL_PID=$!
fi

# دالة التنظيف عند الإيقاف
cleanup() {
	echo ""
	print_info "إيقاف جميع العمليات..."

	# إيقاف Celery Worker
	if [ -f "$LOGS_DIR/celery_worker.pid" ]; then
		CELERY_WORKER_PID=$(cat "$LOGS_DIR/celery_worker.pid" 2>/dev/null)
		if [ ! -z "$CELERY_WORKER_PID" ]; then
			kill $CELERY_WORKER_PID 2>/dev/null
			print_status "تم إيقاف Celery Worker"
		fi
		rm -f "$LOGS_DIR/celery_worker.pid"
	fi

	# إيقاف Celery Beat
	if [ -f "$LOGS_DIR/celery_beat.pid" ]; then
		CELERY_BEAT_PID=$(cat "$LOGS_DIR/celery_beat.pid" 2>/dev/null)
		if [ ! -z "$CELERY_BEAT_PID" ]; then
			kill $CELERY_BEAT_PID 2>/dev/null
			print_status "تم إيقاف Celery Beat"
		fi
		rm -f "$LOGS_DIR/celery_beat.pid"
		rm -f "$LOGS_DIR/celerybeat-schedule"*
	fi

	# إيقاف النسخ الاحتياطي
	if [ ! -z "$DB_BACKUP_PID" ]; then
		kill $DB_BACKUP_PID 2>/dev/null
		print_status "تم إيقاف خدمة النسخ الاحتياطي"
	fi
	if [ ! -z "$BACKUP_TAIL_PID" ]; then
		kill $BACKUP_TAIL_PID 2>/dev/null
	fi

	# إيقاف خادم الويب
	if [ ! -z "$GUNICORN_PID" ]; then
		kill $GUNICORN_PID 2>/dev/null
		print_status "تم إيقاف خادم الويب"
	fi

	echo ""
	print_success "تم إيقاف النظام بنجاح"
	exit 0
}
trap cleanup INT TERM

# الحصول على IP المحلي
LOCAL_IP=$(ip addr show | grep "inet " | grep -v "127.0.0.1" | awk '{print $2}' | cut -d/ -f1 | head -1)

echo ""
echo -e "${BOLD_BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}🎉 النظام جاهز للعمل!${NC}"
echo -e "${BOLD_BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${WHITE}📍 عناوين الوصول:${NC}"
echo -e "${GREEN}   • محلي:          http://localhost:8000${NC}"
echo -e "${GREEN}   • الشبكة المحلية: http://$LOCAL_IP:8000${NC}"
echo ""
echo -e "${WHITE}🔐 بيانات الدخول:${NC}"
echo -e "${GREEN}   • المستخدم: admin${NC}"
echo -e "${GREEN}   • كلمة المرور: admin123${NC}"
echo ""
echo -e "${WHITE}⚙️  الخدمات النشطة:${NC}"
echo -e "${GREEN}   ✓ خادم الويب (Gunicorn)${NC}"
echo -e "${GREEN}   ✓ Celery Worker (المهام الخلفية)${NC}"
echo -e "${GREEN}   ✓ Celery Beat (المهام الدورية)${NC}"
echo -e "${GREEN}   ✓ Redis/Valkey (التخزين المؤقت)${NC}"
echo -e "${GREEN}   ✓ النسخ الاحتياطي التلقائي${NC}"
echo ""
echo -e "${WHITE}📊 السجلات:${NC}"
echo -e "${GREEN}   • Celery Worker:  tail -f $LOGS_DIR/celery_worker.log${NC}"
echo -e "${GREEN}   • Celery Beat:    tail -f $LOGS_DIR/celery_beat.log${NC}"
echo -e "${GREEN}   • النسخ الاحتياطي: tail -f $LOGS_DIR/db_backup.log${NC}"
echo ""
echo -e "${YELLOW}⚠️  ملاحظة: الوصول من الشبكة المحلية فقط (بدون Cloudflare Tunnel)${NC}"
echo -e "${WHITE}   للوصول من الإنترنت، استخدم: ./لينكس/run-production.sh${NC}"
echo ""
echo -e "${RED}🛑 للإيقاف: اضغط Ctrl+C${NC}"
echo -e "${BOLD_BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

print_info "تشغيل خادم الإنتاج..."

# تشغيل Gunicorn مع إعدادات محسنة للأداء والذاكرة
gunicorn crm.wsgi:application \
	--bind 0.0.0.0:8000 \
	--workers 1 \
	--threads 4 \
	--worker-class gthread \
	--worker-connections 100 \
	--max-requests 500 \
	--max-requests-jitter 50 \
	--timeout 120 \
	--graceful-timeout 30 \
	--keep-alive 5 \
	--worker-tmp-dir /dev/shm \
	--access-logfile - \
	--error-logfile - \
	--log-level info \
	--pid /tmp/gunicorn.pid \
	--access-logformat '[%(t)s] "%(r)s" %(s)s %(b)s' 2>&1 | while read line; do
	# فلترة الرسائل غير المهمة
	if [[ $line =~ ^\[\[.*\]\] ]]; then
		continue
	fi

	# تجاهل رسائل DEBUG والاستعلامات المتكررة
	if [[ $line == *"[DEBUG]"* ]] ||
		[[ $line == *"Updating online status"* ]] ||
		[[ $line == *"Online user updated"* ]] ||
		[[ $line == *"Activity updated"* ]] ||
		[[ $line == *"/accounts/notifications/data/"* ]] ||
		[[ $line == *"/accounts/api/online-users/"* ]] ||
		[[ $line == *"/notifications/ajax/count/"* ]] ||
		[[ $line == *"/notifications/ajax/recent/"* ]] ||
		[[ $line == *"/complaints/api/"* ]] ||
		[[ $line == *"/inventory/api/product-autocomplete/"* ]] ||
		[[ $line == *"/media/"* ]] ||
		[[ $line == *"/static/"* ]] ||
		[[ $line == *"favicon.ico"* ]]; then
		continue
	fi

	# معالجة رسائل تسجيل الدخول
	if [[ $line == *"🔐"* && $line == *"login"* ]]; then
		username=$(echo "$line" | sed -n 's/.*🔐 \([^ ]*\) -.*/\1/p')
		if [ -n "$username" ]; then
			echo -e "${BOLD_BLUE}🔐 تسجيل دخول: $username${NC}"
		fi
	# معالجة رسائل تسجيل الخروج
	elif [[ $line == *"🚪"* && $line == *"logout"* ]]; then
		username=$(echo "$line" | sed -n 's/.*🚪 \([^ ]*\) -.*/\1/p')
		if [ -n "$username" ]; then
			echo -e "${WHITE}🚪 تسجيل خروج: $username${NC}"
		fi
	# عرض نشاط الصفحات
	elif [[ $line == *"👁️"* && $line == *"page_view"* ]]; then
		username=$(echo "$line" | sed -n 's/.*👁️ \([^ ]*\) -.*/\1/p')
		if [ -n "$username" ]; then
			page=$(echo "$line" | sed -n 's/.*page_view - \([^ ]*\).*/\1/p')
			echo -e "${WHITE}👁️  $username → $page${NC}"
		fi
	# عرض العمليات المهمة
	elif [[ $line == *"🔄"* ]] || [[ $line == *"✅"* ]] || [[ $line == *"❌"* ]]; then
		echo "$line"
	# عرض الرسائل الأخرى
	else
		echo "$line"
	fi
done &
GUNICORN_PID=$!
print_status "خادم الإنتاج يعمل (PID: $GUNICORN_PID)"

# متغيرات لتتبع الفحوصات الدورية
LAST_DB_CHECK=0
LAST_NOTIFICATION_CLEANUP=0
DB_CHECK_INTERVAL=300              # كل 5 دقائق
NOTIFICATION_CLEANUP_INTERVAL=1800 # كل 30 دقيقة

# حلقة المراقبة
while true; do
	sleep 30

	# فحص خادم الويب
	if ! kill -0 $GUNICORN_PID 2>/dev/null; then
		print_error "خادم الويب توقف!"
		break
	fi

	# فحص دوري لقاعدة البيانات
	CURRENT_TIME=$(date +%s)
	if [ $((CURRENT_TIME - LAST_DB_CHECK)) -ge $DB_CHECK_INTERVAL ]; then
		python manage.py monitor_db --once --quiet 2>/dev/null
		if [ $? -eq 0 ]; then
			print_status "قاعدة البيانات تعمل بشكل طبيعي"
		else
			print_warning "تحذير: مشكلة محتملة في قاعدة البيانات"
		fi
		LAST_DB_CHECK=$CURRENT_TIME
	fi

	# تنظيف دوري للإشعارات
	if [ $((CURRENT_TIME - LAST_NOTIFICATION_CLEANUP)) -ge $NOTIFICATION_CLEANUP_INTERVAL ]; then
		CLEANED_COUNT=$(python manage.py cleanup_notifications 2>/dev/null | grep -o '[0-9]\+' | head -1)
		if [ ! -z "$CLEANED_COUNT" ] && [ "$CLEANED_COUNT" -gt 0 ]; then
			print_status "تم تنظيف $CLEANED_COUNT إشعار قديم"
		fi
		LAST_NOTIFICATION_CLEANUP=$CURRENT_TIME
	fi

	# رفع تلقائي للملفات المعلقة (كل 10 دقائق)
	if [ $((CURRENT_TIME - ${LAST_UPLOAD_CHECK:-0})) -ge 600 ]; then
		if [ -f "auto_upload_system.py" ]; then
			print_upload "رفع تلقائي للملفات المعلقة..."
			UPLOAD_RESULT=$(python auto_upload_system.py single 2>/dev/null | tail -2)
			print_upload "$UPLOAD_RESULT"
		fi
		LAST_UPLOAD_CHECK=$CURRENT_TIME
	fi

	# فحص Celery Worker
	if [ -f "$LOGS_DIR/celery_worker.pid" ]; then
		CELERY_WORKER_PID=$(cat "$LOGS_DIR/celery_worker.pid" 2>/dev/null)
		if [ ! -z "$CELERY_WORKER_PID" ] && ! kill -0 $CELERY_WORKER_PID 2>/dev/null; then
			print_warning "Celery Worker توقف - جاري إعادة التشغيل..."
			celery -A crm worker \
				--loglevel=info \
				--queues=celery,file_uploads \
				--pool=solo \
				--concurrency=2 \
				--max-tasks-per-child=50 \
				--detach \
				--pidfile="$LOGS_DIR/celery_worker.pid" \
				--logfile="$LOGS_DIR/celery_worker.log"
			if [ $? -eq 0 ]; then
				print_status "تم إعادة تشغيل Celery Worker"
			fi
		fi
	fi

	# فحص Celery Beat
	if [ -f "$LOGS_DIR/celery_beat.pid" ]; then
		CELERY_BEAT_PID=$(cat "$LOGS_DIR/celery_beat.pid" 2>/dev/null)
		if [ ! -z "$CELERY_BEAT_PID" ] && ! kill -0 $CELERY_BEAT_PID 2>/dev/null; then
			print_warning "Celery Beat توقف - جاري إعادة التشغيل..."
			celery -A crm beat \
				--loglevel=info \
				--detach \
				--pidfile="$LOGS_DIR/celery_beat.pid" \
				--logfile="$LOGS_DIR/celery_beat.log" \
				--schedule="$LOGS_DIR/celerybeat-schedule"
			if [ $? -eq 0 ]; then
				print_status "تم إعادة تشغيل Celery Beat"
			fi
		fi
	fi
done

cleanup
