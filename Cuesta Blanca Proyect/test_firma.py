from dte_builder import build_boleta_xml
from dte_signer import cargar_certificado_pfx, firmar_xml

# =========================
# RUTA Y CLAVE DE TU CERTIFICADO
# =========================
ruta_pfx = r"C:\Users\prand\Downloads\Certificado E-Certchile.pfx"
password = "mama2990"

# =========================
# DATOS DEL EMISOR (TU EMPRESA)
# =========================
emisor = {
    "rut": "76.295.242-0",
    "razon_social": "Comercializadora Prandelli Ltda.",
    "giro": "Comercializadora",
    "direccion": "Las Parcelas 7950",
    "comuna": "Peñalolen",
    "ciudad": "Santiago"
}

# =========================
# RECEPTOR GENÉRICO
# =========================
receptor = {
    "rut": "66666666-6",
    "razon_social": "CONSUMIDOR FINAL"
}

# =========================
# ITEMS DE PRUEBA
# =========================
items = [
    {
        "NroLinDet": 1,
        "NmbItem": "Protector Solar SPF50",
        "QtyItem": 1,
        "PrcItem": 5000,
        "MontoItem": 5000
    }
]

# =========================
# TOTALES DE PRUEBA
# =========================
totales = {
    "MntNeto": 4200,
    "IVA": 800,
    "MntTotal": 5000
}

# =========================
# GENERAR XML SIN FIRMA
# =========================
xml_sin_firma = build_boleta_xml(
    folio=1,
    emisor=emisor,
    receptor=receptor,
    items=items,
    totales=totales
)

# =========================
# CARGAR CERTIFICADO
# =========================
private_key, certificate = cargar_certificado_pfx(ruta_pfx, password)

# =========================
# FIRMAR XML
# =========================
xml_firmado = firmar_xml(xml_sin_firma, private_key, certificate)

# =========================
# GUARDAR ARCHIVO FIRMADO
# =========================
with open("boleta_firmada.xml", "wb") as f:
    f.write(xml_firmado)

print("Boleta firmada generada correctamente: boleta_firmada.xml")