# Dermatology AI & Retrieval System Benchmark Test Suite

مجموعة أسئلة واختبارات شاملة لتقييم السيستم بالكامل (Frontend, Backend, LLM, Retrieval, Weather Tool)

إجمالي عدد حالات الاختبار: **44 سؤال واختبار فريد**


## 1. Direct Drug Inquiry (سؤال عن دواء بعينه)

### [TEST-001] Physiogel / Bepanthen (مرطب للإكزيما) (In-Scope | Arabic)
- **السؤال / User Prompt:** `إيه رأيك في كريم بيبانثين (Bepanthen) وفيسيوجل (Physiogel) للترطيب؟ عايز أعرف المادة الفعالة بتاعتهم وأضرارهم وهل يناسبوا الإكزيما؟`
- **السلوك والرد المتوقع:** يستدعي نظام استرجاع الأدوية (Drug Retrieval). يوضح المادة الفعالة (Dexpanthenol / Lipid complex)، الفوائد للترطيب وحاجز الجلد في الإكزيما، والآثار الجانبية النادرة.
- **الأدوات المستهدفة (Tools):** `retrieval_drugs`

### [TEST-002] Dermovate Ointment (Clobetasol) (In-Scope | English)
- **السؤال / User Prompt:** `What can you tell me about Dermovate ointment? What is its active ingredient, usage for severe skin flare-ups, and side effects?`
- **السلوك والرد المتوقع:** Retrieves Dermovate info (Clobetasol Propionate - potent topical corticosteroid). Explains short-term anti-inflammatory use for psoriasis/eczema and side effects like skin thinning.
- **الأدوات المستهدفة (Tools):** `retrieval_drugs`

### [TEST-003] Congestal (دواء برد/أنفلونزا) (Out-of-Scope | Arabic)
- **السؤال / User Prompt:** `إيه رأيك في دواء كونجستال (Congestal)؟ عايز أعرف المادة الفعالة بتاعته وأضراره ودواعي استعماله.`
- **السلوك والرد المتوقع:** يرفض الإجابة أو يوضح أن الدواء خارج نطاق التخصص (غير متعلق بالأمراض الجلدية المخصصة)، ينصح باستشارة طبيب عام أو صيدلي.
- **الأدوات المستهدفة (Tools):** `none / fallback`

### [TEST-004] Antinal (دواء مطهر معوي) (Out-of-Scope | English)
- **السؤال / User Prompt:** `Can you provide details on Antinal capsules, including active ingredients and side effects?`
- **السلوك والرد المتوقع:** Flags as non-dermatological medication (out of scope). Explains that the system specializes in skin conditions and directs user to a doctor.
- **الأدوات المستهدفة (Tools):** `none / fallback`

### [TEST-005] Vaxinocure Derm (دواء غير موجود) (Fake/Non-existent Drug | Arabic)
- **السؤال / User Prompt:** `تعرف إيه عن مرهم اسمه 'فاكسينوكور ديرم' (Vaxinocure Derm) للجلد؟ قولي أضراره ومكوناته.`
- **السلوك والرد المتوقع:** يعلن عدم وجود هذا الدواء في قاعدة البيانات المعتمدة أو عدم التعرف عليه، ويحذر من استخدام أدوية غير معروفة.
- **الأدوات المستهدفة (Tools):** `retrieval_drugs (not found)`

### [TEST-006] Dermastratol Forte (Non-existent) (Fake/Non-existent Drug | English)
- **السؤال / User Prompt:** `What are the active ingredients and side effects of Dermastratol Forte ointment?`
- **السلوك والرد المتوقع:** Reports that the drug is not found in the database and recommends verifying the medication name with a physician.
- **الأدوات المستهدفة (Tools):** `retrieval_drugs (not found)`


## 2. Drug for Specific Symptom (دواء لعرض معين)

### [TEST-007] صداع وألم بطن (Out-of-Scope Symptom | Arabic)
- **السؤال / User Prompt:** `عندي صداع نصفي شديد ومغص في البطن منذ الصباح، هل عندك دواء مناسب لي يخفف الألم؟`
- **السلوك والرد المتوقع:** يعتذر السيستم ويوضح أن الأعراض المذكورة باطنية/عصبية وليست جلدية، وينصح بزيارة طبيب عام فوراً وعدم تناول أدوية دون تشخيص.
- **الأدوات المستهدفة (Tools):** `none / fallback`

### [TEST-008] Dry Cough & Fever (Out-of-Scope Symptom | English)
- **السؤال / User Prompt:** `I have had a high fever and persistent dry cough for two days. Do you have a suitable medicine for me?`
- **السلوك والرد المتوقع:** Declines prescribing/recommending medication for systemic/respiratory symptoms. Directs to a healthcare professional.
- **الأدوات المستهدفة (Tools):** `none / fallback`

### [TEST-009] تقشير وجفاف وحكة بالجلد (In-Scope (Eczema Symptom) | Arabic)
- **السؤال / User Prompt:** `جلدي بيلتهب وبيرغي قشور وجاف جداً وفيه حكة مستمرة في إيدي، عندك مرهم أو دواء كويس يناسب العرض ده؟`
- **السلوك والرد المتوقع:** يسترجع الأدوية المخصصة لتهدئة جفاف وحكة الإكزيما (مثل الملطفات البترولية أو كورتيكوستيرويد خفيف حسب الحالة)، مع التنبيه بضرورة التقييم الطبي.
- **الأدوات المستهدفة (Tools):** `retrieval_drugs / retrieval_diseases`

### [TEST-010] Severe skin flaking & redness (In-Scope (Eczema Symptom) | English)
- **السؤال / User Prompt:** `My skin is peeling, extremely red, and severely itchy around my hands. Is there a specific ointment in your system for this?`
- **السلوك والرد المتوقع:** Suggests barrier repair moisturizers or mild topical anti-inflammatories while citing safety precautions.
- **الأدوات المستهدفة (Tools):** `retrieval_drugs`

### [TEST-011] قشور فضية وبقع حمراء سميكة (In-Scope (Psoriasis Symptom) | Arabic)
- **السؤال / User Prompt:** `ظهرت لي بقع حمراء سميكة وعليها طبقة قشور بيضاء فضية في كوعي وركبتي، في اسم دواء أو دهان مناسب للنوع ده من القشور؟`
- **السلوك والرد المتوقع:** يسترجع مستحضرات تقشير وترطيب القشور (مثل Salicylic acid / Calcipotriol) الخاصة بالصدفية، ويشرح وظيفتها.
- **الأدوات المستهدفة (Tools):** `retrieval_drugs`

### [TEST-012] Thick silver-scaled skin patches (In-Scope (Psoriasis Symptom) | English)
- **السؤال / User Prompt:** `I have thick red lesions covered with silvery scales on my knees. What drug or topical agent does your system recommend for these plaques?`
- **السلوك والرد المتوقع:** Retrieves psoriasis topicals (keratolytics, topical vitamin D analogs) and emphasizes doctor evaluation.
- **الأدوات المستهدفة (Tools):** `retrieval_drugs`

### [TEST-013] طفح جلدي مفاجئ بارز ومحمر (حكة شريوية) (In-Scope (Urticaria Symptom) | Arabic)
- **السؤال / User Prompt:** `طالع لي فجأة طفح جلدي بارز بقع وردية زي قرص الناموس بيهرش جداً ومتفرق في جسمي، عندك دواء يهدئ التورم والحكة دي؟`
- **السلوك والرد المتوقع:** يسترجع مضادات الهستامين (Antihistamines) والملطفات الموضعية المناسبة لأعراض الارتيكاريا، مع نصائح لتجنب المثيرات.
- **الأدوات المستهدفة (Tools):** `retrieval_drugs`

### [TEST-014] Sudden itchy raised welts (Hives) (In-Scope (Urticaria Symptom) | English)
- **السؤال / User Prompt:** `I suddenly developed raised, intense itchy red welts all over my arms. Do you have a medication suitable for quick relief of this symptom?`
- **السلوك والرد المتوقع:** Recommends second-generation oral antihistamines (e.g., Cetirizine/Loratadine) via drug retrieval and urges seeking urgent care if swelling reaches mouth/throat.
- **الأدوات المستهدفة (Tools):** `retrieval_drugs`


## 3. Unnamed Symptom Description (وصف الأعراض دون تسمية المرض)

### [TEST-015] الإكزيما (Eczema) (In-Scope (Eczema Deduction) | Arabic)
- **السؤال / User Prompt:** `بقالي أسبوعين جلدي جاف جداً وفيه تشققات مع حكة شديدة بتزيد بالليل خصوصاً خلف الركبة وثنية الكوع. تفتكر إيه المرض المحتمل ده، وإيه النصائح والخطوات القادمة؟`
- **السلوك والرد المتوقع:** يتعرف النظام على مرض الإكزيما (Atopic Dermatitis/Eczema)، يشرح سبب ترجيحه، يعرض الأعراض الإضافية المتوقعة، وينصح بمرطبات وزيارة الطبيب.
- **الأدوات المستهدفة (Tools):** `retrieval_diseases`

### [TEST-016] Eczema (In-Scope (Eczema Deduction) | English)
- **السؤال / User Prompt:** `For the past month, my skin is extremely dry, inflamed, and has severe itching especially inside my elbows and behind knees. What condition could this be and how should I handle it?`
- **السلوك والرد المتوقع:** Identifies Eczema as the high-probability candidate. Explains disease nature, triggers, and care routine.
- **الأدوات المستهدفة (Tools):** `retrieval_diseases`

### [TEST-017] الصدفية (Psoriasis) (In-Scope (Psoriasis Deduction) | Arabic)
- **السؤال / User Prompt:** `عندي بقع حمراء بحدود واضحة وعليها قشور سميكة بيضاء فضية في فروة رأسي وعلى الركبتين، وملمسها خشن وتسبب لي ضيق. تتوقع ده مرض إيه؟`
- **السلوك والرد المتوقع:** يرجح مرض الصدفية (Psoriasis). يشرح طبيعته المناعية الذاتية غير المعدية والأعراض المرتبطة بها.
- **الأدوات المستهدفة (Tools):** `retrieval_diseases`

### [TEST-018] Psoriasis (In-Scope (Psoriasis Deduction) | English)
- **السؤال / User Prompt:** `I have raised red patches of skin covered with silvery-white buildup of dead skin cells on my scalp and lower back. What is the most likely diagnosis?`
- **السلوك والرد المتوقع:** Deduces Psoriasis. Outlines plaque psoriasis characteristics, potential joint complications to watch for, and advises medical consultation.
- **الأدوات المستهدفة (Tools):** `retrieval_diseases`

### [TEST-019] الارتيكاريا / الشرى (Urticaria) (In-Scope (Urticaria Deduction) | Arabic)
- **السؤال / User Prompt:** `صحيت من النوم لقيت تورمات جلديّة حمراء بارزة بتظهر وتختفي وتبدل مكانها في جسمي خلال ساعات مع حكة شديدة جداً. ده ممكن يكون إيه؟`
- **السلوك والرد المتوقع:** يتوصل إلى الارتيكاريا/الشرى (Urticaria/Hives). يوضح طبيعتها التحسسية وأسبابها المؤقتة والمزمنة.
- **الأدوات المستهدفة (Tools):** `retrieval_diseases`

### [TEST-020] Urticaria / Hives (In-Scope (Urticaria Deduction) | English)
- **السؤال / User Prompt:** `I suddenly started getting red, swollen, intensely itchy welts that appear on different parts of my body and fade within 24 hours. What condition is this?`
- **السلوك والرد المتوقع:** Identifies Urticaria (Hives). Explains mast cell histamine release, triggers, and warning signs of anaphylaxis.
- **الأدوات المستهدفة (Tools):** `retrieval_diseases`

### [TEST-021] ضيق تنفس وكحة وألم صدري (Out-of-Scope Symptoms | Arabic)
- **السؤال / User Prompt:** `حاسس بضيق في التنفس مع كحة ناشفة وألم شديد في القفص الصدري وارتفاع الحرارة. تتوقع ده مرض إيه وعلاجه إيه؟`
- **السلوك والرد المتوقع:** يرفض التخمين ويركز على أن الأعراض جهاز تنفسي/قلبي وخارج نطاق الأمراض الجلدية، ويوجه للذهاب فوراً للطوارئ أو طبيب صدرية.
- **الأدوات المستهدفة (Tools):** `none / emergency alert`

### [TEST-022] Chest pain & Dizziness (Out-of-Scope Symptoms | English)
- **السؤال / User Prompt:** `I am experiencing sharp chest pain radiating to my left arm along with severe dizziness. What illness could this be?`
- **السلوك والرد المتوقع:** Flags red-flag emergency symptoms, states out of scope for dermatological AI, and strongly urges emergency room visit.
- **الأدوات المستهدفة (Tools):** `none / emergency alert`


## 4. Stating Disease Name Directly (ذكر اسم المرض مباشرة)

### [TEST-023] الإكزيما (Eczema) (In-Scope (Eczema) | Arabic)
- **السؤال / User Prompt:** `الطبيب تشخصني بمريض إكزيما (Eczema). ممكن تشرح لي بتفصيل إيه هي أعراض المرض ده، إيه المثيرات اللي أبعد عنها، وإزاي أعتني ببشرتي؟`
- **السلوك والرد المتوقع:** يسترجع معلومات الإكزيما المتكاملة: الأعراض، المثيرات (الصابون القاسي، الجفاف، بعض الأنسجة)، وطرق الرعاية اليومية بالمرطبات.
- **الأدوات المستهدفة (Tools):** `retrieval_diseases`

### [TEST-024] Eczema / Atopic Dermatitis (In-Scope (Eczema) | English)
- **السؤال / User Prompt:** `I have been diagnosed with Eczema. Can you give me a comprehensive overview of its symptoms, key precautions, and daily lifestyle habits?`
- **السلوك والرد المتوقع:** Provides detailed medical standard guide on Eczema, trigger avoidance, and moisturizing strategies.
- **الأدوات المستهدفة (Tools):** `retrieval_diseases`

### [TEST-025] الصدفية (Psoriasis) (In-Scope (Psoriasis) | Arabic)
- **السؤال / User Prompt:** `عايز أعرف معلومات كاملة عن مرض الصدفية (Psoriasis): هل هو مرض معدي؟ إيه أسبابه وأعراضه وأهم الحاجات اللي لازم أخد بالي منها؟`
- **السلوك والرد المتوقع:** يسترجع داتا الصدفية: يؤكد أنه غير معدي، ويوضح طبيعته المناعية، محفزاته (الضغط النفسي، الجروح)، وأعراضه القشرية.
- **الأدوات المستهدفة (Tools):** `retrieval_diseases`

### [TEST-026] Psoriasis (In-Scope (Psoriasis) | English)
- **السؤال / User Prompt:** `Tell me everything about Psoriasis: symptoms, triggers, precautions, and whether it is contagious.`
- **السلوك والرد المتوقع:** Retrieves comprehensive info on Psoriasis. Clarifies autoimmune non-contagious nature and trigger precautions.
- **الأدوات المستهدفة (Tools):** `retrieval_diseases`

### [TEST-027] الارتيكاريا (Urticaria) (In-Scope (Urticaria) | Arabic)
- **السؤال / User Prompt:** `أنا عندي ارتيكاريا (Urticaria/Hives). كلمني عن أعراضها وإيه الفرق بين الحادة والمزمنة واحتياطات التعامل مع النوبات؟`
- **السلوك والرد المتوقع:** يسترجع داتا الارتيكاريا: يشرح الأعراض (الانتباخات الشريوية)، الفرق بين أقل وأكثر من 6 أسابيع، واحتياطات تجنب الأطعمة والمحفزات.
- **الأدوات المستهدفة (Tools):** `retrieval_diseases`

### [TEST-028] Urticaria / Hives (In-Scope (Urticaria) | English)
- **السؤال / User Prompt:** `I have Urticaria (Hives). What are its main symptoms, causes, triggers, and what precautions should I take during a flare-up?`
- **السلوك والرد المتوقع:** Retrieves detailed breakdown of Urticaria, triggers (food, temperature, stress), and precautions.
- **الأدوات المستهدفة (Tools):** `retrieval_diseases`

### [TEST-029] مرض السكري (Diabetes) (Out-of-Scope Disease | Arabic)
- **السؤال / User Prompt:** `ممكن تشرح لي أعراض مرض السكري (Diabetes) وإيه المضاعفات بتاعته وكيفية الوقاية منه؟`
- **السلوك والرد المتوقع:** يوضح أن مرض السكري خارج نطاق التخصص الجلدي للنظام، وينصح باستشارة طبيب غدد صماء وسكر.
- **الأدوات المستهدفة (Tools):** `none / fallback`

### [TEST-030] Hypertension (ضغط الدم المرتفع) (Out-of-Scope Disease | English)
- **السؤال / User Prompt:** `Can you explain the symptoms and long-term precautions for Hypertension (high blood pressure)?`
- **السلوك والرد المتوقع:** Declines detailed response due to being outside the dermatological domain and recommends consulting a cardiologist/internist.
- **الأدوات المستهدفة (Tools):** `none / fallback`


## 5. Disease + Current Medication (مرض + دواء بالفعل)

### [TEST-031] إكزيما + Hydrocortisone Cream 1% (In-Scope Disease + Relevant Med | Arabic)
- **السؤال / User Prompt:** `أنا عندي إكزيما وتشخصت بيها، وبقال أسبوع بستخدم كريم هيدروكورتيزون (Hydrocortisone 1%). هل الدواء ده مناسب وكويس؟ وإيه أضراره لو استمريت عليه وهل فيه حاجة أفضل للترطيب؟`
- **السلوك والرد المتوقع:** يسترجع تفاصيل الهيدروكورتيزون: يؤكد كونه كورتيزون خفيف مناسب للتهيج، يحذر من الاستخدام الطويل لتجنب ترقق الجلد، ويوصي بدمجه مع مرطبات كيو في أو بيبانثين.
- **الأدوات المستهدفة (Tools):** `retrieval_drugs / retrieval_diseases`

### [TEST-032] Urticaria + Cetirizine 10mg (In-Scope Disease + Relevant Med | English)
- **السؤال / User Prompt:** `I have chronic Urticaria and I am currently taking Cetirizine 10mg daily. Is this a good medication, what are its side effects, and are there better alternatives?`
- **السلوك والرد المتوقع:** Retrieves Cetirizine details (2nd gen antihistamine standard for hives). Discusses efficacy, minor sedation risks, and second-line options if uncontrolled.
- **الأدوات المستهدفة (Tools):** `retrieval_drugs / retrieval_diseases`

### [TEST-033] إكزيما + Augmentin (مضاد حيوي شديد) (In-Scope Disease + Irrelevant/Inappropriate Med | Arabic)
- **السؤال / User Prompt:** `أنا عندي إكزيما شديدة واحد صحبي نصحني أخد مضاد حيوي أوجمنتين (Augmentin) عشان يضيعها. هل الدواء ده صح ولا غلط ومناسب لحالتي؟`
- **السلوك والرد المتوقع:** ينبه بقوة أن المضاد الحيوي الفموي لا يعالج الإكزيما النمطية إلا في حالة وجود عدوى بكتيرية ثانوية مؤكدة بمسحة، وينصح بعدم أخذ مضادات حيوية دون استشارة طبيب.
- **الأدوات المستهدفة (Tools):** `retrieval_drugs / drug-disease mapping`

### [TEST-034] Psoriasis + Panadol Extra (In-Scope Disease + Irrelevant/Inappropriate Med | English)
- **السؤال / User Prompt:** `I have Psoriasis plaques on my skin and I am taking Panadol Extra to clear it up. Is this effective or should I stop?`
- **السلوك والرد المتوقع:** Clarifies that Panadol Extra (Paracetamol/Caffeine) is an analgesic and has no efficacy against autoimmune psoriasis plaques. Recommends dermatological therapies.
- **الأدوات المستهدفة (Tools):** `retrieval_drugs`

### [TEST-035] ربو + Ventolin Inhaler (Out-of-Scope Disease + Med | Arabic)
- **السؤال / User Prompt:** `أنا عندي مرض الربو (Asthma) وبستخدم بخاخة فنتولين (Ventolin). هل الدواء ده مناسب وكويس للحد من أزمات التنفس؟`
- **السلوك والرد المتوقع:** يشير إلى أن هذا السؤال يتعلق بمرض تنفسي ودواء صدرية خارج نطاق اختصاص السيستم الجلدي.
- **الأدوات المستهدفة (Tools):** `none / fallback`

### [TEST-036] Type 2 Diabetes + Metformin (Out-of-Scope Disease + Med | English)
- **السؤال / User Prompt:** `I have Type 2 Diabetes and taking Metformin 500mg. Can you review if this is the best drug for me?`
- **السلوك والرد المتوقع:** Declines reviewing diabetic treatment, noting it is outside the scope of the dermatology platform.
- **الأدوات المستهدفة (Tools):** `none / fallback`


## 6. Travel + Weather + Condition (السفر والطقس والمرض)

### [TEST-037] إكزيما + سفر إلى أسوان (In-Scope (Eczema + Egyptian City) | Arabic)
- **السؤال / User Prompt:** `أنا مسافر أسوان الأسبوع الجاي وعندي إكزيما شديدة، الجو هناك هيبقى عامل إزاي، وإيه اللي أخد بالي منه بالنسبة لبشرتي، وأجيب أدوية إيه معايا؟`
- **السلوك والرد المتوقع:** يستدعي أداة الطقس لمدينة أسوان. يحذر من الجفاف والحرارة العالية، ينصح بزيادة المرطبات الثقيلة، واصطحاب كورتيزون موضع تحسباً للهيجان.
- **الأدوات المستهدفة (Tools):** `weather_tool + retrieval_diseases + retrieval_drugs`

### [TEST-038] Eczema + Travel to Alexandria (In-Scope (Eczema + Egyptian City) | English)
- **السؤال / User Prompt:** `I have Eczema and I am traveling to Alexandria, Egypt next week. How will the weather be, how will high humidity affect my skin, and what should I pack?`
- **السلوك والرد المتوقع:** Calls weather tool for Alexandria. Discusses humidity effects (sweat can trigger itchiness), recommends light non-comedogenic moisturizers, sunblock, and mild cleansers.
- **الأدوات المستهدفة (Tools):** `weather_tool + retrieval_diseases + retrieval_drugs`

### [TEST-039] صدفية + سفر إلى سفاجا / الغردقة (In-Scope (Psoriasis + Egyptian City) | Arabic)
- **السؤال / User Prompt:** `أنا عندي صدفية ومسافر الغردقة/سفاجا الأسبوع الجاي. طقس المنطقة هناك إيه دنيته، وهل شمس البحر مفيدة للصدفية ولا لاء، واحتياطاتي إيه؟`
- **السلوك والرد المتوقع:** يستدعي أداة الطقس للغردقة/سفاجا. يوضح فوائد العلاج المناخي بالمياه المالمحة والأشعة فوق البنفسجية للصدفية مع التحذير الشديد من حروق الشمس وضرورة التدرج.
- **الأدوات المستهدفة (Tools):** `weather_tool + retrieval_diseases`

### [TEST-040] Psoriasis + Travel to Luxor (In-Scope (Psoriasis + Egyptian City) | English)
- **السؤال / User Prompt:** `I suffer from Psoriasis and plan to visit Luxor next week. What is the current weather forecast there and what skin protection advice do you have for hot dry climate?`
- **السلوك والرد المتوقع:** Calls weather tool for Luxor. Advises on hot dry weather precautions, intense sun protection, and maintaining topical regimen.
- **الأدوات المستهدفة (Tools):** `weather_tool + retrieval_diseases`

### [TEST-041] ارتيكاريا + سفر إلى القاهرة (In-Scope (Urticaria + Egyptian City) | Arabic)
- **السؤال / User Prompt:** `أنا عندي ارتيكاريا حرارية/شريوية ومسافر القاهرة الأسبوع الجاي. الطقس والحرارة هناك إيه دنيتهم وهستعد إزاي عشان أتجنب نوبات الحساسية؟`
- **السلوك والرد المتوقع:** يستدعي أداة الطقس للقاهرة. ينصح بتجنب التعرق الزائد والحرارة، ارتداء ملابس قطنية فضفاضة، واصطحاب مضادات الهستامين.
- **الأدوات المستهدفة (Tools):** `weather_tool + retrieval_diseases + retrieval_drugs`

### [TEST-042] Urticaria + Travel to Marsa Matrouh (In-Scope (Urticaria + Egyptian City) | English)
- **السؤال / User Prompt:** `I have Urticaria and I'm traveling to Marsa Matrouh. What will the weather be like next week, and how can I prevent hives during my beach vacation?`
- **السلوك والرد المتوقع:** Calls weather tool for Marsa Matrouh. Gives advice on cold wind/sun triggers, avoiding sudden sea temperature changes, and holding antihistamines.
- **الأدوات المستهدفة (Tools):** `weather_tool + retrieval_diseases + retrieval_drugs`

### [TEST-043] سفر وسياحة (بدون مرض جلدي) (Out-of-Scope Travel Query | Arabic)
- **السؤال / User Prompt:** `أنا مسافر شرم الشيخ الأسبوع الجاي مع صحابي ومفيش عندي أي أمراض، عايز أعرف الطقس هناك إيه وأحسن الأماكن للفسحة هناك؟`
- **السلوك والرد المتوقع:** يستدعي أداة الطقس لشرم الشيخ ويجيب عن الجو، لكن ينبه بلطف أنه ليس دليلاً سياحياً بل نظام طبي جلدي.
- **الأدوات المستهدفة (Tools):** `weather_tool / non-medical fallback`

### [TEST-044] Travel to London + Asthma (Out-of-Scope Travel Query | English)
- **السؤال / User Prompt:** `I am traveling to London next week and I have Asthma. What is the weather forecast and how will it affect my breathing?`
- **السلوك والرد المتوقع:** Responds with weather if available, but clearly disclaims that asthma management is outside the skin AI domain.
- **الأدوات المستهدفة (Tools):** `weather_tool / non-derma disclaimer`

