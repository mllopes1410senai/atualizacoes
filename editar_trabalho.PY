@app.route('/editar_trabalho/<int:id>', methods=['GET', 'POST'])
def editar_trabalho(id):
    cursor = con.cursor()
    nome = buscarUsuario(id)[1]

    try:
        cursor.execute("""
            SELECT
                DATA_SERVICO_DIARIO,
                PACOTES_COLETADOS,
                QTD_TRABALHADORES
            FROM SERVICO_DIARIO
            WHERE ID_SERVICO_DIARIO = ?
        """, (id,))

        servico = cursor.fetchone()

        if servico is None:
            flash("Registro de trabalho NÃO encontrado")
            return redirect(url_for('historico_trabalho'))

        if request.method == 'POST':
            pacotes = int(request.form['pacotes'])
            trabalhadores = int(request.form['trabalhadores'])

            valor_dia_total = calcula_valor_dia(trabalhadores, pacotes)

            cursor.execute("""
                UPDATE SERVICO_DIARIO
                SET PACOTES_COLETADOS = ?,
                    QTD_TRABALHADORES = ?,
                    VALOR_DIA_TOTAL = ?
                WHERE ID_SERVICO_DIARIO = ?
            """, (pacotes, trabalhadores, valor_dia_total, id))

            con.commit()

            flash("Registro de trabalho editado com sucesso!")
            return redirect(url_for('historico_trabalho'))

        return render_template(
            'editar_trabalho.html',
            servico=servico,
            id=id,
            nome=nome
        )

    except Exception as e:
        con.rollback()
        flash(f"Ocorreu um erro! -> {e}")
        return redirect(url_for('historico_trabalho'))

    finally:
        cursor.close()
