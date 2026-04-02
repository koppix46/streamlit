import bcrypt

password = input("Gib das Passwort ein, das du hashen möchtest: ")
hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

print("\nDein fertiger Hash für die Datenbank:")
print(hashed)

# python3 hash_gen.py