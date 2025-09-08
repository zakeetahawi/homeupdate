#!/usr/bin/env python3
"""
إنشاء ملفات صوتية للإشعارات
"""
import wave
import struct
import math
import os

def create_notification_sound(filename, frequency=800, duration=0.3, sample_rate=44100):
    """إنشاء صوت إشعار بسيط"""
    
    # حساب عدد العينات
    num_samples = int(sample_rate * duration)
    
    # إنشاء البيانات الصوتية
    audio_data = []
    for i in range(num_samples):
        # موجة جيبية مع تلاشي
        t = i / sample_rate
        fade = 1.0 - (t / duration)  # تلاشي تدريجي
        
        # موجة جيبية
        sample = math.sin(2 * math.pi * frequency * t) * fade
        
        # تحويل إلى 16-bit integer
        sample_int = int(sample * 32767)
        audio_data.append(sample_int)
    
    # كتابة ملف WAV
    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(1)  # mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        
        # تحويل البيانات إلى bytes
        audio_bytes = b''.join(struct.pack('<h', sample) for sample in audio_data)
        wav_file.writeframes(audio_bytes)
    
    print(f"تم إنشاء {filename}")

def create_send_sound(filename, sample_rate=44100):
    """إنشاء صوت إرسال (نغمة مختلفة)"""
    duration = 0.2
    num_samples = int(sample_rate * duration)
    
    audio_data = []
    for i in range(num_samples):
        t = i / sample_rate
        fade = 1.0 - (t / duration)
        
        # نغمة أعلى للإرسال
        sample = math.sin(2 * math.pi * 1200 * t) * fade * 0.7
        sample_int = int(sample * 32767)
        audio_data.append(sample_int)
    
    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        
        audio_bytes = b''.join(struct.pack('<h', sample) for sample in audio_data)
        wav_file.writeframes(audio_bytes)
    
    print(f"تم إنشاء {filename}")

def create_receive_sound(filename, sample_rate=44100):
    """إنشاء صوت استقبال (نغمة مميزة)"""
    duration = 0.4
    num_samples = int(sample_rate * duration)
    
    audio_data = []
    for i in range(num_samples):
        t = i / sample_rate
        fade = 1.0 - (t / duration)
        
        # نغمة مزدوجة للاستقبال
        freq1 = 600
        freq2 = 900
        sample1 = math.sin(2 * math.pi * freq1 * t) * 0.5
        sample2 = math.sin(2 * math.pi * freq2 * t) * 0.3
        
        sample = (sample1 + sample2) * fade * 0.8
        sample_int = int(sample * 32767)
        audio_data.append(sample_int)
    
    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        
        audio_bytes = b''.join(struct.pack('<h', sample) for sample in audio_data)
        wav_file.writeframes(audio_bytes)
    
    print(f"تم إنشاء {filename}")

def main():
    """الدالة الرئيسية"""
    print("🔊 إنشاء ملفات الصوت للدردشة...")
    
    # إنشاء مجلد الأصوات
    sounds_dir = "static/sounds"
    os.makedirs(sounds_dir, exist_ok=True)
    
    # إنشاء الملفات الصوتية
    receive_file = os.path.join(sounds_dir, "message-receive.wav")
    send_file = os.path.join(sounds_dir, "message-send.wav")
    
    create_receive_sound(receive_file)
    create_send_sound(send_file)
    
    print("\n✅ تم إنشاء جميع الملفات الصوتية!")
    print(f"📁 الملفات في: {sounds_dir}/")
    print("🎵 يمكنك الآن اختبار الأصوات في المتصفح")

if __name__ == "__main__":
    main()
