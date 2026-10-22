
@app.route('/excluir_categoria/<int:id>', methods=['POST'])
def excluir_categoria(id):
   if 'id_usuario' not in session:
       flash('Precisa estar logado')
       return redirect(url_for('login'))


   cursor = con.cursor()
   try:
       if id in [1001, 1002]:
           flash('Esta categoria não pode ser excluída.')
           return redirect(url_for('listar_categorias'))


       cursor.execute("""
           SELECT 1
           FROM CATEGORIA
           WHERE ID_CATEGORIA = ?
             AND ID_USUARIO = ?
       """, (id, session['id_usuario']))


       if cursor.fetchone() is None:
           flash('Categoria não encontrada!')
           return redirect(url_for('listar_categorias'))


       cursor.execute("""
           SELECT 1
           FROM MOVIMENTACAO
           WHERE ID_CATEGORIA = ?
             AND ID_USUARIO = ?
       """, (id, session['id_usuario']))


       if cursor.fetchone() is not None:
           flash('Não é possível excluir uma categoria que possui movimentações.')
           return redirect(url_for('listar_categorias'))


       cursor.execute("""
           DELETE FROM CATEGORIA
           WHERE ID_CATEGORIA = ?
             AND ID_USUARIO = ?
       """, (id, session['id_usuario']))
       con.commit()
       flash('Categoria excluída com sucesso!')


   except Exception as e:
       con.rollback()
       flash(f'Ocorreu um erro: {e}')


   finally:
       cursor.close()


   return redirect(url_for('listar_categorias'))


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
