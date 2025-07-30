import json
import difflib
from google.oauth2 import service_account
from googleapiclient.discovery import build

# قائمة الأسماء الرسمية للبائعين
SALESPEOPLE = [
    'zakee tahawi', 'ابراهيم سليمان اسكندر ابراهيم', 'احمد  عصام جودة قاسم', 'احمد برهان فاروق',
    'احمد حسنى احمد محمد قناوى', 'احمد سعيد زين', 'احمد صلاح احمد محمد على', 'احمد عزت حسن احمد شاكر',
    'احمد فتحى عدلى محمد', 'احمد محمد عبدالحفيظ محمود', 'ارميا فريد راسله يوسف', 'اسحق عبدالنور عبده مرجان',
    'اشرف حسن محمد حسن', 'اميل يوسف سامي غطاس', 'ايمن الهم خليل معوض', 'بدور محمود سيد عبده سيد',
    'بيشوى يوسف شحاته فهيم بطرس', 'جورج وليم وهبه حنا', 'حسام صبحى بباوى بولس', 'حسام مسعود السيد احمد',
    'خليل ابراهيم محمود محمد', 'رضا محمود', 'رومانى رضا نصيف حنا', 'سيد ادم', 'سيد حامد عبدالرسول احمد',
    'سيد محمد حسن محمد', 'شنوده رفعت عبدالشهيد', 'صبحي عزير صبحي', 'طارق صفوت محمد خطاب', 'طه احمد طه حسنين',
    'عصام محمود احمد على', 'على محمود على احمد', 'عواد كمال عواد خليفة', 'فرحان فوزى محمد ابراهيم',
    'ماجد سمير بخيت جندى', 'مجدي الهم خليل معوض', 'محمد احمد صديق خميس', 'محمد السيد احمد السيد',
    'محمد طارق توفيق ابوالنجا', 'محمد عربى عرفات محمود', 'محمود بهجت رشاد عثمان', 'مصطفى على محمد محمود',
    'مصطفى محمود زغلول كامل متولى', 'ميلاد بباوى يوسف بباوى', 'مينا صلاح ذكى سليمان', 'مينا عزت عبدالملاك غطاس',
    'نادر ايمن عبدالغني منصور', 'نادر عصام عبدالمجيد احمد', 'هانى بخيت حبيب بخيت', 'هانى صالح زكى سليمان',
    'هدهود السيد احمد على', 'وائل رشدى عبد السيد', 'يوسف سعد', 'يوسف لمعي بدروس'
]

# قاموس التصحيح اليدوي للأسماء
SALESPEOPLE_FIX = {
    'احمد صبحي': 'حسام صبحى بباوى بولس',
    'حسام صبحي': 'حسام صبحى بباوى بولس',
    'احمد صلاح': 'احمد صلاح احمد محمد على',
    'ارميا': 'ارميا فريد راسله يوسف',
    'ارميا حبيب': 'ارميا فريد راسله يوسف',
    'اسحق': 'اسحق عبدالنور عبده مرجان',
    'سنودة': 'شنوده رفعت عبدالشهيد',
    'شنودة': 'شنوده رفعت عبدالشهيد',
    'شنوده': 'شنوده رفعت عبدالشهيد',
    'محمد طارق': 'محمد طارق توفيق ابوالنجا',
    'محمدطارق': 'محمد طارق توفيق ابوالنجا',
    'محمد عربي': 'محمد عربى عرفات محمود',
    'مينا عزت': 'مينا عزت عبدالملاك غطاس',
    'مينت عزت': 'مينا عزت عبدالملاك غطاس',
    'نادر ايمن': 'نادر ايمن عبدالغني منصور',
    'هاني بخيت': 'هانى بخيت حبيب بخيت',
    'هدير': 'بدور محمود سيد عبده سيد',
    'علاء اللهم': 'ايمن الهم خليل معوض',
    'علاء الهم': 'ايمن الهم خليل معوض',
    'عصام السيد': 'عصام محمود احمد على',
    'حسن المصري': 'يوسف سعد',
    'مينا عزت': 'مينا عزت عبدالملاك غطاس',
}

# إعدادات Google Sheets
SPREADSHEET_ID = "1rrQfEk7RNJp5RILsIv_ohydS2lO7IS0UoK36GK9nTAg"
CREDENTIALS_JSON = "/home/zakee/Downloads/key.json"  # مسار ملف الاعتماد الصحيح
SALES_COL = 'D'
HEADER_ROW = 1

# تحميل بيانات الاعتماد
creds = service_account.Credentials.from_service_account_file(
    CREDENTIALS_JSON,
    scopes=["https://www.googleapis.com/auth/spreadsheets"]
)
service = build('sheets', 'v4', credentials=creds)
sheet_service = service.spreadsheets()

# جلب جميع أسماء الصفحات
sheet_metadata = sheet_service.get(spreadsheetId=SPREADSHEET_ID).execute()
sheet_titles = [s['properties']['title'] for s in sheet_metadata['sheets']]

def best_match(name):
    if not name or not name.strip():
        return name
    name_clean = name.strip()
    # التصحيح اليدوي أولاً
    if name_clean in SALESPEOPLE_FIX:
        return SALESPEOPLE_FIX[name_clean]
    matches = difflib.get_close_matches(name_clean, SALESPEOPLE, n=1, cutoff=0.6)
    return matches[0] if matches else name


# تجميع الأسماء غير المعالجة لكل صفحة
unmatched_report = {}

for sheet_title in sheet_titles:
    range_notation = f"{sheet_title}!{SALES_COL}{HEADER_ROW+1}:{SALES_COL}"
    result = sheet_service.values().get(spreadsheetId=SPREADSHEET_ID, range=range_notation).execute()
    values = result.get('values', [])
    if not values:
        print(f"لا يوجد بيانات في الصفحة: {sheet_title}")
        continue
    updated = False
    new_values = []
    unmatched = []
    for row in values:
        original = row[0] if row else ''
        fixed = best_match(original)
        new_values.append([fixed])
        if fixed != original:
            updated = True
        # إذا لم يتم التصحيح (أي الاسم لم يتغير)
        if fixed == original and fixed.strip() and fixed not in SALESPEOPLE:
            unmatched.append(original)
    if unmatched:
        unmatched_report[sheet_title] = unmatched
    if updated:
        update_range = f"{sheet_title}!{SALES_COL}{HEADER_ROW+1}:{SALES_COL}{HEADER_ROW+len(new_values)}"
        sheet_service.values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=update_range,
            valueInputOption="RAW",
            body={"values": new_values}
        ).execute()
        print(f"تم تصحيح الأسماء في الصفحة: {sheet_title}")
    else:
        print(f"لا حاجة للتصحيح في الصفحة: {sheet_title}")

# تجميع كل الأسماء غير المعالجة من جميع الصفحات بدون تكرار
all_unmatched = set()
for names in unmatched_report.values():
    all_unmatched.update(names)

print("\nتقرير الأسماء التي لم يتم تصحيحها في جميع الصفحات (بدون تكرار):")
if not all_unmatched:
    print("جميع الأسماء تم تصحيحها أو مطابقتها.")
else:
    for name in sorted(all_unmatched):
        print(f"- {name}")
