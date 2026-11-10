#!/usr/bin/env python3
"""Genera el informe territorial integrado a partir de los agregados MATRABA."""
import argparse, csv, json, calendar
from collections import Counter
from datetime import date
from pathlib import Path

MOTOS = {"50", "51"}

def rows(path, required):
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        missing = set(required) - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path}: faltan columnas {sorted(missing)}")
        return list(reader)

def fmt(value):
    return f"{int(value):,}".replace(",", ".")

def dec(value, digits=2):
    if value is None: return "n/d"
    return f"{float(value):,.{digits}f}".replace(",", "X").replace(".", ",").replace("X", ".")

def pct(value):
    return dec(value) + "%" if value is not None else "n/d"

def mdtable(headers, data):
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    out += ["| " + " | ".join(map(str, r)) + " |" for r in data]
    return "\n".join(out)

def build_report(data_dir="public/data", output="informes/informe-territorial-integrado.md"):
    d = Path(data_dir)
    provincial = rows(d/"matriculaciones_motocicletas_por_provincia.csv",
        {"periodo","ambito_provincial","COD_PROVINCIA","provincia","COD_TIPO","nuevo_usado","recuento"})
    ranking = rows(d/"ranking_motocicletas_provincia.csv",
        {"ambito_provincial","provincia","recuento","peso_porcentual","puesto"})
    intensity = rows(d/"indicadores_intensidad_territorial.csv",
        {"provincia","matriculaciones_nuevas","matriculaciones_por_1000_habitantes","matriculaciones_sobre_parque_pct","umbral_revision_parque_pct","alerta_revision"})
    balance = rows(d/"dispersion_balance_provincial.csv",
        {"COD_PROVINCIA","provincia","salidas_interprovinciales","entradas_interprovinciales","saldo_neto_entradas_menos_salidas"})
    flows = rows(d/"dispersion_provincias_flujos.csv",
        {"provincia_matriculacion","provincia_domicilio_vehiculo","recuento"})
    types = rows(d/"matriculaciones_nuevos_usados_por_tipo.csv", {"periodo","COD_TIPO","nuevo_usado","recuento"})
    dispersion = json.loads((d/"informe_dispersion_provincias.json").read_text(encoding="utf-8"))
    periods = sorted({r["periodo"] for r in provincial})
    if not periods: raise ValueError("No hay periodos provinciales")
    y, m = map(int, periods[-1].split("-"))
    cutoff = date(y,m,calendar.monthrange(y,m)[1]).strftime("%d/%m/%Y")
    new, used = Counter(), Counter()
    for r in types:
        if r["COD_TIPO"] in MOTOS:
            (new if r["nuevo_usado"]=="Nuevo" else used)[r["periodo"]] += int(r["recuento"])
    total_new, total_used = sum(new.values()), sum(used.values())
    val = dispersion["validacion"]
    if total_new != int(dispersion["total_matriculaciones"]) or not val["agregado_provincial_coincide"]:
        raise ValueError("No concilian los totales de motocicletas nuevas y el cruce provincial")
    monthly = [[p,fmt(new[p]),fmt(used[p]),fmt(new[p]+used[p])] for p in periods]
    ranks = sorted((r for r in ranking if r["ambito_provincial"]=="matriculacion"),key=lambda r:int(r["puesto"]))
    top5, top10 = sum(float(r["peso_porcentual"]) for r in ranks[:5]),sum(float(r["peso_porcentual"]) for r in ranks[:10])
    by_pop = sorted(intensity,key=lambda r:float(r["matriculaciones_por_1000_habitantes"]),reverse=True)
    by_park = sorted(intensity,key=lambda r:float(r["matriculaciones_sobre_parque_pct"]),reverse=True)
    alerts = [r for r in intensity if r["alerta_revision"].strip()]
    dr = sorted(dispersion["ranking_provincial"],key=lambda r:(-(r["porcentaje_domicilio_externo_sobre_conocidos"] or 0),-r["domicilio_otra_provincia"]))
    neg = sorted(balance,key=lambda r:int(r["saldo_neto_entradas_menos_salidas"]))[:10]
    pos = sorted(balance,key=lambda r:int(r["saldo_neto_entradas_menos_salidas"]),reverse=True)[:10]
    seg = dispersion["segovia"]
    sb = next((r for r in balance if r["COD_PROVINCIA"]=="SG"),{})
    text = [
      "# Informe territorial integrado de matriculaciones de motocicletas",
      f"## España · {periods[0]} a {periods[-1]}","",f"**Fecha de corte:** {cutoff}",
      "**Universo:** motocicletas DGT de códigos 50 y 51.","",
      "## 1. Resumen ejecutivo","",
      f"El periodo acumula **{fmt(total_new)} matriculaciones nuevas** y **{fmt(total_used)} registros usados** (cambios de titularidad).",
      f"- Las cinco primeras provincias reúnen el **{dec(top5)}%**; las diez primeras, el **{dec(top10)}%**.",
      f"- {fmt(dispersion['otra_provincia'])} ({pct(dispersion['porcentaje_interprovincial_sobre_domicilios_conocidos'])}) de las nuevas tienen domicilio registral en otra provincia.",
      f"- Conciliación del cruce: diferencia {fmt(val['diferencias'])} registros.",
      f"- Alertas REVISAR: {', '.join(r['provincia'] for r in alerts) if alerts else 'ninguna'}.",
      "Los indicadores son descriptivos; no son cuotas comerciales, tasas de renovación, medidas de residencia efectiva ni movimientos físicos.","",
      "## 2. Alcance y metodología","",
      "- Se incluyen exclusivamente los códigos 50 y 51; se excluyen 52–54 y 90–92.",
      "- Nuevas: fecha de matriculación y provincia COD_PROVINCIA_MAT.",
      "- Usadas: fecha de trámite de cambio de titularidad y provincia COD_PROVINCIA_VEH; no representan todas las compraventas.",
      "- El domicilio registral del vehículo no acredita residencia efectiva, concesionario, lugar de compra/entrega ni uso habitual.",
      "- Población de referencia: 1-1-2025 (INE). Parque: 31-12-2025 (DGT, Anuario 2025, tabla 75).",
      "- Los bastidores están parcialmente enmascarados; no se atribuyen identidades individuales ni causas no demostradas.","",
      "## 3. Evolución mensual","",mdtable(["Periodo","Nuevas","Usadas (cambio titularidad)","Total"],monthly),"",
      "## 4. Concentración provincial","",
      "### Diez primeras provincias por nuevas","",
      mdtable(["Puesto","Provincia","Nuevas","Peso"],[[r["puesto"],r["provincia"],fmt(r["recuento"]),pct(r["peso_porcentual"])] for r in ranks[:10]]),
      f"Top 5: {dec(top5)}%. Top 10: {dec(top10)}%. El ranking representa provincia de matriculación.","",
      "## 5. Intensidad territorial","",
      "### Matriculaciones por 1.000 habitantes","",
      mdtable(["Provincia","Nuevas","Por 1.000"],[[r["provincia"],fmt(r["matriculaciones_nuevas"]),dec(r["matriculaciones_por_1000_habitantes"])] for r in by_pop[:10]]),"",
      "### Matriculaciones respecto al parque","",
      mdtable(["Provincia","Nuevas","Nuevas / parque"],[[r["provincia"],fmt(r["matriculaciones_nuevas"]),pct(r["matriculaciones_sobre_parque_pct"])] for r in by_park[:10]]),
      "El umbral REVISAR es una señal operativa, no una anomalía confirmada ni motivo para excluir registros.","",
      "## 6. Dispersión matriculación-domicilio","",
      mdtable(["Relación","Registros","Porcentaje"],[
        ["Misma provincia",fmt(dispersion["misma_provincia"]),pct(dispersion["porcentaje_misma_provincia"])],
        ["Provincia distinta",fmt(dispersion["otra_provincia"]),pct(dispersion["porcentaje_interprovincial_sobre_domicilios_conocidos"])],
        ["Domicilio no informado",fmt(dispersion["domicilio_no_informado"]),pct(100*dispersion["domicilio_no_informado"]/dispersion["total_matriculaciones"] if dispersion["total_matriculaciones"] else None)],
        ["Total",fmt(dispersion["total_matriculaciones"]),"100,00%"]]),
      f"Matriz: {fmt(dispersion['matriz_filas'])} celdas. Cruce y agregado provincial: {fmt(val['total_cruce'])} y {fmt(val['total_agregado_provincial'])}; diferencia cero.","",
      "### Mayor proporción de domicilios externos","",
      mdtable(["Provincia de matriculación","Nuevas","Domicilio externo","Porcentaje"],[[r["provincia_matriculacion"],fmt(r["matriculaciones"]),fmt(r["domicilio_otra_provincia"]),pct(r["porcentaje_domicilio_externo_sobre_conocidos"])] for r in dr[:10]]),"",
      "## 7. Balance interprovincial","",
      "Salidas: matriculadas en la provincia y domiciliadas fuera. Entradas: domiciliadas en la provincia y matriculadas fuera. Saldo = entradas menos salidas. No son movimientos físicos.","",
      "### Saldos negativos","",mdtable(["Provincia","Salidas","Entradas","Saldo"],[[r["provincia"],fmt(r["salidas_interprovinciales"]),fmt(r["entradas_interprovinciales"]),fmt(r["saldo_neto_entradas_menos_salidas"])] for r in neg]),"",
      "### Saldos positivos","",mdtable(["Provincia","Salidas","Entradas","Saldo"],[[r["provincia"],fmt(r["salidas_interprovinciales"]),fmt(r["entradas_interprovinciales"]),"+"+fmt(r["saldo_neto_entradas_menos_salidas"])] for r in pos]),"",
      "### Principales flujos","",mdtable(["Provincia matriculación","Domicilio vehículo","Registros"],[[r["provincia_matriculacion"],r["provincia_domicilio_vehiculo"],fmt(r["recuento"])] for r in flows[:15]]),"",
      "## 8. Seguimiento de Segovia","",
      f"Segovia registra **{fmt(seg['matriculaciones'])} nuevas**; {pct(seg['porcentaje_domicilio_externo_sobre_conocidos'])} tienen domicilio en otra provincia. El flujo a Madrid suma {fmt(seg['domicilio_madrid'])} ({pct(seg['porcentaje_domicilio_madrid_sobre_total'])}).","",
      mdtable(["Magnitud","Registros"],[
        ["Salidas (matriculadas en Segovia, domicilio fuera)",fmt(sb.get("salidas_interprovinciales",0))],
        ["Entradas (matriculadas fuera, domicilio Segovia)",fmt(sb.get("entradas_interprovinciales",0))],
        ["Saldo neto",fmt(sb.get("saldo_neto_entradas_menos_salidas",0))],
        ["Misma provincia",fmt(seg["domicilio_segovia"])] ]),"",
      "La concentración es una señal de revisión. La proximidad a Madrid y posibles estructuras administrativas o comerciales son hipótesis, no causas demostradas. No se corrigen ni excluyen registros por su magnitud.","",
      "### Evolución mensual de Segovia","",
      mdtable(["Periodo","Matriculaciones","Domicilio Segovia","Domicilio Madrid","Otras provincias"],[[r["periodo"],fmt(r["matriculaciones"]),fmt(r["domicilio_segovia"]),fmt(r["domicilio_madrid"]),fmt(r["domicilio_otras_provincias"])] for r in seg["evolucion_mensual"]]),"",
      "## 9. Conclusiones y seguimiento","",
      f"1. {fmt(total_new)} nuevas en {len(periods)} periodos; top 10 provincial: {dec(top10)}%.",
      f"2. Dispersión interprovincial: {pct(dispersion['porcentaje_interprovincial_sobre_domicilios_conocidos'])} de domicilios conocidos.",
      f"3. Conciliación de cruce: diferencia {fmt(val['diferencias'])}.",
      f"4. Alertas activas: {', '.join(r['provincia'] for r in alerts) if alerts else 'ninguna'}.",
      "5. Las alertas requieren seguimiento y contraste; no prueban error, fraude ni causalidad.","",
      "## 10. Fuentes y reproducibilidad","",
      "Los CSV y JSON fuente se publican en public/data: agregado provincial, ranking, evolución, indicadores de intensidad, matriz, flujos, balance y resumen de dispersión. Este documento se regenera en cada ejecución que publica agregados.","",
      "**Nota metodológica:** Resultados orientativos por el enmascaramiento parcial de bastidores. El acceso a bastidores completos permitiría verificar coincidencias individuales y reducir incertidumbres.",""
    ]
    target=Path(output); target.parent.mkdir(parents=True,exist_ok=True); target.write_text("\n".join(text),encoding="utf-8")
    return {"periodos":periods,"nuevas":total_new,"usadas":total_used,"alertas":[r["provincia"] for r in alerts],"output":str(target)}

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument("--data-dir",default="public/data"); p.add_argument("--output",default="informes/informe-territorial-integrado.md")
    a=p.parse_args(); print(json.dumps(build_report(a.data_dir,a.output),ensure_ascii=False,indent=2))
if __name__=="__main__": main()
