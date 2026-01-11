#!/bin/bash
# 🛠️ تشغيل النظام للتطوير مع مراقبة مبسطة

RED='\033[0;31m'
GREEN='\033[0;32m'
WHITE='\033[1;37m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

PROJECT_DIR="/home/xhunterx/homeupdate"

print_status() { echo -e "${GREEN}$1${NC}"; }
print_error() { echo -e "${RED}$1${NC}"; }
print_info() { echo -e "${WHITE}$1${NC}"; }
print_dev() { echo -e "${CYAN}$1${NC}"; }
print_warning() { echo -e "${YELLOW}$1${NC}"; }

if [ ! -d "$PROJECT_DIR" ]; then
	print_error "مجلد المشروع غير موجود: $PROJECT_DIR"
	exit 1
fi
cd "$PROJECT_DIR"

print_info "تشغيل التحديثات..."
python manage.py migrate --noinput
print_status "✔️ تم تطبيق التحديثات"

print_info "تجميع الملفات الثابتة..."
python manage.py collectstatic --noinput
print_status "✔️ تم تجميع الملفات الثابتة"

# فحص وتشغيل Redis/Valkey
print_info "فحص وتشغيل Redis/Valkey..."
if ! pgrep -x "valkey-server\|redis-server" >/dev/null; then
	if command -v valkey-server &>/dev/null; then
		valkey-server --daemonize yes --port 6379 --dir /tmp
		print_status "✔️ تم تشغيل Valkey"
	elif command -v redis-server &>/dev/null; then
		redis-server --daemonize yes --port 6379 --dir /tmp
		print_status "✔️ تم تشغيل Redis"
	else
		print_error "❌ Redis/Valkey غير مثبت"
		print_info "قم بتثبيته: sudo pacman -S valkey"
		exit 1
	fi
else
	print_status "✔️ Redis/Valkey يعمل بالفعل"
fi

# اختبار اتصال Redis
sleep 2
if command -v valkey-cli &>/dev/null; then
	if valkey-cli ping >/dev/null 2>&1; then
		print_status "✔️ Valkey متصل ويعمل"
	else
		print_error "❌ فشل في الاتصال بـ Valkey"
		exit 1
	fi
elif command -v redis-cli &>/dev/null; then
	if redis-cli ping >/dev/null 2>&1; then
		print_status "✔️ Redis متصل ويعمل"
	else
		print_error "❌ فشل في الاتصال بـ Redis"
		exit 1
	fi
fi

# تشغيل Celery Worker
print_info "تشغيل Celery Worker..."
celery -A crm worker --loglevel=info --detach --pidfile=/tmp/celery_worker_dev.pid --logfile=/tmp/celery_worker_dev.log
if [ $? -eq 0 ]; then
	CELERY_WORKER_PID=$(cat /tmp/celery_worker_dev.pid 2>/dev/null)
	print_status "✔️ تم تشغيل Celery Worker (PID: $CELERY_WORKER_PID)"
else
	print_error "❌ فشل في تشغيل Celery Worker"
	exit 1
fi

# تشغيل Celery Beat
print_info "تشغيل Celery Beat..."
celery -A crm beat --loglevel=info --detach --pidfile=/tmp/celery_beat_dev.pid --logfile=/tmp/celery_beat_dev.log --schedule=/tmp/celerybeat-schedule-dev
if [ $? -eq 0 ]; then
	CELERY_BEAT_PID=$(cat /tmp/celery_beat_dev.pid 2>/dev/null)
	print_status "✔️ تم تشغيل Celery Beat (PID: $CELERY_BEAT_PID)"
else
	print_error "❌ فشل في تشغيل Celery Beat"
	exit 1
fi

print_info "فحص المستخدمين..."
USER_COUNT=$(python -c "import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings'); import django; django.setup(); from accounts.models import User; print(User.objects.count())")
if [ "$USER_COUNT" -eq 0 ]; then
	print_status "لا يوجد مستخدمين، سيتم إنشاء admin/admin123"
	python -c "import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings'); import django; django.setup(); from accounts.models import User; User.objects.create_superuser('admin', 'admin@example.com', 'admin123'); print('تم إنشاء المستخدم admin/admin123')"
else
	print_status "عدد المستخدمين الحالي: $USER_COUNT (لن يتم إنشاء مستخدم جديد)"
fi

# تخطي Cloudflare في وضع التطوير المحلي
print_info "وضع التطوير المحلي - تخطي Cloudflare Tunnel"

cleanup() {
	print_info "إيقاف العمليات..."

	# إيقاف Celery Worker
	if [ -f "/tmp/celery_worker_dev.pid" ]; then
		CELERY_WORKER_PID=$(cat /tmp/celery_worker_dev.pid 2>/dev/null)
		if [ ! -z "$CELERY_WORKER_PID" ]; then
			kill $CELERY_WORKER_PID 2>/dev/null
			print_status "تم إيقاف Celery Worker"
		fi
		rm -f /tmp/celery_worker_dev.pid
	fi

	# إيقاف Celery Beat
	if [ -f "/tmp/celery_beat_dev.pid" ]; then
		CELERY_BEAT_PID=$(cat /tmp/celery_beat_dev.pid 2>/dev/null)
		if [ ! -z "$CELERY_BEAT_PID" ]; then
			kill $CELERY_BEAT_PID 2>/dev/null
			print_status "تم إيقاف Celery Beat"
		fi
		rm -f /tmp/celery_beat_dev.pid
		rm -f /tmp/celerybeat-schedule-dev*
	fi

	# إيقاف Daphne
	if [ ! -z "$DJANGO_PID" ]; then
		kill $DJANGO_PID 2>/dev/null
		print_status "تم إيقاف Daphne"
	fi

	exit 0
}
trap cleanup INT TERM

print_status "🛠️ بدء خادم التطوير المحلي..."
print_info "الموقع: http://localhost:8000"
print_info "المستخدم: admin | كلمة المرور: admin123"
print_dev "وضع التطوير - إعادة تحميل تلقائية"
print_info "📊 مراقبة Celery Worker: tail -f /tmp/celery_worker_dev.log"
print_info "⏰ مراقبة Celery Beat: tail -f /tmp/celery_beat_dev.log"
print_info "Ctrl+C للإيقاف"

# تشغيل خادم Django للتطوير
python manage.py runserver 0.0.0.0:8000 &
DJANGO_PID=$!
print_status "خادم التطوير يعمل (PID: $DJANGO_PID)"

# مراقبة العمليات
while true; do
	sleep 30

	# فحص Daphne
	if ! kill -0 $DJANGO_PID 2>/dev/null; then
		print_error "❌ Daphne توقف!"
		break
	fi

	# فحص Celery Worker
	if [ -f "/tmp/celery_worker_dev.pid" ]; then
		CELERY_WORKER_PID=$(cat /tmp/celery_worker_dev.pid 2>/dev/null)
		if [ ! -z "$CELERY_WORKER_PID" ] && ! kill -0 $CELERY_WORKER_PID 2>/dev/null; then
			print_warning "⚠️ Celery Worker توقف - إعادة تشغيل..."
			celery -A crm worker --loglevel=info --detach --pidfile=/tmp/celery_worker_dev.pid --logfile=/tmp/celery_worker_dev.log
			if [ $? -eq 0 ]; then
				print_status "✔️ تم إعادة تشغيل Celery Worker"
			else
				print_error "❌ فشل في إعادة تشغيل Celery Worker"
			fi
		fi
	fi

	# فحص Celery Beat
	if [ -f "/tmp/celery_beat_dev.pid" ]; then
		CELERY_BEAT_PID=$(cat /tmp/celery_beat_dev.pid 2>/dev/null)
		if [ ! -z "$CELERY_BEAT_PID" ] && ! kill -0 $CELERY_BEAT_PID 2>/dev/null; then
			print_warning "⚠️ Celery Beat توقف - إعادة تشغيل..."
			celery -A crm beat --loglevel=info --detach --pidfile=/tmp/celery_beat_dev.pid --logfile=/tmp/celery_beat_dev.log --schedule=/tmp/celerybeat-schedule-dev
			if [ $? -eq 0 ]; then
				print_status "✔️ تم إعادة تشغيل Celery Beat"
			else
				print_error "❌ فشل في إعادة تشغيل Celery Beat"
			fi
		fi
	fi

	# فحص Redis/Valkey
	if command -v valkey-cli &>/dev/null; then
		if ! valkey-cli ping >/dev/null 2>&1; then
			print_warning "⚠️ Valkey منقطع - محاولة إعادة الاتصال..."
			valkey-server --daemonize yes --port 6379 --dir /tmp
			sleep 2
			if valkey-cli ping >/dev/null 2>&1; then
				print_status "✔️ تم إعادة تشغيل Valkey"
			else
				print_error "❌ فشل في إعادة تشغيل Valkey"
			fi
		fi
	elif command -v redis-cli &>/dev/null; then
		if ! redis-cli ping >/dev/null 2>&1; then
			print_warning "⚠️ Redis منقطع - محاولة إعادة الاتصال..."
			redis-server --daemonize yes --port 6379 --dir /tmp
			sleep 2
			if redis-cli ping >/dev/null 2>&1; then
				print_status "✔️ تم إعادة تشغيل Redis"
			else
				print_error "❌ فشل في إعادة تشغيل Redis"
			fi
		fi
	fi

	print_status "✅ النظام يعمل بشكل طبيعي - التطوير المحلي"
done

cleanup
