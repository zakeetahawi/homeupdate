#!/bin/bash
# فلتر لإخفاء الطلبات غير المرغوب فيها من logs الخادم

while IFS= read -r line; do
    # تجاهل طلبات الإشعارات
    if [[ "$line" == *"/accounts/notifications/data/"* ]]; then
        continue
    fi
    
    # تجاهل طلبات API المستخدمين النشطين
    if [[ "$line" == *"/accounts/api/online-users/"* ]]; then
        continue
    fi
    
    # تجاهل طلبات الصور
    if [[ "$line" == *"/media/users/"* ]] || [[ "$line" == *"/media/"* ]]; then
        continue
    fi
    
    # تجاهل طلبات الملفات الثابتة
    if [[ "$line" == *"/static/"* ]]; then
        continue
    fi
    
    # تجاهل طلبات favicon
    if [[ "$line" == *"favicon.ico"* ]]; then
        continue
    fi
    
    # عرض باقي الطلبات
    echo "$line"
done
