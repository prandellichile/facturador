# dte_signer.py
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.hazmat.backends import default_backend
from signxml import XMLSigner
from lxml import etree


def cargar_certificado_pfx(ruta_pfx, password):
    """
    Carga un certificado .pfx y devuelve:
    - clave privada
    - certificado X.509
    """
    with open(ruta_pfx, "rb") as f:
        pfx_data = f.read()

    private_key, certificate, _ = pkcs12.load_key_and_certificates(
        pfx_data,
        password.encode(),
        backend=default_backend()
    )

    return private_key, certificate


def firmar_xml(xml_bytes, private_key, certificate):
    """
    Firma un XML usando XMLDSig (enveloped signature)
    Compatible con versiones nuevas de signxml.
    """
    xml_tree = etree.fromstring(xml_bytes)

    signer = XMLSigner(
        signature_algorithm="rsa-sha256",
        digest_algorithm="sha256"
    )

    signed_xml = signer.sign(
        xml_tree,
        key=private_key,
        cert=certificate
    )

    return etree.tostring(
        signed_xml,
        xml_declaration=True,
        encoding="ISO-8859-1"
    )