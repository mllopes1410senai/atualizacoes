@app.route('/historico_trabalho')
def historico_trabalho():
    if 'id_usuario' not in session:
        flash('Precisa estar loggado')
        return redirect(url_for('login'))

    else:
        cursor = con.cursor()
        cursor.execute(""" SELECT sd.DATA_SERVICO_DIARIO 
                                 ,sd.PACOTES_COLETADOS 
                                 ,sd.QTD_TRABALHADORES 
                                 ,sd.VALOR_DIA_TOTAL 
                                 ,sd.ID_SERVICO_DIARIO
                                 ,sd.STATUS
                                FROM SERVICO_DIARIO sd
                                WHERE SD.ID_USUARIO = ?""", (session['id_usuario'],))
        trabalhos = cursor.fetchall()
        cursor.close()

        nome = buscarUsuario(id)[1]
        data = date.today()
        return render_template('historico_trabalho.html', trabalhos=trabalhos, data=data, nome=nome)
