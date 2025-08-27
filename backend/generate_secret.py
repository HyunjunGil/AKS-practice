import secrets
import base64

secret_key = secrets.token_hex(32)
encoded_key = base64.b64encode(secret_key.encode()).decode()

mariadb_password_raw = "MyQ3n9NNA0%"
mariadb_password_encoded = base64.b64encode(mariadb_password_raw.encode()).decode()

print(mariadb_password_raw)

redis_password_raw = "GjA0PHx96N"
redis_password_encoded = base64.b64encode(redis_password_raw.encode()).decode()

print("redis_password_raw: ", redis_password_raw)
print("redis_password_encoded: ", redis_password_encoded)



print(encoded_key) 
print(mariadb_password_encoded)