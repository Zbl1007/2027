#!/usr/bin/env python3
"""Restore only verified Git checkout newline damage; retain byte-for-byte backups."""
import hashlib
import json
from pathlib import Path
import subprocess
from datetime import datetime, timezone
from coupon_common import ROOT, write_json


def main():
    sha = lambda b: hashlib.sha256(b).hexdigest()
    expected = {x['snapshot']:x['sha256'] for x in json.loads((ROOT/'references/import_manifest.json').read_text(encoding='utf-8'))['files']}
    for s in json.loads((ROOT/'sources/catalog.json').read_text(encoding='utf-8'))['sources']:
        if s.get('local_snapshot'):
            expected[s['local_snapshot']]=s['sha256']
    paths=set(expected)
    paths.update(subprocess.check_output(['git','ls-files','references','cases/minimal_coupons/definition.json',
                 'outputs/minimal_coupon_v1/manifest.json','outputs/minimal_coupon_v1/h0_z16'],cwd=ROOT,text=True).splitlines())
    backup=ROOT/'outputs/comsol_h0/byte_recovery'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    pending=[]
    for name in sorted(paths):
        p=ROOT/name
        old=p.read_bytes()
        original=subprocess.check_output(['git','show','HEAD:'+name],cwd=ROOT)
        if name in expected and sha(original)!=expected[name]:
            raise ValueError('Git blob does not match registered evidence: '+name)
        if old==original:
            continue
        if old.replace(b'\r\n',b'\n')!=original.replace(b'\r\n',b'\n'):
            raise ValueError('Substantive local changes; refusing restoration: '+name)
        pending.append((name,old,original))
    report=[]
    for name,old,original in pending:
        dest=backup/name
        dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_bytes(old)
        (ROOT/name).write_bytes(original)
        report.append({'path':name,'before_sha256':sha(old),'restored_sha256':sha(original),'source':'git HEAD blob',
                       'registered_hash_verified':name in expected})
    write_json(backup/'restoration.json',{'reason':'Windows core.autocrlf checkout conversion breaks byte-addressed evidence',
                                       'count':len(report),'files':report})
    print(json.dumps({'restored_files':len(report),'backups':str(backup)}))


if __name__=='__main__':
    main()
