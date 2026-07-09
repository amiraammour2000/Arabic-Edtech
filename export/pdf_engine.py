# export/pdf_engine.py
"""
Génération de PDF professionnels avec rendu Arabic RTL parfait.
Utilise WeasyPrint + HTML/CSS + police Amiri.
"""
from typing import Optional
from io import BytesIO
from loguru import logger
from weasyprint import HTML, CSS
from core.models import ExamPackage


class PDFEngine:

    # CSS académique professionnel
    CSS_TEMPLATE = """
    @font-face {
        font-family: 'Amiri';
        src: url('assets/fonts/Amiri-Regular.ttf') format('truetype');
    }
    @font-face {
        font-family: 'Amiri';
        src: url('assets/fonts/Amiri-Bold.ttf') format('truetype');
        font-weight: bold;
    }
    
    * {
        direction: rtl;
        text-align: right;
        font-family: 'Amiri', 'Scheherazade New', serif;
        box-sizing: border-box;
    }
    
    @page {
        size: A4;
        margin: 2cm 1.5cm 2cm 1.5cm;
        
        @top-center {
            content: "اختبار في اللغة العربية";
            font-family: 'Amiri', serif;
            font-size: 10pt;
            color: #666;
        }
        @bottom-center {
            content: "Arabic EdTech Pro — صفحة " counter(page) " من " counter(pages);
            font-family: 'Amiri', serif;
            font-size: 9pt;
            color: #999;
        }
        @bottom-left {
            content: "{{security_hash}}";
            font-size: 7pt;
            color: #ccc;
        }
    }
    
    body {
        font-size: 14pt;
        line-height: 2.2;
        color: #1a1a1a;
    }
    
    .exam-header {
        text-align: center;
        border: 2px solid #1a73e8;
        border-radius: 8px;
        padding: 20px;
        margin-bottom: 20px;
        background: #f8f9fa;
    }
    
    .exam-title {
        font-size: 20pt;
        font-weight: bold;
        color: #1a73e8;
        margin-bottom: 10px;
    }
    
    .exam-meta {
        font-size: 11pt;
        color: #444;
        display: flex;
        justify-content: space-around;
        margin-top: 10px;
    }
    
    .student-info {
        display: flex;
        justify-content: space-between;
        margin: 15px 0;
        gap: 10px;
    }
    
    .student-field {
        flex: 1;
        border-bottom: 1.5px solid #333;
        padding: 5px;
        font-size: 11pt;
        color: #666;
    }
    
    .instructions {
        background: #fff3cd;
        border-right: 4px solid #ffc107;
        padding: 12px 20px;
        border-radius: 4px;
        margin: 15px 0;
        font-size: 12pt;
    }
    
    .text-section {
        background: #fafafa;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 25px;
        margin: 20px 0;
        font-size: 16pt;
        line-height: 2.4;
        text-align: justify;
    }
    
    .section-title {
        font-size: 16pt;
        font-weight: bold;
        color: #1a73e8;
        border-bottom: 2px solid #1a73e8;
        padding-bottom: 5px;
        margin: 25px 0 15px 0;
    }
    
    .question {
        margin: 15px 0;
        padding: 10px 15px;
        font-size: 14pt;
    }
    
    .question-number {
        font-weight: bold;
        color: #1a73e8;
        margin-left: 8px;
    }
    
    .question-points {
        float: left;
        font-size: 10pt;
        color: #666;
        background: #e8f0fe;
        padding: 2px 8px;
        border-radius: 4px;
    }
    
    .options {
        margin-right: 30px;
        margin-top: 8px;
    }
    
    .option {
        padding: 4px 0;
        font-size: 13pt;
    }
    
    .answer-line {
        border-bottom: 1.5px dotted #999;
        display: inline-block;
        min-width: 200px;
        margin: 0 5px;
    }
    
    .answer-key {
        background: #fff;
        border: 2px solid #28a745;
        border-radius: 8px;
        padding: 20px;
    }
    
    .correct-answer {
        color: #c62828;
        font-weight: bold;
        background: #ffebee;
        padding: 2px 6px;
        border-radius: 3px;
    }
    
    .i3rab-box {
        background: #e8f5e9;
        border-right: 3px solid #28a745;
        padding: 10px 15px;
        margin: 8px 0;
        font-size: 12pt;
        border-radius: 4px;
    }
    
    .qr-code {
        position: fixed;
        bottom: 1cm;
        left: 1cm;
        width: 80px;
        height: 80px;
    }
    
    .watermark {
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%) rotate(-30deg);
        font-size: 60pt;
        color: rgba(0, 0, 0, 0.03);
        z-index: -1;
        font-weight: bold;
    }
    
    .blueprint-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 10pt;
        margin: 15px 0;
    }
    
    .blueprint-table th, .blueprint-table td {
        border: 1px solid #ddd;
        padding: 6px 10px;
        text-align: center;
    }
    
    .blueprint-table th {
        background: #1a73e8;
        color: white;
    }
    """

    @classmethod
    def generate_pdf(cls, exam: ExamPackage, is_answer_key: bool = False) -> bytes:
        html_content = cls._build_html(exam, is_answer_key)
        css = cls.CSS_TEMPLATE.replace("{{security_hash}}", exam.security_hash[:32])

        buf = BytesIO()
        HTML(string=html_content, base_url=".").write_pdf(
            buf,
            stylesheets=[CSS(string=css)]
        )
        logger.info("PDF generated (answer_key={}) — {} bytes", is_answer_key, len(buf.getvalue()))
        return buf.getvalue()

    @classmethod
    def _build_html(cls, exam: ExamPackage, is_answer_key: bool) -> str:
        meta = exam.metadata
        mode = "ANSWER KEY — مفتاح التصحيح" if is_answer_key else "EXAM — ورقة الاختبار"

        html_parts = [
            f'<div class="watermark">{exam.watermark_text}</div>',
            # En-tête
            f'<div class="exam-header">',
            f'  <div class="exam-title">{meta.title}</div>',
            f'  <div style="font-size:12pt; color:#666;">{mode}</div>',
            f'  <div class="exam-meta">',
            f'    <span>المؤسسة: {meta.institution or "—"}</span>',
            f'    <span>الأستاذ: {meta.teacher or "—"}</span>',
            f'    <span>المدة: {meta.duration_minutes} دقيقة</span>',
            f'    <span>المجموع: {exam.total_points} نقطة</span>',
            f'  </div>',
            f'</div>',
        ]

        # Champs étudiants (seulement sur l'examen, pas le corrigé)
        if not is_answer_key and meta.student_name_field:
            html_parts.append(
                f'<div class="student-info">'
                f'  <div class="student-field">الاسم الكامل: ................................</div>'
                f'  <div class="student-field">القسم: ........................</div>'
                f'  <div class="student-field">التاريخ: ....................</div>'
                f'</div>'
            )

        # Instructions
        html_parts.append(f'<div class="instructions">📋 {meta.instructions}</div>')

        # Texte vocalisé
        html_parts.append(
            f'<div class="section-title">📖 النص المشكّل</div>'
            f'<div class="text-section">{exam.vocalized_text}</div>'
        )

        # QCM
        if exam.questions_mcq:
            html_parts.append(
                f'<div class="section-title">I. أسئلة الفهم والمعجم ({sum(q.points for q in exam.questions_mcq)} نقطة)</div>'
            )
            for i, q in enumerate(exam.questions_mcq, 1):
                html_parts.append(
                    f'<div class="question">'
                    f'  <span class="question-points">{q.points} ن</span>'
                    f'  <span class="question-number">{i}.</span> {q.question_text}'
                    f'</div>'
                )
                if not is_answer_key:
                    html_parts.append('<div class="options">')
                    for j, opt in enumerate(q.options):
                        letter = "أبجد" [j] if j < 4 else str(j)
                        html_parts.append(f'<div class="option">{letter}) {opt.text}</div>')
                    html_parts.append('</div>')
                else:
                    html_parts.append('<div class="options">')
                    for opt in q.options:
                        cls_ = "correct-answer" if opt.is_correct else ""
                        html_parts.append(f'<div class="option {cls_}">{opt.text}</div>')
                    html_parts.append('</div>')
                    if q.explanation:
                        html_parts.append(f'<div class="i3rab-box">💡 {q.explanation}</div>')

        # Trous (Nahw + Sarf)
        if exam.questions_cloze:
            nahw_pts = sum(q.points for q in exam.questions_cloze if q.grammar_category == "nahw")
            sarf_pts = sum(q.points for q in exam.questions_cloze if q.grammar_category == "sarf")

            if nahw_pts:
                html_parts.append(
                    f'<div class="section-title">II. الإعراب والنحو ({nahw_pts} نقطة)</div>'
                )
            if sarf_pts:
                html_parts.append(
                    f'<div class="section-title">III. الصرف والاشتقاق ({sarf_pts} نقطة)</div>'
                )

            nahw_idx = 0
            sarf_idx = 0
            for q in exam.questions_cloze:
                if q.grammar_category == "nahw":
                    nahw_idx += 1
                    num = nahw_idx
                else:
                    sarf_idx += 1
                    num = sarf_idx

                html_parts.append(
                    f'<div class="question">'
                    f'  <span class="question-points">{q.points} ن</span>'
                    f'  <span class="question-number">{num}.</span> {q.cloze_sentence}'
                    f'</div>'
                )
                if is_answer_key:
                    html_parts.append(
                        f'<div class="i3rab-box">'
                        f'  ✅ الإجابة: <span class="correct-answer">{q.answer_vocalized}</span><br>'
                        f'  📐 القاعدة: {q.i3rab_rule}<br>'
                        f'  📝 الإعراب: {q.i3rab_detailed}'
                        f'</div>'
                    )
                else:
                    html_parts.append('<div style="margin-right:30px; margin-top:5px; color:#999; font-size:11pt;">الإجابة: ............................................</div>')

        # Imlae
        if exam.questions_imlae:
            imlae_pts = sum(q.points for q in exam.questions_imlae)
            html_parts.append(
                f'<div class="section-title">IV. التصحيح الإملائي ({imlae_pts} نقطة)</div>'
            )
            html_parts.append(
                '<div style="font-size:12pt; color:#666; margin-bottom:10px;">'
                'صحّح الأخطاء الإملائية في الجمل التالية:'
                '</div>'
            )
            for i, q in enumerate(exam.questions_imlae, 1):
                html_parts.append(
                    f'<div class="question">'
                    f'  <span class="question-points">{q.points} ن</span>'
                    f'  <span class="question-number">{i}.</span> {q.sentence_with_errors}'
                    f'</div>'
                )
                if is_answer_key:
                    html_parts.append(
                        f'<div class="i3rab-box">'
                        f'  ✅ الجملة الصحيحة: {q.corrected_sentence}<br>'
                    )
                    for err in q.errors:
                        html_parts.append(
                            f'  ❌ «{err.error_word}» → ✅ «{err.original_word}» — {err.rule_explanation}<br>'
                        )
                    html_parts.append('</div>')
                else:
                    html_parts.append('<div style="margin-right:30px; margin-top:5px; color:#999; font-size:11pt;">التصحيح: ............................................</div>')

        # Vocabulaire
        if exam.questions_vocab:
            vocab_pts = sum(q.points for q in exam.questions_vocab)
            html_parts.append(
                f'<div class="section-title">V. المعجم ({vocab_pts} نقطة)</div>'
            )
            for i, v in enumerate(exam.questions_vocab, 1):
                html_parts.append(
                    f'<div class="question">'
                    f'  <span class="question-points">{v.points} ن</span>'
                    f'  <span class="question-number">{i}.</span> '
                    f'  اشرح كلمة «<b>{v.vocalized}</b>» في سياقها: {v.context_sentence}'
                    f'</div>'
                )
                if is_answer_key:
                    extras = []
                    if v.root:
                        extras.append(f"الجذر: {v.root}")
                    if v.pos:
                        extras.append(f"النوع: {v.pos}")
                    if v.synonyms:
                        extras.append(f"المرادفات: {', '.join(v.synonyms)}")
                    if extras:
                        html_parts.append(f'<div class="i3rab-box">📚 {" | ".join(extras)}</div>')
                else:
                    html_parts.append('<div style="margin-right:30px; margin-top:5px; color:#999; font-size:11pt;">المعنى: ............................................</div>')

        # Blueprint (uniquement sur le corrigé)
        if is_answer_key and exam.blueprint:
            html_parts.append(
                f'<div class="section-title">📊 جدول المواصفات</div>'
                f'<table class="blueprint-table">'
                f'  <tr><th>المعيار</th><th>التوزيع</th></tr>'
                f'  <tr><td>المستويات المعرفية (Bloom)</td><td>{", ".join(f"{k}: {v}" for k, v in exam.blueprint.bloom_distribution.items())}</td></tr>'
                f'  <tr><td>مستويات الصعوبة</td><td>{", ".join(f"{k}: {v}" for k, v in exam.blueprint.difficulty_distribution.items())}</td></tr>'
                f'  <tr><td>المهارات</td><td>{", ".join(f"{k}: {v}" for k, v in exam.blueprint.skill_coverage.items())}</td></tr>'
                f'  <tr><td>معامل الثبات (Cronbach α)</td><td>{exam.blueprint.estimated_reliability}</td></tr>'
                f'</table>'
            )

        # QR Code
        if exam.qr_code_b64:
            html_parts.append(f'<img src="{exam.qr_code_b64}" class="qr-code" />')

        return f'<html><head><meta charset="utf-8"></head><body>{"".join(html_parts)}</body></html>'