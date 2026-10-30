"""Check release files and archives for private paths and conversational residue."""
from pathlib import Path
from zipfile import ZipFile, BadZipFile
import argparse
import io
import json
import os
import re

ROOT=Path(__file__).resolve().parents[1]
MACHINE_PATH=re.compile(r'(?i)\b[a-z]:[\\/]+(?:Users|Documents and Settings)[\\/]+|/(?:home|Users)/[^/\s]+/')
WORKFLOW_TEXT=re.compile(r'(?i)(?:supplied|your) screenshot|additional user instructions')
TEXT_SUFFIXES={'.json','.md','.txt','.py','.jl','.toml','.yaml','.yml','.csv','.html','.js','.mjs','.ps1','.xml','.rels','.log','.mps','.lp'}
ARCHIVE_SUFFIXES={'.zip','.pptx','.docx','.xlsx'}


def inspect_bytes(label,data,findings,counts,depth=0):
    suffix=Path(label.split('!')[-1]).suffix.lower()
    if suffix in ARCHIVE_SUFFIXES and depth<4:
        with ZipFile(io.BytesIO(data)) as package:
            if package.testzip() is not None:raise BadZipFile('Archive CRC check failed')
            for name in package.namelist():
                if name.endswith('/'):continue
                counts['archive_members_checked']+=1
                inspect_bytes(label+'!'+name,package.read(name),findings,counts,depth+1)
    elif suffix in TEXT_SUFFIXES:
        try:text=data.decode('utf-8-sig')
        except UnicodeDecodeError:return
        for number,line in enumerate(text.splitlines(),1):
            if MACHINE_PATH.search(line):
                findings.append({'file':label,'line':number,'issue':'machine_specific_path'})
            if suffix=='.md' and WORKFLOW_TEXT.search(line):
                findings.append({'file':label,'line':number,'issue':'conversational_document_text'})


def audit(root):
    findings=[]
    counts={'files_checked':0,'archive_members_checked':0}
    for folder,dirs,files in os.walk(root):
        dirs[:]=[d for d in dirs if not d.startswith('.') and d not in {'tmp','__pycache__'}]
        for name in sorted(files):
            path=Path(folder)/name
            if path.suffix.lower() not in TEXT_SUFFIXES|ARCHIVE_SUFFIXES:continue
            counts['files_checked']+=1
            inspect_bytes(path.relative_to(root).as_posix(),path.read_bytes(),findings,counts)
    return {'status':'passed' if not findings else 'failed',**counts,'finding_count':len(findings),'findings':findings}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=ROOT)
    args=parser.parse_args()
    report=audit(args.root.resolve())
    print(json.dumps(report,indent=2))
    return int(bool(report['finding_count']))


if __name__=='__main__':raise SystemExit(main())
