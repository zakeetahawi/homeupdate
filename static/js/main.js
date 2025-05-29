// Theme Management
document.addEventListener('DOMContentLoaded', function() {
    // Get theme selector element
    const themeSelector = document.getElementById('themeSelector');
    if (!themeSelector) return;

    // Load saved theme from localStorage
    const savedTheme = localStorage.getItem('selectedTheme') || 'default';
    themeSelector.value = savedTheme;
    applyTheme(savedTheme);

    // Listen for theme changes
    themeSelector.addEventListener('change', function(e) {
        const selectedTheme = e.target.value;
        applyTheme(selectedTheme);
        localStorage.setItem('selectedTheme', selectedTheme);
        
        // تأخير بسيط قبل إضافة الزر لضمان تحميل كافة العناصر
        setTimeout(() => {
            // إضافة زر تفعيل بجانب اسم الثيم المحدد مباشرة
            addActivateButton(selectedTheme);
        }, 100);
    });
    
    // إضافة وظيفة النقر بالزر الأيمن على خيارات الثيم
    setupRightClickThemeSelector();
    
    // تأخير بسيط قبل إضافة الزر لضمان تحميل كافة العناصر
    setTimeout(() => {
        // إضافة أزرار التفعيل مباشرة عند تحميل الصفحة
        addActivateButton(savedTheme);
        
        // تأكيد أن القوائم المنسدلة تظهر أمام كل شيء
        fixDropdownZIndex();
        
        // إضافة التلميح حتى لو لم يظهر الزر
        addThemeRightClickHint();
    }, 300);
});

function applyTheme(theme) {
    // تطبيق انتقال سلس
    document.body.style.transition = 'background-color 0.3s ease, color 0.3s ease';
    document.documentElement.style.transition = 'background-color 0.3s ease, color 0.3s ease';
    
    // إزالة أي ثيم موجود
    document.body.removeAttribute('data-theme');
    document.documentElement.removeAttribute('data-theme');
    
    // تطبيق الثيم الجديد إذا لم يكن افتراضياً
    if (theme !== 'default') {
        document.body.setAttribute('data-theme', theme);
        document.documentElement.setAttribute('data-theme', theme);
    }

    // حفظ تفضيل الثيم
    localStorage.setItem('selectedTheme', theme);

    // إزالة الانتقال بعد اكتماله
    setTimeout(() => {
        document.body.style.transition = '';
        document.documentElement.style.transition = '';
    }, 300);
    
    // تطبيق فوري على الجداول إذا كان الثيم أسود
    if (theme === 'modern-black') {
        applyTableStyles();
    }
}

// تطبيق أنماط الجداول فوراً
function applyTableStyles() {
    const tables = document.querySelectorAll('table, .table');
    tables.forEach(table => {
        table.style.backgroundColor = '#1a1a1a';
        table.style.color = '#ffffff';
        table.style.border = '1px solid #333333';
        
        // تطبيق على الصفوف والخلايا
        const cells = table.querySelectorAll('th, td');
        cells.forEach(cell => {
            cell.style.backgroundColor = cell.tagName === 'TH' ? '#222222' : '#1a1a1a';
            cell.style.color = '#ffffff';
            cell.style.borderColor = '#333333';
        });
    });
}

// إضافة زر تعيين الثيم الافتراضي
document.addEventListener('DOMContentLoaded', function() {
    const themeSelector = document.getElementById('themeSelector');
    if (themeSelector && window.user && window.user.is_staff) {
        // إنشاء زر تعيين كافتراضي
        const setDefaultBtn = document.createElement('button');
        setDefaultBtn.className = 'btn btn-sm btn-outline-secondary mt-2';
        setDefaultBtn.innerHTML = '<i class="fas fa-star"></i> تعيين كافتراضي';
        setDefaultBtn.onclick = function() {
            setAsDefaultTheme();
        };
        
        // إضافة الزر بعد منتقي الثيم
        const themeContainer = themeSelector.parentElement;
        themeContainer.appendChild(setDefaultBtn);
    }
});

// دالة تعيين الثيم كافتراضي
function setAsDefaultTheme() {
    const currentTheme = document.getElementById('themeSelector').value;
    
    // إرسال طلب لحفظ الثيم كافتراضي
    fetch('/set-default-theme/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({
            theme: currentTheme
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            Swal.fire({
                icon: 'success',
                title: 'تم تعيين الثيم الافتراضي!',
                text: `تم تعيين "${getThemeName(currentTheme)}" كثيم افتراضي للنظام`,
                confirmButtonText: 'حسناً',
                timer: 3000
            });
        } else {
            Swal.fire({
                icon: 'error',
                title: 'خطأ!',
                text: 'فشل في تعيين الثيم الافتراضي. يرجى المحاولة مرة أخرى.',
                confirmButtonText: 'حسناً'
            });
        }
    })
    .catch(error => {
        console.error('Error:', error);
        Swal.fire({
            icon: 'error',
            title: 'خطأ!',
            text: 'حدث خطأ في الاتصال. يرجى المحاولة مرة أخرى.',
            confirmButtonText: 'حسناً'
        });
    });
}

// الحصول على اسم الثيم
function getThemeName(themeValue) {
    const themeNames = {
        'default': 'الثيم الافتراضي',
        'modern-black': 'الأسود الحديث',
        'apple-dark-mode': 'Apple الوضع الليلي',
        'light-sky': 'السماوي الفاتح',
        'soft-pink': 'الوردي الناعم',
        'fresh-mint': 'الأخضر المنعش',
        'calm-lavender': 'البنفسجي الهادئ',
        'warm-beige': 'البيج الدافئ',
        'pastel-blue': 'الأزرق الباستيل',
        'peachy-yellow': 'الأصفر المشمشي',
        'light-gray': 'الرمادي الفاتح',
        'light-turquoise': 'التركواز الفاتح',
        'soft-lilac': 'الليلكي الناعم'
    };
    return themeNames[themeValue] || themeValue;
}

// الحصول على CSRF token
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Generic alert dismissal
document.addEventListener('DOMContentLoaded', function() {
    // Auto-hide alerts after 5 seconds
    setTimeout(function() {
        const alerts = document.querySelectorAll('.alert');
        alerts.forEach(function(alert) {
            const dismissBtn = new bootstrap.Alert(alert);
            dismissBtn.close();
        });
    }, 5000);
});

// Form validation
document.addEventListener('DOMContentLoaded', function() {
    const forms = document.querySelectorAll('.needs-validation');
    
    Array.from(forms).forEach(function(form) {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });
});

// Initialize tooltips and popovers
document.addEventListener('DOMContentLoaded', function() {
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
});

// Responsive table handling
document.addEventListener('DOMContentLoaded', function() {
    const tables = document.querySelectorAll('.table-responsive table');
    tables.forEach(table => {
        if (table.offsetWidth > table.parentElement.offsetWidth) {
            table.parentElement.classList.add('table-scroll');
        }
    });
});

// Dynamic form fields
function addFormField(containerId, template) {
    const container = document.getElementById(containerId);
    const newRow = template.cloneNode(true);
    container.appendChild(newRow);
}

// Format currency in Egyptian Pounds
function formatCurrency(amount) {
    return new Intl.NumberFormat('ar-EG', { 
        style: 'currency', 
        currency: 'EGP' 
    }).format(amount);
}

// Function to toggle password visibility
function togglePasswordVisibility(inputId, iconId) {
    var passwordInput = document.getElementById(inputId);
    var icon = document.getElementById(iconId);
    
    if (passwordInput.type === 'password') {
        passwordInput.type = 'text';
        icon.classList.remove('fa-eye');
        icon.classList.add('fa-eye-slash');
    } else {
        passwordInput.type = 'password';
        icon.classList.remove('fa-eye-slash');
        icon.classList.add('fa-eye');
    }
}

// تصحيح مشكلة ظهور القوائم المنسدلة خلف العناصر
function fixDropdownZIndex() {
    // جلب جميع القوائم المنسدلة
    const dropdowns = document.querySelectorAll('.dropdown');
    
    // تعيين z-index عالي لكل قائمة
    dropdowns.forEach(dropdown => {        dropdown.style.position = 'relative';
        dropdown.style.zIndex = '10000000';
        
        // تعيين مستويات أعلى للقوائم في الثيم الداكن
        if (document.documentElement.getAttribute('data-theme') === 'modern-black') {
            const menu = dropdown.querySelector('.dropdown-menu');
            if (menu) {
                menu.style.zIndex = '10000000';
                menu.style.position = 'absolute';
            }
        }
    });
}

// دالة إضافة زر التفعيل بجوار اسم الثيم
function addActivateButton(currentTheme) {
    console.log('Adding activate button for theme:', currentTheme);
    // إزالة أي أزرار سابقة
    const oldButtons = document.querySelectorAll('.theme-activate-btn');
    oldButtons.forEach(btn => btn.remove());
    
    // إضافة زر تفعيل بجانب الثيم المحدد
    const themeSelector = document.getElementById('themeSelector');
    if (!themeSelector) {
        console.error('Theme selector not found');
        return;
    }
    
    // إنشاء زر التفعيل
    const activateBtn = document.createElement('button');
    activateBtn.type = 'button'; // تحديد النوع لمنع إرسال النماذج
    activateBtn.className = 'btn btn-success theme-activate-btn';
    activateBtn.setAttribute('id', 'theme-activate-button');
    activateBtn.style.position = 'relative';
    activateBtn.style.zIndex = '2147483647'; // أقصى قيمة z-index
    activateBtn.style.padding = '10px 20px';
    activateBtn.style.fontWeight = 'bold';
    activateBtn.style.boxShadow = '0 0 20px rgba(0,255,136,0.8)';
    activateBtn.style.fontSize = '16px';
    activateBtn.style.border = '2px solid #00FF88';
    activateBtn.style.background = 'linear-gradient(135deg, #00D2FF, #00FF88)';
    activateBtn.style.color = '#000';
    activateBtn.style.borderRadius = '8px';
    activateBtn.style.cursor = 'pointer';
    activateBtn.style.textShadow = '0 1px 1px rgba(255,255,255,0.5)';
    activateBtn.style.marginTop = '15px';
    activateBtn.style.marginBottom = '5px';
    activateBtn.innerHTML = '<i class="fas fa-check-circle"></i> تفعيل الثيم';
    activateBtn.title = 'تفعيل وتثبيت هذا الثيم كافتراضي للنظام';
    
    // إضافة حدث النقر
    activateBtn.onclick = function(e) {
        e.preventDefault();
        e.stopPropagation();
        console.log('Activate button clicked');
        setAsDefaultTheme();
    };
    
    // البحث عن الحاوية المناسبة
    const container = themeSelector.closest('.px-3');
    if (container) {
        console.log('Container found for activate button');
        container.style.position = 'relative';
        
        // إنشاء حاوية مخصصة للزر للتأكد من عرضه بشكل صحيح
        const btnContainer = document.createElement('div');
        btnContainer.id = 'theme-activate-btn-container';
        btnContainer.style.position = 'relative';
        btnContainer.style.width = '100%';
        btnContainer.style.marginTop = '15px';
        btnContainer.style.marginBottom = '5px';
        btnContainer.style.display = 'flex';
        btnContainer.style.justifyContent = 'center';
        btnContainer.style.alignItems = 'center';
        btnContainer.style.zIndex = '2147483647'; // أقصى قيمة
        
        // إضافة الزر مع تأكيد أنه يظهر بوضوح
        activateBtn.style.display = 'block';
        activateBtn.style.width = '100%';
        
        // إضافة تأثير النبض للزر
        const pulseStyle = document.createElement('style');
        pulseStyle.textContent = `
            @keyframes pulse {
                0% {transform: scale(1);}
                50% {transform: scale(1.05);}
                100% {transform: scale(1);}
            }
            #theme-activate-button {
                animation: pulse 2s infinite;
            }
        `;
        document.head.appendChild(pulseStyle);
        
        // إضافة الزر إلى الحاوية
        btnContainer.appendChild(activateBtn);
        
        // إضافة حاوية الزر إلى الحاوية الرئيسية
        container.appendChild(btnContainer);
        
        // إضافة التلميح النصي
        addThemeRightClickHint();
    } else {
        console.error('Container not found for activate button');
    }
}

// دالة إضافة تلميح النقر بزر الماوس الأيمن
function addThemeRightClickHint() {
    // إزالة أي تلميحات سابقة
    const oldHints = document.querySelectorAll('.theme-right-click-hint');
    oldHints.forEach(hint => hint.remove());
    
    const themeSelector = document.getElementById('themeSelector');
    if (!themeSelector) return;
    
    const container = themeSelector.closest('.px-3');
    if (container) {
        // إضافة نص توضيحي
        const helpText = document.createElement('div');
        helpText.className = 'small mt-2 theme-right-click-hint';
        helpText.style.color = '#00D2FF';
        helpText.style.textAlign = 'center';
        helpText.style.fontWeight = 'bold';
        helpText.style.textShadow = '0 0 3px rgba(0,0,0,0.7)';
        helpText.style.zIndex = '2147483647';
        helpText.innerHTML = 'اضغط على زر التفعيل لتثبيت الثيم كافتراضي للنظام <br><span style="font-size: 11px;"><i class="fas fa-mouse"></i> أو انقر بزر الماوس الأيمن على أي ثيم لتفعيله</span>';
        container.appendChild(helpText);
    }
}

// دالة إعداد وظيفة النقر بالزر الأيمن على خيارات الثيم
function setupRightClickThemeSelector() {
    console.log('Setting up right-click theme selector');
    const themeSelector = document.getElementById('themeSelector');
    if (!themeSelector) {
        console.error('Theme selector not found');
        return;
    }
    
    // إضافة أحداث النقر بالزر الأيمن لكل خيار
    const options = themeSelector.querySelectorAll('option');
    options.forEach(option => {
        // إضافة خاصية مخصصة لتحديد قيمة الثيم
        option.setAttribute('data-theme-value', option.value);
        
        // إضافة النمط ليظهر بشكل قابل للنقر عليه
        option.style.cursor = 'context-menu';
        
        // إضافة تلميح عند مرور المؤشر
        option.title = "انقر بزر الماوس الأيمن لتعيين هذا الثيم كافتراضي";
    });
    
    // إضافة حدث النقر بالزر الأيمن لمنتقي الثيم نفسه
    themeSelector.addEventListener('contextmenu', function(e) {
        e.preventDefault();
        console.log('Right-click detected on theme selector');
        
        // الحصول على الخيار المحدد حالياً
        const themeValue = themeSelector.value;
        
        // عرض قائمة سياق
        showContextMenu(e.clientX, e.clientY, themeValue);
    });
    
    // إضافة حدث تغيير للقائمة المنسدلة
    themeSelector.addEventListener('mousedown', function(e) {
        // التحقق ما إذا كان النقر بالزر الأيمن
        if (e.button === 2) {
            e.preventDefault();
            e.stopPropagation();
            console.log('Right mouse button detected');
            
            // الحصول على الخيار المحدد حالياً
            const themeValue = themeSelector.value;
            
            // عرض قائمة سياق
            showContextMenu(e.clientX, e.clientY, themeValue);
        }
    });
    
    // إغلاق القائمة المنسدلة عند النقر في أي مكان آخر
    document.addEventListener('click', function() {
        hideContextMenu();
    });
    
    // إضافة معالجة حق السياق لقائمة الثيم بأكملها
    document.addEventListener('DOMContentLoaded', function() {
        // منع القائمة الافتراضية للنقر بالزر الأيمن على منتقي الثيم
        const themeSelector = document.getElementById('themeSelector');
        if (themeSelector) {
            themeSelector.addEventListener('contextmenu', function(e) {
                e.preventDefault();
                e.stopPropagation();
                return false;
            });
            
            // إضافة حدث للنقر المباشر على القائمة نفسها
            themeSelector.parentElement.addEventListener('contextmenu', function(e) {
                e.preventDefault();
                e.stopPropagation();
                
                // الحصول على الثيم الحالي
                const themeValue = themeSelector.value;
                
                // عرض قائمة السياق
                showContextMenu(e.clientX, e.clientY, themeValue);
                return false;
            });
        }
        
        // إعداد مؤشر تلقائي على قائمة النقر بالزر الأيمن
        document.addEventListener('mousedown', function(e) {
            // النقر بالزر الأيمن فقط
            if (e.button === 2) {
                const themeSelector = document.getElementById('themeSelector');
                const themeHint = document.querySelector('.theme-selector-hint');
                const themeContainer = themeSelector?.closest('.px-3');
                
                // التحقق مما إذا كان النقر داخل منطقة الثيم
                if (themeContainer && themeContainer.contains(e.target)) {
                    e.preventDefault();
                    e.stopPropagation();
                    
                    // الحصول على الثيم الحالي والعرض
                    const themeValue = themeSelector.value;
                    showContextMenu(e.clientX, e.clientY, themeValue);
                    return false;
                }
            }
        });
    });
}

// عرض قائمة النقر بالزر الأيمن
function showContextMenu(x, y, themeValue) {
    console.log('Showing context menu for theme:', themeValue);
    // إزالة أي قوائم سابقة
    hideContextMenu();
    
    // إنشاء قائمة السياق
    const contextMenu = document.createElement('div');
    contextMenu.id = 'theme-context-menu';
    contextMenu.style.position = 'fixed';
    contextMenu.style.left = `${x}px`;
    contextMenu.style.top = `${y}px`;
    contextMenu.style.backgroundColor = 'var(--card-bg, #ffffff)';
    contextMenu.style.border = '1px solid var(--border, #ccc)';
    contextMenu.style.borderRadius = '8px';
    contextMenu.style.boxShadow = '0 5px 15px rgba(0,0,0,0.2)';
    contextMenu.style.padding = '10px 0';
    contextMenu.style.zIndex = '9999999999';
    contextMenu.style.minWidth = '200px';
    
    // التأكد من أن القائمة تظهر في حدود الشاشة
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;
    
    // إضافة عنوان القائمة
    const contextMenuHeader = document.createElement('div');
    contextMenuHeader.style.padding = '5px 15px';
    contextMenuHeader.style.borderBottom = '1px solid var(--border, #ccc)';
    contextMenuHeader.style.marginBottom = '5px';
    contextMenuHeader.style.fontWeight = 'bold';
    contextMenuHeader.style.color = 'var(--primary, #000)';
    contextMenuHeader.style.fontSize = '14px';
    contextMenuHeader.innerHTML = `<i class="fas fa-palette"></i> ثيم: ${getThemeName(themeValue)}`;
    contextMenu.appendChild(contextMenuHeader);
    
    // إضافة خيار تعيين الثيم كافتراضي
    const setDefaultOption = document.createElement('div');
    setDefaultOption.style.padding = '8px 15px';
    setDefaultOption.style.cursor = 'pointer';
    setDefaultOption.style.transition = 'all 0.2s ease';
    setDefaultOption.style.color = 'var(--text-primary, #000)';
    setDefaultOption.innerHTML = '<i class="fas fa-star"></i> تعيين كثيم افتراضي';
    setDefaultOption.addEventListener('mouseover', function() {
        this.style.backgroundColor = 'var(--primary, #f0f0f0)';
        if (document.documentElement.getAttribute('data-theme') === 'modern-black') {
            this.style.color = '#000';
        }
    });
    setDefaultOption.addEventListener('mouseout', function() {
        this.style.backgroundColor = 'transparent';
        if (document.documentElement.getAttribute('data-theme') === 'modern-black') {
            this.style.color = 'var(--text-primary, #fff)';
        }
    });
    setDefaultOption.addEventListener('click', function() {
        setAsDefaultTheme();
        hideContextMenu();
    });
    contextMenu.appendChild(setDefaultOption);
    
    // إضافة قائمة السياق إلى الصفحة
    document.body.appendChild(contextMenu);
    
    // التأكد من أن القائمة تظهر في حدود الشاشة
    setTimeout(() => {
        const menuRect = contextMenu.getBoundingClientRect();
        
        // تصحيح موقع القائمة إذا كانت خارج حدود الشاشة
        if (menuRect.right > viewportWidth) {
            contextMenu.style.left = `${viewportWidth - menuRect.width - 10}px`;
        }
        
        if (menuRect.bottom > viewportHeight) {
            contextMenu.style.top = `${viewportHeight - menuRect.height - 10}px`;
        }
    }, 0);
}

// إخفاء قائمة النقر بالزر الأيمن
function hideContextMenu() {
    const contextMenu = document.getElementById('theme-context-menu');
    if (contextMenu) {
        contextMenu.remove();
    }
}

// وظيفة اختبار لقياس مشكلة عدم ظهور القائمة والزر
function debugThemeControls() {
    console.log('----- Theme Debug Info -----');
    
    // التحقق من وجود منتقي الثيم
    const themeSelector = document.getElementById('themeSelector');
    console.log('Theme Selector exists:', !!themeSelector);
    
    if (themeSelector) {
        // بيانات منتقي الثيم
        console.log('Theme Selector value:', themeSelector.value);
        console.log('Theme Selector parent:', themeSelector.parentElement);
        console.log('Container (.px-3):', themeSelector.closest('.px-3'));
        
        // التحقق من زر التفعيل
        const activateBtn = document.getElementById('theme-activate-button');
        console.log('Activate Button exists:', !!activateBtn);
        
        if (activateBtn) {
            console.log('Activate Button display:', window.getComputedStyle(activateBtn).display);
            console.log('Activate Button visibility:', window.getComputedStyle(activateBtn).visibility);
        }
        
        // التحقق من تلميح النقر بالزر الأيمن
        const rightClickHint = document.querySelector('.theme-right-click-hint');
        console.log('Right-click hint exists:', !!rightClickHint);
    }
    
    console.log('---------------------------');
}

// استدعاء وظيفة تصحيح بعد تحميل الصفحة
document.addEventListener('DOMContentLoaded', function() {
    // تأخير بسيط قبل تنفيذ اختبار القائمة
    setTimeout(debugThemeControls, 1000);
});
