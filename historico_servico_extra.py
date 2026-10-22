@app.route('/historico_servico_extra')
def historico_servico_extra():
    if 'id_usuario' not in session:
        flash('Precisa estar logado')
        return redirect(url_for('login'))

    cursor = con.cursor()

    try:
        cursor.execute("""
            SELECT
                se.ID_SERVICO_EXTRA,
                se.ID_USUARIO,
                se.DATA_SERVICO_EXTRA,
                se.SERVICO,
                se.VALOR_RECEBIDO,
                se.STATUS
            FROM SERVICO_EXTRA se
            WHERE se.ID_USUARIO = ?
            ORDER BY se.DATA_SERVICO_EXTRA DESC
        """, (session['id_usuario'],))

        servicos = cursor.fetchall()

        nome = buscarUsuario(session['id_usuario'])[1]
        data = date.today()

        return render_template(
            'historico_servico_extra.html',
            servicos=servicos,
            data=data,
            nome=nome
        )

    finally:
        cursor.close()
