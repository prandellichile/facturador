# test_envio_sii.py
from dte_signer import cargar_certificado_pfx, firmar_xml
from dte_builder import build_boleta_xml
from dte_sender import obtener_semilla, firmar_semilla, obtener_token, enviar_dte

# =========================
# RUTA Y CLAVE DEL CERTIFICADO
# =========================
ruta_pfx = r"C:\Users\prand\Downloads\Certificado E-Certchile.pfx"
password = "mama2990"

# =========================
# DATOS DEL EMISOR
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
# 1) GENERAR XML SIN FIRMA
# =========================
xml_sin_firma = build_boleta_xml(
    folio=1,
    emisor=emisor,
    receptor=receptor,
    items=items,
    totales=totales
)

# =========================
# 2) CARGAR CERTIFICADO
# =========================
private_key, certificate = cargar_certificado_pfx(ruta_pfx, password)

# =========================
# 3) FIRMAR XML
# =========================
xml_firmado = firmar_xml(xml_sin_firma, private_key, certificate)

# =========================
# 4) OBTENER SEMILLA
# =========================
semilla = obtener_semilla()
print("Semilla:", semilla)

# =========================
# 5) FIRMAR SEMILLA
# =========================
semilla_firmada = firmar_semilla(semilla, private_key, certificate)

# =========================
# 6) OBTENER TOKEN
# =========================
token = obtener_token(semilla_firmada)
print("TOKEN:", token)

# =========================
# 7) ENVIAR DTE
# =========================
track_id = enviar_dte(xml_firmado, token)
print("TRACK ID:", track_id)