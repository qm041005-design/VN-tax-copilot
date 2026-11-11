"""Export structured research drafts to DOCX bytes without writing user paths."""
from io import BytesIO
from urllib.parse import urlparse

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt
from docx.opc.constants import RELATIONSHIP_TYPE

from ai_engine.synthesis.prompt_templates import SECTION_LABELS


def _text(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('Expected nonempty text')
    if any(ord(c) < 32 and c not in '\n\r\t' for c in value):
        raise ValueError('XML control characters are not allowed')
    return value


def export_research_docx(result, sources, *, title='Báo cáo nghiên cứu thuế', matter_id=''):
    """Return a draft DOCX. sources maps passage_id to trusted citation metadata.

    Required source fields: document_number, article, source_url. Optional:
    clause, point, version_note. Authorization and legal support verification
    belong to upstream services; this function verifies structural references.
    It never accepts an LLM-provided approval status.
    """
    if not isinstance(result, dict) or result.get('status') not in {'draft', 'clarify', 'abstain'}:
        raise ValueError('Unsupported research status')
    sections = result.get('sections')
    if not isinstance(sections, dict) or set(sections) != set(SECTION_LABELS):
        raise ValueError('Exactly six research sections are required')
    if not isinstance(sources, dict):
        raise ValueError('sources must map passage IDs to metadata')
    for field in ('warnings', 'clarification_questions'):
        if not isinstance(result.get(field), list):
            raise ValueError(f'{field} must be a list')
        for value in result[field]:
            _text(value)
    if result['status'] == 'clarify' and not result['clarification_questions']:
        raise ValueError('Clarification questions are required')
    used = []
    for key, items in sections.items():
        if not isinstance(items, list):
            raise ValueError('Section must contain a list')
        if result['status'] == 'draft' and key in ('authority', 'analysis') and not items:
            raise ValueError('Draft requires authority and analysis')
        for item in items:
            if not isinstance(item, dict):
                raise ValueError('Section item must be an object')
            _text(item.get('text'))
            refs = item.get('citation_ids')
            if not isinstance(refs, list) or any(not isinstance(r, str) for r in refs):
                raise ValueError('citation_ids must be a list of strings')
            if result['status'] == 'draft' and key in ('authority', 'analysis') and not refs:
                raise ValueError('Authority and analysis items require citations')
            for ref in refs:
                if ref not in sources:
                    raise ValueError(f'Unknown citation: {ref}')
                if ref not in used:
                    used.append(ref)
    for ref in used:
        source = sources[ref]
        if not isinstance(source, dict):
            raise ValueError('Invalid source metadata')
        for key in ('document_number', 'article', 'source_url'):
            _text(source.get(key))
        url = urlparse(source['source_url'])
        if url.scheme not in ('https', 'http') or not url.hostname or url.username or url.password:
            raise ValueError('Citation requires an HTTP(S) source URL')
        for key in ('clause', 'point', 'version_note'):
            if source.get(key):
                _text(source[key])
    doc = Document()
    section = doc.sections[0]
    section.page_width, section.page_height = Cm(21), Cm(29.7)
    section.top_margin = section.bottom_margin = Cm(2)
    section.left_margin = section.right_margin = Cm(2.2)
    normal = doc.styles['Normal']
    normal.font.name, normal.font.size = 'Arial', Pt(11)
    normal.paragraph_format.space_after = Pt(6)
    section.header.paragraphs[0].text = 'THTax | Vietnam Tax Research Copilot'
    section.footer.paragraphs[0].text = 'Dự thảo nghiên cứu - Chờ chuyên gia thẩm định'
    doc.add_heading(_text(title), 0)
    doc.add_paragraph('DỰ THẢO - CHƯA ĐƯỢC CHUYÊN GIA PHÊ DUYỆT')
    statuses = {'draft': 'Bản nghiên cứu', 'clarify': 'Cần bổ sung thông tin', 'abstain': 'Chưa đủ căn cứ kết luận'}
    doc.add_paragraph(statuses[result['status']])
    if matter_id:
        doc.add_paragraph('Hồ sơ: ' + _text(matter_id))
    numbers = {ref: i + 1 for i, ref in enumerate(used)}
    for key, label in SECTION_LABELS.items():
        doc.add_heading(label, 1)
        for item in sections[key]:
            suffix = ' '.join(f'[{numbers[r]}]' for r in item['citation_ids'])
            doc.add_paragraph(item['text'] + (' ' + suffix if suffix else ''))
        if not sections[key]:
            doc.add_paragraph('Chưa có nội dung.')
    for key, label in [('clarification_questions', 'Thông tin cần làm rõ'), ('warnings', 'Lưu ý nghiên cứu')]:
        if result[key]:
            doc.add_heading(label, 1)
            for value in result[key]:
                doc.add_paragraph(value, style='List Bullet')
    doc.add_heading('Danh mục nguồn trích dẫn', 1)
    for ref in used:
        s = sources[ref]
        p = doc.add_paragraph(f'[{numbers[ref]}] ' + ', '.join(s[k] for k in ('document_number', 'article', 'clause', 'point') if s.get(k)))
        doc.add_paragraph('Mã đoạn nguồn: ' + ref)
        if s.get('version_note'):
            doc.add_paragraph(s['version_note'])
        p = doc.add_paragraph()
        link = OxmlElement('w:hyperlink')
        link.set(qn('r:id'), p.part.relate_to(s['source_url'], RELATIONSHIP_TYPE.HYPERLINK, is_external=True))
        run = OxmlElement('w:r')
        text = OxmlElement('w:t')
        text.text = s['source_url']
        run.append(text)
        link.append(run)
        p._p.append(link)
    stream = BytesIO()
    doc.save(stream)
    return stream.getvalue()
