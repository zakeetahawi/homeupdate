"""
Custom widgets for Django admin
"""

from django import forms
from django.utils.safestring import mark_safe


class DurationRangeWidget(forms.NumberInput):
    """Widget لتحديد مدة العرض مع slider وتحديد النطاق"""

    def __init__(self, attrs=None):
        default_attrs = {
            "class": "duration-range-input",
            "min": "10",
            "max": "50",
            "step": "1",
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)

    def render(self, name, value, attrs=None, renderer=None):
        if value is None:
            value = 20  # القيمة الافتراضية

        attrs = self.build_attrs(self.attrs, attrs)
        attrs["class"] = attrs.get("class", "") + " duration-range-input"

        input_html = super().render(name, value, attrs, renderer)

        widget_html = f"""
        <div class="duration-range-container" style="margin-top: 10px;">
            <div style="display: flex; align-items: center; gap: 15px; margin-bottom: 10px;">
                <label style="font-weight: 500; color: #333; min-width: 120px;">مدة العرض:</label>
                {input_html}
                <span id="duration-display-{name}" style="
                    background: #007bff; 
                    color: white; 
                    padding: 4px 12px; 
                    border-radius: 15px; 
                    font-size: 12px;
                    font-weight: 500;
                    min-width: 60px;
                    text-align: center;
                ">{value} ثانية</span>
            </div>
            
            <div style="margin: 10px 0;">
                <input type="range" 
                       id="duration-slider-{name}"
                       min="10" 
                       max="50" 
                       step="1" 
                       value="{value}"
                       style="width: 100%; height: 6px; background: #ddd; outline: none; border-radius: 3px;"
                       oninput="updateDuration_{name}(this.value)">
                <div style="display: flex; justify-content: space-between; font-size: 11px; color: #666; margin-top: 5px;">
                    <span>10 ثواني</span>
                    <span>30 ثانية</span>
                    <span>50 ثانية</span>
                </div>
            </div>
            
            <div style="font-size: 11px; color: #666; margin-top: 8px;">
                <i class="fas fa-info-circle" style="color: #17a2b8;"></i>
                يمكنك تحديد مدة عرض الرسالة من 10 إلى 50 ثانية
            </div>
        </div>
        
        <script>
            function updateDuration_{name}(value) {{
                const input = document.querySelector('input[name="{name}"]');
                const display = document.getElementById('duration-display-{name}');
                const slider = document.getElementById('duration-slider-{name}');
                
                input.value = value;
                display.textContent = value + ' ثانية';
                
                // تغيير لون المؤشر حسب القيمة
                const percentage = (value - 10) / (50 - 10) * 100;
                if (percentage < 33) {{
                    display.style.background = '#28a745'; // أخضر للقيم المنخفضة
                }} else if (percentage < 66) {{
                    display.style.background = '#ffc107'; // أصفر للقيم المتوسطة  
                    display.style.color = '#333';
                }} else {{
                    display.style.background = '#dc3545'; // أحمر للقيم العالية
                    display.style.color = 'white';
                }}
            }}
            
            // ربط التحديث عند تغيير الحقل النصي
            document.querySelector('input[name="{name}"]').addEventListener('input', function() {{
                const value = Math.max(10, Math.min(50, parseInt(this.value) || 20));
                this.value = value;
                document.getElementById('duration-slider-{name}').value = value;
                updateDuration_{name}(value);
            }});
            
            // تحديث المظهر الأولي
            updateDuration_{name}({value});
        </script>
        
        <style>
            .duration-range-input {{
                border: 2px solid #ddd;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 14px;
                width: 80px;
                text-align: center;
                transition: all 0.3s ease;
            }}
            
            .duration-range-input:focus {{
                border-color: #007bff;
                box-shadow: 0 0 0 3px rgba(0, 123, 255, 0.1);
                outline: none;
            }}
            
            input[type="range"] {{
                -webkit-appearance: none;
                appearance: none;
            }}
            
            input[type="range"]::-webkit-slider-thumb {{
                -webkit-appearance: none;
                appearance: none;
                width: 18px;
                height: 18px;
                background: #007bff;
                border-radius: 50%;
                cursor: pointer;
                transition: all 0.3s ease;
            }}
            
            input[type="range"]::-webkit-slider-thumb:hover {{
                background: #0056b3;
                transform: scale(1.1);
            }}
            
            input[type="range"]::-moz-range-thumb {{
                width: 18px;
                height: 18px;
                background: #007bff;
                border-radius: 50%;
                cursor: pointer;
                border: none;
                transition: all 0.3s ease;
            }}
            
            input[type="range"]::-moz-range-thumb:hover {{
                background: #0056b3;
                transform: scale(1.1);
            }}
        </style>
        """

        return mark_safe(widget_html)


class ColorPickerWidget(forms.TextInput):
    """Widget لاختيار الألوان مع معاينة مرئية"""

    def __init__(self, attrs=None):
        default_attrs = {"class": "color-picker-input"}
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)

    def render(self, name, value, attrs=None, renderer=None):
        # إضافة class خاص للـ widget
        if attrs is None:
            attrs = {}
        attrs["class"] = attrs.get("class", "") + " color-picker-input"

        # إنشاء HTML للـ input الأساسي
        input_html = super().render(name, value, attrs, renderer)

        # قائمة الألوان المحددة مسبقاً
        predefined_colors = [
            ("primary", "#007bff", "أزرق أساسي"),
            ("secondary", "#6c757d", "رمادي ثانوي"),
            ("success", "#28a745", "أخضر نجاح"),
            ("danger", "#dc3545", "أحمر خطر"),
            ("warning", "#ffc107", "أصفر تحذير"),
            ("info", "#17a2b8", "أزرق معلومات"),
            ("light", "#f8f9fa", "رمادي فاتح"),
            ("dark", "#343a40", "رمادي داكن"),
        ]

        # إنشاء HTML للمعاينة والاختيار
        color_picker_html = f"""
        <div class="color-picker-container" style="margin-top: 10px;">
            <div class="predefined-colors" style="display: flex; flex-wrap: wrap; gap: 5px; margin-bottom: 10px;">
                <small style="width: 100%; color: #666;">الألوان المحددة مسبقاً:</small>
        """

        for color_key, color_value, color_name in predefined_colors:
            color_picker_html += f"""
                <button type="button" 
                        class="color-option" 
                        data-color="{color_key}"
                        style="width: 30px; height: 30px; background-color: {color_value}; border: 2px solid #ddd; border-radius: 4px; cursor: pointer; position: relative;"
                        title="{color_name}"
                        onclick="selectColor('{name}', '{color_key}', '{color_value}')">
                </button>
            """

        color_picker_html += """
            </div>
            <div class="custom-color" style="margin-top: 10px;">
                <small style="color: #666;">أو اختر لون مخصص:</small>
                <input type="color" 
                       class="custom-color-picker" 
                       style="width: 40px; height: 30px; border: none; cursor: pointer; margin-left: 10px;"
                       onchange="selectCustomColor(this, '{name}')">
            </div>
            <div class="current-color-preview" style="margin-top: 10px; padding: 10px; border: 1px solid #ddd; border-radius: 4px; background-color: #f8f9fa;">
                <small style="color: #666;">المعاينة:</small>
                <div class="preview-box" 
                     style="width: 100%; height: 30px; border-radius: 4px; margin-top: 5px; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold;"
                     id="{name}_preview">
                    نص تجريبي
                </div>
            </div>
        </div>
        
        <script>
        function selectColor(inputName, colorKey, colorValue) {{
            const input = document.querySelector(`input[name="${{inputName}}"]`);
            const preview = document.getElementById(inputName + '_preview');
            
            input.value = colorKey;
            updateColorPreview(preview, colorKey, colorValue);
        }}
        
        function selectCustomColor(colorInput, inputName) {{
            const input = document.querySelector(`input[name="${{inputName}}"]`);
            const preview = document.getElementById(inputName + '_preview');
            const customColor = colorInput.value;
            
            input.value = customColor;
            updateColorPreview(preview, customColor, customColor);
        }}
        
        function updateColorPreview(preview, colorKey, colorValue) {{
            if (colorKey === 'light') {{
                preview.style.backgroundColor = colorValue;
                preview.style.color = '#333';
            }} else {{
                preview.style.backgroundColor = colorValue;
                preview.style.color = 'white';
            }}
        }}
        
        // تحديث المعاينة عند تحميل الصفحة
        document.addEventListener('DOMContentLoaded', function() {{
            const input = document.querySelector(`input[name="{name}"]`);
            const preview = document.getElementById('{name}_preview');
            
            if (input && preview && input.value) {{
                const colorMap = {{
                    'primary': '#007bff',
                    'secondary': '#6c757d', 
                    'success': '#28a745',
                    'danger': '#dc3545',
                    'warning': '#ffc107',
                    'info': '#17a2b8',
                    'light': '#f8f9fa',
                    'dark': '#343a40'
                }};
                
                const colorValue = colorMap[input.value] || input.value;
                updateColorPreview(preview, input.value, colorValue);
            }}
        }});
        </script>
        """.format(
            name=name
        )

        return mark_safe(input_html + color_picker_html)


class IconPickerWidget(forms.TextInput):
    """Widget لاختيار الأيقونات مع معاينة مرئية"""

    def __init__(self, attrs=None):
        default_attrs = {"class": "icon-picker-input"}
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)

    def render(self, name, value, attrs=None, renderer=None):
        if attrs is None:
            attrs = {}
        attrs["class"] = attrs.get("class", "") + " icon-picker-input"

        input_html = super().render(name, value, attrs, renderer)

        # قائمة الأيقونات المحددة مسبقاً
        predefined_icons = [
            ("fas fa-bell", "جرس"),
            ("fas fa-info-circle", "معلومات"),
            ("fas fa-exclamation-triangle", "تحذير"),
            ("fas fa-check-circle", "صح"),
            ("fas fa-times-circle", "خطأ"),
            ("fas fa-star", "نجمة"),
            ("fas fa-heart", "قلب"),
            ("fas fa-home", "منزل"),
            ("fas fa-user", "مستخدم"),
            ("fas fa-envelope", "بريد"),
            ("fas fa-phone", "هاتف"),
            ("fas fa-calendar", "تقويم"),
            ("fas fa-clock", "ساعة"),
            ("fas fa-cog", "إعدادات"),
            ("fas fa-search", "بحث"),
            ("fas fa-plus", "إضافة"),
            ("fas fa-minus", "حذف"),
            ("fas fa-edit", "تعديل"),
            ("fas fa-trash", "سلة مهملات"),
            ("fas fa-download", "تحميل"),
            ("fas fa-upload", "رفع"),
            ("fas fa-share", "مشاركة"),
            ("fas fa-print", "طباعة"),
            ("fas fa-save", "حفظ"),
        ]

        icon_picker_html = f"""
        <div class="icon-picker-container" style="margin-top: 10px;">
            <div class="predefined-icons" style="margin-bottom: 10px;">
                <small style="color: #666; display: block; margin-bottom: 10px;">الأيقونات المحددة مسبقاً:</small>
                <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 5px; max-height: 300px; overflow-y: auto; border: 1px solid #ddd; padding: 10px; border-radius: 4px;">
        """

        for icon_class, icon_name in predefined_icons:
            icon_picker_html += f"""
                <button type="button" 
                        class="icon-option" 
                        data-icon="{icon_class}"
                        style="display: flex; align-items: center; padding: 8px; border: 1px solid #ddd; border-radius: 4px; background: white; cursor: pointer; transition: all 0.2s;"
                        title="{icon_name}"
                        onclick="selectIcon('{name}', '{icon_class}')"
                        onmouseover="this.style.backgroundColor='#f0f0f0'"
                        onmouseout="this.style.backgroundColor='white'">
                    <i class="{icon_class}" style="margin-left: 8px; width: 16px; text-align: center;"></i>
                    <small>{icon_name}</small>
                </button>
            """

        icon_picker_html += f"""
                </div>
            </div>
            <div class="custom-icon" style="margin-top: 10px;">
                <small style="color: #666;">أو اكتب اسم الأيقونة يدوياً (FontAwesome):</small>
                <input type="text" 
                       class="custom-icon-input" 
                       placeholder="مثال: fas fa-home"
                       style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; margin-top: 5px;"
                       onkeyup="previewCustomIcon(this, '{name}')"
                       onchange="selectCustomIcon(this, '{name}')">
            </div>
            <div class="current-icon-preview" style="margin-top: 10px; padding: 10px; border: 1px solid #ddd; border-radius: 4px; background-color: #f8f9fa; text-align: center;">
                <small style="color: #666; display: block; margin-bottom: 10px;">المعاينة:</small>
                <div class="preview-icon" 
                     id="{name}_preview"
                     style="font-size: 24px; color: #333;">
                    <i class="fas fa-question"></i>
                </div>
                <small id="{name}_preview_text" style="color: #666; margin-top: 5px; display: block;">لم يتم تحديد أيقونة</small>
            </div>
        </div>
        
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
        
        <script>
        function selectIcon(inputName, iconClass) {{
            const input = document.querySelector(`input[name="${{inputName}}"]`);
            const preview = document.getElementById(inputName + '_preview');
            const previewText = document.getElementById(inputName + '_preview_text');
            
            input.value = iconClass;
            preview.innerHTML = `<i class="${{iconClass}}"></i>`;
            previewText.textContent = iconClass;
        }}
        
        function selectCustomIcon(iconInput, inputName) {{
            const input = document.querySelector(`input[name="${{inputName}}"]`);
            const preview = document.getElementById(inputName + '_preview');
            const previewText = document.getElementById(inputName + '_preview_text');
            const customIcon = iconInput.value.trim();
            
            if (customIcon) {{
                input.value = customIcon;
                preview.innerHTML = `<i class="${{customIcon}}"></i>`;
                previewText.textContent = customIcon;
            }}
        }}
        
        function previewCustomIcon(iconInput, inputName) {{
            const preview = document.getElementById(inputName + '_preview');
            const previewText = document.getElementById(inputName + '_preview_text');
            const customIcon = iconInput.value.trim();
            
            if (customIcon) {{
                preview.innerHTML = `<i class="${{customIcon}}"></i>`;
                previewText.textContent = customIcon;
            }} else {{
                preview.innerHTML = `<i class="fas fa-question"></i>`;
                previewText.textContent = 'لم يتم تحديد أيقونة';
            }}
        }}
        
        // تحديث المعاينة عند تحميل الصفحة
        document.addEventListener('DOMContentLoaded', function() {{
            const input = document.querySelector(`input[name="{name}"]`);
            const preview = document.getElementById('{name}_preview');
            const previewText = document.getElementById('{name}_preview_text');
            
            if (input && preview && input.value) {{
                preview.innerHTML = `<i class="${{input.value}}"></i>`;
                previewText.textContent = input.value;
            }}
        }});
        </script>
        """

        return mark_safe(input_html + icon_picker_html)
