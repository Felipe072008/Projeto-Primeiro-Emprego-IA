"""Cria a única conta administrativa localmente; não recebe segredos por argumentos."""
import getpass
import sys
from admin import create_account


def main():
    if not sys.stdin.isatty():
        raise SystemExit('Execute em um console interativo. Não envie credenciais por argumentos ou pipe.')
    username = input('Usuário do administrador: ').strip()
    password = getpass.getpass('Senha (mínimo 12 caracteres): ')
    if password != getpass.getpass('Confirme a senha: '):
        raise SystemExit('As senhas não coincidem.')
    pin = getpass.getpass('PIN numérico de 6 dígitos: ')
    if pin != getpass.getpass('Confirme o PIN: '):
        raise SystemExit('Os PINs não coincidem.')
    try:
        create_account(username, password, pin)
    except ValueError as exc:
        raise SystemExit(str(exc)) from None
    print('Administrador criado. Nenhuma credencial foi exibida ou gravada em texto simples.')


if __name__ == '__main__':
    main()
