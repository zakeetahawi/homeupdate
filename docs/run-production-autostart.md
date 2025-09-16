تشغيل `run-production.sh` عند الإقلاع (systemd)
===============================================

الطريقة الموصى بها لتشغيل سكربت الإنتاج تلقائيًا عند إقلاع النظام هي استخدام وحدة `systemd` مخصصة.

ما أضفناه
----------
- `systemd/run-production.service` — وحدة جاهزة لتشغيل `/home/zakee/homeupdate/لينكس/run-production.sh` باسم المستخدم `zakee`، مع `Restart=on-failure`.

كيفية التثبيت
-------------
1. انسخ الوحدة إلى نظام systemd:

   sudo cp systemd/run-production.service /etc/systemd/system/

2. أعد تحميل systemd ومكّن الخدمة لتبدأ عند الإقلاع:

   sudo systemctl daemon-reload
   sudo systemctl enable --now run-production.service

3. تحقق من الحالة والسجلات:

   sudo systemctl status run-production.service
   journalctl -u run-production.service -f

ملاحظات أمان وتشغيل
-------------------
- المستخدم المحدد في الوحدة هو `zakee`. عدّله إذا يجب أن يعمل كـ مستخدم آخر.
- تأكد أن `run-production.sh` قابل للتنفيذ: `chmod +x لينكس/run-production.sh`.
- الوحدة تعتمد على `network.target` و `postgresql.service` و `redis.service` عبر `After`/`Wants`، لكن لا تضمن الترتيب الكامل للتشغيل؛ إن احتجت لإنشاء اعتمادية صارمة، ضع `Requires=postgresql.service` أو أنشئ target مخصص.

بدائل
------
- Cron @reboot: `@reboot /bin/bash /home/zakee/homeupdate/لينكس/run-production.sh`
- `/etc/rc.local` (غير مفضل في الأنظمة الحديثة)
