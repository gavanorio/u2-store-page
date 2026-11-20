import re,json,collections
import xml.etree.ElementTree as ET
def rules(path):
    s=open(path,encoding='utf-8',errors='replace').read()
    s=re.sub(r'<\?xml[^>]*\?>','',s)
    root=ET.fromstring('<R>'+s+'</R>')
    out=[]
    def walk(e,node):
        if e.tag=='Component':
            node=e.get('Node') or node
            nid=None; code=None
            for ch in e:
                if ch.tag=='UseTemplate' and 'Visibility' in (ch.get('Name') or ''):
                    c=ch.find('VISIBILITY_CODE'); n=ch.find('NODE_ID')
                    if c is not None: out.append(((n.text if n is not None else None) or e.get('Node') or e.get('ID'), c.text.strip(), e.get('ID')))
                if ch.tag=='Visibility':
                    c=ch.find('Parameter/Code')
                    if c is not None: out.append((e.get('Node') or e.get('ID'), c.text.strip(), e.get('ID')))
        for ch in e: walk(ch,node)
    walk(root,None)
    return out
if __name__=='__main__':
    import sys
    for f in sys.argv[1:]:
        r=rules(f); print('##',f,len(r))
        by=collections.defaultdict(list)
        for n,c,i in r: by[c].append(n)
        for c,ns in by.items(): print('  CODE:',c[:300],'\n     ->',len(ns),ns[:60])
