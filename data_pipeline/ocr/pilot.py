"""Collect official PDFs and extract page-mapped text with Vietnamese OCR fallback.

Run from repo root: python -m data_pipeline.ocr.pilot --max-pages 1
Omit --max-pages to process every page. No cloud/model API is called.
"""
import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse
import unicodedata

import pymupdf as fitz
import pytesseract
import requests
from bs4 import BeautifulSoup
from PIL import Image

SOURCES = [
    ('TT219_2013', '219/2013/TT-BTC', '172570'),
    ('TT111_2013', '111/2013/TT-BTC', '169566'),
    ('TT96_2015', '96/2015/TT-BTC', '180650'),
    ('TT26_2015', '26/2015/TT-BTC', '179270'),
    ('ND123_2020', '123/2020/NĐ-CP', '201365'),
    ('TT78_2014', '78/2014/TT-BTC', '174750'),
    ('LUAT48_2024', '48/2024/QH15', '212476'),
    ('LUAT67_2025', '67/2025/QH15', '214607'),
    ('LUAT109_2025', '109/2025/QH15', '216495'),
    ('ND70_2025', '70/2025/NĐ-CP', '213179'),
]


def official(url):
    host = urlparse(url).hostname or ''
    return urlparse(url).scheme == 'https' and (host == 'chinhphu.vn' or host.endswith('.chinhphu.vn'))


def fetch(session, url):
    if not official(url):
        raise ValueError('Only official HTTPS sources are permitted')
    response = session.get(url, timeout=90)
    response.raise_for_status()
    if not official(response.url):
        raise ValueError('Redirected outside approved source domains')
    return response


def pdf_links(html, url):
    soup = BeautifulSoup(html, 'html.parser')
    return list(dict.fromkeys(urljoin(url, a['href']) for a in soup.select('a[href]')
                if '.pdf' in a['href'].lower() or 'tai-ve-van-ban' in a['href'].lower()))


def extract(pdf, source_id, max_pages=None, force_ocr=False):
    pages = []
    with fitz.open(pdf) as doc:
        total = len(doc)
        for index in range(min(total, max_pages or total)):
            page = doc[index]
            native = page.get_text(sort=True).strip()
            # Signed scans can contain a digital-signature text layer only.
            image_area = sum(fitz.Rect(info['bbox']).get_area() for info in page.get_image_info())
            scan_with_overlay = image_area > page.rect.get_area() * 0.5 and len(native) < 1000
            use_ocr = force_ocr or scan_with_overlay or len(native) < 80 or '\ufffd' in native
            record = dict(source_id=source_id, original_page=index + 1,
                          extraction_method='tesseract_vie_eng' if use_ocr else 'native_pdf',
                          quality_status='pending_human_review')
            try:
                if use_ocr:
                    pix = page.get_pixmap(dpi=250, alpha=False)
                    img = Image.frombytes('RGB', (pix.width, pix.height), pix.samples)
                    data = pytesseract.image_to_data(img, lang='vie+eng',
                        config='--psm 3', output_type=pytesseract.Output.DICT, timeout=150)
                    # Preserve OCR line breaks, never claim table structure is reconstructed.
                    lines = {}
                    confs = []
                    for i, word in enumerate(data['text']):
                        if word.strip():
                            key = (data['block_num'][i], data['par_num'][i], data['line_num'][i])
                            lines.setdefault(key, []).append(word)
                            if float(data['conf'][i]) >= 0:
                                confs.append(float(data['conf'][i]))
                    text = '\n'.join(' '.join(words) for words in lines.values())
                    record['mean_ocr_confidence'] = sum(confs) / len(confs) if confs else None
                else:
                    text = native
                record['text'] = unicodedata.normalize('NFC', text)
                if not text.strip():
                    record['quality_status'] = 'quarantined_empty'
                elif use_ocr and (record['mean_ocr_confidence'] or 0) < 70:
                    record['quality_status'] = 'quarantined_low_confidence'
            except Exception as exc:
                record.update(text='', quality_status='quarantined_error', error=str(exc))
            pages.append(record)
    return total, pages


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--output', type=Path, default=Path('data_pipeline/local_data'))
    parser.add_argument('--max-pages', type=int)
    parser.add_argument('--force-ocr', action='store_true')
    args = parser.parse_args()
    if args.max_pages is not None and args.max_pages < 1:
        parser.error('--max-pages must be positive')
    pytesseract.pytesseract.tesseract_cmd = os.getenv('TESSERACT_CMD', 'tesseract')
    args.output.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers['User-Agent'] = 'VN-tax-copilot research pilot/0.1'
    previous_file = args.output / 'manifest.json'
    previous = {r['source_id']: r for r in json.loads(previous_file.read_text(encoding='utf-8'))} if previous_file.exists() else {}
    manifest = []
    for sid, number, location in SOURCES:
        url = location if location.startswith('https') else f'https://vanban.chinhphu.vn/?pageid=27160&docid={location}'
        record = dict(source_id=sid, legal_identifier=number, official_url=url,
                      retrieved_at=datetime.now(timezone.utc).isoformat(),
                      rights_status='pending_review_before_enterprise_ingestion',
                      applicability_status='not_verified', status='failed')
        try:
            pdf = args.output / f'{sid}.pdf'
            if pdf.exists() and sid in previous:
                for key in ('download_url', 'retrieved_at'):
                    if key in previous[sid]:
                        record[key] = previous[sid][key]
            if not pdf.exists():
                page = fetch(session, url)
                candidates = pdf_links(page.text, url)
                for link in candidates:
                    try:
                        response = fetch(session, link)
                        if response.content.startswith(b'%PDF-'):
                            pdf.write_bytes(response.content)
                            record['download_url'] = response.url
                            break
                    except requests.RequestException:
                        continue
                if not pdf.exists():
                    raise ValueError('No accessible PDF attachment found')
            record['sha256'] = hashlib.sha256(pdf.read_bytes()).hexdigest()
            total, pages = extract(pdf, sid, args.max_pages, args.force_ocr)
            out = args.output / f'{sid}.pages.json'
            out.write_text(json.dumps(pages, ensure_ascii=False, indent=2), encoding='utf-8')
            record.update(status='collected', total_pages=total, processed_pages=len(pages),
                          full_document_processed=len(pages) == total,
                          ocr_pages=sum(p['extraction_method'] == 'tesseract_vie_eng' for p in pages),
                          quarantined_pages=sum(p['quality_status'].startswith('quarantined') for p in pages),
                          pdf_path=str(pdf), pages_path=str(out))
        except Exception as exc:
            record['error'] = str(exc)
        manifest.append(record)
        (args.output / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f"{sid}: {record['status']}", flush=True)
    return 0 if all(r['status'] == 'collected' and not r['quarantined_pages'] for r in manifest) else 1


if __name__ == '__main__':
    raise SystemExit(main())
