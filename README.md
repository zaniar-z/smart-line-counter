# smart-line-counter
A feature-rich desktop word analysis tool built with **PySide6** and **Python** by AI.
Supports multiple languages via a JSON-based i18n system, dark/light themes, threaded processing, and frequency charts.

---

## ✨ Features

- **File & Direct Input** — analyze a `.txt` file or paste text directly
- **Regex-based word splitting** — punctuation is never counted as part of a word
- **Threaded analysis** — UI never freezes, even on large files
- **Progress bar** — real-time processing feedback
- **Frequency chart** — horizontal bar chart of the top 10 words (matplotlib)
- **Word exclusion** — comma-separated stopwords filter
- **Analysis history** — every result is saved in-session; click any card to reload it
- **Dark / Light theme** — toggle at any time, chart colors adapt automatically
- **i18n** — add any language by dropping a single JSON file into `locales/`
- **RTL support** — Persian, Arabic, Hebrew layouts handled automatically
- **Drag & Drop** — drop a file anywhere on the window

---

## 🗂 Project Structure

```
word_counter/
├── main.py
└── locales/
    ├── fa.json   ← Persian
    └── en.json   ← English
```

---

## 🚀 Installation

```bash
pip install PySide6 matplotlib
```

## ▶️ Run

```bash
python main.py
```

---

## 🌐 Adding a New Language

make a  issue or do this:

1. Create `locales/XX.json` (e.g. `ar.json` for Arabic)
2. Copy all keys from `en.json` and translate the values
3. Set `lang_name` to the display name of the language (e.g. `"العربية"`)
4. Restart the app — it auto-discovers all locale files

For RTL languages (Arabic, Hebrew), set `"lang_code"` to one of `fa`, `ar`, `he` and the layout direction switches automatically.

but i suggestion you to make a issue

---

## 📦 Dependencies

| Package | Purpose |
|---|---|
| `PySide6` | GUI framework |
| `matplotlib` | Word frequency chart |

---

## 📄 License

MIT

---
---

# 📝 شمارنده کلمات پیشرفته

یک ابزار دسکتاپ برای آنالیز متن، ساخته‌شده با **PySide6** و **Python** توسط هوش مصنوعی.
پشتیبانی از چند زبان از طریق سیستم i18n مبتنی بر JSON، تم روشن/تاریک، پردازش موازی، و نمودار فراوانی کلمات.

---

## ✨ امکانات

- **فایل و ورودی مستقیم** — آنالیز فایل `.txt` / `.md` یا paste مستقیم متن
- **جداسازی کلمات با Regex** — علائم نگارشی هرگز بخشی از کلمه حساب نمی‌شوند
- **پردازش در Thread جداگانه** — رابط کاربری حتی روی فایل‌های بزرگ freeze نمی‌کند
- **Progress bar** — نشانگر پیشرفت در زمان واقعی
- **نمودار فراوانی** — نمودار افقی ۱۰ کلمه پرتکرار (matplotlib)
- **فیلتر کلمات** — حذف Stopword با جداکننده کاما
- **تاریخچه آنالیز** — هر نتیجه در session ذخیره می‌شود؛ با کلیک روی هر کارت بارگذاری می‌شود
- **تم روشن / تاریک** — قابل تغییر در هر لحظه، رنگ نمودار هم سازگار می‌شود
- **i18n** — با اضافه‌کردن یک فایل JSON به پوشه `locales/` زبان جدید اضافه کنید
- **پشتیبانی RTL** — فارسی، عربی، عبری به‌صورت خودکار مدیریت می‌شوند
- **Drag & Drop** — فایل را روی هر جای پنجره رها کنید

---

## 🗂 ساختار پروژه

```
word_counter/
├── main.py
└── locales/
    ├── fa.json   ← فارسی
    └── en.json   ← انگلیسی
```

---

## 🚀 نصب

```bash
pip install PySide6 matplotlib
```

## ▶️ اجرا

```bash
python main.py
```

---

## 🌐 افزودن زبان جدید

یک درخواست ثبت کنید یا:

1. فایل `locales/XX.json` بسازید (مثلاً `ar.json` برای عربی)
2. همه کلیدها را از `en.json` کپی کنید و مقادیر را ترجمه کنید
3. مقدار `lang_name` را نام نمایشی آن زبان قرار دهید (مثلاً `"العربية"`)
4. برنامه را ری‌استارت کنید — فایل‌های locale به‌صورت خودکار کشف می‌شوند

برای زبان‌های RTL (عربی، عبری)، کد زبان را `ar` یا `he` قرار دهید تا جهت چیدمان به‌صورت خودکار تغییر کند.

پیشنهاد میشه درخواست ثبت کنید.
---

## 📦 وابستگی‌ها

| پکیج | کاربرد |
|---|---|
| `PySide6` | فریم‌ورک رابط گرافیکی |
| `matplotlib` | نمودار فراوانی کلمات |

---

## 📄 لایسنس

MIT
