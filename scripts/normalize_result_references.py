"""Replace machine-specific artifact references without changing experiment data."""
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath, PureWindowsPath
import hashlib
import json

ROOT=Path(__file__).resolve().parents[1]


def portable_reference(value, root=ROOT):
    if not isinstance(value,str):
        return value
    path=PureWindowsPath(value) if PureWindowsPath(value).is_absolute() else PurePosixPath(value)
    if not path.is_absolute():
        return value
    # Only replace references whose repository-relative target actually exists.
    for index,part in enumerate(path.parts):
        if part not in {'output','reproduction'}:
            continue
        relative=PurePosixPath(*path.parts[index:]).as_posix()
        target=(root/relative).resolve()
        if target.is_relative_to(root.resolve()) and target.is_file():
            return relative
    raise ValueError('Absolute artifact reference has no matching project file')


def normalize_file(path, root=ROOT):
    raw=path.read_bytes()
    text=raw.decode('utf-8')
    before=json.loads(text)
    expected=deepcopy(before)
    replacements=[]

    def visit(item):
        if isinstance(item,dict):
            for key,value in item.items():
                if key in {'model','plan'} and isinstance(value,str):
                    normalized=portable_reference(value,root)
                    if normalized!=value:
                        replacements.append((value,normalized))
                        item[key]=normalized
                else:
                    visit(value)
        elif isinstance(item,list):
            for value in item:visit(value)

    visit(expected)
    for old,new in replacements:
        old_token=json.dumps(old)
        if old_token not in text:
            raise ValueError('Cannot locate the original JSON string token')
        text=text.replace(old_token,json.dumps(new))
    assert json.loads(text)==expected
    if replacements:
        path.write_bytes(text.encode('utf-8'))
    return {'path':path.relative_to(root).as_posix(),'references_changed':len(replacements),
            'before_sha256':hashlib.sha256(raw).hexdigest(),
            'after_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}


def main():
    changes=[]
    for path in sorted((ROOT/'output').rglob('*.json')):
        change=normalize_file(path)
        if change['references_changed']:changes.append(change)
    report={'created_utc':datetime.now(timezone.utc).isoformat(),
            'scope':'Artifact-reference metadata only; no experiment reruns or changed numerical results',
            'reference_base':'project root','files_changed':len(changes),
            'references_changed':sum(c['references_changed'] for c in changes),
            'other_json_values_unchanged':True,'changes':changes}
    output=ROOT/'output/reproduction/reference_metadata_cleanup.json'
    if changes:output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({key:value for key,value in report.items() if key!='changes'},indent=2))


if __name__=='__main__':main()
