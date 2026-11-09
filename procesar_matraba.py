#!/usr/bin/env python3
"""Procesador de microdatos diarios MATRABA DGT. No publica datos personales."""
import argparse,csv,hashlib,json,re
from collections import Counter
from datetime import date,datetime
from pathlib import Path

START=date(2026,9,1)
MISSING='Dato no disponible en DGT'
WIDTHS=[8,1,8,30,22,1,21,2,1,5,6,6,6,3,2,2,2,2,24,2,2,1,8,5,8,1,1,9,3,5,30,7,3,5,1,1,1,1,1,1,11,25,25,35,70,6,6,4,4,3,8,4,4,4,6,30,50,35,25,35,4,4,4,1,25,1,4,25,8]
assert len(WIDTHS)==69 and sum(WIDTHS)==714

# Catálogo COD_TIPO MATRABA: motocicletas, motocarros/cuadriciclos
# incluidos en el ámbito acordado y ciclomotores. Se conserva cada código.
TYPES={
 '50':'Motocicleta de 2 ruedas sin sidecar',
 '51':'Motocicleta con sidecar',
 '52':'Motocarro',
 '53':'Automóvil de 3 ruedas',
 '54':'Cuadriciclo pesado',
 '90':'Ciclomotor de 2 ruedas',
 '91':'Ciclomotor de 3 ruedas',
 '92':'Cuadriciclo ligero',
}
TARGET_TYPE_CODES=frozenset(TYPES)

OPS={
 '1':'Matriculación ordinaria y de ciclomotores',
 '2':'Transferencia',
 '3':'Baja definitiva',
 '4':'Baja definitiva por Plan Renove',
 '5':'Rematriculación',
 '6':'Baja temporal',
 '7':'Baja definitiva por exportación y tránsito comunitario',
 '8':'Matriculación de vehículo especial',
 '9':'Matriculación temporal',
 'A':'Prórroga de matrícula temporal',
 'B':'Paso de matrícula temporal a definitiva',
}

def parse_date(s):
 try:return datetime.strptime(s,'%d%m%Y').date()
 except (ValueError,TypeError):return None

def is_target_type(code):
 return code in TARGET_TYPE_CODES

def main():
 p=argparse.ArgumentParser()
 p.add_argument('--input-dir',required=True)
 p.add_argument('--output-dir',required=True)
 p.add_argument('--coverage-file')
 a=p.parse_args()
 src=Path(a.input_dir);out=Path(a.output_dir);out.mkdir(parents=True,exist_ok=True)
 counts=Counter();opcounts=Counter();manifest=[];periods=set()
 excluded_types=Counter()
 files=sorted(src.glob('export_mat_????????.txt'))

 for f in files:
  m=re.fullmatch(r'export_mat_(\d{8})\.txt',f.name)
  if not m:continue
  named=datetime.strptime(m.group(1),'%Y%m%d').date()
  raw=f.read_bytes()
  normalized=raw.replace(b'\r\n',b'\n')
  physical=[line for line in normalized.split(b'\n') if line.strip()]
  header=b'Veh\xedculos matriculados. Letras de la serie de la \xfaltima matr\xedcula asignada:'
  if physical and physical[0].startswith(header):
   physical=physical[1:]
  invalid=[len(line) for line in physical if len(line)!=714]
  if invalid:
   lengths=sorted(set(invalid))
   raise ValueError(f'{f.name}: registros de ancho inesperado tras retirar cabecera DGT reconocida; longitudes detectadas: {lengths[:10]}')
  rows=[line.decode('cp1252') for line in physical]

  for n,row in enumerate(rows,1):
   vals=[];pos=0
   for w in WIDTHS:
    vals.append(row[pos:pos+w].strip());pos+=w
   dproc=parse_date(vals[68])
   if dproc!=named:
    raise ValueError(f'{f.name}:{n}: FEC_PROCESO no coincide con fecha del fichero')
   dm=parse_date(vals[0]);dt=parse_date(vals[2])
   clave=vals[21];nuevo=vals[25];tipo=vals[7]

   # Ambos informes se restringen al ámbito acordado. No se infieren
   # categorías para códigos desconocidos ni se agrupan códigos distintos.
   if not is_target_type(tipo):
    excluded_types[tipo]+=1
    continue

   ref=dm if nuevo=='N' else (dt if dt and dt<=dproc else dproc if nuevo=='U' else None)
   star=nuevo=='U' and (not dt or dt>dproc)

   if clave=='1' and ref and ref>=START and nuevo in ('N','U'):
    counts[(ref.strftime('%Y-%m'),tipo,nuevo,star)]+=1
    periods.add(ref.strftime('%Y-%m'))
   if clave in OPS and ref and ref>=START:
    opcounts[(ref.strftime('%Y-%m'),clave,star)]+=1

  manifest.append({
   'archivo':f.name,
   'sha256':hashlib.sha256(raw).hexdigest(),
   'registros':len(rows),
   'fecha_proceso':named.isoformat()
  })

 with (out/'matriculaciones_nuevos_usados_por_tipo.csv').open('w',newline='',encoding='utf-8-sig') as h:
  w=csv.writer(h)
  w.writerow(['periodo','COD_TIPO','descripcion_tipo','nuevo_usado','recuento','fecha_sustitutiva_con_asterisco'])
  for k,v in sorted(counts.items()):
   w.writerow([k[0],k[1],TYPES[k[1]],'Nuevo' if k[2]=='N' else 'Usado',v,'*' if k[3] else ''])

 with (out/'tipo_operacion.csv').open('w',newline='',encoding='utf-8-sig') as h:
  w=csv.writer(h)
  w.writerow(['periodo','CLAVE_TRAMITE','descripcion_operacion','recuento','fecha_sustitutiva_con_asterisco'])
  for k,v in sorted(opcounts.items()):
   w.writerow([k[0],k[1],OPS[k[1]],v,'*' if k[2] else ''])

 coverage={}
 if a.coverage_file:
  coverage=json.loads(Path(a.coverage_file).read_text(encoding='utf-8'))
  (out/'cobertura_diaria.json').write_text(json.dumps(coverage,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 monthly={}
 for day in coverage.get('dias',[]):
  month=day['fecha'][:7]
  entry=monthly.setdefault(month,{'dias_inventariados':0,'estados':Counter()})
  entry['dias_inventariados']+=1
  entry['estados'][day['estado']]+=1
 month_status={}
 for month,entry in sorted(monthly.items()):
  states=dict(entry['estados']); total=entry['dias_inventariados']
  valid=states.get('descargado_validado',0)
  month_status[month]={'estado':'completo' if valid==total else 'incompleto','dias_inventariados':total,'dias_descargados_validados':valid,'estados':states,'mensaje':None if valid else MISSING}
 (out/'manifest.json').write_text(json.dumps({'criterio_inicio':'2026-09-01','filtro_cod_tipo':sorted(TARGET_TYPE_CODES),'archivos':manifest,'cobertura_diaria':coverage.get('dias',[]),'cobertura_mensual':month_status},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 (out/'periodos.json').write_text(json.dumps({'periodos_disponibles':sorted(periods),'cobertura_mensual':month_status,'mensaje_sin_datos':MISSING},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 (out/'resumen.json').write_text(
  json.dumps({
   'archivos_procesados':len(manifest),
   'registros_matriculaciones':sum(counts.values()),
   'registros_operaciones':sum(opcounts.values()),
   'filtro_cod_tipo':sorted(TARGET_TYPE_CODES),
   'registros_excluidos_por_cod_tipo':sum(excluded_types.values()),
   'nota_fecha':'* Fecha de referencia asignada a partir de la fecha de proceso del fichero DGT, al no existir una fecha de tramitación válida o por ser esta posterior a la fecha de proceso.',
   'privacidad':'No exportar campos personales ni identificadores sensibles.'
  },ensure_ascii=False,indent=2)+'\n',
  encoding='utf-8'
 )

if __name__=='__main__':
 main()
