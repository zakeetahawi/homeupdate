/**
 * base-utilities.js
 * ==================
 * وظائف JavaScript الأساسية المُستخرجة من base.html
 * تاريخ الاستخراج: 2026-02-15
 *
 * يحتوي على:
 * - تبديل قائمة المستخدم المنسدلة
 * - تنبيه نجاح الاستعادة (SweetAlert)
 * - تحديث اللوغو المباشر
 * - تحويل القوائم المنسدلة للهاتف المحمول
 * - إصلاح modal backdrop
 * - دالة Toast notification
 */

// ═══════════════════════════════════════════════════════════════════
// 1. قائمة المستخدم المنسدلة
// ═══════════════════════════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', function () {
    var userBtn = document.getElementById('customUserBtn');
    var userDropdown = document.getElementById('customUserDropdown');
    if (userBtn && userDropdown) {
        userBtn.addEventListener('click', function (e) {
            e.stopPropagation();
            userDropdown.style.display = userDropdown.style.display === 'block' ? 'none' : 'block';
            userDropdown.focus();
        });
    }
    document.addEventListener('click', function (e) {
        if (userDropdown) userDropdown.style.display = 'none';
    });
    if (userDropdown) userDropdown.addEventListener('click', function (e) { e.stopPropagation(); });
});

// ═══════════════════════════════════════════════════════════════════
// 2. تنبيه نجاح الاستعادة (Restore Success Alert)
// ═══════════════════════════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', function () {
    var messages = document.querySelectorAll('.alert-success');

    messages.forEach(function (messageElement) {
        var messageText = messageElement.textContent.trim();

        if (messageText.includes('تم استعادة النسخة الاحتياطية بنجاح') ||
            messageText.includes('تمت الاستعادة بنجاح') ||
            messageText.includes('تم استعادة البيانات بنجاح') ||
            messageText.includes('تمت استعادة البيانات بنجاح')) {

            messageElement.style.display = 'none';

            Swal.fire({
                title: 'تمت الاستعادة بنجاح! 🎉',
                html: '<div style="text-align: right; direction: rtl; font-family: \'Segoe UI\', Tahoma, Geneva, Verdana, sans-serif;">' +
                    '<p style="font-size: 16px; margin-bottom: 20px; color: #2c3e50;">' +
                    '<strong>لضمان ظهور جميع البيانات، يرجى اتباع إحدى الخطوات التالية:</strong>' +
                    '</p>' +
                    '<div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 15px 0;">' +
                    '<p style="margin: 8px 0; color: #495057;">' +
                    '<i class="fas fa-sync-alt" style="color: #007bff; margin-left: 8px;"></i>' +
                    '<strong>1. تحديث الصفحة (F5)</strong>' +
                    '</p>' +
                    '<p style="margin: 8px 0; color: #495057;">' +
                    '<i class="fas fa-sign-in-alt" style="color: #28a745; margin-left: 8px;"></i>' +
                    '<strong>2. إعادة تسجيل الدخول</strong>' +
                    '</p>' +
                    '<p style="margin: 8px 0; color: #495057;">' +
                    '<i class="fas fa-clock" style="color: #ffc107; margin-left: 8px;"></i>' +
                    '<strong>3. انتظار دقيقة واحدة للتحديث التلقائي</strong>' +
                    '</p>' +
                    '</div>' +
                    '<p style="font-size: 14px; color: #6c757d; margin-top: 15px;">' +
                    '<i class="fas fa-info-circle" style="margin-left: 5px;"></i>' +
                    'هذا أمر طبيعي ويحدث بسبب التخزين المؤقت للبيانات' +
                    '</p>' +
                    '</div>',
                icon: 'success',
                showCancelButton: true,
                confirmButtonText: '<i class="fas fa-sync-alt"></i> تحديث الصفحة الآن',
                cancelButtonText: '<i class="fas fa-times"></i> إغلاق',
                confirmButtonColor: '#007bff',
                cancelButtonColor: '#6c757d',
                width: '600px',
                customClass: {
                    popup: 'rtl-popup',
                    title: 'rtl-title',
                    content: 'rtl-content'
                },
                showClass: {
                    popup: 'animate__animated animate__fadeInDown'
                },
                hideClass: {
                    popup: 'animate__animated animate__fadeOutUp'
                }
            }).then(function (result) {
                if (result.isConfirmed) {
                    location.reload();
                } else {
                    var reminderToast = Swal.mixin({
                        toast: true,
                        position: 'top-end',
                        showConfirmButton: false,
                        timer: 5000,
                        timerProgressBar: true,
                        didOpen: function (toast) {
                            toast.addEventListener('mouseenter', Swal.stopTimer);
                            toast.addEventListener('mouseleave', Swal.resumeTimer);
                        }
                    });

                    reminderToast.fire({
                        icon: 'info',
                        title: 'تذكير: قم بتحديث الصفحة لرؤية جميع البيانات'
                    });

                    setTimeout(function () {
                        Swal.fire({
                            title: 'تحديث تلقائي',
                            text: 'سيتم تحديث الصفحة الآن لإظهار جميع البيانات',
                            icon: 'info',
                            timer: 3000,
                            timerProgressBar: true,
                            showConfirmButton: false
                        }).then(function () {
                            location.reload();
                        });
                    }, 60000);
                }
            });
        }
    });
});

// ═══════════════════════════════════════════════════════════════════
// 3. تحديث اللوغو المباشر عند الرفع
// ═══════════════════════════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', function () {
    if (!window.location.pathname.includes('/admin/accounts/companyinfo/')) return;

    var logoInput = document.querySelector('input[type="file"][name="logo"]');
    var headerLogoInput = document.querySelector('input[type="file"][name="header_logo"]');
    var headerLogo = document.getElementById('header-logo');
    var homeLogo = document.getElementById('home-logo');
    var aboutLogo = document.getElementById('about-logo');

    if (logoInput) {
        logoInput.addEventListener('change', function (e) {
            var file = e.target.files[0];
            if (file) {
                var tempUrl = URL.createObjectURL(file);
                var otherLogos = [homeLogo, aboutLogo];
                otherLogos.forEach(function (logo) {
                    if (logo) {
                        logo.src = tempUrl + '?v=' + Date.now();
                        logo.style.opacity = '0.7';
                        setTimeout(function () { logo.style.opacity = '1'; }, 200);
                    }
                });

                Swal.fire({
                    title: 'تم رفع لوغو النظام بنجاح! 🎉',
                    text: 'سيتم تحديث اللوغو في جميع صفحات النظام',
                    icon: 'success',
                    timer: 2000,
                    timerProgressBar: true,
                    showConfirmButton: false,
                    position: 'top-end',
                    toast: true
                });
            }
        });
    }

    if (headerLogoInput) {
        headerLogoInput.addEventListener('change', function (e) {
            var file = e.target.files[0];
            if (file) {
                var tempUrl = URL.createObjectURL(file);
                if (headerLogo) {
                    headerLogo.src = tempUrl + '?v=' + Date.now();
                    headerLogo.style.opacity = '0.7';
                    setTimeout(function () { headerLogo.style.opacity = '1'; }, 200);
                }

                Swal.fire({
                    title: 'تم رفع لوغو الهيدر بنجاح! 🎉',
                    text: 'سيتم تحديث لوغو الهيدر في جميع صفحات النظام',
                    icon: 'success',
                    timer: 2000,
                    timerProgressBar: true,
                    showConfirmButton: false,
                    position: 'top-end',
                    toast: true
                });
            }
        });
    }

    // تحديث جميع اللوغوهات عند التحميل لتجنب التخزين المؤقت
    var allLogos = ['header-logo', 'home-logo', 'about-logo'];
    allLogos.forEach(function (logoId) {
        var logo = document.getElementById(logoId);
        if (logo && logo.src && !logo.src.includes('?v=')) {
            logo.src = logo.src + '?v=' + Date.now();
        }
    });
});

// ═══════════════════════════════════════════════════════════════════
// 4. تحويل القوائم المنسدلة إلى أيقونات في الهاتف المحمول
// ═══════════════════════════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', function () {
    function convertDropdownsToIcons() {
        if (window.innerWidth <= 992) {
            var navbarNav = document.querySelector('.navbar-nav');
            if (!navbarNav) return;

            var dropdowns = navbarNav.querySelectorAll('.nav-item.dropdown');

            dropdowns.forEach(function (dropdown) {
                var dropdownMenu = dropdown.querySelector('.dropdown-menu');
                if (!dropdownMenu) return;

                var items = dropdownMenu.querySelectorAll('.dropdown-item');

                items.forEach(function (item) {
                    if (item.tagName === 'HR') return;

                    var href = item.getAttribute('href');
                    var icon = item.querySelector('i');
                    var text = item.textContent.trim();

                    if (href && icon) {
                        var newNavItem = document.createElement('li');
                        newNavItem.className = 'nav-item mobile-icon-item';

                        var newLink = document.createElement('a');
                        newLink.className = 'nav-link';
                        newLink.href = href;

                        var newIcon = icon.cloneNode(true);
                        newIcon.style.fontSize = '2rem';
                        newIcon.style.marginBottom = '0.5rem';

                        var textSpan = document.createElement('span');
                        textSpan.className = 'nav-text';
                        textSpan.textContent = text;

                        newLink.appendChild(newIcon);
                        newLink.appendChild(textSpan);
                        newNavItem.appendChild(newLink);

                        navbarNav.insertBefore(newNavItem, dropdown);
                    }
                });
            });
        }
    }

    convertDropdownsToIcons();

    var resizeTimer;
    window.addEventListener('resize', function () {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(function () {
            document.querySelectorAll('.mobile-icon-item').forEach(function (el) { el.remove(); });
            convertDropdownsToIcons();
        }, 250);
    });

    // إصلاح القوائم المنسدلة في وضع Desktop
    if (window.innerWidth > 992) {
        var dropdownToggles = document.querySelectorAll('.dropdown-toggle');

        dropdownToggles.forEach(function (toggle) {
            toggle.addEventListener('click', function (e) {
                e.preventDefault();
                e.stopPropagation();

                document.querySelectorAll('.dropdown-menu.show').forEach(function (menu) {
                    menu.classList.remove('show');
                });

                var targetMenu = this.nextElementSibling;
                if (targetMenu && targetMenu.classList.contains('dropdown-menu')) {
                    targetMenu.classList.toggle('show');
                }
            });
        });

        document.addEventListener('click', function (e) {
            if (!e.target.closest('.dropdown')) {
                document.querySelectorAll('.dropdown-menu.show').forEach(function (menu) {
                    menu.classList.remove('show');
                });
            }
        });
    }
});

// ═══════════════════════════════════════════════════════════════════
// 5. إصلاح Modal Backdrop
// ═══════════════════════════════════════════════════════════════════

$(document).ready(function () {
    // منع إنشاء backdrop من الأساس
    $.fn.modal.Constructor.Default.backdrop = false;

    $(document).on('show.bs.modal', '.modal', function () {
        $('.modal-backdrop').remove();
        $('body').removeClass('modal-open');
        $('body').css('padding-right', '');
    });

    $(document).on('hidden.bs.modal', '.modal', function () {
        $('.modal-backdrop').remove();
        $('body').removeClass('modal-open');
        $('body').css('padding-right', '');
    });

    setInterval(function () {
        $('.modal-backdrop').remove();
    }, 5000);
});

// ═══════════════════════════════════════════════════════════════════
// 6. Toast Notification Function
// ═══════════════════════════════════════════════════════════════════

function showToastNotification(type, message) {
    var alertClass = type === 'success' ? 'alert-success' :
        type === 'error' || type === 'danger' ? 'alert-danger' :
            type === 'warning' ? 'alert-warning' : 'alert-info';
    var iconClass = type === 'success' ? 'fa-check-circle' :
        type === 'error' || type === 'danger' ? 'fa-exclamation-circle' :
            type === 'warning' ? 'fa-exclamation-triangle' : 'fa-info-circle';

    var toast = document.createElement('div');
    toast.className = 'alert ' + alertClass + ' alert-dismissible fade show';
    toast.style.cssText = 'position: fixed; top: 80px; right: 20px; z-index: 9999; min-width: 300px; max-width: 500px; box-shadow: 0 4px 12px rgba(0,0,0,0.15);';
    toast.innerHTML =
        '<i class="fas ' + iconClass + ' me-2"></i>' + message +
        '<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>';

    document.body.appendChild(toast);

    setTimeout(function () {
        toast.classList.remove('show');
        setTimeout(function () { toast.remove(); }, 150);
    }, 5000);
}
