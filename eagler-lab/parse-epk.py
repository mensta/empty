import struct,collections,sys,json,zlib
b=open(sys.argv[1],'rb').read()
p=4; l=b[p]; p+=1+l; vl=struct.unpack('>I',b[p:p+4])[0]; p+=4+vl
files=[]; bad=0
while p<len(b) and b[p:p+5]==b'>FILE':
    p+=5; nl=b[p]; name=b[p+1:p+1+nl].decode('utf-8','replace'); q=p+1+nl
    ln=struct.unpack('>I',b[q:q+4])[0]
    crc=struct.unpack('>I',b[q+4:q+8])[0]; data=b[q+8:q+4+ln-1]
    if (zlib.crc32(data)&0xffffffff)!=crc: bad+=1
    assert b[q+4+ln-1:q+4+ln]==b':'
    files.append((name,len(data),q+8)); p=q+4+ln
print('tail',b[p:p+16],'files',len(files),'crc mismatches',bad)
json.dump(files,open(sys.argv[2],'w'))
c=collections.Counter(); sz=collections.Counter()
for n,ln,_ in files:
    parts=n.split('/'); top='/'.join(parts[:3]) if n.startswith('assets/') else parts[0]
    c[top]+=1; sz[top]+=ln
print('--- by top folder (MB, count)')
for k,v in sorted(sz.items(),key=lambda x:-x[1])[:22]: print(f'{v/1e6:7.2f} {c[k]:5d}  {k}')
ext=collections.Counter(n.rsplit('.',1)[-1] for n,_,_ in files if '.' in n)
print('ext',dict(ext.most_common(14)))
print('ogg',sum(1 for n,_,_ in files if n.endswith('.ogg')))
sh=[n for n,_,_ in files if n.endswith(('.fsh','.vsh','.glsl'))]
print('shader files',len(sh),sh[:14])
