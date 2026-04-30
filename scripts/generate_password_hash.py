import hashlib, hmac, getpass
app_secret = getpass.getpass("auth.app_secret: ")
password = getpass.getpass("password: ")
print(hmac.new(app_secret.encode(), password.encode(), hashlib.sha256).hexdigest())
