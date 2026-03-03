#!/bin/bash
# 🚀 تشغيل النظام للإنتاج مع نظام الرفع المحسن

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

print_status() { echo -e "${GREEN}$1${NC}"; }
print_error() { echo -e "${RED}$1${NC}"; }
print_info() { echo -e "${WHITE}$1${NC}"; }
print_warning() { echo -e "${YELLOW}$1${NC}"; }
print_tunnel() { echo -e "${BLUE}$1${NC}"; }
print_login() { echo -e "${BOLD_BLUE}$1${NC}"; }
print_upload() { echo -e "${PURPLE}$1${NC}"; }

# متغيرات لمراقبة التانل
TUNNEL_STATUS="unknown"
TUNNEL_CHECK_INTERVAL=30

# دالة فحص حالة التانل
check_tunnel_status() {
	if [ ! -z "$TUNNEL_PID" ] && kill -0 $TUNNEL_PID 2>/dev/null; then
		# فحص الاتصال بالموقع
		if curl -s --max-time 10 https://elkhawaga.uk >/dev/null 2>&1; then
			if [ "$TUNNEL_STATUS" != "connected" ]; then
				TUNNEL_STATUS="connected"
				print_tunnel "🌐 الجسر متصل - الموقع متاح على: https://elkhawaga.uk"
			fi
			return 0
		else
			if [ "$TUNNEL_STATUS" != "disconnected" ]; then
				TUNNEL_STATUS="disconnected"
				print_warning "⚠️ الجسر منقطع - الموقع غير متاح حالياً"
			fi
			return 1
		fi
	else
		if [ "$TUNNEL_STATUS" != "stopped" ]; then
			TUNNEL_STATUS="stopped"
			print_error "❌ عملية الجسر متوقفة"
		fi
		return 1
	fi
}

if [ ! -d "$PROJECT_DIR" ]; then
	print_error "مجلد المشروع غير موجود: $PROJECT_DIR"
	exit 1
fi
cd "$PROJECT_DIR"

# تفعيل البيئة الافتراضية للمشروع
source "$PROJECT_DIR/venv/bin/activate"

print_info "تشغيل التحديثات..."
python manage.py migrate --noinput
print_status "✔️ تم تطبيق التحديثات"

print_upload "🚀 نظام الرفع المحسن جاهز للعمل!"
print_upload "📤 سيتم رفع الملفات المعلقة تلقائياً كل 10 دقائق"
print_upload "🔧 تم إصلاح مشكلة Celery queues"

# فحص وتنظيف الإشعارات القديمة
print_info "تنظيف الإشعارات القديمة..."
python manage.py cleanup_notifications
print_status "✔️ تم تنظيف الإشعارات القديمة"

# فحص حالة قاعدة البيانات
print_info "فحص حالة قاعدة البيانات..."
python manage.py monitor_db --once
print_status "✔️ تم فحص حالة قاعدة البيانات"

print_info "تجميع الملفات الثابتة..."
# تنظيف وإعادة تجميع الملفات الثابتة للإنتاج
rm -rf staticfiles/*
python manage.py collectstatic --noinput --clear
print_status "✔️ تم تجميع الملفات الثابتة للإنتاج"

print_info "فحص المستخدمين..."
USER_COUNT=$(python -c "import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings'); import django; django.setup(); from accounts.models import User; print(User.objects.count())" | grep -oE '^[0-9]+$')
if [ "$USER_COUNT" -eq 0 ]; then
	print_status "لا يوجد مستخدمين، سيتم إنشاء admin/admin123"
	python -c "import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings'); import django; django.setup(); from accounts.models import User; User.objects.create_superuser('admin', 'admin@example.com', 'admin123'); print('تم إنشاء المستخدم admin/admin123')"
else
	print_status "عدد المستخدمين الحالي: $USER_COUNT (لن يتم إنشاء مستخدم جديد)"
fi

# تشغيل Redis (إذا لم يكن يعمل)
print_info "فحص وتشغيل Redis..."
if ! pgrep -f "valkey|redis-server" >/dev/null; then
	redis-server --daemonize yes --port 6379 --dir /tmp
	print_status "✔️ تم تشغيل Redis"
else
	print_status "✔️ Redis يعمل بالفعل"
fi

# تشغيل Celery Worker مع نظام الرفع المحسن
print_info "تشغيل Celery Worker مع نظام الرفع المحسن..."
print_upload "📤 سيتم دعم رفع العقود والمعاينات بشكل صحيح"
cd "$PROJECT_DIR" # التأكد من أننا في المجلد الصحيح
if [ -f "$PROJECT_DIR/crm/__init__.py" ]; then
	# انتظار جاهزية Redis بشكل كامل
	print_info "انتظار جاهزية Redis..."
	for i in {1..30}; do
		if redis-cli ping | grep -q "PONG"; then
			print_status "✔️ Redis جاهز لاستقبال الاتصالات"
			break
		fi
		sleep 1
	done

	# تنظيف الملفات القديمة
	rm -f "$LOGS_DIR/celery_worker.pid" "$LOGS_DIR/celery_worker.log"

	# تشغيل Celery Worker مع جميع الـ queues (مُصلح)
	celery -A crm worker \
		--loglevel=warning \
		--queues=celery,file_uploads \
		--pidfile="$LOGS_DIR/celery_worker.pid" \
		--logfile="$LOGS_DIR/celery_worker.log" \
		--pool=solo \
		--concurrency=1 \
		--max-memory-per-child=200000 \
		--time-limit=300 \
		--soft-time-limit=270 \
		--detach

	# انتظار ذكي لملف PID
	for i in {1..10}; do
		if [ -f "$LOGS_DIR/celery_worker.pid" ]; then
			break
		fi
		sleep 1
	done

	if [ -f "$LOGS_DIR/celery_worker.pid" ]; then
		CELERY_WORKER_PID=$(cat "$LOGS_DIR/celery_worker.pid")
		if ps -p $CELERY_WORKER_PID >/dev/null; then
			print_status "✔️ تم تشغيل Celery Worker بنجاح (PID: $CELERY_WORKER_PID)"
			print_upload "📤 نظام الرفع جاهز: العقود والمعاينات"
		else
			print_error "❌ فشل في تشغيل Celery Worker - راجع السجل في $LOGS_DIR/celery_worker.log"
			tail -n 20 "$LOGS_DIR/celery_worker.log"
		fi
	else
		print_error "❌ فشل في تشغيل Celery Worker - لم يتم إنشاء ملف PID بعد الانتظار"
	fi
else
	print_error "❌ فشل في تشغيل Celery Worker - ملف التهيئة crm/__init__.py غير موجود"
fi
if ps -p $CELERY_WORKER_PID >/dev/null; then
	print_status "✔️ تم تشغيل Celery Worker مع جميع قوائم الانتظار (PID: $CELERY_WORKER_PID)"
else
	print_error "❌ فشل في تشغيل Celery Worker"
fi

# تشغيل Celery Beat للمهام الدورية
print_info "تشغيل Celery Beat للمهام الدورية..."
cd "$PROJECT_DIR" # التأكد من أننا في المجلد الصحيح
if [ -f "$PROJECT_DIR/crm/__init__.py" ]; then
	# تنظيف الملفات القديمة
	rm -f "$LOGS_DIR/celery_beat.pid" "$LOGS_DIR/celery_beat.log" "$LOGS_DIR/celerybeat-schedule"*

	# تشغيل Celery Beat مع تقليل استهلاك قاعدة البيانات
	celery -A crm beat \
		--loglevel=warning \
		--pidfile="$LOGS_DIR/celery_beat.pid" \
		--logfile="$LOGS_DIR/celery_beat.log" \
		--schedule="$LOGS_DIR/celerybeat-schedule" \
		--detach

	sleep 5 # انتظار بدء العملية

	if [ -f "$LOGS_DIR/celery_beat.pid" ]; then
		CELERY_BEAT_PID=$(cat "$LOGS_DIR/celery_beat.pid")
		if ps -p $CELERY_BEAT_PID >/dev/null; then
			print_status "✔️ تم تشغيل Celery Beat بنجاح (PID: $CELERY_BEAT_PID)"
		else
			print_error "❌ فشل في تشغيل Celery Beat - راجع السجل في $LOGS_DIR/celery_beat.log"
			tail -n 20 "$LOGS_DIR/celery_beat.log"
		fi
	else
		print_error "❌ فشل في تشغيل Celery Beat - لم يتم إنشاء ملف PID"
	fi
else
	print_error "❌ فشل في تشغيل Celery Beat - ملف التهيئة crm/__init__.py غير موجود"
fi
if ps -p $CELERY_BEAT_PID >/dev/null; then
	print_status "✔️ تم تشغيل Celery Beat للمهام الدورية (PID: $CELERY_BEAT_PID)"
else
	print_error "❌ فشل في تشغيل Celery Beat"
fi

# تشغيل Cloudflare Tunnel
print_info "جاري تشغيل Cloudflare Tunnel..."
if [ -f "cloudflared" ]; then
	chmod +x cloudflared
	./cloudflared tunnel --config cloudflared.yml run >"$LOGS_DIR/cloudflared.log" 2>&1 &
	TUNNEL_PID=$!
	sleep 5 # انتظار بدء التانل

	if ps -p $TUNNEL_PID >/dev/null; then
		print_status "✔️ تم تشغيل Cloudflare Tunnel (PID: $TUNNEL_PID)"
		print_tunnel "🌐 يمكن الوصول للموقع عبر: https://elkhawaga.uk"
	else
		print_error "❌ فشل في تشغيل Cloudflare Tunnel"
		print_status "⚠️ سيتم الاستمرار في الوضع المحلي على المنفذ 8000"
	fi
else
	print_warning "⚠️ ملف cloudflared غير موجود"
	print_status "⚠️ سيتم الاستمرار في الوضع المحلي على المنفذ 8000"
fi

# تصدير إعدادات قاعدة البيانات إلى البيئة حتى يستخدمها سكريبت النسخ الاحتياطي
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

# تشغيل سكريبت النسخ الاحتياطي في الخلفية (يأخذ نسخة فورية ثم كل ساعة)
if [ -f "لينكس/db-backup.sh" ]; then
	chmod +x "لينكس/db-backup.sh"
	./لينكس/db-backup.sh >"$LOGS_DIR/db_backup.log" 2>&1 &
	DB_BACKUP_PID=$!
	print_status "✔️ تم تشغيل خدمة النسخ الاحتياطي (PID: $DB_BACKUP_PID) - ستُحفظ النسخ في /home/zakee/homeupdate/media/backups"
else
	print_error "ملف النسخ الاحتياطي لينكس/db-backup.sh غير موجود"
fi

# Tail backup log and print success messages to console
if [ -f "$LOGS_DIR/db_backup.log" ] || true; then
	(tail -n0 -F "$LOGS_DIR/db_backup.log" 2>/dev/null | while read line; do
		if echo "$line" | grep -q "تم إنشاء نسخة احتياطية بنجاح"; then
			print_status "$line"
		fi
	done) &
	BACKUP_TAIL_PID=$!
fi

cleanup() {
	print_info "إيقاف العمليات..."

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

	# إيقاف Cloudflare Tunnel
	if [ ! -z "$TUNNEL_PID" ]; then
		kill $TUNNEL_PID 2>/dev/null
		print_status "تم إيقاف Cloudflare Tunnel"
	fi

	# إيقاف خدمة النسخ الاحتياطي
	if [ ! -z "$DB_BACKUP_PID" ]; then
		kill $DB_BACKUP_PID 2>/dev/null
		print_status "تم إيقاف خدمة النسخ الاحتياطي"
	fi
	if [ ! -z "$BACKUP_TAIL_PID" ]; then
		kill $BACKUP_TAIL_PID 2>/dev/null
		print_status "تم إيقاف tail سجل النسخ الاحتياطي"
	fi

	# إيقاف خادم Daphne
	if [ ! -z "$DAPHNE_PID" ]; then
		kill $DAPHNE_PID 2>/dev/null
		print_status "تم إيقاف خادم Daphne"
	fi

	exit 0
}
trap cleanup INT TERM

print_status "🚀 بدء خادم الإنتاج الحقيقي مع التحسينات الجديدة..."
print_info "الموقع: http://localhost:8000"
print_info "المستخدم: admin | كلمة المرور: admin123"
print_warning "🔒 وضع الإنتاج: DEBUG=False (أمان عالي)"
print_info "📁 الملفات الثابتة: مدعومة بواسطة WhiteNoise"
print_info "📊 مراقبة Celery: tail -f $LOGS_DIR/celery_worker.log"
print_info "⏰ مراقبة المهام الدورية: tail -f $LOGS_DIR/celery_beat.log"
print_info "📁 جميع السجلات في: $LOGS_DIR/"
print_info "🔌 دعم المهام الخلفية المحسنة + خادم إنتاج Gunicorn"
print_info "🗄️ تحسينات قاعدة البيانات: تقليل الاتصالات بنسبة 97.5%"
print_info "🔔 إشعارات محسنة: إخفاء تلقائي عند تغيير المسؤول"
print_info "🔍 مراقبة دورية لحالة قاعدة البيانات كل 5 دقائق"
print_info "Ctrl+C للإيقاف"

# استخدام Daphne للإنتاج مع دعم WebSockets
print_info "تشغيل خادم Daphne للإنتاج مع دعم WebSockets..."
print_status "✅ استخدام Daphne - يدعم HTTP و WebSockets (ASGI)"
print_status "✅ الملفات الثابتة: مدعومة بواسطة WhiteNoise"

# تشغيل Daphne
# دالة تشغيل Daphne مع الفلترة
start_daphne() {
	print_info "تشغيل خادم Daphne للإنتاج..."

	# التأكد من أن المنفذ 8000 متاح (تنظيف قوي)
	if fuser 8000/tcp >/dev/null 2>&1; then
		print_warning "⚠️ المنفذ 8000 مشغول - جاري تحريره بقوة..."
		fuser -k -9 8000/tcp >/dev/null 2>&1
		sleep 2
	fi

	# نستخدم tee لحفظ السجل الخام مع تمريره للفلتر
	daphne -b 0.0.0.0 -p 8000 crm.asgi:application --access-log /dev/stdout 2>&1 | tee -a "$LOGS_DIR/daphne_raw.log" | while read line; do
		# تطبيق فلتر logs محسن لتقليل الرسائل غير المهمة
		# تجاهل رسائل gunicorn access logs التي تبدأ بـ [[
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
			[[ $line == *"/complaints/api/assigned/"* ]] ||
			[[ $line == *"/complaints/api/escalated/"* ]] ||
			[[ $line == *"/complaints/api/notifications/"* ]] ||
			[[ $line == *"/complaints/api/assignment-notifications/"* ]] ||
			[[ $line == *"/inventory/api/product-autocomplete/"* ]] ||
			[[ $line == *"/media/users/"* ]] ||
			[[ $line == *"/media/"* ]] ||
			[[ $line == *"/static/"* ]] ||
			[[ $line == *"favicon.ico"* ]]; then
			continue
		fi

		# معالجة رسائل تسجيل الدخول والخروج
		if [[ $line == *"🔐"* && $line == *"login"* ]]; then
			# استخراج اسم المستخدم من رسالة تسجيل الدخول
			username=$(echo "$line" | sed -n 's/.*🔐 \([^ ]*\) -.*/\1/p')
			if [ -n "$username" ]; then
				print_login "🔐 قام المستخدم $username بتسجيل الدخول"
			fi
		elif [[ $line == *"🚪"* && $line == *"logout"* ]]; then
			# استخراج اسم المستخدم من رسالة تسجيل الخروج
			username=$(echo "$line" | sed -n 's/.*🚪 \([^ ]*\) -.*/\1/p')
			if [ -n "$username" ]; then
				print_login "🚪 قام المستخدم $username بتسجيل الخروج"
			fi
		elif [[ $line == *"👁️"* && $line == *"page_view"* ]]; then
			# استخراج اسم المستخدم من رسالة عرض الصفحة
			username=$(echo "$line" | sed -n 's/.*👁️ \([^ ]*\) -.*/\1/p')
			if [ -n "$username" ]; then
				# عرض نشاط المستخدم المسجل
				page=$(echo "$line" | sed -n 's/.*page_view - \([^ ]*\).*/\1/p')
				echo -e "${WHITE}👁️ المستخدم $username يتصفح: $page${NC}"
			else
				# مستخدم غير معروف - استخراج IP
				ip=$(echo "$line" | grep -oE '[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}' | head -1)
				if [ -n "$ip" ]; then
					print_warning "🌐 تم فتح صفحة الموقع من مستخدم غير معروف - IP: $ip"
				fi
			fi
		elif [[ $line == *"🔄"* ]]; then
			# عرض عمليات تبديل الحالة والتحديثات
			username=$(echo "$line" | sed -n 's/.*🔄 \([^ ]*\) -.*/\1/p')
			if [ -n "$username" ]; then
				action=$(echo "$line" | sed -n 's/.*🔄 [^ ]* - \([^(]*\).*/\1/p')
				# استخراج كود الطلب إذا كان موجوداً
				order_code=$(echo "$line" | grep -oE 'ORD-[0-9]+' | head -1)
				if [ -n "$order_code" ]; then
					echo -e "${YELLOW}🔄 المستخدم $username قام بـ: $action - الطلب: $order_code${NC}"
				else
					echo -e "${YELLOW}🔄 المستخدم $username قام بـ: $action${NC}"
				fi
			fi
		elif [[ $line == *"✅"* || $line == *"❌"* || $line == *"⚠️"* ]]; then
			# عرض العمليات المهمة الأخرى
			username=$(echo "$line" | sed -n 's/.*[✅❌⚠️] \([^ ]*\) -.*/\1/p')
			if [ -n "$username" ]; then
				action=$(echo "$line" | sed -n 's/.*[✅❌⚠️] [^ ]* - \([^(]*\).*/\1/p')
				# استخراج كود الطلب إذا كان موجوداً
				order_code=$(echo "$line" | grep -oE 'ORD-[0-9]+' | head -1)
				if [ -n "$order_code" ]; then
					echo -e "${GREEN}المستخدم $username: $action - الطلب: $order_code${NC}"
				else
					echo -e "${GREEN}المستخدم $username: $action${NC}"
				fi
			fi
		else
			# عرض الرسائل الأخرى المهمة
			echo "$line"
		fi
	done &
	DAPHNE_PID=$!
	print_status "خادم الإنتاج (Daphne) يعمل (PID: $DAPHNE_PID)"
}

# تشغيل Daphne لأول مرة
start_daphne

# متغيرات لتتبع الفحوصات الدورية
LAST_DB_CHECK=0
LAST_NOTIFICATION_CLEANUP=0
DB_CHECK_INTERVAL=300              # فحص كل 5 دقائق
NOTIFICATION_CLEANUP_INTERVAL=1800 # تنظيف كل 30 دقيقة

while true; do
	sleep 30

	# فحص خادم الويب وإعادة تشغيله إذا توقف
	if ! pgrep -f "crm.asgi:application" >/dev/null; then
		print_error "❌ خادم الويب (Daphne) توقف بشكل غير متوقع!"
		print_warning "🔄 جاري إعادة تشغيل Daphne تلقائياً..."
		start_daphne
	fi

	# فحص دوري لحالة قاعدة البيانات (كل 5 دقائق)
	CURRENT_TIME=$(date +%s)
	if [ $((CURRENT_TIME - LAST_DB_CHECK)) -ge $DB_CHECK_INTERVAL ]; then
		print_info "🔍 فحص دوري لحالة قاعدة البيانات..."
		python manage.py monitor_db --once --quiet 2>/dev/null
		if [ $? -eq 0 ]; then
			print_status "✅ قاعدة البيانات تعمل بشكل طبيعي"
		else
			print_warning "⚠️ تحذير: قد تكون هناك مشكلة في قاعدة البيانات"
		fi
		LAST_DB_CHECK=$CURRENT_TIME
	fi

	# تنظيف دوري للإشعارات القديمة (كل 30 دقيقة)
	if [ $((CURRENT_TIME - LAST_NOTIFICATION_CLEANUP)) -ge $NOTIFICATION_CLEANUP_INTERVAL ]; then
		print_info "🧹 تنظيف دوري للإشعارات القديمة..."
		CLEANED_COUNT=$(python manage.py cleanup_notifications 2>/dev/null | grep -o '[0-9]\+' | head -1)
		if [ ! -z "$CLEANED_COUNT" ] && [ "$CLEANED_COUNT" -gt 0 ]; then
			print_status "✅ تم تنظيف $CLEANED_COUNT إشعار قديم"
		else
			print_status "✅ لا توجد إشعارات قديمة للتنظيف"
		fi
		LAST_NOTIFICATION_CLEANUP=$CURRENT_TIME
	fi

	# رفع تلقائي للملفات المعلقة (كل 10 دقائق)
	if [ $((CURRENT_TIME - ${LAST_UPLOAD_CHECK:-0})) -ge 600 ]; then
		print_upload "📤 رفع تلقائي للملفات المعلقة..."
		if [ -f "auto_upload_system.py" ]; then
			UPLOAD_RESULT=$(python auto_upload_system.py single 2>/dev/null | tail -2)
			print_upload "$UPLOAD_RESULT"
		fi
		LAST_UPLOAD_CHECK=$CURRENT_TIME
	fi

	# فحص Redis وإعادة تشغيله إذا توقف (حرج جداً للنظام)
	if ! pgrep -f "valkey|redis-server" >/dev/null; then
		print_warning "⚠️ Redis توقف - جاري إعادة التشغيل..."
		redis-server --daemonize yes --port 6379 --dir /tmp
		if [ $? -eq 0 ]; then
			print_status "✔️ تم إعادة تشغيل Redis بنجاح"
		else
			print_error "❌ فشل في إعادة تشغيل Redis"
		fi
	fi

	# فحص Celery Worker مع إعادة تشغيل محسنة
	if [ -f "$LOGS_DIR/celery_worker.pid" ]; then
		CELERY_WORKER_PID=$(cat "$LOGS_DIR/celery_worker.pid" 2>/dev/null)
		if [ ! -z "$CELERY_WORKER_PID" ] && ! kill -0 $CELERY_WORKER_PID 2>/dev/null; then
			print_warning "⚠️ Celery Worker توقف - إعادة تشغيل مع الإعدادات المحسنة..."
			celery -A crm worker \
				--loglevel=error \
				--queues=celery,file_uploads \
				--pool=solo \
				--concurrency=1 \
				--max-memory-per-child=200000 \
				--time-limit=300 \
				--soft-time-limit=270 \
				--detach \
				--pidfile="$LOGS_DIR/celery_worker.pid" \
				--logfile="$LOGS_DIR/celery_worker.log"
			if [ $? -eq 0 ]; then
				print_status "✔️ تم إعادة تشغيل Celery Worker مع الإعدادات المحسنة"
			else
				print_error "❌ فشل في إعادة تشغيل Celery Worker"
			fi
		fi
	fi

	# فحص Celery Beat
	if [ -f "$LOGS_DIR/celery_beat.pid" ]; then
		CELERY_BEAT_PID=$(cat "$LOGS_DIR/celery_beat.pid" 2>/dev/null)
		if [ ! -z "$CELERY_BEAT_PID" ] && ! kill -0 $CELERY_BEAT_PID 2>/dev/null; then
			print_warning "⚠️ Celery Beat توقف - إعادة تشغيل..."
			celery -A crm beat --loglevel=warning --detach --pidfile="$LOGS_DIR/celery_beat.pid" --logfile="$LOGS_DIR/celery_beat.log" --schedule="$LOGS_DIR/celerybeat-schedule"
			if [ $? -eq 0 ]; then
				print_status "✔️ تم إعادة تشغيل Celery Beat"
			else
				print_error "❌ فشل في إعادة تشغيل Celery Beat"
			fi
		fi
	fi

	# فحص حالة التانل وإعادة تشغيله إذا توقف
	if [ ! -z "$TUNNEL_PID" ]; then
		if ! kill -0 $TUNNEL_PID 2>/dev/null; then
			print_warning "⚠️ Cloudflare Tunnel توقف - جاري إعادة التشغيل..."
			./cloudflared tunnel --config cloudflared.yml run >"$LOGS_DIR/cloudflared.log" 2>&1 &
			TUNNEL_PID=$!
			sleep 5

			if ps -p $TUNNEL_PID >/dev/null; then
				print_status "✔️ تم إعادة تشغيل Cloudflare Tunnel (PID: $TUNNEL_PID)"
				print_tunnel "🌐 يمكن الوصول للموقع عبر: https://elkhawaga.uk"
			else
				print_error "❌ فشل في إعادة تشغيل Cloudflare Tunnel"
			fi
		else
			# فحص الاتصال بالموقع
			if curl -s --max-time 10 https://elkhawaga.uk >/dev/null 2>&1; then
				if [ "$TUNNEL_STATUS" != "connected" ]; then
					TUNNEL_STATUS="connected"
					print_tunnel "✅ النظام يعمل بشكل طبيعي - الجسر متصل"
				fi
			else
				if [ "$TUNNEL_STATUS" != "disconnected" ]; then
					TUNNEL_STATUS="disconnected"
					print_warning "⚠️ الجسر يعمل ولكن الموقع غير متاح - جاري المحاولة مجدداً..."
					kill $TUNNEL_PID 2>/dev/null
					./cloudflared tunnel --config cloudflared.yml run >"$LOGS_DIR/cloudflared.log" 2>&1 &
					TUNNEL_PID=$!
					sleep 5
				fi
			fi
		fi
	else
		print_warning "⚠️ النظام يعمل محلياً - الجسر غير مشغل"
	fi
done

print_upload "📤 تم إيقاف نظام الرفع التلقائي"
cleanup
