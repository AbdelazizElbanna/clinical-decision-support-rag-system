# 🎤 السكريبت التفصيلي للعرض التقديمي (MedLens AI)
هذا الملف يحتوي على الهيكل الشامل للـ Slides المطلوبة بناءً على ملف الـ PDF الخاص بالتقييم، مع **الكلام التفصيلي (السكربت)** الذي ستقوله أثناء العرض (مزيج بين العربي المفهوم والمصطلحات التقنية الإنجليزية).

---

## Slide 1: Executive Summary & Core Philosophy
**Slide Content (English):**
- MedLens AI: Clinical Decision Support RAG.
- Core Philosophy: Fluent Answer ≠ Safe Answer. Every clinical recommendation must be grounded.

**🗣️ Speaker Script (Mix):**
"مساء الخير جميعاً. إحنا النهاردة بنقدم **MedLens AI**، وهو RAG System متخصص في الأمراض الجلدية زي الإكزيما والصدفية. الفلسفة الأساسية لمشروعنا هي إن (Fluent Answer is not a Safe Answer). في المجال الطبي، إن الموديل يجاوب بثقة وطلاقة ده شيء خطير لو الإجابة مش مبنية على دليل. علشان كده السيستم بتاعنا مبني بالكامل على الـ Clinical Grounding وإن كل كلمة تطلع لازم يكون ليها Citation واضح."

---

## Slide 2: Clinical Problem & Scope
**Slide Content (English):**
- **The Risk:** Generic LLMs hallucinate. Unacceptable in clinical context.
- **Our Scope:** Narrow, well-defined dermatology guidance sourced strictly from official guidelines (WHO, NICE).

**🗣️ Speaker Script (Mix):**
"المشكلة اللي بنحلها إن الـ Generic LLMs بتجاوب من الـ Parametric Memory بتاعتها، وده بيعمل Hallucinations. في السياق الطبي ده غير مقبول تماماً. الـ Scope بتاعنا كان واضح ومحدد جداً (Narrow and well-defined). إحنا بنعتمد فقط على Official Guidelines زي بروتوكولات منظمة الصحة العالمية وNICE، ومفيش أي Private Data بتدخل عشان نضمن الـ Traceability."

---

## Slide 3: End-to-End System Architecture
**Slide Content (English):**
- A modular, layered pipeline: Ingestion ➔ Chunking ➔ Embeddings ➔ Retrieval ➔ Guardrails ➔ Grounded LLM ➔ Evidence Panel.

**🗣️ Speaker Script (Mix):**
"لو بصينا على الـ System Architecture، هنلاقيه Modular ومتقسم لـ 7 طبقات أساسية. كل طبقة فيهم Independently testable. الداتا بتدخل يحصلها Chunking، بعدين Embeddings، مرورا بالـ Retrieval، وأهم مرحلة هي الـ Guardrails قبل ما توصل للـ LLM علشان يجاوب، وفي النهاية بتتعرض في الـ Evidence Panel للمستخدم."

---

## Slide 4: Ingestion & Chunking Strategy
**Slide Content (English):**
- Section-Aware Chunking (preserving context).
- Rich Metadata Schema (document_name, section, chunk_id).

**🗣️ Speaker Script (Mix):**
"بالنسبة للـ Ingestion، إحنا معملناش Chunking عشوائي للـ PDFs. إحنا طبقنا **Section-Aware Chunking** عشان نحافظ على السياق الطبي لكل فقرة. وكل Chunk مربوط بـ Metadata Schema قوية جداً بتشمل اسم الملف، القسم، واللينك الأساسي، وده اللي بيخلي الـ Citations بتاعتنا دقيقة جداً."

---

## Slide 5: Retrieval Pipeline & Optimization (🔥 نقطة قوة)
**Slide Content (English):**
- Multilingual Embeddings: `BAAI/bge-m3`.
- Precision Reranking: `ms-marco-MiniLM` Cross-Encoder.
- Optimized for Top-K precision.

**🗣️ Speaker Script (Mix):**
"وهنا بييجي الجزء اللي ركزنا عليه جداً لرفع الـ Retrieval Quality (وده عليه 30% من التقييم). إحنا استخدمنا `bge-m3` لأنه ممتاز في الـ Cross-lingual search بين العربي والإنجليزي. وعشان نعالج مشكلة الـ (Lost in the middle)، ضفنا مرحلة **Cross-Encoder Reranking** باستخدام `MiniLM`.. يعني بنجيب أفضل 15 نتيجة، والـ Reranker بيعيد ترتيبهم بناءً على علاقتهم الدقيقة بالسؤال عشان يفلترهم لأفضل 5 فقط (Top-5 Precision)."

---

## Slide 6: Grounded Generation & Citation Mechanics
**Slide Content (English):**
- LLM acts strictly as an evidence synthesizer, never a diagnostician.
- Strict 4-part structure (Short Answer, Evidence, Recommendations, Safety).
- Tight claim-to-chunk binding with exact `[Source N]` formatting.

**🗣️ Speaker Script (Mix):**
"الـ LLM في السيستم بتاعنا مش بيشخص (Never a diagnostician)، هو بيشتغل كـ **Evidence Synthesizer** فقط. وعاملين Prompt Engineering صارم بيجبر الموديل يقسم إجابته لـ 4 أجزاء محددة (إجابة قصيرة، الأدلة، توصيات، وأمان). والأهم إنه مجبر يربط كل Recommendations بـ Exact Citation في شكل `[Source N]`."

---

## Slide 7: Safety, Guardrails & UX (🔥 نقطة قوة إضافية)
**Slide Content (English):**
- Intent Extractor (Input Risk Classification).
- Live API triggers (Weather/UV Index).
- STT (Whisper) & TTS (Karaoke-style playback).

**🗣️ Speaker Script (Mix):**
"بخصوص الأمان والـ UX، بنينا **Intent Extractor** بيشتغل كعقل مدبر. أولاً بيعمل Block لأي سؤال بره السياق الطبي. ثانياً، لو المريض سأل عن تأثير الجو على الحساسية، السيستم بيسحب بيانات الطقس والـ UV Index لايف عبر API ويدمجها في القرار. ولتحسين تجربة المستخدم (UX)، ضفنا دعم للصوت (STT) عبر Whisper، والموديل بيعرف إن السؤال جاي من Voice فبيتغاضى عن الأخطاء الإملائية. وضفنا كمان Karaoke-style TTS بيبدأ فوراً بدون أي تأخير (Zero Latency)."

---

## Slide 8: Empirical Evaluation
**Slide Content (English):**
- Evaluated on 20 questions across RAGAS, Noise Robustness, and LLM-as-a-Judge.
- All metrics exceed defined safety thresholds.

| Metric | Result |
|--------|--------|
| Faithfulness | **1.0 (100%)** |
| Noise Robustness | **1.0 (100%)** — 20/20 cases |
| Context Precision | **1.0 (100%)** |
| Answer Relevance | **0.834 (83.4%)** |
| LLM-Judge (Medical Accuracy / Groundedness / Safety / Helpfulness) | **5.0 / 5.0** |
| Reranker Precision@4 Gain (Disease) | **+8.96%** |

**🗣️ Speaker Script (Mix):**
"وعلشان نثبت كفاءة السيستم بالأرقام الفعلية، شغلنا منظومة Evaluation شاملة على 20 سؤال مختلف. النتائج كانت: **Faithfulness 100%** يعني مفيش حاجة واحدة قالها الموديل من دماغه بدون مصدر. **Noise Robustness 100%** يعني في كل الحالات الـ 20 التي أدخلنا فيها معلومات طبية مفبركة جوه الـ Retrieval، الموديل رفض يستخدمها. **Context Precision 100%**، و**Answer Relevance 83.4%**. وأهم حاجة: الـ LLM-as-a-Judge اللي شغلناه كان بيديه **5 من 5 في Medical Accuracy والـ Safety والـ Groundedness والـ Helpfulness**. ده بيثبت إن السيستم safe ومفيد في نفس الوقت."

---

## Slide 9: LIVE DEMO 💻
**(أثناء العرض ستفتح التطبيق وتنفذ الحالات الثلاثة المطلوبة في التقييم)**

**🗣️ Speaker Script (Mix):**
"ودلوقتي هننتقل للـ Live Demo وهنجرب 3 سيناريوهات زي ما هو مطلوب:
1. **(Case A - Success):** هنسأل سؤال مباشر: *(مثال: ما هو علاج الإكزيما؟)* .. زي ما حضراتكم شايفين، الإجابة طلعت بـ Citations واضحة، ولما نفتح الـ Evidence Panel بنشوف الـ Chunk الأصلي اللي جاب منه المعلومة.
2. **(Case B - Complex):** هنجرب نسجل بالصوت وندمج الـ Weather: *(مثال بالصوت: الجو حر النهاردة وعندي صدفية أعمل إيه؟)* .. الـ Intent Extractor فهم الصوت وجاب الطقس، ولو شغلنا الـ TTS هنشوف الـ Karaoke highlighting شغال لايف.
3. **(Case C - Safe Refusal):** هنسأل سؤال بره الـ Scope: *(مثال: ما هو علاج سرطان الثدي؟)* .. السيستم هنا بيعمل Safe Refusal بيرفض يجاوب بثقة وبيوضح إن المعلومات دي مش في الـ Guidelines بتاعته."

"شكراً جداً لوقتكم ومستعدين لأي أسئلة."
