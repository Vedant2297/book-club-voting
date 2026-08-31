import hashlib
password = input("Enter your admin password: ")
print(hashlib.sha256(password.encode("utf-8")).hexdigest())
