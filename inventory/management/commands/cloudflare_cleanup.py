"""
Management command لتنظيف Cloudflare KV بعد إعادة هيكلة أكواد المنتجات
يستخدم Cloudflare Worker endpoints بدلاً من REST API المباشر

الاستخدام:
    python manage.py cloudflare_cleanup --strategy=list
    python manage.py cloudflare_cleanup --strategy=list --export=old_keys.txt
    python manage.py cloudflare_cleanup --strategy=redirect
    python manage.py cloudflare_cleanup --strategy=delete --dry-run
    python manage.py cloudflare_cleanup --strategy=delete
"""

import json
import logging

import requests
from django.conf import settings
from django.core.management.base import BaseCommand

from inventory.models import BaseProduct, Product

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "تنظيف مفاتيح Cloudflare KV القديمة بعد إعادة هيكلة المنتجات"

    def add_arguments(self, parser):
        parser.add_argument(
            "--strategy",
            type=str,
            choices=["list", "redirect", "delete"],
            required=True,
            help="استراتيجية التنفيذ: list | redirect | delete",
        )
        parser.add_argument(
            "--export",
            type=str,
            help="تصدير المفاتيح القديمة لملف نصي (مع list فقط)",
        )
        parser.add_argument(
            "--output",
            type=str,
            default="cloudflare_redirects.json",
            help="مسار ملف redirects الناتج (مع redirect فقط)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="عرض ما سيتم حذفه دون تنفيذ (مع delete فقط)",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=1000,
            help="عدد المفاتيح لكل صفحة عند القراءة من Cloudflare (افتراضي: 1000)",
        )

    def handle(self, *args, **options):
        strategy = options["strategy"]
        export_path = options.get("export")
        output_path = options.get("output")
        dry_run = options.get("dry_run", False)
        limit = options.get("limit")

        worker_url = getattr(settings, "CLOUDFLARE_WORKER_URL", None)
        api_key = getattr(settings, "CLOUDFLARE_SYNC_API_KEY", None)
        enabled = getattr(settings, "CLOUDFLARE_SYNC_ENABLED", False)

        if not worker_url or not api_key:
            self.stdout.write(self.style.ERROR("❌ إعدادات Cloudflare Worker غير مكتملة"))
            self.stdout.write("تأكد من وجود القيم التالية في .env:")
            self.stdout.write("  - CLOUDFLARE_WORKER_URL")
            self.stdout.write("  - CLOUDFLARE_SYNC_API_KEY")
            return

        if not enabled:
            self.stdout.write(
                self.style.WARNING(
                    "⚠️  CLOUDFLARE_SYNC_ENABLED=False. استمرار العملية على أي حال..."
                )
            )

        headers = {
            "X-Sync-API-Key": api_key,
            "Content-Type": "application/json",
        }

        self.stdout.write(self.style.SUCCESS("🔍 جلب مفاتيح Cloudflare KV..."))
        all_keys = self._list_all_keys(worker_url, headers, limit=limit)

        if not all_keys:
            self.stdout.write(self.style.WARNING("⚠️  لم يتم العثور على مفاتيح."))
            return

        current_codes = self._get_current_codes()
        old_keys = self._find_old_keys(all_keys, current_codes)

        if strategy == "list":
            self._handle_list(old_keys, export_path)
            return

        if strategy == "redirect":
            self._handle_redirect(
                old_keys, current_codes, worker_url, headers, output_path
            )
            return

        if strategy == "delete":
            self._handle_delete(old_keys, worker_url, headers, dry_run=dry_run)
            return

    def _get_current_codes(self):
        base_codes = (
            BaseProduct.objects.exclude(code__isnull=True)
            .exclude(code="")
            .values_list("code", flat=True)
        )
        legacy_codes = (
            Product.objects.exclude(code__isnull=True)
            .exclude(code="")
            .values_list("code", flat=True)
        )
        return set(list(base_codes) + list(legacy_codes))

    def _normalize_key(self, key):
        if key.startswith("products/"):
            return key.split("/", 1)[1]
        return key

    def _is_candidate_key(self, key):
        if not key:
            return False
        if key.startswith("__"):
            return False
        if ":" in key:
            return False
        return True

    def _find_old_keys(self, all_keys, current_codes):
        old_keys = []
        for key in all_keys:
            if not self._is_candidate_key(key):
                continue
            normalized = self._normalize_key(key)
            if normalized not in current_codes:
                old_keys.append(key)
        return old_keys

    def _list_all_keys(self, worker_url, headers, limit=1000):
        """جلب جميع المفاتيح من Cloudflare KV عبر Worker"""
        keys = []
        cursor = None

        while True:
            payload = {"action": "list_keys", "limit": limit}
            if cursor:
                payload["cursor"] = cursor

            try:
                response = requests.post(
                    f"{worker_url}/sync",
                    headers=headers,
                    json=payload,
                    timeout=30
                )
                
                if response.status_code != 200:
                    self.stdout.write(
                        self.style.ERROR(
                            f"❌ فشل جلب المفاتيح: {response.status_code} - {response.text}"
                        )
                    )
                    return []

                data = response.json()
                if not data.get("success"):
                    self.stdout.write(
                        self.style.ERROR(f"❌ خطأ من Worker: {data}")
                    )
                    return []

                keys.extend(data.get("keys", []))
                
                if data.get("list_complete", True):
                    break
                    
                cursor = data.get("cursor")
                if not cursor:
                    break

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"❌ خطأ في الاتصال بـ Worker: {e}")
                )
                return []

        return keys

    def _fetch_kv_value(self, worker_url, headers, key):
        """جلب قيمة مفتاح محدد من KV عبر Worker"""
        try:
            payload = {"action": "get_key", "key": key}
            response = requests.post(
                f"{worker_url}/sync",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code != 200:
                return None
            
            data = response.json()
            if data.get("success"):
                return data.get("value")
            return None
            
        except Exception:
            return None

    def _handle_list(self, old_keys, export_path=None):
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("📋 المفاتيح القديمة التي يجب حذفها:"))
        if not old_keys:
            self.stdout.write(self.style.SUCCESS("✅ لا توجد مفاتيح قديمة."))
            return

        for key in old_keys:
            self.stdout.write(f"  🔑 {key}")

        self.stdout.write(self.style.WARNING(f"⚠️  إجمالي المفاتيح القديمة: {len(old_keys)}"))

        if export_path:
            try:
                with open(export_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(old_keys))
                self.stdout.write(
                    self.style.SUCCESS(f"✅ تم تصدير القائمة إلى: {export_path}")
                )
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ فشل التصدير: {e}"))

    def _handle_redirect(
        self, old_keys, current_codes, worker_url, headers, output_path
    ):
        if not old_keys:
            self.stdout.write(self.style.SUCCESS("✅ لا توجد مفاتيح قديمة لإنشاء redirects."))
            return

        redirects = []
        skipped = 0

        self.stdout.write(self.style.SUCCESS("🔧 إنشاء redirects من القديم إلى الجديد..."))

        for key in old_keys:
            normalized = self._normalize_key(key)
            value = self._fetch_kv_value(worker_url, headers, key)
            if not value or not isinstance(value, dict):
                skipped += 1
                continue

            name = value.get("name")
            if not name:
                skipped += 1
                continue

            match = BaseProduct.objects.filter(name__iexact=name).first()
            if not match or not match.code or match.code not in current_codes:
                skipped += 1
                continue

            redirects.append(
                {
                    "from": f"/products/{normalized}",
                    "to": f"/products/{match.code}",
                    "status": 301,
                    "name": name,
                }
            )

        if not redirects:
            self.stdout.write(self.style.WARNING("⚠️  لم يتم إنشاء أي redirects."))
            return

        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(redirects, f, ensure_ascii=False, indent=2)
            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ تم إنشاء {len(redirects)} redirect(s) في الملف: {output_path}"
                )
            )
            if skipped:
                self.stdout.write(
                    self.style.WARNING(f"⚠️  تم تخطي {skipped} عنصر بسبب نقص بيانات المطابقة")
                )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ فشل حفظ الملف: {e}"))

    def _handle_delete(self, old_keys, worker_url, headers, dry_run=False):
        if not old_keys:
            self.stdout.write(self.style.SUCCESS("✅ لا توجد مفاتيح قديمة للحذف."))
            return

        if dry_run:
            self.stdout.write(self.style.WARNING("🔍 وضع المعاينة - لن يتم الحذف"))
            for key in old_keys:
                self.stdout.write(f"  🗑️ {key}")
            self.stdout.write(self.style.WARNING(f"⚠️  عدد المفاتيح: {len(old_keys)}"))
            return

        confirm = input(
            "⚠️  تحذير: هذا سيحذف المفاتيح نهائياً من Cloudflare! اكتب 'نعم' للتأكيد: "
        )
        if confirm.strip() != "نعم":
            self.stdout.write(self.style.WARNING("❌ تم إلغاء العملية."))
            return

        # حذف الدفعات - 50 مفتاح في كل مرة لتجنب timeout
        batch_size = 50
        deleted = 0
        failed = 0

        for i in range(0, len(old_keys), batch_size):
            batch = old_keys[i : i + batch_size]
            
            try:
                payload = {"action": "delete_keys", "keys": batch}
                response = requests.post(
                    f"{worker_url}/sync",
                    headers=headers,
                    json=payload,
                    timeout=60  # timeout أطول للدفعات
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("success"):
                        count = data.get("count", len(batch))
                        deleted += count
                        for key in batch:
                            self.stdout.write(self.style.SUCCESS(f"  ✅ تم حذف: {key}"))
                    else:
                        failed += len(batch)
                        self.stdout.write(
                            self.style.ERROR(f"  ❌ فشل حذف الدفعة: {data}")
                        )
                else:
                    failed += len(batch)
                    self.stdout.write(
                        self.style.ERROR(
                            f"  ❌ فشل حذف الدفعة: {response.status_code} - {response.text}"
                        )
                    )
            except Exception as e:
                failed += len(batch)
                self.stdout.write(
                    self.style.ERROR(f"  ❌ خطأ في حذف الدفعة: {e}")
                )

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"✅ المحذوف: {deleted}"))
        if failed:
            self.stdout.write(self.style.ERROR(f"❌ فشل: {failed}"))
