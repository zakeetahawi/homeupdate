"""
Mixins مساعدة للتطبيق
"""

class PaginationFixMixin:
    """
    Mixin لإصلاح مشكلة pagination عندما يكون GET parameters arrays
    يجب إضافته لجميع ListView classes التي تستخدم pagination
    """
    
    def dispatch(self, request, *args, **kwargs):
        # إصلاح مشكلة GET parameters عندما تكون arrays
        new_get = request.GET.copy()
        fixed_params = False
        
        # قائمة بالمعاملات التي يجب أن تكون arrays (فلاتر متعددة الاختيار)
        array_params = [
            'status', 'branch', 'order_type', 'production_line', 
            'search_columns', 'status[]', 'branch[]', 'order_type[]', 
            'production_line[]', 'search_columns[]'
        ]
        
        for key, value in request.GET.items():
            if isinstance(value, (list, tuple)):
                # إذا كان parameter هو list وهو ليس فلتر متعدد الاختيار، خذ العنصر الأول
                if key not in array_params and not key.endswith('[]'):
                    new_value = value[0] if value else ''
                    new_get[key] = new_value
                    fixed_params = True
                # إذا كان فلتر متعدد الاختيار، احتفظ بالقيم كما هي
            elif isinstance(value, str) and value.startswith('[') and value.endswith(']'):
                # إذا كان parameter هو string يحتوي على ['value']، استخرج القيمة
                try:
                    import re
                    # البحث عن pattern ['value'] أو [value] أو ["value"]
                    match = re.search(r"\['([^']+)'\]|\[\"([^\"]+)\"\]|\[([^\]]+)\]", value)
                    if match:
                        new_value = match.group(1) or match.group(2) or match.group(3)
                        new_get[key] = new_value
                        fixed_params = True
                except:
                    pass
        
        if fixed_params:
            request.GET = new_get
        
        return super().dispatch(request, *args, **kwargs)