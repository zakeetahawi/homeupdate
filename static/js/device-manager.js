/**
 * Device Manager - Elkhawaga System
 * ==================================
 * مدير الجهاز الموحد - نظام الخواجه
 * 
 * يدير:
 * - حفظ/قراءة Token من IndexedDB
 * - جمع معلومات الجهاز الأساسية (Device Info)
 * 
 * الاستخدام:
 * await DeviceManager.init();
 * const token = await DeviceManager.getToken();
 * const deviceInfo = DeviceManager.collectDeviceInfo();
 */

const DeviceManager = {
    // إعدادات IndexedDB
    dbName: 'ElkhawagaDeviceDB',
    storeName: 'deviceToken',
    db: null,
    
    /**
     * تهيئة IndexedDB
     */
    async initDB() {
        if (this.db) return this.db;
        
        return new Promise((resolve, reject) => {
            const request = indexedDB.open(this.dbName, 1);
            
            request.onerror = () => {
                // console.error('❌ Failed to open IndexedDB:', request.error);
                reject(request.error);
            };
            
            request.onsuccess = () => {
                this.db = request.result;
                // console.log('✅ IndexedDB initialized');
                resolve(this.db);
            };
            
            request.onupgradeneeded = (e) => {
                const db = e.target.result;
                if (!db.objectStoreNames.contains(this.storeName)) {
                    db.createObjectStore(this.storeName);
                    // console.log('✅ IndexedDB object store created');
                }
            };
        });
    },
    
    /**
     * حفظ Token في IndexedDB
     */
    async saveToken(token) {
        const db = await this.initDB();
        return new Promise((resolve, reject) => {
            const tx = db.transaction([this.storeName], 'readwrite');
            const store = tx.objectStore(this.storeName);
            const request = store.put(token, 'device_token');
            
            request.onsuccess = () => {
                // console.log('✅ Device Token saved:', token);
                resolve();
            };
            
            request.onerror = () => {
                // console.error('❌ Failed to save token:', request.error);
                reject(request.error);
            };
        });
    },
    
    /**
     * قراءة Token من IndexedDB
     */
    async getToken() {
        const db = await this.initDB();
        return new Promise((resolve, reject) => {
            const tx = db.transaction([this.storeName], 'readonly');
            const store = tx.objectStore(this.storeName);
            const request = store.get('device_token');
            
            request.onsuccess = () => {
                const token = request.result;
                if (token) {
                    // console.log('✅ Device Token loaded:', token.substring(0, 8) + '...');
                } else {
                    // console.log('⚠️ No device token found');
                }
                resolve(token);
            };
            
            request.onerror = () => {
                // console.error('❌ Failed to read token:', request.error);
                reject(request.error);
            };
        });
    },
    
    /**
     * حذف Token من IndexedDB
     */
    async deleteToken() {
        const db = await this.initDB();
        return new Promise((resolve, reject) => {
            const tx = db.transaction([this.storeName], 'readwrite');
            const store = tx.objectStore(this.storeName);
            const request = store.delete('device_token');
            
            request.onsuccess = () => {
                // console.log('✅ Device Token deleted');
                resolve();
            };
            
            request.onerror = () => {
                // console.error('❌ Failed to delete token:', request.error);
                reject(request.error);
            };
        });
    },
    
    /**
     * جمع معلومات الجهاز الأساسية (Device Info)
     * تستخدم فقط للمرجعية وليس للمصادقة
     */
    collectDeviceInfo() {
        return {
            screen_resolution: window.screen.width + 'x' + window.screen.height,
            timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
            timezone_offset: new Date().getTimezoneOffset(),
            language: navigator.language,
            platform: navigator.platform,
            user_agent: navigator.userAgent,
            color_depth: window.screen.colorDepth,
            pixel_ratio: window.devicePixelRatio,
            has_touch: 'ontouchstart' in window,
            cpu_cores: navigator.hardwareConcurrency || 0,
        };
    },
    
    /**
     * تهيئة النظام بالكامل
     */
    async init() {
        await this.initDB();
        // console.log('✅ Device Manager initialized');
    }
};

// Auto-initialize on load
if (typeof window !== 'undefined') {
    window.DeviceManager = DeviceManager;
    // console.log('📱 Device Manager loaded');
}
