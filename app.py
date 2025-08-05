import os
from flask import Flask, request, send_from_directory, jsonify
from uuid import uuid4
import asyncio
from playwright.async_api import async_playwright

app = Flask(__name__, static_folder='web', static_url_path='')
PDF_DIR = 'pdfs'
os.makedirs(PDF_DIR, exist_ok=True)

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/export_pdf', methods=['POST'])
def export_pdf():
    data = request.get_json()
    html_content = data.get('html', '')
    scale = float(data.get('scale', 1))
    width = int(data.get('width', 1200))
    if not html_content:
        return jsonify({'error': 'No HTML provided'}), 400
    pdf_name = f"{uuid4().hex}.pdf"
    pdf_path = os.path.join(PDF_DIR, pdf_name)
    try:
        asyncio.run(html_to_pdf(html_content, pdf_path, scale, width))
        cleanup_pdfs_folder(PDF_DIR, keep_count=10)
        url = f"/download_pdf/{pdf_name}"
        return jsonify({'url': url})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download_pdf/<filename>')
def download_pdf(filename):
    return send_from_directory(PDF_DIR, filename, as_attachment=True)

async def html_to_pdf(html, output_path, scale=1, width=1200):
    # 自动注入防分页 CSS，确保内容不被切断
    injected_css = '''<style>\nhtml, body { width: 100%; }\n* { box-sizing: border-box; }\n@media print {\n  html, body { width: 100%; }\n  body { margin: 0; }\n  .no-break, * { page-break-before: auto !important; page-break-after: auto !important; page-break-inside: avoid !important; }\n}\n</style>'''
    if '<head>' in html:
        html = html.replace('<head>', f'<head>{injected_css}')
    else:
        html = injected_css + html
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.set_content(html)
        await page.pdf(path=output_path, format='A4', print_background=True, scale=scale, width=f'{width}px', height='auto')
        await browser.close()

def cleanup_pdfs_folder(folder_path, keep_count=10):
    pdf_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.pdf')]
    pdf_files_full = [os.path.join(folder_path, f) for f in pdf_files]
    pdf_files_full.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    for old_file in pdf_files_full[keep_count:]:
        try:
            os.remove(old_file)
        except Exception:
            pass

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9876, debug=True)
