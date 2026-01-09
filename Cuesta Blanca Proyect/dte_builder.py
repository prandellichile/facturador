import datetime
import xml.etree.ElementTree as ET


# =========================
# DATOS DEL EMISOR (TU EMPRESA)
# =========================

EMISOR = {
    "rut": "76.295.242-0",
    "razon_social": "Comercializadora Prandelli Ltda.",
    "giro": "Comercializadora",
    "direccion": "Las Parcelas 7950",
    "comuna": "Peñalolen",
    "ciudad": "Santiago"
}


# =========================
# CONSTRUCTOR DE DTE (BOLETA ELECTRÓNICA)
# =========================

def build_boleta_xml(folio, emisor, receptor, items, totales, tipo_dte=39):
    """
    Construye el XML base de una boleta electrónica (DTE tipo 39).
    """

    # Raíz DTE
    dte = ET.Element("DTE", attrib={"version": "1.0"})
    documento = ET.SubElement(dte, "Documento", attrib={"ID": f"DTE{tipo_dte}"})

    # ===== Encabezado =====
    encabezado = ET.SubElement(documento, "Encabezado")

    # IdDoc
    iddoc = ET.SubElement(encabezado, "IdDoc")
    ET.SubElement(iddoc, "TipoDTE").text = str(tipo_dte)
    ET.SubElement(iddoc, "Folio").text = str(folio)
    ET.SubElement(iddoc, "FchEmis").text = datetime.date.today().strftime("%Y-%m-%d")

    # Emisor
    emisor_xml = ET.SubElement(encabezado, "Emisor")
    ET.SubElement(emisor_xml, "RUTEmisor").text = emisor["rut"]
    ET.SubElement(emisor_xml, "RznSoc").text = emisor["razon_social"]
    ET.SubElement(emisor_xml, "GiroEmis").text = emisor["giro"]
    ET.SubElement(emisor_xml, "DirOrigen").text = emisor["direccion"]
    ET.SubElement(emisor_xml, "CmnaOrigen").text = emisor["comuna"]
    ET.SubElement(emisor_xml, "CiudadOrigen").text = emisor["ciudad"]

    # Receptor
    receptor_xml = ET.SubElement(encabezado, "Receptor")
    ET.SubElement(receptor_xml, "RUTRecep").text = receptor["rut"]
    ET.SubElement(receptor_xml, "RznSocRecep").text = receptor["razon_social"]

    # Totales
    totales_xml = ET.SubElement(encabezado, "Totales")
    ET.SubElement(totales_xml, "MntNeto").text = str(totales["MntNeto"])
    ET.SubElement(totales_xml, "IVA").text = str(totales["IVA"])
    ET.SubElement(totales_xml, "MntTotal").text = str(totales["MntTotal"])

    # ===== Detalle =====
    for item in items:
        det = ET.SubElement(documento, "Detalle")
        ET.SubElement(det, "NroLinDet").text = str(item["NroLinDet"])
        ET.SubElement(det, "NmbItem").text = item["NmbItem"]
        ET.SubElement(det, "QtyItem").text = str(item["QtyItem"])
        ET.SubElement(det, "PrcItem").text = str(item["PrcItem"])
        ET.SubElement(det, "MontoItem").text = str(item["MontoItem"])

    # Convertir a string con declaración XML
    xml_bytes = ET.tostring(dte, encoding="utf-8")
    xml_str = b'<?xml version="1.0" encoding="ISO-8859-1"?>\n' + xml_bytes

    return xml_str


# =========================
# EJEMPLO DE USO (TEST LOCAL)
# =========================

if __name__ == "__main__":
    # Receptor genérico (consumidor final)
    receptor = {
        "rut": "66666666-6",
        "razon_social": "CONSUMIDOR FINAL"
    }

    # Ítems de ejemplo (simulando tu carrito)
    items = [
        {
            "NroLinDet": 1,
            "NmbItem": "Protector Solar SPF50 Workteen",
            "QtyItem": 2,
            "PrcItem": 5000,
            "MontoItem": 10000
        },
        {
            "NroLinDet": 2,
            "NmbItem": "After Sun Aloe",
            "QtyItem": 1,
            "PrcItem": 4000,
            "MontoItem": 4000
        }
    ]

    # Totales de ejemplo
    totales = {
        "MntNeto": 11765,   # ejemplo
        "IVA": 2235,        # ejemplo
        "MntTotal": 14000
    }

    # Folio de prueba (luego vendrá del CAF)
    folio = 1

    xml_dte = build_boleta_xml(
        folio=folio,
        emisor=EMISOR,
        receptor=receptor,
        items=items,
        totales=totales
    )

    # Guardar archivo para inspección
    with open("boleta_ejemplo.xml", "wb") as f:
        f.write(xml_dte)

    print("XML de boleta generado: boleta_ejemplo.xml")