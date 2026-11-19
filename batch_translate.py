import fitz  # PyMuPDF
from deep_translator import GoogleTranslator
import os
import subprocess
from pathlib import Path

def force_ocr_and_rebuild(input_path, output_path, target_lang="en", font_path=None):
    temp_ocr = Path("temp_ocr_work.pdf")
    
    # 1. 强制执行带图像清理的 OCR，提取文字坐标
    cmd = [
        "ocrmypdf",
        "-l", "chi_sim+eng",
        "--force-ocr",
        str(input_path),
        str(temp_ocr)
    ]
    subprocess.run(cmd, check=True)

    src_doc = fitz.open(str(temp_ocr))
    out_doc = fitz.open()  # 创建全新的干净空白 PDF，彻底丢弃 13.5MB 的中文扫描底图
    translator = GoogleTranslator(source='auto', target=target_lang)

    use_custom_font = bool(font_path and os.path.exists(font_path))
    font_name = "custom_font" if use_custom_font else "helv"

    for page_num, src_page in enumerate(src_doc):
        # 在新 PDF 中创建相同尺寸的白纸页面
        new_page = out_doc.new_page(width=src_page.rect.width, height=src_page.rect.height)
        if use_custom_font:
            new_page.insert_font(fontname=font_name, fontfile=font_path)

        blocks = src_page.get_text("blocks")
        print(f"  第 {page_num + 1} 页识别到 {len(blocks)} 个文本块...")

        for b in blocks:
            if b[6] == 0:
                rect = fitz.Rect(b[0], b[1], b[2], b[3])
                raw_text = b[4].strip()
                if not raw_text or raw_text.isdigit():
                    continue
                clean_text = raw_text.replace("\n", " ")[:4500]
                try:
                    translated_text = translator.translate(clean_text)
                    print(f"    [译] {clean_text[:15]}... -> {translated_text[:20]}...")
                except Exception as e:
                    print(f"    [跳过] {e}")
                    translated_text = clean_text

                # 将英文写入新白纸页面的对应坐标
                font_size = 10
                while font_size >= 6:
                    rc = new_page.insert_textbox(
                        rect,
                        translated_text,
                        fontsize=font_size,
                        fontname=font_name,
                        color=(0, 0, 0),
                        align=fitz.TEXT_ALIGN_LEFT
                    )
                    if rc >= 0:
                        break
                    font_size -= 1

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    out_doc.save(output_path, garbage=4, deflate=True)
    src_doc.close()
    out_doc.close()
    if temp_ocr.exists():
        temp_ocr.unlink()

def main():
    input_dir = Path("input_pdfs")
    output_dir = Path("translated_pdfs")
    target_lang = "en"
    linux_font = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"

    for pdf_file in input_dir.glob("*.pdf"):
        print(f"开始重构翻译: {pdf_file.name}")
        out_file = output_dir / f"{pdf_file.stem}_{target_lang}.pdf"
        force_ocr_and_rebuild(str(pdf_file), str(out_file), target_lang, linux_font)
        print(f"完成输出: {out_file.name}")

if __name__ == "__main__":
    main()
