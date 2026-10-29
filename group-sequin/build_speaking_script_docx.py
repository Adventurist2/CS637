"""Build the named three-speaker script matching the final presentation."""
from pathlib import Path
import json
import re
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT=Path(__file__).resolve().parent
CONTENT=ROOT/'output/documents/presentation_script.json'
OUT=ROOT/'output/documents/SEQUIN_15_Minute_Three_Speaker_Script.docx'


def build():
    data=json.loads(CONTENT.read_text(encoding='utf-8'))
    parts=data['parts']
    assert [s['number'] for p in parts for s in p['slides']]==list(range(15,31))
    doc=Document()
    section=doc.sections[0]
    section.page_width=Inches(8.27)
    section.page_height=Inches(11.69)
    section.top_margin=section.bottom_margin=Inches(.65)
    section.left_margin=section.right_margin=Inches(.75)
    for name,size,bold in [('Normal',11.5,False),('Title',20,True),('Heading 1',16,True),('Heading 2',12,True)]:
        style=doc.styles[name]
        style.font.name='Arial'
        style.font.size=Pt(size)
        style.font.bold=bold
        style.font.color.rgb=RGBColor(0,0,0)
        style.paragraph_format.space_after=Pt(6)
        style.paragraph_format.line_spacing=1.08
        style.element.get_or_add_rPr().get_or_add_rFonts().set(qn('w:hAnsi'),'Arial')
        if name.startswith('Heading'):
            style.paragraph_format.keep_with_next=True
    doc.styles['Heading 1'].paragraph_format.space_before=Pt(8)
    doc.styles['Heading 2'].paragraph_format.space_before=Pt(9)
    doc.add_paragraph('SEQUIN Final Presentation Speaking Script',style='Title')
    doc.add_paragraph('This script matches slides 15 to 30 of SEQUIN_Final_Presentation.pptx and its matching PDF. Chandan presents the first five minutes, Saksham the next five and Tejas the final five.')
    p=doc.add_paragraph()
    p.add_run('Least technical role  ').bold=True
    p.add_run('Tejas keeps the verification, demonstration, conclusions and future-work section.')
    doc.add_paragraph('Read the main paragraphs aloud. The italic visual cues are stage directions. Pause while pointing to graphs and rehearse once with a timer to keep each part near five minutes.')
    split_at=[2,2,3]
    for i,part in enumerate(parts):
        if i:doc.add_page_break()
        doc.add_paragraph(part['title'],style='Heading 1')
        doc.add_paragraph(part['meta'])
        for j,slide in enumerate(part['slides']):
            if j==split_at[i]:
                doc.add_page_break()
                doc.add_paragraph(part['title']+' Continued',style='Heading 1')
                doc.add_paragraph(part['meta'])
            doc.add_paragraph(f"Slide {slide['number']} {slide['heading']}",style='Heading 2')
            cue=doc.add_paragraph()
            cue.paragraph_format.keep_with_next=True
            run=cue.add_run('Visual cue  '+slide['cue'])
            run.italic=True
            run.font.size=Pt(10.5)
            for paragraph in slide['paragraphs']:
                doc.add_paragraph(paragraph)
    p=doc.add_paragraph('Move to the original closing slide 31. The presentation is complete.')
    p.runs[0].italic=True
    p.runs[0].font.size=Pt(10.5)
    footer=section.footer.paragraphs[0]
    footer.alignment=2
    run=footer.add_run()
    run.font.size=Pt(9)
    field=OxmlElement('w:fldSimple')
    field.set(qn('w:instr'),'PAGE')
    run._r.addnext(field)
    doc.core_properties.title='SEQUIN Final Presentation Speaking Script'
    doc.core_properties.subject='Chandan Saksham and Tejas speaking script for final slides 15 to 30'
    doc.core_properties.author=''
    for element in (doc.element,doc.styles.element):
        for border in list(element.xpath('.//w:pBdr')):
            border.getparent().remove(border)
    OUT.parent.mkdir(parents=True,exist_ok=True)
    doc.save(OUT)
    counts=[sum(len(re.findall(r'\b[\w]+\b',p)) for s in part['slides'] for p in s['paragraphs']) for part in parts]
    print(OUT)
    print('Spoken words by presenter:',counts)


if __name__=='__main__':
    build()
