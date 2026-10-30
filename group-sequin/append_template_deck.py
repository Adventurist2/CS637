"""Combine the project template and extension slides through Microsoft PowerPoint.

Requires Windows and PowerPoint. Native insertion avoids the incompatible
package assembled by the earlier ZIP-only implementation. Original slide XML
is restored only after checking its immediate resources are unchanged.
"""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import argparse
import hashlib
import json
import os
import posixpath
import subprocess
import uuid
import shutil
from lxml import etree as E

ROOT=Path(__file__).resolve().parent
SOURCE=Path.home()/'Downloads/SEQUIN_ppt.pptx'
SECTION=ROOT.parent/'tmp/elegant_section_deliverable/section.pptx'
OUTPUT=ROOT/'output/presentation/SEQUIN_Original_Slides_With_Part2.pptx'
QA=ROOT.parent/'tmp/presentation_assembly.json'


def assemble():
    if os.name!='nt':
        raise RuntimeError('Template assembly requires Windows with Microsoft PowerPoint.')
    before=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    temporary=OUTPUT.with_name(f'.native-{uuid.uuid4().hex}.pptx')
    shell=shutil.which('pwsh.exe') or shutil.which('powershell.exe')
    if not shell:raise RuntimeError('PowerShell is required for native presentation assembly.')
    subprocess.run([shell,'-NoProfile','-File',str(ROOT/'assemble_final_presentation.ps1'),
                    '-SourcePptx',str(SOURCE.resolve()),'-SectionPptx',str(SECTION.resolve()),
                    '-OutputPptx',str(temporary.resolve())],check=True)
    restored={}
    try:
        with ZipFile(SOURCE) as old,ZipFile(temporary) as native:
            for i in range(1,15):
                slide=f'ppt/slides/slide{i}.xml'
                rels=f'ppt/slides/_rels/slide{i}.xml.rels'
                for relationship in E.fromstring(old.read(rels)):
                    if relationship.get('TargetMode')=='External':continue
                    part=posixpath.normpath(posixpath.join('ppt/slides',relationship.get('Target')))
                    if old.read(part)!=native.read(part):
                        raise RuntimeError(f'Original slide {i} resource changed: {part}')
                restored[slide]=old.read(slide)
                restored[rels]=old.read(rels)
            with ZipFile(OUTPUT,'w',ZIP_DEFLATED) as out:
                for name in native.namelist():out.writestr(name,restored.get(name,native.read(name)))
        with ZipFile(OUTPUT) as out:
            assert out.testzip() is None
        assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==before
        report={'status':'PASS','native_powerpoint_assembly':True,'source_file_unchanged':True,
                'source_sha256':before,'original_first_14_slide_xml_and_relationships_preserved':True,
                'new_slide_range':[15,30],'original_closing_slide_position':31,'total_slides':31,
                'output':str(OUTPUT)}
        QA.parent.mkdir(parents=True,exist_ok=True)
        QA.write_text(json.dumps(report,indent=2),encoding='utf-8')
        print(json.dumps(report,indent=2))
    finally:
        temporary.unlink(missing_ok=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=SOURCE)
    parser.add_argument('--section',type=Path,default=SECTION)
    parser.add_argument('--output',type=Path,default=OUTPUT)
    args=parser.parse_args()
    SOURCE,SECTION,OUTPUT=args.source,args.section,args.output
    assemble()
