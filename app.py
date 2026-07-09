# app.py
import streamlit as st
import sys
import os

# Ajouter le chemin racine
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.models import ExamPackage, ExamMetadata, DifficultyLevel
from core.engine import ExamEngine
from export.pdf_engine import PDFEngine
from export.docx_engine import DOCXEngine
from loguru import logger

# --- Config ---
st.set_page_config(
    page_title="Arabic EdTech Pro v3.0",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS ---
def load_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Amiri:wght@400;700&display=swap');
    
    * { direction: rtl; text-align: right; font-family: 'Amiri', serif; }
    
    .main-header {
        background: linear-gradient(135deg, #1a73e8 0%, #0d47a1 100%);
        color: white;
        padding: 30px 40px;
        border-radius: 12px;
        margin-bottom: 20px;
        text-align: center;
    }
    .main-header h1 { font-size: 28px; margin: 0; }
    .main-header p { font-size: 14px; opacity: 0.9; margin-top: 5px; }
    
    .step-card {
        background: #fff;
        border: 1px solid #e0e0e0;
        border-radius: 12px;
        padding: 2rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        margin-bottom: 1rem;
    }
    
    .metric-card {
        background: #f8f9fa;
        border-radius: 8px;
        padding: 15px;
        text-align: center;
        border: 2px solid #e0e0e0;
    }
    .metric-card .value { font-size: 28px; font-weight: bold; color: #1a73e8; }
    .metric-card .label { font-size: 12px; color: #666; }
    
    .quality-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 14px;
        font-weight: bold;
    }
    .quality-excellent { background: #e8f5e9; color: #2e7d32; }
    .quality-good { background: #fff3e0; color: #e65100; }
    .quality-warning { background: #ffebee; color: #c62828; }
    
    .stButton > button {
        border-radius: 8px;
        padding: 10px 24px;
        font-weight: bold;
        transition: 0.3s;
        border: none;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    
    .question-preview {
        background: #fafafa;
        border-right: 4px solid #1a73e8;
        padding: 12px 20px;
        margin: 10px 0;
        border-radius: 4px;
    }
    
    .vocalized-text {
        font-size: 20px;
        line-height: 2.6;
        text-align: justify;
        background: #fffde7;
        padding: 25px;
        border-radius: 10px;
        border: 1px solid #f0e68c;
    }
    </style>
    """, unsafe_allow_html=True)

load_css()

# --- Init Engine ---
@st.cache_resource
def get_engine():
    return ExamEngine()

# --- Session State ---
if 'engine' not in st.session_state:
    st.session_state.engine = get_engine()
    st.session_state.step = 1
    st.session_state.result = None
    st.session_state.raw_text = ""

# --- Header ---
st.markdown("""
<div class="main-header">
    <h1>🎓 مُولّد التقييمات اللغوية الذكي — النسخة الاحترافية</h1>
    <p>محرك NLP عربي كامل | تحليل صرفي ونحوي دقيق | تصدير احترافي PDF/DOCX | ضمان جودة آلي</p>
    <p>-مركز البحث العلمي و التقني لتطوير اللغة العربية -تلمسان</p>
</div>
""", unsafe_allow_html=True)

# --- Sidebar ---
with st.sidebar:
    st.markdown("### ⚙️ لوحة التحكم")
    st.markdown("---")
    
    if st.session_state.result:
        st.metric("نقاط الجودة", f"{st.session_state.result.quality_score:.1f}/100")
        st.metric("إجمالي النقاط", st.session_state.result.total_points)
        if st.session_state.result.blueprint:
            st.metric("معامل الثبات", f"{st.session_state.result.blueprint.estimated_reliability:.3f}")
    
    st.markdown("---")
    st.markdown("#### 📊 حالة النظام")
    st.success("✅ Pipeline NLP: نشط")
    st.success("✅ محرك الإعراب: نشط")
    st.success("✅ مولد الدistracteurs: نشط")
    st.success("✅ ضمان الجودة: نشط")
    
    st.markdown("---")
    st.caption("v3.0 — Arabic EdTech Pro")

# --- STEP 1: Text Input ---
if st.session_state.step == 1:
    st.markdown("### 📝 الخطوة 1: إدخال النص المصدر")
    
    with st.container():
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.markdown('<div class="step-card">', unsafe_allow_html=True)
            raw_text = st.text_area(
                "الصق النص العربي (صحافة، أدب، تاريخ، علوم)...",
                height=350,
                key="input_text",
                placeholder="مثال: يُعدّ التعليم ركيزة أساسية في بناء المجتمعات وتقدّمها..."
            )
            word_count = len(raw_text.split()) if raw_text else 0
            st.caption(f"📊 عدد الكلمات: {word_count} | {'✅ نص كافٍ' if word_count >= 30 else '⚠️ يُفضّل نص أطول (30+ كلمة)'}")
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="step-card">', unsafe_allow_html=True)
            st.markdown("#### 💡 نصائح للجودة")
            st.markdown("""
            - استخدم نصاً أصلياً (غير مُنقّح)
            - تجنّب النصوص المترجمة آلياً
            - 50-200 كلمة = حجم مثالي
            - تأكّد من وجود علامات ترقيم
            """)
            st.markdown('</div>', unsafe_allow_html=True)
        
        if st.button("➡️ الخطوة التالية: التخصيص", use_container_width=True, type="primary", disabled=not raw_text or word_count < 10):
            st.session_state.raw_text = raw_text
            st.session_state.step = 2
            st.rerun()

# --- STEP 2: Configuration ---
elif st.session_state.step == 2:
    st.markdown("### ⚙️ الخطوة 2: تخصيص الاختبار")
    
    # Métadonnées de l'examen
    with st.expander("📋 معلومات الاختبار (اختياري)", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            exam_title = st.text_input("عنوان الاختبار", value="اختبار في اللغة العربية")
            institution = st.text_input("المؤسسة", value="")
        with col2:
            teacher = st.text_input("اسم الأستاذ", value="")
            duration = st.number_input("المدة (دقيقة)", min_value=10, max_value=180, value=60)
        with col3:
            academic_year = st.text_input("السنة الدراسية", value="")
            instructions = st.text_area("التعليمات", value="اقرأ النص بعناية ثم أجب عن الأسئلة بدقة.", height=80)
    
    st.markdown("---")
    
    # Configuration des exercices
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="step-card">', unsafe_allow_html=True)
        st.markdown("#### 🎯 المستوى والصعوبة")
        difficulty = st.selectbox(
            "المستوى المستهدف (CEFR)",
            [d.value for d in DifficultyLevel],
            index=2
        )
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="step-card">', unsafe_allow_html=True)
        st.markdown("#### ❓ أسئلة الاختيار من متعدد")
        num_mcq = st.slider("عدد أسئلة الفهم", 0, 15, 5)
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="step-card">', unsafe_allow_html=True)
        st.markdown("#### 📝 الإعراب والنحو")
        num_nahw = st.slider("عدد أسئلة الإعراب", 0, 15, 5)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="step-card">', unsafe_allow_html=True)
        st.markdown("#### 🔤 الصرف والاشتقاق")
        cloze_sarf = st.checkbox("تمارين الاشتقاق الصرفي", value=True)
        num_sarf = st.slider("عدد تمارين الصرف", 0, 10, 3) if cloze_sarf else 0
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="step-card">', unsafe_allow_html=True)
        st.markdown("#### ✍️ الإملاء")
        imlae_enabled = st.checkbox("تمرين تصحيح الأخطاء الإملائية", value=True)
        num_imlae = st.slider("عدد تمارين الإملاء", 0, 5, 2) if imlae_enabled else 0
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="step-card">', unsafe_allow_html=True)
        st.markdown("#### 📖 المعجم")
        vocab_enabled = st.checkbox("استخراج المفردات", value=True)
        num_vocab = st.slider("عدد المفردات", 0, 15, 5) if vocab_enabled else 0
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Résumé
    total_estimated = num_mcq + num_nahw + num_sarf + num_imlae + num_vocab
    est_points = num_mcq * 1 + num_nahw * 2 + num_sarf * 2 + num_imlae * 3 + num_vocab * 1
    
    col_info, col_gen = st.columns([2, 1])
    with col_info:
        st.info(f"📊 ملخص: {total_estimated} سؤال | ~{est_points} نقطة | المستوى: {difficulty}")
    with col_gen:
        if st.button("🚀 توليد الاختبار", use_container_width=True, type="primary"):
            config = {
                "difficulty": difficulty,
                "mcq": num_mcq > 0,
                "num_mcq": num_mcq,
                "cloze_nahw": num_nahw > 0,
                "num_nahw": num_nahw,
                "cloze_sarf": cloze_sarf,
                "num_sarf": num_sarf,
                "imlae": imlae_enabled,
                "num_imlae": num_imlae,
                "vocab": vocab_enabled,
                "num_vocab": num_vocab,
            }
            
            metadata = ExamMetadata(
                title=exam_title,
                institution=institution,
                teacher=teacher,
                duration_minutes=duration,
                academic_year=academic_year,
                instructions=instructions,
            )
            
            with st.spinner("🔄 جاري التحليل اللغوي الدقيق..."):
                try:
                    st.session_state.result = st.session_state.engine.build_exam(
                        st.session_state.raw_text, config, metadata
                    )
                    st.session_state.step = 3
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ خطأ في التوليد: {e}")
                    logger.error("Generation failed: {}", e)

# --- STEP 3: Preview & Export ---
elif st.session_state.step == 3 and st.session_state.result:
    pkg: ExamPackage = st.session_state.result
    
    st.markdown("### 📊 الخطوة 3: المعاينة والتصدير")
    
    # Quality badges
    score = pkg.quality_score
    if score >= 80:
        badge_cls = "quality-excellent"
        badge_text = f"✅ جودة ممتازة ({score:.1f}/100)"
    elif score >= 60:
        badge_cls = "quality-good"
        badge_text = f"⚠️ جودة جيدة ({score:.1f}/100)"
    else:
        badge_cls = "quality-warning"
        badge_text = f"❌ جودة تحتاج تحسين ({score:.1f}/100)"
    
    st.markdown(f'<span class="quality-badge {badge_cls}">{badge_text}</span>', unsafe_allow_html=True)
    
    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<div class="metric-card"><div class="value">{pkg.total_points}</div><div class="label">إجمالي النقاط</div></div>', unsafe_allow_html=True)
    with col2:
        total_q = len(pkg.questions_mcq) + len(pkg.questions_cloze) + len(pkg.questions_imlae) + len(pkg.questions_vocab)
        st.markdown(f'<div class="metric-card"><div class="value">{total_q}</div><div class="label">عدد الأسئلة</div></div>', unsafe_allow_html=True)
    with col3:
        if pkg.blueprint:
            st.markdown(f'<div class="metric-card"><div class="value">{pkg.blueprint.estimated_reliability:.2f}</div><div class="label">معامل الثبات</div></div>', unsafe_allow_html=True)
    with col4:
        st.markdown(f'<div class="metric-card"><div class="value">{len(pkg.questions_mcq) + len(pkg.questions_cloze)}</div><div class="label">مهارات مغطّاة</div></div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📖 النص المشكّل", "❓ الأسئلة", "📐 جدول المواصفات", "⬇️ التصدير"])
    
    with tab1:
        st.markdown(f'<div class="vocalized-text">{pkg.vocalized_text}</div>', unsafe_allow_html=True)
    
    with tab2:
        # QCM
        if pkg.questions_mcq:
            st.markdown("#### ❓ أسئلة الاختيار من متعدد")
            for i, q in enumerate(pkg.questions_mcq, 1):
                st.markdown(f'<div class="question-preview"><b>{i}.</b> {q.question_text} <em style="color:#666;">({q.points} نقطة)</em></div>', unsafe_allow_html=True)
                for j, opt in enumerate(q.options):
                    letter = "أبجد"[j] if j < 4 else str(j)
                    marker = "✅" if opt.is_correct else "⭕"
                    st.markdown(f"&nbsp;&nbsp;&nbsp;{marker} {letter}) {opt.text}")
                if q.explanation:
                    st.caption(f"💡 {q.explanation}")
        
        # Cloze
        if pkg.questions_cloze:
            st.markdown("#### 📝 أسئلة الإعراب والصرف")
            for i, q in enumerate(pkg.questions_cloze, 1):
                st.markdown(f'<div class="question-preview"><b>{i}.</b> {q.cloze_sentence} <em style="color:#666;">({q.points} نقطة)</em></div>', unsafe_allow_html=True)
                st.caption(f"✅ الإجابة: {q.answer_vocalized}")
                st.caption(f"📐 القاعدة: {q.i3rab_rule}")
                st.caption(f"📝 الإعراب: {q.i3rab_detailed}")
        
        # Imlae
        if pkg.questions_imlae:
            st.markdown("#### ✍️ تمارين الإملاء")
            for i, q in enumerate(pkg.questions_imlae, 1):
                st.markdown(f'<div class="question-preview"><b>{i}.</b> {q.sentence_with_errors} <em style="color:#666;">({q.points} نقطة)</em></div>', unsafe_allow_html=True)
                st.caption(f"✅ التصحيح: {q.corrected_sentence}")
                for err in q.errors:
                    st.caption(f"❌ «{err.error_word}» → ✅ «{err.original_word}» — {err.rule_explanation}")
        
        # Vocab
        if pkg.questions_vocab:
            st.markdown("#### 📖 المعجم")
            for i, v in enumerate(pkg.questions_vocab, 1):
                st.markdown(f'<div class="question-preview"><b>{i}.</b> اشرح كلمة «{v.vocalized}» <em style="color:#666;">({v.points} نقطة)</em></div>', unsafe_allow_html=True)
                st.caption(f"الجذر: {v.root or '—'} | النوع: {v.pos or '—'}")
                if v.synonyms:
                    st.caption(f"المرادفات: {', '.join(v.synonyms)}")
    
    with tab3:
        if pkg.blueprint:
            st.markdown("#### 📐 جدول المواصفات (Table of Specifications)")
            
            st.markdown("**المستويات المعرفية (Bloom):**")
            for level, count in pkg.blueprint.bloom_distribution.items():
                st.progress(count / max(pkg.blueprint.bloom_distribution.values()), text=f"{level}: {count}")
            
            st.markdown("**مستويات الصعوبة:**")
            for level, count in pkg.blueprint.difficulty_distribution.items():
                st.progress(count / max(pkg.blueprint.difficulty_distribution.values()), text=f"{level}: {count}")
            
            st.markdown("**المهارات المغطّاة:**")
            for skill, count in pkg.blueprint.skill_coverage.items():
                st.progress(count / max(pkg.blueprint.skill_coverage.values()), text=f"{skill}: {count}")
            
            st.metric("معامل الثبات المُقدّر (Cronbach α)", f"{pkg.blueprint.estimated_reliability:.3f}")
            st.caption("ملاحظة: التقديرheuristique. للقياس الدقيق، استخدم نتائج الطلاب الفعلية.")
    
    with tab4:
        st.markdown("#### ⬇️ تحميل الملفات")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**📄 ملفات PDF**")
            pdf_exam = PDFEngine.generate_pdf(pkg, is_answer_key=False)
            pdf_key = PDFEngine.generate_pdf(pkg, is_answer_key=True)
            
            st.download_button(
                "📥 ورقة الاختبار (PDF)",
                data=pdf_exam,
                file_name=f"Exam_{pkg.id[:8]}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
            st.download_button(
                "📥 مفتاح التصحيح (PDF)",
                data=pdf_key,
                file_name=f"AnswerKey_{pkg.id[:8]}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        
        with col2:
            st.markdown("**📝 ملفات Word**")
            docx_exam = DOCXEngine.generate_docx(pkg, is_answer_key=False)
            docx_key = DOCXEngine.generate_docx(pkg, is_answer_key=True)
            
            st.download_button(
                "📥 ورقة الاختبار (Word)",
                data=docx_exam,
                file_name=f"Exam_{pkg.id[:8]}.docx",
                use_container_width=True
            )
            st.download_button(
                "📥 مفتاح التصحيح (Word)",
                data=docx_key,
                file_name=f"AnswerKey_{pkg.id[:8]}.docx",
                use_container_width=True
            )
        
        st.markdown("---")
        st.caption(f"🔐 رمز الأمان: `{pkg.security_hash[:32]}...`")
        st.caption(f"📊 معرّف الاختبار: `{pkg.id}`")
    
    st.markdown("---")
    if st.button("🔄 إنشاء اختبار جديد", use_container_width=True):
        st.session_state.step = 1
        st.session_state.result = None
        st.session_state.raw_text = ""
        st.rerun()
