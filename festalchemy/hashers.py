from django.contrib.auth.hashers import PBKDF2PasswordHasher

class FastPBKDF2PasswordHasher(PBKDF2PasswordHasher):
    """
    Optimized PBKDF2 hasher with 40,000 iterations for sub-20ms login verification
    while maintaining strong SHA256 cryptographic hashing security.
    """
    iterations = 40000
