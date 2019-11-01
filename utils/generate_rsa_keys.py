#!/usr/bin/env python3
import base64

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

private_key = rsa.generate_private_key(
    public_exponent=65537, key_size=2048, backend=default_backend()
)

public_key_pem = private_key.public_key().public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo,
)

private_key_pem = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
)

print("Private Key:")
print(private_key_pem.decode("utf-8") + "\n")
print("Base64 encoded string:")
print(base64.b64encode(private_key_pem))
print("")
print("Public Key:")
print(public_key_pem.decode("utf-8") + "\n")
print("Base64 encoded string:")
print(base64.b64encode(public_key_pem))
