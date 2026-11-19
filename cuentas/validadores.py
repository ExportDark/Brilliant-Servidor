"""Los validadores de contraseña de Django, con los mensajes de Brilliant: cortos, de tú,
y sin punto final, como los que la app muestra bajo el campo. Los de Django salían largos
y uno sin gramática ("La contraseña es demasiado similar a la de nombre de usuario.")."""

from django.contrib.auth import password_validation


class LargoMinimo(password_validation.MinimumLengthValidator):
    def get_error_message(self):
        return f'Al menos {self.min_length} caracteres'


class ParecidaAlUsuario(password_validation.UserAttributeSimilarityValidator):
    def get_error_message(self):
        return 'Se parece demasiado a tu usuario'


class Comun(password_validation.CommonPasswordValidator):
    def get_error_message(self):
        return 'Es demasiado común'


class SoloNumeros(password_validation.NumericPasswordValidator):
    def get_error_message(self):
        return 'No puede ser solo números'
