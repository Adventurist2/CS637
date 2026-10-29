"""Append an Artifact Tool section without round-tripping uploaded slides.

Every original slide, relationship, theme, layout and image is copied byte for
byte. Only presentation navigation, content types and slide-count metadata
change. New resources live under ppt/part2/ to prevent name collisions.
"""
from pathlib import Path,PurePosixPath
from zipfile import ZipFile,ZIP_DEFLATED
import copy
import hashlib
import json
import posixpath
from lxml import etree as E

ROOT=Path(__file__).resolve().parent
SOURCE=Path(r'C:\Users\chand.CHANDAN\Downloads\SEQUIN_ppt.pptx')
SECTION=ROOT.parent/'tmp'/'template_part2_only.pptx'
OUTPUT=ROOT/'output'/'presentation'/'SEQUIN_Original_Slides_With_Part2.pptx'
QA=ROOT.parent/'tmp'/'template_preservation_check.json'
P='http://schemas.openxmlformats.org/presentationml/2006/main'
R='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
REL='http://schemas.openxmlformats.org/package/2006/relationships'
CT='http://schemas.openxmlformats.org/package/2006/content-types'
NS={'p':P,'r':R,'rel':REL,'ct':CT}


def xml(data):return E.fromstring(data)
def serialized(root):return E.tostring(root,xml_declaration=True,encoding='UTF-8',standalone=True)
def target(owner,path):return posixpath.normpath(posixpath.join(posixpath.dirname(owner),path)) if not path.startswith('/') else path[1:]
def owner_of_rels(path):
    return posixpath.join(posixpath.dirname(posixpath.dirname(path)),posixpath.basename(path)[:-5])


def assemble():
    source_hash=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    with ZipFile(SOURCE) as old,ZipFile(SECTION) as new:
        base={n:old.read(n) for n in old.namelist()}
        incoming={n:new.read(n) for n in new.namelist()}
        mapping={n:'ppt/part2/'+n[4:] for n in incoming if n.startswith('ppt/') and n not in ('ppt/presentation.xml','ppt/_rels/presentation.xml.rels')}
        added={}
        for src,dst in mapping.items():
            data=incoming[src]
            if src.endswith('.rels'):
                tree=xml(data);owner=owner_of_rels(src);mapped_owner=mapping[owner]
                for rel in tree:
                    if rel.get('TargetMode')=='External':continue
                    resolved=target(owner,rel.get('Target'))
                    if resolved in mapping:
                        rel.set('Target',posixpath.relpath(mapping[resolved],posixpath.dirname(mapped_owner)))
                    else:raise ValueError(f'Unmapped section relation: {src} -> {resolved}')
                data=serialized(tree)
            added[dst]=data
        pres=xml(base['ppt/presentation.xml']);rels=xml(base['ppt/_rels/presentation.xml.rels'])
        newpres=xml(incoming['ppt/presentation.xml']);newrels=xml(incoming['ppt/_rels/presentation.xml.rels'])
        relmap={x.get('Id'):x for x in newrels}
        next_rel=max([int(x.get('Id')[3:]) for x in rels if x.get('Id','').startswith('rId') and x.get('Id')[3:].isdigit()]+[0])+1
        def add_relation(typ,part):
            nonlocal next_rel
            rid=f'rId{next_rel}';next_rel+=1
            E.SubElement(rels,f'{{{REL}}}Relationship',Id=rid,Type=typ,Target=posixpath.relpath(part,'ppt'))
            return rid
        masters=pres.find('p:sldMasterIdLst',NS)
        if masters is None:
            masters=E.Element(f'{{{P}}}sldMasterIdLst');pres.insert(0,masters)
        master_id=max([int(x.get('id')) for x in masters]+[2147483647])+1
        for node in newpres.findall('p:sldMasterIdLst/p:sldMasterId',NS):
            rel=relmap[node.get(f'{{{R}}}id')];part=mapping[target('ppt/presentation.xml',rel.get('Target'))]
            rid=add_relation(rel.get('Type'),part)
            E.SubElement(masters,f'{{{P}}}sldMasterId',id=str(master_id),attrib={f'{{{R}}}id':rid});master_id+=1
        # New notes keep their own notes-master dependencies. Register those
        # masters without editing any existing notes or their resources.
        newnotes=newpres.findall('p:notesMasterIdLst/p:notesMasterId',NS)
        if newnotes:
            notes=pres.find('p:notesMasterIdLst',NS)
            if notes is None:
                notes=E.Element(f'{{{P}}}notesMasterIdLst');pres.insert(list(pres).index(masters)+1,notes)
            for node in newnotes:
                rel=relmap[node.get(f'{{{R}}}id')];rid=add_relation(rel.get('Type'),mapping[target('ppt/presentation.xml',rel.get('Target'))])
                E.SubElement(notes,f'{{{P}}}notesMasterId',attrib={f'{{{R}}}id':rid})
        # Native table styles can be presentation-wide. Retain every existing
        # style definition and add only missing IDs if the section defines any.
        table_old=next((x for x in rels if x.get('Type','').endswith('/tableStyles')),None)
        table_new=next((x for x in newrels if x.get('Type','').endswith('/tableStyles')),None)
        allowed={'[Content_Types].xml','ppt/presentation.xml','ppt/_rels/presentation.xml.rels','docProps/app.xml'}
        if table_new is not None:
            newpart=target('ppt/presentation.xml',table_new.get('Target'))
            if table_old is None:add_relation(table_new.get('Type'),mapping[newpart])
            else:
                oldpart=target('ppt/presentation.xml',table_old.get('Target'));styles=xml(base[oldpart]);other=xml(incoming[newpart]);existing={x.get('styleId') for x in styles}
                missing=[x for x in other if x.get('styleId') not in existing]
                if missing:
                    for item in missing:styles.append(copy.deepcopy(item))
                    base[oldpart]=serialized(styles);allowed.add(oldpart)
        ids=pres.find('p:sldIdLst',NS);original_ids=list(ids)
        next_id=max(int(x.get('id')) for x in ids)+1
        new_nodes=[]
        for node in newpres.findall('p:sldIdLst/p:sldId',NS):
            rel=relmap[node.get(f'{{{R}}}id')];part=mapping[target('ppt/presentation.xml',rel.get('Target'))]
            rid=add_relation(rel.get('Type'),part)
            new_nodes.append(E.Element(f'{{{P}}}sldId',id=str(next_id),attrib={f'{{{R}}}id':rid}));next_id+=1
        # First fourteen uploaded slides remain at the same positions. Their
        # original closing slide follows the newly inserted second part.
        ids.remove(original_ids[-1])
        for item in new_nodes:ids.append(item)
        ids.append(original_ids[-1])
        base['ppt/presentation.xml']=serialized(pres);base['ppt/_rels/presentation.xml.rels']=serialized(rels)
        content=xml(base['[Content_Types].xml']);newcontent=xml(incoming['[Content_Types].xml'])
        defaults={x.get('Extension'):x.get('ContentType') for x in content if E.QName(x).localname=='Default'}
        for item in newcontent:
            if E.QName(item).localname=='Default':
                ext=item.get('Extension')
                if ext not in defaults:content.append(copy.deepcopy(item));defaults[ext]=item.get('ContentType')
            else:
                part=item.get('PartName','').lstrip('/')
                if part in mapping:
                    out=copy.deepcopy(item);out.set('PartName','/'+mapping[part]);content.append(out)
        base['[Content_Types].xml']=serialized(content)
        if 'docProps/app.xml' in base:
            app=xml(base['docProps/app.xml'])
            for el in app.iter():
                if E.QName(el).localname=='Slides':el.text=str(len(ids))
            base['docProps/app.xml']=serialized(app)
        OUTPUT.parent.mkdir(parents=True,exist_ok=True)
        with ZipFile(OUTPUT,'w',ZIP_DEFLATED) as out:
            for name in old.namelist():out.writestr(copy.copy(old.getinfo(name)),base[name])
            for name,data in added.items():out.writestr(name,data)
        with ZipFile(OUTPUT) as out:
            changed=[n for n in old.namelist() if old.read(n)!=out.read(n)]
            assert set(changed).issubset(allowed),changed
            original_slide_parts=[n for n in old.namelist() if n.startswith('ppt/slides/')]
            assert all(old.read(n)==out.read(n) for n in original_slide_parts)
            # Every internal relation must resolve, including notes, masters,
            # chart styles and embedded chart workbooks.
            entries=set(out.namelist());missing=[]
            for n in entries:
                if not n.endswith('.rels'):continue
                owner=owner_of_rels(n) if n!='_rels/.rels' else ''
                for rel in xml(out.read(n)):
                    if rel.get('TargetMode')=='External':continue
                    resolved=target(owner,rel.get('Target'))
                    if resolved not in entries:missing.append((n,resolved))
            assert not missing,missing
            assert out.testzip() is None
        assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==source_hash
        report={'status':'PASS','source_sha256':source_hash,'original_slide_count':len(original_ids),'new_slide_count':len(new_nodes),'total_slides':len(ids),
                'original_slide_parts_and_rels_identical':len(original_slide_parts),'changed_original_package_entries':changed,
                'all_other_original_entries_byte_identical':True,'source_file_unchanged':True,'new_slide_range':[15,14+len(new_nodes)],
                'original_closing_slide_position':len(ids),'all_internal_relationships_resolve':True,'output':str(OUTPUT)}
        QA.write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))


if __name__=='__main__':assemble()
