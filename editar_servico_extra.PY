@app.route('/editar_servico_extra/<int:id>', methods=['GET', 'POST'])
def editar_servico_extra(id):
    if 'id_usuario' not in session:
        flash('Precisa estar logado')
        return redirect(url_for('login'))

    cursor = con.cursor()

    try:
        cursor.execute("""
            SELECT SERVICO, VALOR_RECEBIDO, DATA_SERVICO_EXTRA
            FROM SERVICO_EXTRA
            WHERE ID_SERVICO_EXTRA = ?
            AND ID_USUARIO = ?
        """, (id, session['id_usuario']))

        servico = cursor.fetchone()

        if servico is None:
            flash('Serviço extra não encontrado!')
            return redirect(url_for('historico_servico_extra'))

        if request.method == 'POST':
            nome_servico = request.form['servico'].strip()
            valor = float(request.form['valor'].replace(',', '.'))

            if not nome_servico or valor <= 0:
                flash('Informe um serviço e um valor válido!')
                return redirect(url_for('editar_servico_extra', id=id))

            cursor.execute("""
                UPDATE SERVICO_EXTRA
                SET SERVICO = ?, VALOR_RECEBIDO = ?
                WHERE ID_SERVICO_EXTRA = ?
                AND ID_USUARIO = ?
            """, (nome_servico, valor, id, session['id_usuario']))

            con.commit()
            flash('Serviço extra editado com sucesso!')
            return redirect(url_for('historico_servico_extra'))

        nome = buscarUsuario(session['id_usuario'])[1]

        return render_template(
            'editar_servico_extra.html',
            servico=servico,
            id=id,
            nome=nome
        )

    except Exception as e:
        con.rollback()
        flash(f'Ocorreu um erro: {e}')
        return redirect(url_for('historico_servico_extra'))

    finally:
        cursor.close()
