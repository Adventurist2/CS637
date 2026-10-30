import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import io
from zipfile import ZipFile

from scripts.normalize_result_references import normalize_file,portable_reference
from scripts.audit_public_release import inspect_bytes


def test_metadata_cleanup_preserves_numeric_bytes_and_resolves_target(tmp_path):
    target=tmp_path/'output/models/round1.mps'
    target.parent.mkdir(parents=True)
    target.write_text('model fixture',encoding='utf-8')
    record=tmp_path/'output/models/round1_solution.json'
    old=json.dumps({'model':str(target.resolve()),'objective':0.12345678901234567,
                    'values':{'v1':12345678901234567890,'v2':-0.0},'status':'error',
                    'error':'recorded solver failure'},indent=2)
    record.write_bytes(old.replace('\n','\r\n').encode())
    numeric_tail=record.read_bytes().split(b'"objective"',1)[1]
    result=normalize_file(record,tmp_path)
    assert result['references_changed']==1
    payload=json.loads(record.read_text())
    assert payload['model']=='output/models/round1.mps'
    assert record.read_bytes().split(b'"objective"',1)[1]==numeric_tail
    assert normalize_file(record,tmp_path)['references_changed']==0


def test_relative_references_and_model_descriptions_are_unchanged(tmp_path):
    for value in ['output/models/round1.mps','Original DC model',None]:
        assert portable_reference(value,tmp_path)==value


def test_solver_writer_emits_portable_reference_even_when_solve_fails(tmp_path,monkeypatch):
    class SolverError(Exception):pass
    def unavailable(**kwargs):raise SolverError('license unavailable')
    fake=SimpleNamespace(gurobi=SimpleNamespace(version=lambda:(12,0,3)),Env=unavailable,GurobiError=SolverError)
    monkeypatch.setitem(sys.modules,'gurobipy',fake)
    source=Path(__file__).resolve().parents[1]/'scripts/solve_original_mps.py'
    spec=importlib.util.spec_from_file_location('reference_writer_test',source)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module,'ROOT',tmp_path)
    model=tmp_path/'output/models/example.mps'
    result=tmp_path/'output/models/example_solution.json'
    monkeypatch.setattr(sys,'argv',[str(source),str(model),str(result)])
    assert module.main()==1
    payload=json.loads(result.read_text())
    assert payload['model']=='output/models/example.mps'
    assert payload['status']=='error' and payload['error']=='license unavailable'
    assert str(tmp_path) not in result.read_text()


def test_release_audit_checks_json_inside_archives():
    stream=io.BytesIO()
    with ZipFile(stream,'w') as archive:
        archive.writestr('results.json',json.dumps({'model':str(Path.home()/'private/model.mps')}))
    findings=[]
    counts={'archive_members_checked':0}
    inspect_bytes('delivery.zip',stream.getvalue(),findings,counts)
    assert findings==[{'file':'delivery.zip!results.json','line':1,'issue':'machine_specific_path'}]
