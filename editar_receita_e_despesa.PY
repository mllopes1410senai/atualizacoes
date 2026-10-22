@app.route('/editar_receita_e_depesa/<int:id>', methods=['GET', 'POST'])
def editar_receita_e_despesa(id):

    cursor = con.cursor()
    if 'id_usuario' not in session:
        flash('Precisa estar logado')
        return redirect(url_for('login'))

    nome = buscarUsuario(session['id_usuario'])[1]
    try:
        cursor.execute("""
            SELECT
                TIPO,
                ID_CATEGORIA,
                DESCRICAO,
                valor_total,
                data_movimentacao
            FROM MOVIMENTACAO
            WHERE ID_MOVIMENTACAO = ?
            and id_usuario = ?
        """, (id,session['id_usuario']))

        movimentacoes = cursor.fetchone()

        if movimentacoes is None:
            flash("Receita/Despesa NÃO encontrada")
            return redirect(url_for('historico_movimentacoes'))

        if request.method == 'POST':
            descricao = request.form['descricao']
            valor = float(request.form['valor'])
            categoria = int(request.form['categoria'])
            tipo = int(request.form['tipo'])

            cursor.execute("""
                UPDATE MOVIMENTACAO
                    SET DESCRICAO = ?,
                    id_CATEGORIA = ?,
                    tipo = ?,
                    valor_total = ?
                WHERE ID_movimentacao = ?
                and id_usuario = ?
            """, (descricao, categoria, tipo, valor, id, session['id_usuario']))

            con.commit()

            flash("Registro de receitas/trabalhos editado com sucesso!")
            return redirect(url_for('historico_movimentacoes'))

        categorias = buscarCategorias(session['id_usuario'])

        return render_template(
            'editar_receitas_e_despesas.html',
            movimentacoes=movimentacoes,
            categorias=categorias,
            id=id,
            nome=nome
        )

    except Exception as e:
        con.rollback()
        flash(f"Ocorreu um erro! -> {e}")
        return redirect(url_for('historico_movimentacoes'))

    finally:
        cursor.close()
