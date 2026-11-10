import socket

import servir


def test_un_puerto_libre_no_esta_ocupado():
    with socket.socket() as libre:
        libre.bind(('0.0.0.0', 0))
        puerto = libre.getsockname()[1]

    assert not servir.puerto_ocupado(puerto)


def test_un_puerto_con_un_servidor_escuchando_esta_ocupado():
    with socket.socket() as escuchando:
        escuchando.bind(('0.0.0.0', 0))
        escuchando.listen()
        puerto = escuchando.getsockname()[1]

        assert servir.puerto_ocupado(puerto)


def test_si_el_puerto_esta_ocupado_lo_dice_y_no_se_levanta(monkeypatch, capsys):
    monkeypatch.setattr(servir, 'puerto_ocupado', lambda puerto: True)

    codigo = servir.main()

    assert codigo == servir.PUERTO_OCUPADO
    assert 'Ya hay un servidor' in capsys.readouterr().out
