// order_items.js
// جميع وظائف إدارة عناصر الطلب بشكل منظم وحديث

// تعريف مصفوفة العناصر العامة
window.orderItems = window.orderItems || [];

// دالة لتنسيق القيم العشرية بشكل صحيح (حل مشكلة الاقتطاع في الهواتف المحمولة)
function formatDecimalQuantity(quantity) {
    try {
        if (quantity === null || quantity === undefined) {
            return '0';
        }

        // تحويل إلى رقم للتأكد من صحة القيمة
        const numValue = Number(quantity);

        if (isNaN(numValue) || !isFinite(numValue)) {
            return '0';
        }

        // تنسيق القيمة مع إزالة الأصفار الزائدة
        const formatted = numValue.toFixed(3).replace(/\.?0+$/, '');
        return formatted || '0';

    } catch (error) {
        console.error('خطأ في تنسيق الكمية:', error, 'القيمة:', quantity);
        return '0';
    }
}

// تحديث جدول العناصر المختارة
window.updateLiveOrderItemsTable = function() {
    const tableDiv = document.getElementById('live-order-items-table');
    if (!tableDiv) return;
    
    if (!window.orderItems.length) {
        tableDiv.innerHTML = `
            <div class="text-center py-4">
                <i class="fas fa-shopping-cart text-muted" style="font-size: 2rem;"></i>
                <p class='text-muted mt-2'>لم يتم اختيار أي عناصر بعد</p>
                <p class="small text-muted">اضغط على زر "إضافة عنصر" لبدء إضافة المنتجات</p>
            </div>
        `;
        return;
    }
    
    const totalAmount = window.orderItems.reduce((sum, item) => sum + item.total, 0);
    const totalDiscount = window.orderItems.reduce((sum, item) => {
        const discountPercentage = item.discount_percentage || 0;
        return sum + (item.total * discountPercentage / 100);
    }, 0);
    const totalAfterDiscount = totalAmount - totalDiscount;
    
    let html = `
        <div class="card border-success">
            <div class="card-header text-white" style="background-color: #198754; font-weight: bold;">
                <h6 class="mb-0">
                    <i class="fas fa-list me-2"></i>العناصر المختارة (${window.orderItems.length})
                </h6>
            </div>
            <div class="card-body p-0">
                <div class="table-responsive">
                    <table class='table table-sm mb-0 table-hover'>
                        <thead class="table-light">
                            <tr>
                                <th width="50">#</th>
                                <th>المنتج</th>
                                <th width="80">الكمية</th>
                                <th width="100">سعر الوحدة</th>
                                <th width="100">الخصم %</th>
                                <th width="100">مبلغ الخصم</th>
                                <th width="120">الإجمالي بعد الخصم</th>
                                <th width="80">إجراءات</th>
                            </tr>
                        </thead>
                        <tbody>
    `;
    
    window.orderItems.forEach((item, idx) => {
        const discountPercentage = item.discount_percentage || 0;
        const discountAmount = (item.total * discountPercentage / 100);
        const totalAfterDiscount = item.total - discountAmount;
        
        html += `
            <tr>
                <td><span class="badge bg-primary">${idx+1}</span></td>
                <td>
                    <strong>${item.name}</strong>
                    ${item.code ? `<br><small class="text-muted">كود: ${item.code}</small>` : ''}
                    ${item.notes ? `<br><small class="text-info"><i class="fas fa-sticky-note me-1"></i>${item.notes}</small>` : ''}
                </td>
                <td><span class="badge bg-info">${formatDecimalQuantity(item.quantity)}</span></td>
                <td>${item.unit_price} ج.م</td>
                <td>
                    <select class="form-select form-select-sm discount-select" 
                            onchange="updateItemDiscount(${idx}, this.value)" 
                            style="width: 80px; font-size: 0.875rem;">
                        <option value="0" ${discountPercentage == 0 ? 'selected' : ''}>0%</option>
                        <option value="1" ${discountPercentage == 1 ? 'selected' : ''}>1%</option>
                        <option value="2" ${discountPercentage == 2 ? 'selected' : ''}>2%</option>
                        <option value="3" ${discountPercentage == 3 ? 'selected' : ''}>3%</option>
                        <option value="4" ${discountPercentage == 4 ? 'selected' : ''}>4%</option>
                        <option value="5" ${discountPercentage == 5 ? 'selected' : ''}>5%</option>
                        <option value="6" ${discountPercentage == 6 ? 'selected' : ''}>6%</option>
                        <option value="7" ${discountPercentage == 7 ? 'selected' : ''}>7%</option>
                        <option value="8" ${discountPercentage == 8 ? 'selected' : ''}>8%</option>
                        <option value="9" ${discountPercentage == 9 ? 'selected' : ''}>9%</option>
                        <option value="10" ${discountPercentage == 10 ? 'selected' : ''}>10%</option>
                        <option value="11" ${discountPercentage == 11 ? 'selected' : ''}>11%</option>
                        <option value="12" ${discountPercentage == 12 ? 'selected' : ''}>12%</option>
                        <option value="13" ${discountPercentage == 13 ? 'selected' : ''}>13%</option>
                        <option value="14" ${discountPercentage == 14 ? 'selected' : ''}>14%</option>
                        <option value="15" ${discountPercentage == 15 ? 'selected' : ''}>15%</option>
                    </select>
                </td>
                <td>
                    ${discountAmount > 0 ? 
                        `<span class="text-danger">-${discountAmount.toFixed(2)} ج.م</span>` : 
                        '<span class="text-muted">0.00 ج.م</span>'
                    }
                </td>
                <td><strong class="text-success">${totalAfterDiscount.toFixed(2)} ج.م</strong></td>
                <td>
                    <button type="button" class="btn btn-sm btn-danger" 
                            onclick="removeOrderItem(${idx})" 
                            title="حذف العنصر">
                        <i class="fas fa-trash"></i>
                    </button>
                </td>
            </tr>
        `;
    });
    
    html += `
                        </tbody>
                    </table>
                </div>
            </div>
            <div class="card-footer text-center bg-success text-white">
                <div class="row">
                    <div class="col-md-4">
                        <strong class="fs-6">
                            <i class="fas fa-calculator me-2"></i>
                            الإجمالي: ${totalAmount.toFixed(2)} ج.م
                        </strong>
                    </div>
                    <div class="col-md-4">
                        <strong class="fs-6">
                            <i class="fas fa-percentage me-2"></i>
                            إجمالي الخصم: ${totalDiscount.toFixed(2)} ج.م
                        </strong>
                    </div>
                    <div class="col-md-4">
                        <strong class="fs-5">
                            <i class="fas fa-money-bill-wave me-2"></i>
                            الإجمالي النهائي: ${totalAfterDiscount.toFixed(2)} ج.م
                        </strong>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    tableDiv.innerHTML = html;
};

// تحديث خصم العنصر
window.updateItemDiscount = function(idx, discountPercentage) {
    if (window.orderItems[idx]) {
        window.orderItems[idx].discount_percentage = parseFloat(discountPercentage);
        window.updateLiveOrderItemsTable();
        
        // تحديث الحقول المخفية إذا كانت متوفرة
        if (typeof syncOrderItemsToFormFields === 'function') {
            syncOrderItemsToFormFields();
        }
        
        // تحديث التحقق من النموذج إذا كانت متوفرة
        if (typeof validateFormRealTime === 'function') {
            validateFormRealTime();
        }
    }
};

// حذف عنصر من القائمة
window.removeOrderItem = function(idx) {
    if (confirm('هل تريد حذف هذا العنصر من الطلب؟')) {
        window.orderItems.splice(idx, 1);
        window.updateLiveOrderItemsTable();
        
        // تحديث الحقول المخفية إذا كانت متوفرة
        if (typeof syncOrderItemsToFormFields === 'function') {
            syncOrderItemsToFormFields();
        }
        
        // تحديث التحقق من النموذج إذا كانت متوفرة
        if (typeof validateFormRealTime === 'function') {
            validateFormRealTime();
        }
    }
};

// إضافة عنصر جديد
window.addOrderItem = function(item) {
    // التحقق من عدم تكرار المنتج
    const exists = window.orderItems.find(x => x.product_id === item.product_id);
    if (exists) {
        if (typeof Swal !== 'undefined') {
            Swal.fire({
                icon: 'warning',
                title: 'تنبيه',
                text: 'تمت إضافة هذا المنتج بالفعل!',
                confirmButtonText: 'موافق'
            });
        } else {
            alert('تمت إضافة هذا المنتج بالفعل!');
        }
        return false;
    }
    
    // إضافة العنصر
    window.orderItems.push(item);
    window.updateLiveOrderItemsTable();
    
    // تحديث الحقول المخفية إذا كانت متوفرة
    if (typeof syncOrderItemsToFormFields === 'function') {
        syncOrderItemsToFormFields();
    }
    
    // تحديث التحقق من النموذج إذا كانت متوفرة
    if (typeof validateFormRealTime === 'function') {
        validateFormRealTime();
    }
    
    return true;
};

// دالة لحساب الإجمالي
window.calculateTotalAmount = function() {
    return window.orderItems.reduce((sum, item) => sum + item.total, 0);
};

// دالة لتنظيف جميع العناصر
window.clearAllOrderItems = function() {
    if (confirm('هل تريد حذف جميع العناصر من الطلب؟')) {
        window.orderItems = [];
        window.updateLiveOrderItemsTable();
        
        // تحديث الحقول المخفية إذا كانت متوفرة
        if (typeof syncOrderItemsToFormFields === 'function') {
            syncOrderItemsToFormFields();
        }
        
        // تحديث التحقق من النموذج إذا كانت متوفرة
        if (typeof validateFormRealTime === 'function') {
            validateFormRealTime();
        }
    }
};

// دالة للحصول على عنصر بواسطة معرف المنتج
window.getOrderItemByProductId = function(productId) {
    return window.orderItems.find(item => item.product_id === productId);
};

// دالة لتحديث كمية عنصر موجود مع معالجة محسنة للقيم العشرية
window.updateOrderItemQuantity = function(productId, newQuantity) {
    const item = window.orderItems.find(x => x.product_id === productId);
    if (item) {
        try {
            // تحويل الكمية الجديدة إلى رقم مع التحقق من صحتها
            const quantity = Number(newQuantity);

            if (isNaN(quantity) || !isFinite(quantity) || quantity <= 0) {
                console.error('كمية غير صالحة:', newQuantity);
                return false;
            }

            // تحديث الكمية والإجمالي بدقة
            item.quantity = quantity;
            item.total = Number((item.unit_price * quantity).toFixed(2));

            window.updateLiveOrderItemsTable();

            // تحديث الحقول المخفية إذا كانت متوفرة
            if (typeof syncOrderItemsToFormFields === 'function') {
                syncOrderItemsToFormFields();
            }

            console.log(`✅ تم تحديث كمية المنتج ${productId}: ${quantity}`);
            return true;

        } catch (error) {
            console.error('خطأ في تحديث كمية العنصر:', error);
            return false;
        }
    }
    return false;
};

// دالة للحصول على عدد العناصر
window.getOrderItemsCount = function() {
    return window.orderItems.length;
};

// دالة للتحقق من وجود عناصر في الطلب
window.hasOrderItems = function() {
    return window.orderItems.length > 0;
};

// عند تحميل الصفحة، حدث الجدول مباشرة
window.addEventListener('DOMContentLoaded', () => {
    // تأكد من وجود العنصر قبل التحديث
    if (document.getElementById('live-order-items-table')) {
        window.updateLiveOrderItemsTable();
    }
});

// تصدير الوظائف للاستخدام في ملفات أخرى
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        updateLiveOrderItemsTable: window.updateLiveOrderItemsTable,
        removeOrderItem: window.removeOrderItem,
        addOrderItem: window.addOrderItem,
        calculateTotalAmount: window.calculateTotalAmount,
        clearAllOrderItems: window.clearAllOrderItems,
        getOrderItemByProductId: window.getOrderItemByProductId,
        updateOrderItemQuantity: window.updateOrderItemQuantity,
        getOrderItemsCount: window.getOrderItemsCount,
        hasOrderItems: window.hasOrderItems
    };
}