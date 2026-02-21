"""
Meta WhatsApp Service - Simplified Version
إرسال مباشر لميتا بدون مطابقة قوالب محلية
"""

import logging

import requests
from django.utils import timezone

logger = logging.getLogger(__name__)


class WhatsAppService:
    """خدمة WhatsApp عبر Meta Cloud API - مبسطة"""

    BASE_URL = "https://graph.facebook.com/v18.0"

    # كاش للقوالب (لتجنب طلبات متكررة)
    _templates_cache = {}
    _cache_time = None
    CACHE_DURATION = 300  # 5 دقائق

    def __init__(self):
        from .models import WhatsAppSettings

        self.settings = WhatsAppSettings.objects.first()
        if not self.settings:
            raise ValueError("WhatsApp settings not configured")

        self.phone_id = self.settings.phone_number_id
        self.waba_id = self.settings.business_account_id
        self.token = self.settings.access_token

        if not self.phone_id or not self.token:
            raise ValueError("Phone Number ID and Access Token are required")

    def _get_headers(self):
        """الحصول على headers للطلبات"""
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def _format_phone_number(self, phone):
        """تنسيق رقم الهاتف"""
        if not phone:
            return None

        phone = "".join(filter(str.isdigit, phone))

        if not phone.startswith("20"):
            if phone.startswith("0"):
                phone = "20" + phone[1:]
            else:
                phone = "20" + phone

        return phone

    def _get_template_info_from_meta(self, template_name):
        """
        جلب معلومات القالب من ميتا مباشرة

        Returns:
            dict: {
                'has_header_image': bool,
                'header_handle': str or None,
                'variable_names': list,
                'language': str
            }
        """
        # فحص الكاش
        now = timezone.now()
        if (
            self._cache_time
            and (now - self._cache_time).seconds < self.CACHE_DURATION
            and template_name in self._templates_cache
        ):
            return self._templates_cache[template_name]

        try:
            url = f"{self.BASE_URL}/{self.waba_id}/message_templates"
            params = {
                "name": template_name,
                "fields": "name,language,components,parameter_format",
            }

            response = requests.get(
                url, headers=self._get_headers(), params=params, timeout=10
            )
            data = response.json()

            templates = data.get("data", [])
            if not templates:
                logger.warning(f"Template '{template_name}' not found in Meta")
                return None

            template = templates[0]
            result = {
                "has_header_image": False,
                "header_handle": None,
                "variable_names": [],
                "language": template.get("language", "ar"),
                "parameter_format": template.get("parameter_format", "POSITIONAL"),
            }

            for comp in template.get("components", []):
                comp_type = comp.get("type")

                # استخراج header_handle للصور
                if comp_type == "HEADER" and comp.get("format") == "IMAGE":
                    result["has_header_image"] = True
                    example = comp.get("example", {})
                    handles = example.get("header_handle", [])
                    if handles:
                        result["header_handle"] = handles[0]

                # استخراج أسماء المتغيرات من الـ BODY
                if comp_type == "BODY":
                    example = comp.get("example", {})
                    body_text = example.get("body_text", [[]])
                    if body_text and body_text[0]:
                        # عدد المتغيرات = عدد القيم في المثال
                        result["variable_names"] = [
                            f"var{i+1}" for i in range(len(body_text[0]))
                        ]

                    # أو من text مباشرة
                    text = comp.get("text", "")
                    import re

                    matches = re.findall(r"\{\{(\w+)\}\}", text)
                    if matches:
                        result["variable_names"] = matches

            # حفظ في الكاش
            self._templates_cache[template_name] = result
            self._cache_time = now

            logger.info(f"Fetched template info from Meta: {template_name}")
            logger.info(f"  Header Image: {result['has_header_image']}")
            logger.info(f"  Variables: {result['variable_names']}")
            logger.info(f"  Format: {result['parameter_format']}")

            return result

        except Exception as e:
            logger.error(f"Error fetching template from Meta: {e}")
            return None

    def send_text_message(self, to, message):
        """إرسال رسالة نصية"""
        url = f"{self.BASE_URL}/{self.phone_id}/messages"
        to = self._format_phone_number(to)

        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": message},
        }

        try:
            response = requests.post(
                url, headers=self._get_headers(), json=payload, timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending WhatsApp message: {e}")
            raise

    def _get_or_upload_header_media(self):
        """
        الحصول على Media ID للصورة أو رفعها إذا لم تكن مرفوعة

        Returns:
            str: Media ID أو None
        """
        # إذا كان Media ID موجود، استخدمه
        if self.settings.header_media_id:
            return self.settings.header_media_id

        # إذا لم تكن هناك صورة، ارجع None
        if not self.settings.header_image:
            logger.warning("No header image configured in settings")
            return None

        # رفع الصورة لـ WhatsApp
        try:
            media_id = self._upload_media(self.settings.header_image.path)
            if media_id:
                # حفظ Media ID في الإعدادات
                self.settings.header_media_id = media_id
                self.settings.save(update_fields=["header_media_id"])
                logger.info(f"Uploaded header image, Media ID: {media_id}")
            return media_id
        except Exception as e:
            logger.error(f"Error uploading header image: {e}")
            return None

    def _upload_media(self, file_path):
        """
        رفع ملف وسائط إلى WhatsApp

        Args:
            file_path: مسار الملف المحلي

        Returns:
            str: Media ID
        """
        import mimetypes
        import os

        url = f"{self.BASE_URL}/{self.phone_id}/media"

        # تحديد نوع الملف
        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            mime_type = "image/png"

        try:
            with open(file_path, "rb") as f:
                files = {"file": (os.path.basename(file_path), f, mime_type)}
                data = {"messaging_product": "whatsapp", "type": mime_type}

                response = requests.post(
                    url,
                    headers={"Authorization": f"Bearer {self.token}"},
                    files=files,
                    data=data,
                    timeout=30,
                )

                response.raise_for_status()
                result = response.json()
                return result.get("id")

        except Exception as e:
            logger.error(f"Error uploading media: {e}")
            if hasattr(e, "response") and e.response:
                logger.error(f"Response: {e.response.text}")
            raise

    def send_template_message(self, to, template_name, variables=None, language="ar"):
        """
        إرسال رسالة قالب - مبسط

        Args:
            to: رقم الهاتف
            template_name: اسم القالب في ميتا
            variables: dict أو list بالمتغيرات
            language: كود اللغة

        Returns:
            dict: استجابة API
        """
        url = f"{self.BASE_URL}/{self.phone_id}/messages"
        formatted_phone = self._format_phone_number(to)

        # جلب معلومات القالب من ميتا
        template_info = self._get_template_info_from_meta(template_name)

        # بناء المكونات
        components = []

        # 1. إضافة Header إذا كان القالب يحتوي صورة
        if template_info and template_info.get("has_header_image"):
            # استخدام Media ID المحفوظ أو رفع الصورة
            media_id = self._get_or_upload_header_media()

            if media_id:
                components.append(
                    {
                        "type": "header",
                        "parameters": [{"type": "image", "image": {"id": media_id}}],
                    }
                )
                logger.info(f"Using Media ID for header: {media_id[:20]}...")
            else:
                # fallback: استخدام header_handle من ميتا
                header_handle = template_info.get("header_handle")
                if header_handle:
                    components.append(
                        {
                            "type": "header",
                            "parameters": [
                                {"type": "image", "image": {"link": header_handle}}
                            ],
                        }
                    )
                    logger.warning(f"Using header_handle (may expire)")

        # 2. إضافة متغيرات الـ Body
        if variables:
            params = []
            is_named = (
                template_info and template_info.get("parameter_format") == "NAMED"
            )
            var_names = template_info.get("variable_names", []) if template_info else []

            if isinstance(variables, dict):
                # Dict - استخدام المفاتيح كأسماء
                for name, value in variables.items():
                    param = {"type": "text", "text": str(value)}
                    if is_named:
                        param["parameter_name"] = name
                    params.append(param)

            elif isinstance(variables, list):
                for i, value in enumerate(variables):
                    param = {"type": "text", "text": str(value)}
                    if is_named and i < len(var_names):
                        param["parameter_name"] = var_names[i]
                    params.append(param)

            if params:
                components.append({"type": "body", "parameters": params})

        # بناء الـ Payload
        payload = {
            "messaging_product": "whatsapp",
            "to": formatted_phone,
            "type": "template",
            "template": {"name": template_name, "language": {"code": language}},
        }

        if components:
            payload["template"]["components"] = components

        logger.info(f"Sending template '{template_name}' to {formatted_phone}")
        logger.debug(f"Payload: {payload}")

        try:
            response = requests.post(
                url, headers=self._get_headers(), json=payload, timeout=10
            )

            logger.debug(f"Response: {response.status_code} - {response.text}")

            # إذا فشل بسبب media_id منتهي الصلاحية → أعد الرفع وحاول مجدداً
            if response.status_code == 400:
                resp_data = response.json()
                err_msg = resp_data.get("error", {}).get("message", "")
                if "not a valid whatsapp business account media attachment ID" in err_msg:
                    logger.warning("⚠️ Media ID منتهي الصلاحية - جاري إعادة الرفع تلقائياً...")
                    # مسح الـ ID القديم وإعادة الرفع
                    self.settings.header_media_id = ""
                    self.settings.save(update_fields=["header_media_id"])
                    new_media_id = self._get_or_upload_header_media()
                    if new_media_id:
                        logger.info(f"✅ تم رفع الصورة بنجاح، media_id جديد: {new_media_id}")
                        # تحديث الـ payload بالـ ID الجديد
                        for comp in payload.get("template", {}).get("components", []):
                            if comp.get("type") == "header":
                                for param in comp.get("parameters", []):
                                    if param.get("type") == "image" and "image" in param:
                                        param["image"] = {"id": new_media_id}
                        # إعادة الإرسال
                        response = requests.post(
                            url, headers=self._get_headers(), json=payload, timeout=10
                        )

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending template: {e}")
            if hasattr(e, "response") and e.response:
                logger.error(f"Response body: {e.response.text}")
                # إرفاق تفاصيل الاستجابة بالاستثناء لتُحفظ في DB
                e.meta_response = e.response.text
            raise

    def send_message(
        self,
        customer,
        message_text,
        message_type,
        order=None,
        installation=None,
        inspection=None,
        template=None,
    ):
        """
        إرسال رسالة WhatsApp (واجهة موحدة)
        """
        from .models import WhatsAppMessage

        whatsapp_message = WhatsAppMessage.objects.create(
            customer=customer,
            order=order,
            installation=installation,
            inspection=inspection,
            message_type=message_type,
            template_used=template,
            message_text=message_text,
            phone_number=f"+{self._format_phone_number(customer.phone)}",
            status="PENDING",
        )

        try:
            if self.settings.test_mode:
                logger.info(f"TEST MODE: Would send message to {customer.phone}")
                whatsapp_message.status = "SENT"
                whatsapp_message.external_id = f"TEST_{whatsapp_message.id}"
                whatsapp_message.sent_at = timezone.now()
                whatsapp_message.save()
                return whatsapp_message

            result = self.send_text_message(customer.phone, message_text)

            if result.get("messages"):
                message_id = result["messages"][0].get("id")
                whatsapp_message.external_id = message_id
                whatsapp_message.status = "SENT"
                whatsapp_message.sent_at = timezone.now()
            else:
                whatsapp_message.status = "FAILED"
                whatsapp_message.error_message = str(result)

            whatsapp_message.save()
            return whatsapp_message

        except Exception as e:
            logger.error(f"Error sending WhatsApp message: {e}")
            whatsapp_message.status = "FAILED"
            whatsapp_message.error_message = str(e)
            whatsapp_message.save()
            return whatsapp_message

    def retry_failed_message(self, message_id):
        """إعادة محاولة إرسال رسالة فاشلة"""
        from .models import WhatsAppMessage

        try:
            message = WhatsAppMessage.objects.get(id=message_id)

            if message.status != "FAILED":
                return False

            message.status = "PENDING"
            message.error_message = ""
            message.save()

            result = self.send_text_message(
                to=message.customer.phone, message=message.message_text
            )

            if result.get("messages"):
                message.status = "SENT"
                message.external_id = result["messages"][0].get("id")
                message.sent_at = timezone.now()
            else:
                message.status = "FAILED"
                message.error_message = str(result.get("error", "Unknown error"))

            message.save()
            return message.status == "SENT"

        except Exception as e:
            logger.error(f"Error retrying message {message_id}: {e}")
            return False

    def render_template(self, template, context):
        """تعبئة قالب بالبيانات"""
        text = template.template_text
        for key, value in context.items():
            text = text.replace(f"{{{key}}}", str(value))
        return text
