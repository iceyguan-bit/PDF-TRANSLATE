import fitz  # PyMuPDF
from deep_translator import GoogleTranslator
import os
from pathlib import Path

def translate_single_pdf(input_path, output_path, target_lang="en", font_path=None):
    doc = fitz.open(input_path)
    translator = GoogleTranslator(source='auto', target=target_lang)

    use_custom_font = bool(font_path and os.path.exists(font_path))
    font_name = "custom_font" if use_custom_font else "helv"

    for page_num, page in enumerate(doc):
        if use_custom_font:
            page.insert_font(fontname=font_name, fontfile=font_path)

        blocks = page.get_text("blocks")
        translations = []

        for b in blocks:
            if b[6] == 0:
                rect = fitz.Rect(b[0], b[1], b[2], b[3])
                raw_text = b[4].strip()
                if not raw_text or raw_text.isdigit():
                    continue
                clean_text = raw_text.replace("\n", " ")
                try:
                    translated_text = translator.translate(clean_text)
                    translations.append((rect, translated_text))
                    page.add_redact_annot(rect, fill=(1, 1, 1))
                except Exception as e:
                    print(f"[警告] 第 {page_num + 1} 页段落翻译跳过: {e}")

        page.apply_redactions()

        for rect, trans_text in translations:
            font_size = 10
            while font_size >= 6:
                rc = page.insert_textbox(
                    rect,
                    trans_text,
                    fontsize=font_size,
                    fontname=font_name,
                    color=(0, 0, 0),
                    align=fitz.TEXT_ALIGN_LEFT
                )
                if rc >= 0:
                    break
                font_size -= 1

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    doc.save(output_path)
    doc.close()

def main():
    input_dir = Path("input_pdfs")
    output_dir = Path("translated_pdfs")
    target_lang = "en"  # 目标语言: 'en'(英文), 'zh-CN'(简体中文), 'ja'(日文)
    linux_font = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"

    pdf_files = list(input_dir.glob("*.pdf"))
    print(f"找到 {len(pdf_files)} 个 PDF 文件，开始翻译...")

    for pdf_file in pdf_files:
        print(f"正在处理: {pdf_file.name}")
        out_file = output_dir / f"{pdf_file.stem}_{target_lang}.pdf"
        translate_single_pdf(str(pdf_file), str(out_file), target_lang, linux_font)
        print(f"完成: {out_file.name}")

if __name__ == "__main__":
    main()
