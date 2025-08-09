// order_items.js
// جميع وظائف إدارة عناصر الطلب بشكل منظم وحديث

// تعريف مصفوفة العناصر العامة
window.orderItems = window.orderItems || [];

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
    
    let html = `
        <div class="card border-success">
            <div class="card-header bg-success text-white">
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
                                <th width="120">الإجمالي</th>
                                <th width="80">إجراءات</th>
                            </tr>
                        </thead>
                        <tbody>
    `;
    
    window.orderItems.forEach((item, idx) => {
        html += `
            <tr>
                <td><span class="badge bg-primary">${idx+1}</span></td>
                <td>
                    <strong>${item.name}</strong>
                    ${item.code ? `<br><small class="text-muted">كود: ${item.code}</small>` : ''}
                    ${item.notes ? `<br><small class="text-info"><i class="fas fa-sticky-note me-1"></i>${item.notes}</small>` : ''}
                </td>
                <td><span class="badge bg-info">${item.quantity}</span></td>
                <td>${item.unit_price} ج.م</td>
                <td><strong class="text-success">${item.total.toFixed(2)} ج.م</strong></td>
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
                <strong class="fs-5">
                    <i class="fas fa-calculator me-2"></i>
                    الإجمالي: ${totalAmount.toFixed(2)} ج.م
                </strong>
            </div>
        </div>
    `;
    
    tableDiv.innerHTML = html;
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

// دالة لتحديث كمية عنصر موجود
window.updateOrderItemQuantity = function(productId, newQuantity) {
    const item = window.orderItems.find(x => x.product_id === productId);
    if (item && newQuantity > 0) {
        item.quantity = newQuantity;
        item.total = item.unit_price * newQuantity;
        window.updateLiveOrderItemsTable();
        
        // تحديث الحقول المخفية إذا كانت متوفرة
        if (typeof syncOrderItemsToFormFields === 'function') {
            syncOrderItemsToFormFields();
        }
        
        return true;
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