import hashlib
import hmac

from django.contrib.auth.hashers import BasePasswordHasher


class WerkzeugScryptHasher(BasePasswordHasher):
    """Verifica hashes 'scrypt:N:r:p$salt$hex' gerados pelo Werkzeug (Flask).

    Os hashes importados recebem o prefixo 'werkzeug_scrypt$'. No primeiro login
    bem-sucedido o Django regrava a senha com o hasher padrão (PBKDF2).
    """
    algorithm = 'werkzeug_scrypt'

    def verify(self, password, encoded):
        _, metodo, salt, hash_hex = encoded.split('$', 3)
        _, n, r, p = (int(x) if x.isdigit() else x for x in metodo.split(':'))
        calculado = hashlib.scrypt(
            password.encode(), salt=salt.encode(), n=n, r=r, p=p,
            maxmem=132 * n * r * p, dklen=64,
        )
        return hmac.compare_digest(calculado.hex(), hash_hex)

    def safe_summary(self, encoded):
        return {'algorithm': self.algorithm}

    def must_update(self, encoded):
        return True
