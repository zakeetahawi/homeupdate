/**
 * Device Manager - Elkhawaga System
 * ==================================
 * مدير الجهاز الموحد - نظام الخواجه
 * 
 * يدير:
 * - حفظ/قراءة Token من IndexedDB
 * - توليد البصمة المحسّنة (Enhanced Fingerprint)
 * - جمع معلومات الجهاز (Device Info)
 * 
 * الاستخدام:
 * await DeviceManager.init();
 * const token = await DeviceManager.getToken();
 * const fingerprint = await DeviceManager.generateFingerprint();
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
     * جمع معلومات الجهاز (Device Info)
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
     * Canvas Fingerprint (مستقر)
     */
    generateCanvasFingerprint() {
        try {
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            ctx.textBaseline = 'top';
            ctx.font = '14px Arial';
            ctx.textBaseline = 'alphabetic';
            ctx.fillStyle = '#f60';
            ctx.fillRect(125, 1, 62, 20);
            ctx.fillStyle = '#069';
            ctx.fillText('Elkhawaga Device', 2, 15);
            ctx.fillStyle = 'rgba(102, 204, 0, 0.7)';
            ctx.fillText('Elkhawaga Device', 4, 17);
            return canvas.toDataURL();
        } catch(e) {
            // console.error('Canvas fingerprint failed:', e);
            return '';
        }
    },
    
    /**
     * WebGL Fingerprint (معلومات GPU - مستقر جداً)
     */
    generateWebGLFingerprint() {
        try {
            const canvas = document.createElement('canvas');
            const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
            
            if (!gl) return { vendor: '', renderer: '' };
            
            const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
            if (debugInfo) {
                return {
                    vendor: gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL),
                    renderer: gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL)
                };
            }
            return { vendor: '', renderer: '' };
        } catch(e) {
            // console.error('WebGL fingerprint failed:', e);
            return { vendor: '', renderer: '' };
        }
    },
    
    /**
     * Audio Fingerprint (مستقر جداً)
     */
    async generateAudioFingerprint() {
        try {
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioContext.createOscillator();
            const analyser = audioContext.createAnalyser();
            const gainNode = audioContext.createGain();
            const scriptProcessor = audioContext.createScriptProcessor(4096, 1, 1);
            
            gainNode.gain.value = 0;
            oscillator.connect(analyser);
            analyser.connect(scriptProcessor);
            scriptProcessor.connect(gainNode);
            gainNode.connect(audioContext.destination);
            
            oscillator.start(0);
            
            return new Promise((resolve) => {
                const audioData = [];
                scriptProcessor.onaudioprocess = function(event) {
                    if (audioData.length >= 100) {
                        oscillator.stop();
                        audioContext.close();
                        
                        // Hash the audio data (requires CryptoJS)
                        if (typeof CryptoJS !== 'undefined') {
                            const hash = CryptoJS.SHA256(audioData.join(',')).toString().substring(0, 16);
                            resolve(hash);
                        } else {
                            resolve('');
                        }
                        return;
                    }
                    
                    const output = event.outputBuffer.getChannelData(0);
                    for (let i = 0; i < output.length && audioData.length < 100; i++) {
                        audioData.push(output[i]);
                    }
                };
                
                // Timeout after 2 seconds
                setTimeout(() => {
                    oscillator.stop();
                    audioContext.close();
                    resolve('');
                }, 2000);
            });
        } catch(e) {
            // console.error('Audio fingerprint failed:', e);
            return '';
        }
    },
    
    /**
     * توليد البصمة المحسّنة الكاملة (Enhanced Fingerprint)
     * تتضمن فقط العوامل المستقرة
     */
    async generateFingerprint() {
        // console.log('🔐 Generating enhanced fingerprint...');
        
        // 1. معلومات الجهاز الأساسية
        const deviceInfo = this.collectDeviceInfo();
        
        // 2. Canvas Fingerprint
        deviceInfo.canvas_fingerprint = this.generateCanvasFingerprint();
        
        // 3. WebGL Fingerprint (GPU Info)
        const webgl = this.generateWebGLFingerprint();
        deviceInfo.webgl_vendor = webgl.vendor;
        deviceInfo.webgl_renderer = webgl.renderer;
        
        // 4. Audio Fingerprint
        deviceInfo.audio_fingerprint = await this.generateAudioFingerprint();
        
        // 5. توليد Hash نهائي (يتطلب CryptoJS)
        if (typeof CryptoJS !== 'undefined') {
            const fingerprintString = JSON.stringify(deviceInfo, Object.keys(deviceInfo).sort());
            const fingerprint = CryptoJS.SHA256(fingerprintString).toString();
            // console.log('✅ Fingerprint generated:', fingerprint.substring(0, 16) + '...');
            return { fingerprint, deviceInfo };
        } else {
            // console.error('❌ CryptoJS not loaded!');
            return { fingerprint: null, deviceInfo };
        }
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
