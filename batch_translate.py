import fitz  # PyMuPDF
from deep_translator import GoogleTranslator
import os
import subprocess
from pathlib import Path

def has_text_layer(pdf_path):
    """检测 PDF 是否已经包含可选中的文字层"""
    doc = fitz.open(pdf_path)
    total_chars = sum(len(page.get_text().strip()) for page in doc)
    doc.close()
    return total_chars > 20

def run_ocr_if_needed(input_path, temp_ocr_path):
    """如果是纯图片扫描件，调用 ocrmypdf 自动识别中英文生成文字层"""
    if has_text_layer(input_path):
        print("  -> 检测到原生文字层，跳过 OCR 直接翻译。")
        return input_path

    print("  -> 检测到纯图片扫描件，正在执行自动 OCR 识别（约需 10~30 秒）...")
    cmd = [
        "ocrmypdf",
        "-l", "chi_sim+eng",  # 同时识别简体中文和英文
        "--force-ocr",        # 强制识别图片区域
        "--deskew",           # 自动纠偏倾斜的扫描页
        str(input_path),
        str(temp_ocr_path)
    ]
    subprocess.run(cmd, check=True)
    print("  -> OCR 识别完成！")
    return temp_ocr_path

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
                clean_text = raw_text.replace("\n", " ")[:4500]  # 限制单次长度防超限
                try:
                    translated_text = translator.translate(clean_text)
                    translations.append((rect, translated_text))
                    page.add_redact_annot(rect, fill=(1, 1, 1))
                except Exception as e:
                    print(f"  [警告] 第 {page_num + 1} 页段落跳过: {e}")

        page.apply_redactions()

        for rect, trans_text in translations:
            font_size = 9
            while font_size >= 5:
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
    temp_dir = Path("temp_ocr_pdfs")
    output_dir = Path("translated_pdfs")
    os.makedirs(temp_dir, exist_ok=True)

    target_lang = "en"  # 目标语言: 'en'(英文), 'zh-CN'(简体中文)
    linux_font = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"

    pdf_files = list(input_dir.glob("*.pdf"))
    print(f"找到 {len(pdf_files)} 个 PDF 文件，开始处理...")

    for pdf_file in pdf_files:
        print(f"正在处理: {pdf_file.name}")
        temp_ocr_file = temp_dir / pdf_file.name
        processable_pdf = run_ocr_if_needed(pdf_file, temp_ocr_file)

        out_file = output_dir / f"{pdf_file.stem}_{target_lang}.pdf"
        translate_single_pdf(str(processable_pdf), str(out_file), target_lang, linux_font)
        print(f"完成: {out_file.name}")

if __name__ == "__main__":
    main()
