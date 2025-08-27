import secrets
import base64

secret_key = secrets.token_hex(32)
encoded_key = base64.b64encode(secret_key.encode()).decode()

mariadb_password_raw = ""
mariadb_password_encoded = base64.b64encode(mariadb_password_raw.encode()).decode()

print(mariadb_password_raw, mariadb_password_encoded)

redis_password_raw = ""
redis_password_encoded = base64.b64encode(redis_password_raw.encode()).decode()

print("redis_password_raw: ", redis_password_raw)
print("redis_password_encoded: ", redis_password_encoded)

kafka_password_raw = ""
kafka_password_encoded = base64.b64encode(kafka_password_raw.encode()).decode()

print("kafka_password_raw: ", kafka_password_raw)
print("kafka_password_encoded: ", kafka_password_encoded)



print(encoded_key) 
print(mariadb_password_encoded)