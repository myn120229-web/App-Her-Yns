# unemployed — Telegram Mini App edition

ابزار جستجوی شغل‌های دورکاری (remote)، بازنویسی‌شده به صورت یک **Mini App تلگرام**
با بک‌اند FastAPI. منطق اصلی (fetch / filter / score / resume) همان کدهای
پروژه `unemployed-clone` است، فقط لایه UI از Streamlit به یک وب‌اپلیکیشن تلگرام
تبدیل شده.

## امکانات

- 🔍 جستجو از ۵ بورد شغل دورکاری عمومی (Remotive، Arbeitnow، RemoteOK، We Work Remotely، Jobicy)
- 🧹 فیلتر خودکار روی remote جهانی / سطح سابقه / سال تجربه / تابع شغلی
- 🎯 امتیازدهی ۰–۱۰۰ با مدل LLM (۵ بخش وزن‌دار)
- 📄 تولید رزومه یک‌صفحه‌ای PDF (بولت‌های ردیابی‌شده به دانش‌بیس)
- ⚙️ **تغییر endpoint و api_key در زمان اجرا** — از هر API سازگار با OpenAI استفاده کنید

## اجرای محلی

```bash
pip install -r requirements.txt
export PORT=8000
uvicorn server:app --host 0.0.0.0 --port $PORT
```

سپس مرورگر را باز کنید: http://localhost:8000

## استقرار روی Railway

۱. این ریپو را به Railway وصل کنید (New Project → Deploy from GitHub repo).
۲. Railway به‌طور خودکار از `railway.json` / `Dockerfile` استفاده می‌کند.
۳. متغیر محیطی `PORT` را Railway خودکار تنظیم می‌کند.
۴. پس از دیپلوی، آدرس HTTPS پروژه را بگیرید.

### اتصال به تلگرام (Mini App)

۱. در @BotFather: `BotFather → your bot → Menu Button → Configure menu button`
۲. آدرس HTTPS پروژه Railway را وارد کنید.
۳. در چت بات، دکمه منو را بزنید تا Mini App باز شود.

## تنظیم مدل (API دلخواه)

در تب «⚙️ تنظیم API» داخل Mini App:

| فیلد | مقدار پیش‌فرض | توضیح |
|------|--------------|-------|
| Base URL | `http://127.0.0.1:11434/v1` | هر endpoint سازگار با OpenAI |
| API Key | `ollama` | کلید API ارائه‌دهنده |
| Model | `qwen2.5:3b` | نام مدل |

مثال با Zyloo:
- Base URL: `https://api.zyloo.io/v1`
- API Key: `sk-zy-...`
- Model: `gpt-4o-mini`

تنظیمات در `data/llm_config.json` ذخیره می‌شود.

## ساختار پروژه

```
server.py              FastAPI: API + سرو Mini App
public/index.html      رابط کاربری Mini App
public/app.js          منطق فرانت‌اند
app/                   منطق اصلی (از unemployed-clone)
  remote_boards.py     فچ از بوردهای شغل
  filters.py           فیلترها
  scorer.py            امتیازدهی LLM
  resume_writer.py     تولید رزومه PDF
  llm_client.py        wrapper مدل (پشتیبانی هر OpenAI-compatible API)
  data_store.py        ذخیره‌سازی JSON
requirements.txt       وابستگی‌ها
Dockerfile / railway.json / Procfile   تنظیمات دیپلوی
```

## نکات

- داده‌های شخصی (`data/profile.json` و غیره) در `.gitignore` هستند و همراه ریپو پوش نمی‌شوند.
- اگر مدل در دسترس نباشد، بخش امتیازدهی خطا می‌دهد — از تب تنظیم API چک کنید.
