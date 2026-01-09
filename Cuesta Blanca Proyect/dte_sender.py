# dte_sender.py
import requests
from lxml import etree
from signxml import XMLSigner
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization


URL_SEMILLA = "https://palena.sii.cl/DTEWS/CrSeed.jws"
URL_TOKEN = "https://palena.sii.cl/DTEWS/GetTokenFromSeed.jws"
URL_UPLOAD = "https://palena.sii.cl/cgi_dte/UPL/DTEUpload"


# ============================================================
# CARGAR CERTIFICADO
# ============================================================
def cargar_certificado_pfx(ruta_pfx, password):
    with open(ruta_pfx, "rb") as f:
        pfx_data = f.read()

    private_key, certificate, _ = pkcs12.load_key_and_certificates(
        pfx_data,
        password.encode(),
        backend=default_backend()
    )

    return private_key, certificate


# ============================================================
# 1) OBTENER SEMILLA
# ============================================================
def obtener_semilla():
    resp = requests.get(URL_SEMILLA)
    xml = etree.fromstring(resp.content)
    semilla = xml.xpath("//SEMILLA/text()")[0]
    return semilla


# ============================================================
# 2) FIRMAR SEMILLA
# ============================================================
def firmar_semilla(semilla, private_key, certificate):
    xml = f"""
    <getToken>
        <item>
            <Semilla>{semilla}</Semilla>
        </item>
    </getToken>
    """

    xml_tree = etree.fromstring(xml.encode("ISO-8859-1"))

    # Convertir certificado a DER
    cert_der = certificate.public_bytes(
        encoding=serialization.Encoding.DER
    )

    signer = XMLSigner(
        signature_algorithm="rsa-sha256",
        digest_algorithm="sha256"
    )

    signed = signer.sign(xml_tree, key=private_key, cert=cert_der)
    return etree.tostring(signed, encoding="ISO-8859-1")


# ============================================================
# 3) OBTENER TOKEN
# ============================================================
def obtener_token(semilla_firmada):
    headers = {"Content-Type": "text/xml"}
    resp = requests.post(URL_TOKEN, data=semilla_firmada, headers=headers)

    xml = etree.fromstring(resp.content)
    token = xml.xpath("//TOKEN/text()")[0]
    return token


# ============================================================
# 4) SUBIR DTE FIRMADO
# ============================================================
def enviar_dte(xml_firmado, token):
    headers = {
        "Cookie": f"TOKEN={token}"
    }

    files = {
        "archivo": ("dte.xml", xml_firmado, "text/xml")
    }

    resp = requests.post(URL_UPLOAD, files=files, headers=headers)

    xml = etree.fromstring(resp.content)
    track_id = xml.xpath("//TRACKID/text()")[0]

    return track_id