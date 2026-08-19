# 🚀 دليل تشغيل مشروع MedLens AI

هذا الدليل يشرح بالتفصيل كيفية إعداد وتشغيل منصة **MedLens AI** من الصفر. يتكون المشروع من ثلاث واجهات رئيسية: 
1. **Frontend:** React + Vite
2. **Backend:** Python + FastAPI + ChromaDB
3. **Database & Edge Functions:** Supabase

---

## 📋 المتطلبات الأساسية (Prerequisites)
يجب أن تتأكد من تثبيت البرامج التالية على جهازك:
- [Node.js](https://nodejs.org/) (إصدار 18 فما فوق)
- [Python](https://www.python.org/) (إصدار 3.9 فما فوق)
- [Supabase CLI](https://supabase.com/docs/guides/cli) لإدارة قاعدة البيانات والـ Edge Functions.
- [ngrok](https://ngrok.com/) لعمل ربط بين سيرفرات Supabase السحابية والباك إند المحلي.

---

## ⚙️ 1. إعداد الـ Backend (Python)

الباك إند مسؤول عن معالجة الذكاء الاصطناعي (RAG) والبحث في قاعدة البيانات (ChromaDB).

1. افتح الـ Terminal في مجلد `backend/`.
2. قم بتثبيت المكتبات المطلوبة:
   ```bash
   pip install -r requirements.txt
   ```
3. قم بإنشاء ملف `.env` داخل مجلد `backend/` وضع فيه المفاتيح التالية (مثال):
   ```env
   # .env (Backend)
   GROQ_API_KEY="gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
   # إذا كنت تستخدم نماذج إضافية (اختياري)
   HF_TOKEN="hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx" 
   ```
4. لتشغيل السيرفر المحلي:
   ```bash
   python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

---

## ☁️ 2. إعداد قاعدة البيانات والـ Edge Functions (Supabase)

نظراً لأن الـ Edge Function تعمل على السحابة، فإنها تحتاج إلى رابط للوصول إلى الباك إند المحلي الخاص بك. هنا نستخدم **ngrok**.

1. في نافذة Terminal جديدة، قم بتشغيل ngrok لفتح مسار (Tunnel) للباك إند:
   ```bash
   ngrok http 8000
   ```
   > سيظهر لك رابط يبدأ بـ `https://...ngrok.app`. **انسخه!**

2. الآن افتح Terminal في المجلد الرئيسي للمشروع وسجل الدخول لـ Supabase:
   ```bash
   supabase login
   ```
3. اربط الكود بمشروعك السحابي:
   ```bash
   supabase link --project-ref <YOUR_PROJECT_ID>
   ```
4. ارفع الجداول (Tables) إلى قاعدة البيانات:
   ```bash
   supabase db push
   ```
5. قم بتعريف رابط الـ ngrok كمتغير بيئي (Secret) داخل Supabase لكي تتمكن الـ Edge Function من مخاطبته:
   ```bash
   # استبدل الرابط برابط ngrok الخاص بك وأضف في نهايته /api/query
   supabase secrets set PYTHON_BACKEND_URL="https://your-ngrok-url.ngrok.app/api/query"
   ```
6. أخيراً، قم برفع الـ Edge Function:
   ```bash
   supabase functions deploy chat-gateway --no-verify-jwt
   ```

---

## 🎨 3. إعداد الـ Frontend (React)

الواجهة الأمامية تعتمد على Vite وتتصل بـ Supabase لمعرفة إذا كان المستخدم قد وافق على الشروط أم لا.

1. افتح Terminal في مجلد `frontend/`.
2. قم بتثبيت الحزم:
   ```bash
   npm install
   ```
3. تأكد من أن ملف `src/supabaseClient.js` يحتوي على المفاتيح الصحيحة من لوحة تحكم Supabase الخاصة بك:
   ```javascript
   // مثال لمحتوى supabaseClient.js
   import { createClient } from '@supabase/supabase-js';

   const supabaseUrl = 'https://<YOUR_PROJECT_ID>.supabase.co';
   const supabaseAnonKey = 'sb_publishable_xxxxxxxxxxxxxxxxxxx';

   export const supabase = createClient(supabaseUrl, supabaseAnonKey);
   ```
4. لتشغيل الواجهة الأمامية:
   ```bash
   npm run dev
   ```

---

## 💡 كيف يعمل النظام (دورة حياة الرسالة)؟

1. **تسجيل الدخول / الموافقة:** عندما يفتح المستخدم الموقع، سيُطلب منه الموافقة على شروط الاستخدام في صفحة `/terms`. يتم حفظ الموافقة في Supabase بجدول `device_sessions`.
2. **إرسال الرسالة:** عندما يكتب المستخدم رسالة في الشات، يتم إرسالها إلى الـ **Supabase Edge Function** (`chat-gateway`).
3. **التحقق الأمني (Server-Side):** تتأكد الدالة (Edge Function) من أن الـ `device_id` قد وافق على الشروط.
   - إذا *لم يوافق*: ترد الدالة برسالة ثابتة تطلب منه مراجعة الشروط.
   - إذا *وافق*: تقوم الدالة بتمرير الرسالة إلى رابط `ngrok` الذي يحولها بدوره إلى الباك إند المحلي `FastAPI`.
4. **استرجاع المعلومات:** يبحث الباك إند بايثون في ChromaDB ويعيد الإجابة مع المصادر الطبية عبر ngrok، ثم إلى Edge Function، وصولاً إلى الواجهة!

> [!TIP]
> تذكر دائماً: في كل مرة تعيد فيها تشغيل جهازك أو تعيد تشغيل `ngrok`، سيتغير الرابط. يجب عليك تحديث الـ Secret في Supabase بالأمر `supabase secrets set PYTHON_BACKEND_URL="..."` وإعادة رفع الـ Function لتجنب انقطاع الخدمة.
