import io
from pypdf import PdfReader

def parse_txt(content: bytes) -> str:
    """解析 TXT 文件"""
    try:
        return content.decode('utf-8')
    except UnicodeDecodeError:
        # 尝试其他编码
        return content.decode('gbk', errors='ignore')

def parse_pdf(content: bytes) -> str:
    """解析 PDF 文件"""
    pdf_file = io.BytesIO(content)
    reader = PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text

def parse_markdown(content: bytes) -> str:
    """解析 Markdown 文件（与 TXT 类似）"""
    return parse_txt(content)

def parse_file_content(content: bytes, file_ext: str) -> str:
    """根据文件扩展名分发解析逻辑"""
    if file_ext == '.pdf':
        return parse_pdf(content)
    elif file_ext in ['.md', '.markdown']:
        return parse_markdown(content)
    else:  # 默认为 txt
        return parse_txt(content)
