#!/usr/bin/env python3
"""
سكريبت لإنشاء ملفات صوتية بسيطة للإشعارات
"""

import numpy as np
import wave
import os

def generate_tone(frequency, duration, sample_rate=44100, amplitude=0.3):
    """إنشاء نغمة صوتية"""
    frames = int(duration * sample_rate)
    arr = np.zeros(frames)
    
    for i in range(frames):
        arr[i] = amplitude * np.sin(2 * np.pi * frequency * i / sample_rate)
    
    return arr

def generate_notification_sound():
    """إنشاء صوت إشعار استقبال رسالة"""
    sample_rate = 44100
    
    # نغمتان قصيرتان
    tone1 = generate_tone(600, 0.1, sample_rate)
    silence = np.zeros(int(0.05 * sample_rate))
    tone2 = generate_tone(800, 0.1, sample_rate)
    
    # دمج الأصوات
    sound = np.concatenate([tone1, silence, tone2])
    
    # تطبيق fade in/out
    fade_frames = int(0.01 * sample_rate)
    sound[:fade_frames] *= np.linspace(0, 1, fade_frames)
    sound[-fade_frames:] *= np.linspace(1, 0, fade_frames)
    
    return sound

def generate_send_sound():
    """إنشاء صوت إرسال رسالة"""
    sample_rate = 44100
    
    # نغمة واحدة قصيرة عالية
    sound = generate_tone(800, 0.15, sample_rate)
    
    # تطبيق fade out
    fade_frames = int(0.05 * sample_rate)
    sound[-fade_frames:] *= np.linspace(1, 0, fade_frames)
    
    return sound

def save_wav(filename, sound, sample_rate=44100):
    """حفظ الصوت كملف WAV"""
    # تحويل إلى 16-bit
    sound_16bit = (sound * 32767).astype(np.int16)
    
    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(1)  # mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(sound_16bit.tobytes())

def main():
    """الدالة الرئيسية"""
    print("🎵 إنشاء ملفات الأصوات...")
    
    # إنشاء المجلد إذا لم يكن موجوداً
    os.makedirs('/home/xhunterx/homeupdate/static/sounds', exist_ok=True)
    
    try:
        # إنشاء صوت استقبال الرسالة
        receive_sound = generate_notification_sound()
        save_wav('/home/xhunterx/homeupdate/static/sounds/message-receive.wav', receive_sound)
        print("✅ تم إنشاء message-receive.wav")
        
        # إنشاء صوت إرسال الرسالة
        send_sound = generate_send_sound()
        save_wav('/home/xhunterx/homeupdate/static/sounds/message-send.wav', send_sound)
        print("✅ تم إنشاء message-send.wav")
        
        print("🎉 تم إنشاء جميع الملفات الصوتية بنجاح!")
        
    except ImportError:
        print("❌ numpy غير مثبت. يمكنك تثبيته بالأمر:")
        print("pip install numpy")
        print("\nأو استخدام الأصوات المُولدة في المتصفح بدلاً من ذلك.")
    except Exception as e:
        print(f"❌ خطأ في إنشاء الملفات: {e}")

if __name__ == "__main__":
    main()
