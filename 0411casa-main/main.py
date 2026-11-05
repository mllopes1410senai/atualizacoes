from flask import Flask, render_template, request, flash, redirect, url_for, session, jsonify, send_file
import fdb
from flask_bcrypt import Bcrypt
from datetime import date
import calendar
from fpdf import FPDF


#imports para o gráfico
import pygal, os
from collections import Counter

app = Flask(__name__)
bcrypt = Bcrypt(app)
app.config['SECRET_KEY'] = 'Meu-salario'
pdf = FPDF()
pdf.add_page()

# conectar o banco:
host = 'localhost'
database = r'C:\Users\rehme\OneDrive\Ambiente de Trabalho\SPRINT03 (1).FDB'
user = 'sysdba'
password = 'sysdba'

con = fdb.connect(host=host, database=database, user=user, password=password, )  # conectar o banco


@app.route('/')
def index():
    return render_template('index.html')


def validar_senha(senha):
    if len(senha) < 8:
        return False
    tem_maiusculo = False
    tem_minusculo = False
    tem_numero = False

    for caractere in senha:
        if caractere.isupper():
            tem_maiusculo = True

        if caractere.islower():
            tem_minusculo = True

        if caractere.isdigit():
            tem_numero = True

    if tem_maiusculo == False:
        return False

    if tem_minusculo == False:
        return False

    if tem_numero == False:
        return False

    return True


# CADASTRAR
@app.route('/cadastro')
def cadastro():
    return render_template('cadastro.html')


@app.route('/cadastrar', methods=['POST'])
def cadastrar():
    nome = request.form['nome']
    cpf = request.form['cpf']
    telefone = request.form['telefone']
    email = request.form['email']
    senha = request.form['senha']
    confirmar = request.form['confirmar']

    if not validar_senha(senha):
        flash('Senha fraca!', 'error')
        return redirect(url_for('cadastro'))

    senha_hash = bcrypt.generate_password_hash(senha).decode('utf-8')
    cursor = con.cursor()

    if senha != confirmar:
        flash('As senhas não são iguais!', 'error')
        return redirect(url_for('cadastro'))

    if nome.strip() and email.strip() and telefone.strip() and cpf.strip() == "":
        flash('Não podem ter campos vazios!', 'error')
        return redirect(url_for('cadastro'))

    else:
        try:
            cursor.execute(""" SELECT 1
                              FROM usuario
                              WHERE email = ? OR TELEFONE = ? OR CPF = ?""", (email, telefone, cpf))
            if cursor.fetchone() is not None:
                flash("Erro: Usuário já cadastrado!", 'error')
                return redirect(url_for('cadastro'))

            cursor.execute("""INSERT INTO usuario (nome, email, cpf, telefone, senha, valor_diario_padrao, valor_diario_excepcional, valor_pacotes, min_pacotes, min_trabalhadores)
                                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (nome, email, cpf, telefone, senha_hash, 0, 0, 0, 0, 0))
            con.commit()
            flash('Usuário cadastrado com sucesso!', 'success')

        except Exception as e:
            flash(f"Ocorreu um erro! -> {e}", 'error')
            con.rollback()

        finally:
            cursor.close()

        return redirect(url_for('login'))


# LOGIN
@app.route('/login')
def login():
    return render_template('login.html')


@app.route('/entrar', methods=['GET', 'POST'])
def entrar():
    print('entrei')
    if request.method == 'POST':
        login = request.form['login']
        senha = request.form['senha']
        print(login, senha)

        print(login[:15])
        cursor = con.cursor()
        try:
            cursor.execute("""SELECT ID_USUARIO, SENHA, TENTATIVA, STATUS, NOME FROM USUARIO WHERE EMAIL = ? OR TELEFONE = ? OR CPF = ?""",
                           (login, login[:15], login[:15]))
            usuario = cursor.fetchone()
            print(usuario)
            if not usuario:  # seleciona um único valor
                flash('Usuário não encontrado!')
                return redirect(url_for('login'))

            id_usuario, senha_hash, tentativa, status, nome = usuario

            if status == 0:
                if usuario:
                    if bcrypt.check_password_hash(senha_hash, senha):
                        session['id_usuario'] = id_usuario
                        session['nome'] = nome

                        flash('Login bem-sucedido!', 'success')
                        tentativas = 0
                        cursor.execute('update usuario set tentativa = ? where id_usuario = ?',
                                       (tentativas, id_usuario))
                        con.commit()

                        return redirect(url_for('dashboard'))

                    else:
                        tentativa += 1
                        cursor.execute('update usuario set tentativa = ? where id_usuario = ?', (tentativa, id_usuario))
                        con.commit()

                        if tentativa == 3:
                            cursor.execute('update usuario set status = 1 where id_usuario = ?', (id_usuario,))
                            con.commit()
                            flash('Usuário está bloqueado , entre em contato com o administrador do sistema!', 'error')
                            return redirect(url_for('login'))

                        flash(f'Email ou senha inválidos!')
                        return redirect(url_for('login'))

                else:
                    return render_template('login.html')
            else:
                flash('Usuário Inativo!', 'error')
                return render_template('login.html')


        except Exception as e:
            flash(f'Ocorreu um erro -> {e}', 'error')
            con.rollback()

        finally:
            cursor.close()

        return redirect(url_for('dashboard'))


@app.route('/logout')
def logout():
    session.pop('id_usuario', None)
    flash('Logout com sucesso!', 'success')
    return redirect(url_for('login'))


@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'id_usuario' not in session:
        flash('Precisa estar loggado', 'error')
        return redirect(url_for('login'))
    else:
        data = date.today()
        receitas = calcular_receitas()
        despesas = calcular_despesas()
        saldo = calcular_saldo()
        ano = request.form.get('ano', data.year)
        tipo_grafico = request.form.get('tipo_grafico', '0')
        grafico_saldos = grafico_saldo(session['id_usuario'], ano, tipo_grafico)
        anos = buscarAnos()
        grafico_movimentacoes = graficos_receitas_despesas(ano)

        meses = buscarMeses(ano)
        usuario = buscarUsuario(id)
        caminho = "img/capas/" + str(usuario[0]) + ".jpg"
        if not os.path.exists(f'static/{caminho}'):
            caminho = 'img/capas/SEMIMAGEM.jpg'

        print('9')
        print(anos, meses)
        return render_template('dashboard.html',
                               nome=session['nome'],
                               receitas=receitas,
                               despesas=despesas,
                               saldo=saldo,
                               grafico_movimentacoes=grafico_movimentacoes,
                               grafico_saldo=grafico_saldos,
                               anos=anos,
                               meses=meses,
                               img=caminho)


def buscarUsuario(id):
    id = session['id_usuario']

    cursor = con.cursor()
    cursor.execute("""SELECT ID_USUARIO, NOME, email, senha, VALOR_DIARIO_PADRAO, VALOR_DIARIO_EXCEPCIONAL, VALOR_PACOTES, MIN_PACOTES, MIN_TRABALHADORES, CPF, TELEFONE
                             FROM USUARIO
                             WHERE id_usuario = ?""", (id,))
    usuario = cursor.fetchone()
    cursor.close()

    return usuario


@app.route('/editar_usuario')
def editar_usuario():
    if 'id_usuario' not in session:
        flash('Precisa estar loggado')
        return redirect(url_for('login'))

    else:
        cursor = con.cursor()

        cursor.execute("""SELECT ID_USUARIO, NOME, email, senha, VALOR_DIARIO_PADRAO, VALOR_DIARIO_EXCEPCIONAL, VALOR_PACOTES, MIN_PACOTES, MIN_TRABALHADORES, CPF, TELEFONE
                                FROM USUARIO
                                WHERE id_usuario = ?""", (session['id_usuario'],))
        usuario = cursor.fetchone()

        cursor.close()
        caminho = "img/capas/" + str(usuario[0]) + ".jpg"

        if not os.path.exists(f'static/{caminho}'):
            caminho = 'img/capas/SEMIMAGEM.jpg'




        return render_template('editar_usuario.html', usuario=usuario, nome=usuario[1], img=caminho)

@app.route('/editar', methods=['GET', 'POST'])
def editar():
    if 'id_usuario' not in session:
        flash('Precisa estar loggado')
        return redirect(url_for('login'))

    else:
        cursor = con.cursor()

        try:
            id = session['id_usuario']

            usuario = buscarUsuario(session['id_usuario'])

            print(request.method)

            if request.method == 'POST':
                nome = request.form['nome']
                email = request.form['email']
                cpf = request.form['cpf']
                telefone = request.form['telefone']
                valor_padrao = float(request.form['valor_padrao'])
                valor_excepcional = float(request.form['valor_excepcional'])
                valor_pacotes = float(request.form['valor_pacotes'])
                min_pacotes = int(request.form['min_pacotes'])
                min_trabalhadores = int(request.form['min_trabalhadores'])
                arquivo = request.files['imagem']

                cursor.execute("""SELECT 1
                                     FROM usuario
                                     WHERE (email = ? 
                                     OR TELEFONE = ? 
                                     OR CPF = ?) 
                                     AND id_usuario != ?""",
                               (email, telefone, cpf, session['id_usuario']))

                if cursor.fetchone() is not None:
                    flash("Erro: Usuário já cadastrado!")
                    return redirect(url_for('editar'))

                if nome.strip() and email.strip() and cpf.strip() and telefone.strip() != "":

                    cursor.execute("""UPDATE USUARIO
                                       SET NOME = ?,
                                       EMAIL = ?,
                                       CPF = ?,
                                       TELEFONE = ?,
                                       VALOR_DIARIO_PADRAO = ?,
                                       VALOR_DIARIO_EXCEPCIONAL = ?,
                                       VALOR_PACOTES = ?,
                                       MIN_PACOTES = ?,
                                       MIN_TRABALHADORES = ?
                                       WHERE ID_USUARIO = ?""",
                                   (nome, email, cpf, telefone, valor_padrao, valor_excepcional, valor_pacotes, min_pacotes, min_trabalhadores, id))
                    con.commit()


                    if arquivo and arquivo.filename != '':

                        caminho = f'static/img/capas/{id}.jpg'

                        if os.path.exists(caminho):
                            os.remove(caminho)

                        arquivo.save(caminho)


                    flash("Usuário editado com sucesso!")

                    usuario = buscarUsuario(id)

                else:
                    flash('Não podem existir campos nulos!')
        except Exception as e:
            print(e)
            flash(f"Ocorreu um erro! -> {e}")

        finally:
            caminho = "img/capas/" + str(usuario[0]) + ".jpg"
            if not os.path.exists(f'static/{caminho}'):
                caminho = 'img/capas/SEMIMAGEM.jpg'
            return render_template('editar_usuario.html', nome=usuario[1], usuario=usuario, img=caminho)

@app.route('/excluir_imagem/<int:id>', methods=['POST'])
def excluir_imagem(id):

    caminho = f'static/img/capas/{id}.jpg'

    if os.path.exists(caminho):
        os.remove(caminho)

    return redirect(url_for('editar'))


def senhas_anteriores(senha_modificada):
    cursor = con.cursor()
    id_usuario = session['id_usuario']

    cursor.execute("""SELECT SENHA, SENHA1, SENHA2 FROM USUARIO WHERE ID_USUARIO = ?""", (id_usuario,))
    senha_atual, senha1, senha2 = cursor.fetchone()

    if (bcrypt.check_password_hash(senha_atual, senha_modificada) or
            (senha1 and bcrypt.check_password_hash(senha1, senha_modificada)) or
            (senha2 and bcrypt.check_password_hash(senha2, senha_modificada))):
        return False
    else:
        alt_senha2 = senha_atual
        alt_senha1 = senha2
        alt_senha = bcrypt.generate_password_hash(senha_modificada).decode('utf-8')

        print(alt_senha, alt_senha1, alt_senha2)

        cursor.execute("""UPDATE USUARIO SET SENHA = ?, SENHA1 = ?, SENHA2 = ? WHERE ID_USUARIO = ?""",
                       (alt_senha, alt_senha1, alt_senha2, id_usuario))
        cursor.close()

        return True


@app.route('/editar_senha')
def editar_senha():
    if 'id_usuario' not in session:
        flash('Precisa estar loggado', 'error')
        return redirect(url_for('login'))
    else:
        nome = buscarUsuario(id)[1]
        usuario = buscarUsuario(id)
        caminho = "img/capas/" + str(usuario[0]) + ".jpg"
        if not os.path.exists(f'static/{caminho}'):
            caminho = 'img/capas/SEMIMAGEM.jpg'

        return render_template('editar_senha.html', nome=nome, img=caminho)


@app.route('/senha', methods=['GET', 'POST'])
def senha():
    if 'id_usuario' not in session:
        flash('Precisa estar loggado', 'error')
        return redirect(url_for('login'))


    else:
        cursor = con.cursor()
        try:
            id = session['id_usuario']
            usuario = buscarUsuario(id)
            print("ID:", id)
            print("USUARIO:", usuario)
            print("TIPO:", type(usuario))

            if request.method == 'POST':
                senha_atual = request.form['senha_atual']
                nova_senha = request.form['nova_senha']
                confirma_senha = request.form['confirma_senha']

                if bcrypt.check_password_hash(usuario[3], senha_atual):
                    if nova_senha == confirma_senha:
                        if validar_senha(nova_senha):
                            if senhas_anteriores(nova_senha):
                                flash("Senha alterada com sucesso!", 'success')
                            else:
                                flash("A senha tem que ser diferente das anteriores!", 'error')
                        else:
                            flash("Informe uma senha segura!", 'error')
                    else:
                        flash("As senhas não são iguais!", 'error')
                else:
                    flash("Senha incorreta!", 'error')


        except Exception as e:
            print(e)
            flash(f"Ocorreu um erro! -> {e}", 'error')

        finally:
            cursor.close()

        nome = usuario[1]
        caminho = "img/capas/" + str(usuario[0]) + ".jpg"
        if not os.path.exists(f'static/{caminho}'):
            caminho = 'img/capas/SEMIMAGEM.jpg'
        return render_template('editar_usuario.html', usuario=usuario, nome=nome, img=caminho)


@app.route('/categorias')
def categorias():
    if 'id_usuario' not in session:
        flash('Precisa estar loggado')
        return redirect(url_for('login'))
    else:
        resultado = buscarCategorias(session['id_usuario'])
        usuario = buscarUsuario([session['id_usuario']])
        caminho = "img/capas/" + str(usuario[0]) + ".jpg"
        if not os.path.exists(f'static/{caminho}'):
            caminho = 'img/capas/SEMIMAGEM.jpg'

        if not resultado:
            id = None
        else:
            id = resultado[0][0]


        return render_template('cad_categorias.html', nome=session['nome'], id=id, img=caminho)




@app.route('/cadcategorias', methods=['POST'])
def cadcategorias():
    if 'id_usuario' not in session:
        flash('Precisa estar loggado')
        return redirect(url_for('login'))

    else:
        cursor = con.cursor()
        nome_categoria = request.form['nome_categoria'].lower()
        cor = request.form['cor']
        icone = request.form['icone']

        buscarCategorias(session['id_usuario'])

        if nome_categoria.strip() == "":
            flash('Preencha o campo para cadastrar!')
            return redirect(url_for('categorias'))

        cursor.execute("""SELECT 1
                          FROM CATEGORIA
                          WHERE LOWER(NOME) = ? AND COR = ?""",
                       (nome_categoria, cor))

        if cursor.fetchone() is not None:
            flash("Erro: Categoria já cadastrada!")
            return redirect(url_for('categorias'))

        else:
            id = session['id_usuario']

            try:
                cursor.execute("""INSERT INTO CATEGORIA
                                  (NOME, STATUS, ID_USUARIO, COR, ICONE)
                                  VALUES (?, ?, ?, ?, ?)""",
                               (nome_categoria, 0, id, cor, icone))

                con.commit()
                flash('Categoria cadastrada com sucesso!')

            except Exception as e:
                flash(f"Ocorreu um erro! -> {e}")
                con.rollback()

            finally:
                if cursor:
                 cursor.close()

            return redirect(url_for('categorias'))


def buscarCategorias(id):
    id = session['id_usuario']

    cursor = con.cursor()
    cursor.execute("""SELECT ID_CATEGORIA, NOME, STATUS
                             FROM CATEGORIA
                             WHERE id_usuario = ?""", (id,))
    categorias = cursor.fetchall()
    cursor.close()
    if not categorias:
        categorias = ''

    return categorias


@app.route('/movimentacoes')
def movimentacoes():
    if 'id_usuario' not in session:
        flash('Precisa estar loggado', 'error')
        return redirect(url_for('login'))
    else:
        id = session['id_usuario']
        data = date.today()
        print(id)
        categorias = buscarCategorias(id)
        print(categorias)
        usuario = buscarUsuario(id)
        caminho = "img/capas/" + str(usuario[0]) + ".jpg"
        if not os.path.exists(f'static/{caminho}'):
            caminho = 'img/capas/SEMIMAGEM.jpg'
        return render_template('cad_movimentacoes.html', nome=session['nome'], categorias=categorias, data=data, img=caminho)


@app.route('/cadmovimentacoes', methods=['POST'])
def cadmovimentacoes():
    if 'id_usuario' not in session:
        flash('Precisa estar loggado', 'error')
        return redirect(url_for('login'))
    else:
        id = session['id_usuario']
        cursor = con.cursor()
        tipo = request.form['tipo']
        print(tipo)
        categoria = request.form['categoria']
        data = date.today()
        descricao = request.form['descricao']
        valor = request.form['valor']

        try:
            cursor.execute("""INSERT INTO movimentacao (id_usuario, tipo, id_categoria, data_movimentacao, descricao, valor_total, status)
                                          values (?,?,?,?,?,?,?)""", (id, tipo, categoria, data, descricao, valor, 0))
            con.commit()
            flash('Movimentação cadastrada com sucesso!', 'success')

        except Exception as e:
            flash(f"Ocorreu um erro! -> {e}", 'error')
            con.rollback()

        finally:
            cursor.close()

        return redirect(url_for('historico_movimentacoes'))  # mudar para colocar editar

@app.route('/historico_movimentacoes', methods=['GET', 'POST'])
def historico_movimentacoes():
    if 'id_usuario' not in session:
        flash('Precisa estar loggado', 'error')
        return redirect(url_for('login'))

    else:
        banco = """SELECT M.DATA_MOVIMENTACAO
                           , CASE M.TIPO
                                WHEN 1 THEN 'Despesa'
                                WHEN 0 THEN 'Receita'
                                ELSE ''
                             END AS tipo
                           , c.nome nome_categoria
                           , M.DESCRICAO
                           , M.VALOR_TOTAL
                           , M.STATUS
                           , M.ID_MOVIMENTACAO
                    FROM MOVIMENTACAO m
                    LEFT JOIN CATEGORIA c ON c.id_categoria = m.ID_CATEGORIA
                    WHERE m.ID_USUARIO = ?"""

        parametros = [session['id_usuario']]

        if request.method == 'POST':
            tipo = request.form['tipo']
            descricao = request.form['descricao'].lower()
            categoria = request.form['categoria']
            data_inicial = request.form['data_inicial']
            data_final = request.form['data_final']

            if descricao:
                banco += ' AND lower(m.descricao) LIKE ? '
                parametros.append(f'%{descricao}%')

            if tipo:
                banco += ' AND m.tipo = ? '
                parametros.append(tipo)

            if categoria:
                banco += ' AND m.id_categoria = ? '
                parametros.append(categoria)

            if data_inicial and data_final:
                banco += ' AND m.data_movimentacao BETWEEN ? AND ? '
                parametros.append(data_inicial)
                parametros.append(data_final)

        cursor = con.cursor()
        cursor.execute(banco, parametros)

        movimentacoes = cursor.fetchall()
        cursor.close()
        print(movimentacoes)

        data = date.today()
        categorias = buscarCategorias(session['id_usuario'])

        usuario = buscarUsuario(id)
        caminho = "img/capas/" + str(usuario[0]) + ".jpg"
        if not os.path.exists(f'static/{caminho}'):
            caminho = 'img/capas/SEMIMAGEM.jpg'

        return (render_template(
            'historico_movimentacoes.html',
            movimentacoes=movimentacoes,
            data=data,
            nome=session['nome'],
            categorias=categorias, img=caminho
        ))

@app.route('/excluir_movimentacao/<int:id>', methods=['POST'])
def excluir_movimentacao(id):
    if 'id_usuario' not in session:
        flash('Precisa estar logado', 'error')
        return redirect(url_for('login'))
    else:
        cursor = con.cursor()

        try:
            cursor.execute("""
                DELETE FROM MOVIMENTACAO
                WHERE ID_MOVIMENTACAO = ?
                AND ID_USUARIO = ?
            """, (id, session['id_usuario']))

            con.commit()
            flash('Movimentação deletado com sucesso!', 'success')
            return redirect(url_for('historico_movimentacoes'))

        except Exception as e:
            con.rollback()
            flash(f'Ocorreu um erro -> {e}', 'error')
            return redirect(url_for('historico_movimentacoes'))

        finally:
            cursor.close()


def calcula_valor_dia(qtd_trabalhadores, vn_PACOTES_COLETADOS):
    id_usuario = session['id_usuario']
    cursor = None

    try:
        cursor = con.cursor()
        cursor.execute('''
           SELECT
               u.VALOR_DIARIO_PADRAO,
               u.VALOR_DIARIO_EXCEPCIONAL,
               u.VALOR_PACOTES,
               u.MIN_PACOTES,
               u.MIN_TRABALHADORES
           FROM USUARIO u
           WHERE u.id_usuario = ?
       ''', (id_usuario,))

        usuario = cursor.fetchone()

        vn_valor_diario_padrao, vn_valor_diario_excepcional, vn_valor_pacotes, vn_min_pacotes, vn_min_trabalhadores = usuario

        if qtd_trabalhadores <= int(vn_min_trabalhadores):
            if vn_min_pacotes < vn_PACOTES_COLETADOS:
                vn_valor_dia_total = (
                        vn_valor_pacotes * vn_PACOTES_COLETADOS
                        + vn_valor_diario_excepcional
                )
            else:
                vn_valor_dia_total = (
                    vn_valor_diario_excepcional
                )
        else:
            if vn_min_pacotes < vn_PACOTES_COLETADOS:
                vn_valor_dia_total = (
                        vn_valor_pacotes * vn_PACOTES_COLETADOS
                        + vn_valor_diario_padrao
                )
            else:
                vn_valor_dia_total = (
                    vn_valor_diario_padrao
                )

        return vn_valor_dia_total

    except Exception as e:
        flash(f'Deu erro {e}', 'error')
        return None


    finally:
        if cursor is not None:
            cursor.close()


# TUDO RELACIONADO AO TRABALHO DIÁRIO:
@app.route('/trabalho_diario')
def trabalho_diario():
    if 'id_usuario' not in session:
        flash('Precisa estar loggado', 'error')
        return redirect(url_for('login'))
    else:
        nome = buscarUsuario(id)[1]
        data = date.today()
        usuario = buscarUsuario(id)
        caminho = "img/capas/" + str(usuario[0]) + ".jpg"
        if not os.path.exists(f'static/{caminho}'):
            caminho = 'img/capas/SEMIMAGEM.jpg'
        return render_template('trabalho_diario.html', nome=nome, data=data, img=caminho)


@app.route('/adicionar_trabalho', methods=['GET', 'POST'])
def adicionar_trabalho():
    cursor = None
    try:
        if request.method == 'POST':
            id = session['id_usuario']
            pacotes = request.form['pacotes']
            trabalhadores = request.form['trabalhadores']
            data = date.today()

            if pacotes.strip() != "" and trabalhadores.strip() != "":
                valor_dia_total = calcula_valor_dia(
                    int(trabalhadores), int(pacotes)
                )

                cursor = con.cursor()
                cursor.execute("""
                   INSERT INTO servico_diario (
                       PACOTES_COLETADOS,
                       QTD_TRABALHADORES,
                       DATA_SERVICO_DIARIO,
                       id_usuario,
                       VALOR_DIA_TOTAL,
                       STATUS
                   )
                   VALUES (?, ?, ?, ?, ?, ?)
               """, (pacotes, trabalhadores, data, id, valor_dia_total, 0))

                con.commit()
                flash("Serviço diário cadastrado com sucesso!", 'success')
                return redirect(url_for('historico_trabalho'))

            else:
                flash("Não podem existir campos nulos!", 'error')
                return redirect(url_for('trabalho_diario'))

    except Exception as e:
        print(e)
        flash(f"Ocorreu um erro! -> {e}", 'error')
        return redirect(url_for('trabalho_diario'))
    finally:
        if cursor is not None:
            cursor.close()
    return render_template('historico_trabalho.html')


@app.route('/historico_trabalho', methods=['GET', 'POST'])
def historico_trabalho():
    if 'id_usuario' not in session:
        flash('Precisa estar loggado', 'error')
        return redirect(url_for('login'))

    else:
        banco = """SELECT sd.DATA_SERVICO_DIARIO 
                     ,sd.PACOTES_COLETADOS 
                     ,sd.QTD_TRABALHADORES 
                     ,sd.VALOR_DIA_TOTAL 
                     ,sd.ID_SERVICO_DIARIO
                     ,sd.STATUS
                    FROM SERVICO_DIARIO sd
                    WHERE SD.ID_USUARIO = ?"""

        parametros = [session['id_usuario']]

        if request.method == 'POST':
            data_inicial = request.form['data_inicial']
            data_final = request.form['data_final']

            if data_inicial and data_final:
                banco += ' AND data_servico_diario BETWEEN ? AND ? '
                parametros.append(data_inicial)
                parametros.append(data_final)

        cursor = con.cursor()
        cursor.execute(banco, parametros)

        trabalhos = cursor.fetchall()
        cursor.close()

        nome = buscarUsuario(id)[1]
        data = date.today()
        usuario = buscarUsuario(id)
        caminho = "img/capas/" + str(usuario[0]) + ".jpg"
        if not os.path.exists(f'static/{caminho}'):
            caminho = 'img/capas/SEMIMAGEM.jpg'
        return render_template('historico_trabalho.html', trabalhos=trabalhos, data=data, nome=nome, img=caminho)


@app.route('/editar_trabalho/<int:id>', methods=['GET', 'POST'])
def editar_trabalho(id):
    cursor = con.cursor()
    nome = buscarUsuario(id)[1]
    usuario = buscarUsuario(id)
    caminho = "img/capas/" + str(usuario[0]) + ".jpg"
    if not os.path.exists(f'static/{caminho}'):
        caminho = 'img/capas/SEMIMAGEM.jpg'

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

            flash("Registro de trabalho editado com sucesso!", 'success')
            return redirect(url_for('historico_trabalho'))

        return render_template(
            'editar_trabalho.html',
            servico=servico,
            id=id,
            nome=nome,
            img=caminho
        )

    except Exception as e:
        con.rollback()
        flash(f"Ocorreu um erro! -> {e}", 'error')
        return redirect(url_for('historico_trabalho'))

    finally:
        cursor.close()


@app.route('/excluir_trabalho/<int:id>', methods=['POST'])
def excluir_trabalho(id):
    if 'id_usuario' not in session:
        flash('Precisa estar logado', 'error')
        return redirect(url_for('login'))
    else:
        cursor = con.cursor()

        try:
            cursor.execute("""
                DELETE FROM MOVIMENTACAO
                WHERE ID_SERVICO_DIARIO = ?
            """, (id,))

            cursor.execute("""
                DELETE FROM SERVICO_DIARIO
                WHERE ID_SERVICO_DIARIO = ?
                AND ID_USUARIO = ?
            """, (id, session['id_usuario']))

            con.commit()
            flash('Serviço diário deletado com sucesso!', 'success')
            return redirect(url_for('historico_trabalho'))

        except Exception as e:
            con.rollback()
            flash(f'Ocorreu um erro -> {e}', 'error')
            return redirect(url_for('historico_trabalho'))

        finally:
            cursor.close()


# TUDO RELACIONADO A SERVIÇO EXTRA
@app.route('/servico_extra')
def servico_extra():
    if 'id_usuario' not in session:
        flash('Precisa estar loggado', 'error')
        return redirect(url_for('login'))
    else:
        nome = buscarUsuario(id)[1]
        data = date.today()
        usuario = buscarUsuario(id)
        caminho = "img/capas/" + str(usuario[0]) + ".jpg"
        if not os.path.exists(f'static/{caminho}'):
            caminho = 'img/capas/SEMIMAGEM.jpg'
        return render_template('servico_extra.html', nome=nome, data=data, img=caminho)


@app.route('/cadastrar_servico', methods=['GET', 'POST'])
def cadastrar_servico():
    try:
        if request.method == 'POST':
            id = session['id_usuario']
            servico = request.form['servico']
            valor = request.form['valor']
            data = date.today()
            cursor = con.cursor()
            if valor.strip() and servico.strip() != "":
                cursor.execute("""INSERT INTO SERVICO_EXTRA (servico,DATA_SERVICO_EXTRA,
                                           VALOR_RECEBIDO, id_usuario, status) values(?,?,?,?,?)""",
                               (servico, data, valor, id, 0))
                con.commit()

                flash("Serviço extra cadastrado com sucesso!", 'success')

            else:
                flash('Não podem existir campos nulos!', 'error')

    except Exception as e:
        print(e)
        flash(f"Ocorreu um erro! -> {e}", 'error')

    finally:
        return redirect(url_for('historico_servico_extra'))

@app.route('/excluir_servico_extra/<int:id>', methods=['POST'])
def excluir_servico_extra(id):
    if 'id_usuario' not in session:
        flash('Precisa estar logado', 'error')
        return redirect(url_for('login'))
    else:
        cursor = con.cursor()

        try:
            cursor.execute("""
                DELETE FROM MOVIMENTACAO
                WHERE ID_SERVICO_EXTRA = ?
            """, (id,))

            cursor.execute("""
                DELETE FROM SERVICO_EXTRA
                WHERE ID_SERVICO_EXTRA = ?
                AND ID_USUARIO = ?
            """, (id, session['id_usuario']))

            con.commit()
            flash('Serviço diário deletado com sucesso!')
            return redirect(url_for('historico_servico_extra'))

        except Exception as e:
            con.rollback()
            flash(f'Ocorreu um erro -> {e}', 'error')
            return redirect(url_for('historico_servico_extra'))

        finally:
            cursor.close()

@app.route('/alterar_status_extra/<int:id>', methods=['POST'])
def alterar_status_extra(id):
    if 'id_usuario' not in session:
        flash('Precisa estar logado', 'error')
        return redirect(url_for('login'))

    else:
        cursor = con.cursor()
        cursor.execute("""SELECT STATUS FROM SERVICO_EXTRA WHERE ID_SERVICO_EXTRA = ? AND ID_USUARIO = ?""", (id, session['id_usuario']))
        status = cursor.fetchone()[0]
        print(status)

        try:

            if status == 0:
                cursor.execute("""UPDATE SERVICO_EXTRA SET STATUS = 1 WHERE ID_SERVICO_EXTRA = ?""", (id,))
                con.commit()
                flash('Status alterado com sucesso!', 'success')

            elif status == 1:
                cursor.execute("""UPDATE SERVICO_EXTRA SET STATUS = 0 WHERE ID_SERVICO_EXTRA = ?""", (id,))
                con.commit()
                flash('Status alterado com sucesso!', 'success')

            return redirect(url_for('historico_servico_extra'))

        except Exception as e:
            con.rollback()
            flash(f'Ocorreu um erro -> {e}', 'error')
            return redirect(url_for('historico_servico_extra'))

        finally:
            cursor.close()



@app.route('/alterar_status_movimentacao/<int:id>', methods=['POST'])
def alterar_status_movimentacao(id):
    print('entrei')
    if 'id_usuario' not in session:
        flash('Precisa estar logado', 'error')
        return redirect(url_for('login'))

    else:
        print('2')
        cursor = con.cursor()
        cursor.execute("""SELECT STATUS FROM MOVIMENTACAO WHERE ID_MOVIMENTACAO = ? AND ID_USUARIO = ?""", (id, session['id_usuario']))
        status = cursor.fetchone()[0]
        print(status)

        try:

            if status == 0:
                print('3')
                cursor.execute("""UPDATE MOVIMENTACAO SET STATUS = 1 WHERE ID_MOVIMENTACAO = ?""", (id,))
                con.commit()
                flash('Status alterado com sucesso!', 'success')

            elif status == 1:
                print('4')
                cursor.execute("""UPDATE MOVIMENTACAO SET STATUS = 0 WHERE ID_MOVIMENTACAO = ?""", (id,))
                con.commit()
                flash('Status alterado com sucesso!', 'success')

            print('5')
            return redirect(url_for('historico_movimentacoes'))

        except Exception as e:
            con.rollback()
            flash(f'Ocorreu um erro -> {e}', 'error')
            return redirect(url_for('historico_movimentacoes'))

        finally:
            cursor.close()

@app.route('/alterar_status_trabalho/<int:id>', methods=['POST'])
def alterar_status_trabalho(id):
    if 'id_usuario' not in session:
        flash('Precisa estar logado', 'error')
        return redirect(url_for('login'))

    else:
        cursor = con.cursor()
        cursor.execute("""SELECT STATUS FROM SERVICO_DIARIO WHERE ID_SERVICO_DIARIO = ? AND ID_USUARIO = ?""", (id, session['id_usuario']))
        status = cursor.fetchone()[0]

        try:

            if status == 0:
                cursor.execute("""UPDATE SERVICO_DIARIO SET STATUS = 1 WHERE ID_SERVICO_DIARIO = ?""", (id,))
                con.commit()
                flash('Status alterado com sucesso!', 'success')

            elif status == 1:
                cursor.execute("""UPDATE SERVICO_DIARIO SET STATUS = 0 WHERE ID_SERVICO_DIARIO = ?""", (id,))
                con.commit()
                flash('Status alterado com sucesso!', 'success')

            return redirect(url_for('historico_trabalho'))

        except Exception as e:
            con.rollback()
            flash(f'Ocorreu um erro -> {e}', 'error')
            return redirect(url_for('historico_trabalho'))

        finally:
            cursor.close()

@app.route('/historico_servico_extra', methods=['GET', 'POST'])
def historico_servico_extra():
    if 'id_usuario' not in session:
        flash('Precisa estar logado', 'error')
        return redirect(url_for('login'))

    banco = """SELECT
                se.ID_SERVICO_EXTRA,
                se.ID_USUARIO,
                se.DATA_SERVICO_EXTRA,
                se.SERVICO,
                se.VALOR_RECEBIDO,
                se.STATUS
            FROM SERVICO_EXTRA se
            WHERE se.ID_USUARIO = ?"""

    parametros = [session['id_usuario']]

    if request.method == 'POST':

        status = request.form['status']
        data_inicial = request.form['data_inicial']
        data_final = request.form['data_final']

        if status:
            banco += ' AND se.status = ? '
            parametros.append(status)

        if data_inicial and data_final:
            banco += ' AND se.data_servico_extra BETWEEN ? AND ? '
            parametros.append(data_inicial)
            parametros.append(data_final)

    cursor = con.cursor()

    try:
        cursor.execute(banco, parametros)

        servicos = cursor.fetchall()

        nome = buscarUsuario(session['id_usuario'])[1]
        data = date.today()
        usuario = buscarUsuario(id)
        caminho = "img/capas/" + str(usuario[0]) + ".jpg"
        if not os.path.exists(f'static/{caminho}'):
            caminho = 'img/capas/SEMIMAGEM.jpg'

        return render_template(
                                'historico_servico_extra.html',
                                servicos=servicos,
                                data=data,
                                nome=nome,
                                img=caminho)

    except Exception as e:
        con.rollback()
        flash(f'Ocorreu um erro -> {e}', 'error')
        return redirect(url_for('historico_servico_extra'))

    finally:
        cursor.close()

#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
#ROTAS DE CÁLCULO AUTOMÁTICO DE SALDO
#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
def calcular_receitas():
    data = date.today()
    banco = """ SELECT cast(SUM(VALOR_TOTAL) as numeric(15,2))
            FROM MOVIMENTACAO
            WHERE ID_USUARIO = ?
            AND TIPO = 0
            AND STATUS = 0"""

    parametros = [session['id_usuario']]

    if request.method == 'POST':
        ano = request.form.get('ano', data.year)
        mes = request.form.get('mes', data.month)

        if ano:
            banco += ' AND EXTRACT(YEAR FROM DATA_MOVIMENTACAO) = ?'
            parametros.append(ano)

        if mes and int(mes) != 0:
            banco += ' AND EXTRACT(MONTH FROM DATA_MOVIMENTACAO) = ?'
            parametros.append(mes)

    cursor = con.cursor()
    try:
        cursor.execute(banco, parametros)

        receitas = cursor.fetchone()[0]
        print('aqui tem as despesas ' + str(receitas))

        if receitas is None:
            receitas = 0

        return receitas
    finally:
        cursor.close()


def calcular_despesas():
    data = date.today()
    banco = """ SELECT cast(SUM(VALOR_TOTAL) as numeric(15,2))
            FROM MOVIMENTACAO
            WHERE ID_USUARIO = ?
            AND TIPO = 1
            AND STATUS = 0"""

    parametros = [session['id_usuario']]

    if request.method == 'POST':
        ano = request.form.get('ano', data.year)
        mes = request.form.get('mes', data.month)

        if ano:
            banco += ' AND EXTRACT(YEAR FROM DATA_MOVIMENTACAO) = ?'
            parametros.append(ano)

        if mes and int(mes) != 0:
            banco += ' AND EXTRACT(MONTH FROM DATA_MOVIMENTACAO) = ?'
            parametros.append(mes)

    cursor = con.cursor()
    try:
        cursor.execute(banco, parametros)

        despesas = cursor.fetchone()[0]
        print('aqui tem as despesas ' + str(despesas))

        if despesas is None:
            despesas = 0

        return despesas
    finally:
        cursor.close()

def calcular_saldo():
    data = date.today()
    banco_receitas = """SELECT cast(SUM(VALOR_TOTAL) as numeric(15,2))
                FROM MOVIMENTACAO
                WHERE ID_USUARIO = ?
                AND TIPO = 0
                AND STATUS = 0"""

    banco_despesas = """SELECT cast(SUM(VALOR_TOTAL) as numeric(15,2))
                    FROM MOVIMENTACAO
                    WHERE ID_USUARIO = ?
                    AND TIPO = 1
                    AND STATUS = 0"""

    parametros = [session['id_usuario']]

    if request.method == 'POST':
        ano = request.form.get('ano',data.year)
        mes = request.form.get('mes', data.month)

        if ano:
            banco_despesas += ' AND EXTRACT(YEAR FROM DATA_MOVIMENTACAO) = ? '
            banco_receitas += ' AND EXTRACT(YEAR FROM DATA_MOVIMENTACAO) = ? '
            parametros.append(ano)
            # parametros.append(ano)

        if mes and int(mes) != 0:
            banco_despesas += ' AND EXTRACT(MONTH FROM DATA_MOVIMENTACAO) = ? '
            banco_receitas += ' AND EXTRACT(MONTH FROM DATA_MOVIMENTACAO) = ? '
            parametros.append(mes)
            # parametros.append(mes)
    print(parametros)

    cursor = con.cursor()

    cursor.execute(banco_receitas,parametros)

    receitas = cursor.fetchone()[0]
    print(receitas)

    if receitas is None:
        receitas = 0

    cursor.execute(banco_despesas,parametros)

    despesas = cursor.fetchone()[0]
    print(despesas)

    if despesas is None:
        despesas = 0

    saldo = receitas - despesas
    cursor.close()
    return saldo

def calcular_servico_extra():
    data = date.today()
    banco = """ SELECT cast(SUM(VALOR_RECEBIDO) as numeric(15,2))
            FROM SERVICO_EXTRA
            WHERE ID_USUARIO = ?
            AND STATUS = 0"""

    parametros = [session['id_usuario']]

    if request.method == 'POST':
        ano = request.form.get('ano', data.year)
        mes = request.form.get('mes', data.month)

        if ano:
            banco += ' AND EXTRACT(YEAR FROM DATA_SERVICO_EXTRA) = ?'
            parametros.append(ano)

        if mes and int(mes) != 0:
            banco += ' AND EXTRACT(MONTH FROM DATA_SERVICO_EXTRA) = ?'
            parametros.append(mes)

    cursor = con.cursor()
    try:
        cursor.execute(banco, parametros)

        extras = cursor.fetchone()[0]

        if extras is None:
            extras = 0

        return extras
    finally:
        cursor.close()


@app.route('/editar_servico_extra/<int:id>', methods=['GET', 'POST'])
def editar_servico_extra(id):
    if 'id_usuario' not in session:
        flash('Precisa estar logado', 'error')
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
            flash('Serviço extra não encontrado!', 'error')
            return redirect(url_for('historico_servico_extra'))

        if request.method == 'POST':
            nome_servico = request.form['servico'].strip()
            valor = float(request.form['valor'].replace(',', '.'))

            if not nome_servico or valor <= 0:
                flash('Informe um serviço e um valor válido!', 'error')
                return redirect(url_for('editar_servico_extra', id=id))

            cursor.execute("""
                UPDATE SERVICO_EXTRA
                SET SERVICO = ?, VALOR_RECEBIDO = ?
                WHERE ID_SERVICO_EXTRA = ?
                AND ID_USUARIO = ?
            """, (nome_servico, valor, id, session['id_usuario']))

            con.commit()
            flash('Serviço extra editado com sucesso!', 'success')
            return redirect(url_for('historico_servico_extra'))

        nome = buscarUsuario(session['id_usuario'])[1]
        usuario = buscarUsuario(id)
        caminho = "img/capas/" + str(usuario[0]) + ".jpg"
        if not os.path.exists(f'static/{caminho}'):
            caminho = 'img/capas/SEMIMAGEM.jpg'

        return render_template(
            'editar_servico_extra.html',
            servico=servico,
            id=id,
            nome=nome,
            img=caminho
        )

    except Exception as e:
        con.rollback()
        flash(f'Ocorreu um erro: {e}', 'error')
        return redirect(url_for('historico_servico_extra'))

    finally:
        cursor.close()

@app.route('/editar_receita_e_depesa/<int:id>', methods=['GET', 'POST'])
def editar_receita_e_despesa(id):

    cursor = con.cursor()
    if 'id_usuario' not in session:
        flash('Precisa estar logado', 'error')
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
            flash("Receita/Despesa NÃO encontrada", 'error')
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

            flash("Registro de receitas/trabalhos editado com sucesso!", 'success')
            return redirect(url_for('historico_movimentacoes'))

        categorias = buscarCategorias(session['id_usuario'])
        usuario = buscarUsuario(id)
        caminho = "img/capas/" + str(usuario[0]) + ".jpg"
        if not os.path.exists(f'static/{caminho}'):
            caminho = 'img/capas/SEMIMAGEM.jpg'

        return render_template(
            'editar_movimentacoes.html',
            movimentacoes=movimentacoes,
            categorias=categorias,
            id=id,
            nome=nome,
            img=caminho
        )

    except Exception as e:
        con.rollback()
        flash(f"Ocorreu um erro! -> {e}", 'error')
        return redirect(url_for('historico_movimentacoes'))

    finally:
        cursor.close()



@app.route('/editar_categorias/<int:id>', methods=['GET', 'POST'])
def editar_categorias(id):
   if 'id_usuario' not in session:
       flash('Precisa estar logado')
       return redirect(url_for('login'))

   cursor = con.cursor()

   try:
       cursor.execute("""
           SELECT NOME, STATUS, cor, icone
           FROM CATEGORIA
           WHERE ID_CATEGORIA = ?
             AND ID_USUARIO = ?
       """, (id, session['id_usuario']))

       categoria = cursor.fetchone()

       if categoria is None:
           flash('Categoria não encontrada!')
           return redirect(url_for('listar_categorias'))

       if id in [1001, 1002]:
           flash('Esta categoria não pode ser editada.')
           return redirect(url_for('listar_categorias'))


       if request.method == 'POST':
           nome_categoria = request.form['nome_categoria']
           nome_categoria.strip().lower()
           cor = request.form['cor']
           icone = request.form['icone']

           if not nome_categoria:
               flash('Informe o nome da categoria!')
               nome = buscarUsuario(session['id_usuario'])[1]
               usuario = buscarUsuario(id)
               caminho = "img/capas/" + str(usuario[0]) + ".jpg"
               if not os.path.exists(f'static/{caminho}'):
                   caminho = 'img/capas/SEMIMAGEM.jpg'

               return render_template(
                   'editar_categorias.html',
                   id=id,
                   nome=nome,
                   categoria=categoria,
                   img=caminho
               )

           cursor.execute("""
               SELECT 1
               FROM CATEGORIA
               WHERE LOWER(NOME) = ? 
                 AND ID_CATEGORIA != ?
           """, (nome_categoria, id))

           if cursor.fetchone() is not None:
               flash('Erro: Categoria já cadastrada!')
               nome = buscarUsuario(session['id_usuario'])[1]
               usuario = buscarUsuario(id)
               caminho = "img/capas/" + str(usuario[0]) + ".jpg"
               if not os.path.exists(f'static/{caminho}'):
                   caminho = 'img/capas/SEMIMAGEM.jpg'
               return render_template(
                   'editar_categorias.html',
                   id=id,
                   nome=nome,
                   categoria=(nome_categoria, categoria[1], cor, icone),
                   img=caminho
               )

           cursor.execute("""
               UPDATE CATEGORIA
               SET NOME = ?, 
               cor = ?,
               icone= ?
               WHERE ID_CATEGORIA = ?
                 AND ID_USUARIO = ?
           """, (
               nome_categoria,
               cor,
               icone,
               id,
               session['id_usuario']
           ))

           con.commit()
           flash('Categoria editada com sucesso!')
           return redirect(url_for('listar_categorias'))

       nome = buscarUsuario(session['id_usuario'])[1]
       usuario = buscarUsuario(id)
       caminho = "img/capas/" + str(usuario[0]) + ".jpg"
       if not os.path.exists(f'static/{caminho}'):
           caminho = 'img/capas/SEMIMAGEM.jpg'

       return render_template(
           'editar_categorias.html',
           id=id,
           nome=nome,
           categoria=categoria,
           img=caminho
       )

   except Exception as e:
       con.rollback()
       flash(f'Ocorreu um erro: {e}')
       return redirect(url_for('listar_categorias'))

   finally:
       cursor.close()


@app.route('/listar_categorias', methods=['GET', 'POST'])
def listar_categorias():
    if 'id_usuario' not in session:
        flash('Precisa estar logado')
        return redirect(url_for('login'))

    banco = """SELECT ID_CATEGORIA, NOME, STATUS, icone
                   FROM CATEGORIA
                   WHERE ID_USUARIO = ?"""

    parametros = [session['id_usuario']]

    if request.method == 'POST':
        nome_categoria = request.form['nome_categoria'].strip().lower()

        if nome_categoria:
            banco += " AND LOWER(NOME) LIKE ?"
            parametros.append(nome_categoria)

    cursor = con.cursor()
    cursor.execute(banco, parametros)
    categorias = cursor.fetchall()
    cursor.close()

    nome = session['nome']
    usuario = buscarUsuario(id)
    caminho = "img/capas/" + str(usuario[0]) + ".jpg"
    if not os.path.exists(f'static/{caminho}'):
        caminho = 'img/capas/SEMIMAGEM.jpg'
    return render_template('listar_categorias.html', categorias=categorias, nome=nome, img=caminho)



@app.route('/alterar_status_categoria/<int:id>', methods=['POST'])
def alterar_status_categoria(id):
    if 'id_usuario' not in session:
        flash('Precisa estar logado', 'error')
        return redirect(url_for('login'))

    else:
        cursor = con.cursor()
        cursor.execute("""SELECT STATUS FROM CATEGORIA WHERE ID_CATEGORIA = ? AND ID_USUARIO = ?""", (id, session['id_usuario']))
        status = cursor.fetchone()[0]

        try:

            if status == 0:
                cursor.execute("""UPDATE CATEGORIA SET STATUS = 1 WHERE ID_CATEGORIA = ?""", (id,))
                con.commit()
                flash('Status alterado com sucesso!', 'success')

            elif status == 1:
                cursor.execute("""UPDATE CATEGORIA SET STATUS = 0 WHERE ID_CATEGORIA = ?""", (id,))
                con.commit()
                flash('Status alterado com sucesso!', 'success')

            return redirect(url_for('listar_categorias'))

        except Exception as e:
            con.rollback()
            flash(f'Ocorreu um erro -> {e}')
            return redirect(url_for('listar_categorias'))

        finally:
            cursor.close()

#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
#TUDO QUE É RELACIONADO AOS GRÁFICOS, FUNÇÕES DE CRIAÇÃO
#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

#RECEITAS E DESPESAS (DASHBOARD E RELATÓRIOS)
def graficos_receitas_despesas(ano):
    cursor = con.cursor()
    print('1')
    id_usuario = session['id_usuario']
    print('2')
    print(id_usuario)
    print(ano)
    cursor.execute("""
            SELECT EXTRACT(MONTH from DATA_MOVIMENTACAO), TIPO, cast(coalesce(sum(VALOR_TOTAL),0) as numeric(15,2))n
            FROM MOVIMENTACAO
            where id_usuario = ?
            AND EXTRACT(YEAR FROM DATA_MOVIMENTACAO) = ?
            AND STATUS = 0
            GROUP BY 1,2
            ORDER BY 1, 2
        """,(id_usuario,ano))
    print('3')
    resultado = cursor.fetchall()
    print(resultado)
    cursor.close()

    dados = {}

    for linha in resultado:
        data = linha[0]
        tipo = linha[1]
        valor = linha[2]

        if data not in dados:
            dados[data] = [0, 0]

        if tipo == 0:
            dados[data][0] += valor
        elif tipo == 1:
            dados[data][1] += valor

    datas = sorted(dados.keys())

    receitas = [dados[data][0] for data in datas]
    despesas = [dados[data][1] for data in datas]

    grafico = pygal.Bar(
        style=pygal.style.Style(
            background='transparent',
            plot_background='transparent',
            foreground='#6B7280',
            foreground_strong='#374151',
            foreground_subtle='#DCE8F0',
            colors=['#0D7C4E', '#72D99B'],
            title_font_size=18,
            label_font_size=12,
            major_label_font_size=10,
            legend_font_size=12,
            font_family='Arial',
            opacity=1,
            opacity_hover=0.85,
            tooltip_font_color= '#FFFFFF'
        ),
        height=400,
        show_legend=True,
        show_y_guides=True,
        show_x_guides=False,
        legend_at_bottom=True,
        rounded_bars=3,
        x_label_rotation=0
    )

    grafico.title = ''
    grafico.x_labels = [
        str(mes) for mes in datas
    ]

    grafico.add('Receitas', receitas)
    grafico.add('Despesas', despesas)

    caminho = os.path.join('static', 'graficos')
    os.makedirs(caminho, exist_ok=True)

    caminho_svg = os.path.join(caminho, 'grafico.svg')
    grafico.render_to_file(caminho_svg)

    return url_for('static', filename='graficos/grafico.svg')

#SALDO (DASHBOARD)
def grafico_saldo(id_usuario, ano, tipo):
    cursor = con.cursor()
    print('TIPO:', repr(tipo))
    if tipo == '0':
        cursor.execute("""
            SELECT DISTINCT
            (SELECT CAST(COALESCE(SUM(MO.VALOR_TOTAL), 0) AS NUMERIC(15,2))
            FROM MOVIMENTACAO MO
            WHERE MO.TIPO = 0
            AND MO.STATUS = 0
            AND MO.ID_USUARIO = M.ID_USUARIO
            AND EXTRACT(YEAR FROM MO.DATA_MOVIMENTACAO) = EXTRACT(YEAR FROM M.DATA_MOVIMENTACAO)
            AND EXTRACT(MONTH FROM MO.DATA_MOVIMENTACAO) = EXTRACT(MONTH FROM M.DATA_MOVIMENTACAO)) RECEITA,
        
            (SELECT CAST(COALESCE(SUM(MO.VALOR_TOTAL), 0) AS NUMERIC(18,2))
            FROM MOVIMENTACAO MO
            WHERE MO.TIPO = 1
            AND MO.STATUS = 0
            AND MO.ID_USUARIO = M.ID_USUARIO
            AND EXTRACT(YEAR FROM MO.DATA_MOVIMENTACAO) = EXTRACT(YEAR FROM M.DATA_MOVIMENTACAO)
            AND EXTRACT(MONTH FROM MO.DATA_MOVIMENTACAO) = EXTRACT(MONTH FROM M.DATA_MOVIMENTACAO)) DESPESA,
            EXTRACT(MONTH FROM M.DATA_MOVIMENTACAO) MES
            FROM MOVIMENTACAO M
            WHERE EXTRACT(YEAR FROM M.DATA_MOVIMENTACAO) = ?
            AND M.ID_USUARIO = ?
            AND M.STATUS = 0
            GROUP BY
                M.ID_USUARIO,
                EXTRACT(YEAR FROM M.DATA_MOVIMENTACAO),
                EXTRACT(MONTH FROM M.DATA_MOVIMENTACAO)
            ORDER BY 3 DESC
            """, (ano, id_usuario))
        print('CONSULTA EXECUTADA')

        print('ESTRUTURA:', cursor.description)



    elif tipo == '1':
        cursor.execute("""
            SELECT
                EXTRACT(YEAR FROM DATA_MOVIMENTACAO) ANO,

                CAST(COALESCE(SUM(
                    CASE WHEN TIPO = 0 THEN VALOR_TOTAL ELSE 0 END
                ), 0) AS NUMERIC(15,2)) RECEITA,

                CAST(COALESCE(SUM(
                    CASE WHEN TIPO = 1 THEN VALOR_TOTAL ELSE 0 END
                ), 0) AS NUMERIC(15,2)) DESPESA

            FROM MOVIMENTACAO

            WHERE ID_USUARIO = ?
            AND STATUS = 0

            GROUP BY EXTRACT(YEAR FROM DATA_MOVIMENTACAO)

            ORDER BY 1
        """, (id_usuario,))

    resultado = cursor.fetchall()

    print('RESULTADO:', resultado)
    cursor.close()

    meses = {
        1: 'Janeiro', 2: 'Fevereiro',
        3: 'Março', 4: 'Abril',
        5: 'Maio', 6: 'Junho',
        7: 'Julho', 8: 'Agosto',
        9: 'Setembro', 10: 'Outubro',
        11: 'Novembro', 12: 'Dezembro'
    }

    nomes_meses = []
    saldos = []

    if tipo == '0':
        for linha in reversed(resultado):
            receita = linha[0]
            despesa = linha[1]
            mes = int(linha[2])

            saldo = receita - despesa

            nomes_meses.append(meses[mes])
            saldos.append(float(saldo))

    elif tipo == '1':
        for linha in resultado:
            ano = int(linha[0])
            receita = linha[1]
            despesa = linha[2]

            saldo = receita - despesa

            nomes_meses.append(str(ano))
            saldos.append(float(saldo))

    grafico = pygal.Bar(
        style=pygal.style.Style(
            background='transparent',
            plot_background='transparent',
            foreground='#6B7280',
            foreground_strong='#374151',
            foreground_subtle='#DCE8F0',
            colors=['#0D7C4E'],
            title_font_size=18,
            label_font_size=12,
            major_label_font_size=10,
            legend_font_size=12,
            font_family='Arial',
            opacity=1,
            opacity_hover=0.85
        ),
        height=400,
        show_legend=False,
        show_y_guides=True,
        show_x_guides=False,
        rounded_bars=3,
        x_label_rotation=0
    )

    grafico.title = ''
    grafico.x_labels = nomes_meses

    grafico.add('Saldo', saldos)

    caminho = os.path.join('static', 'graficos')
    os.makedirs(caminho, exist_ok=True)

    caminho_svg = os.path.join(caminho, 'grafico_saldo.svg')
    grafico.render_to_file(caminho_svg)

    return url_for('static', filename='graficos/grafico_saldo.svg')

def grafico_categorias():
    cursor = con.cursor()
    id_usuario = session['id_usuario']
    cursor.execute("""SELECT
                        C.NOME,
                        CAST(COALESCE(SUM(M.VALOR_TOTAL), 0) AS NUMERIC(15,2)) AS TOTAL
                        FROM MOVIMENTACAO M
                        INNER JOIN CATEGORIA C
                            ON M.ID_CATEGORIA = C.ID_CATEGORIA
                        WHERE M.ID_USUARIO = ?
                        AND M.TIPO = 1
                        AND M.STATUS = 0
                        GROUP BY C.ID_CATEGORIA, C.NOME
                        ORDER BY TOTAL DESC
                        """, (id_usuario,))

    resultado = cursor.fetchall()
    print('RESULTADO:', resultado)
    categorias = []
    valores = []
    for linha in resultado:
        categoria = linha[0]
        valor = linha[1]

        categorias.append(categoria)
        valores.append(float(valor))

    print('CATEGORIAS:', categorias)
    print('VALORES:', valores)

    grafico = pygal.Bar(
        style=pygal.style.Style(
            background='transparent',
            plot_background='transparent',
            foreground='#6B7280',
            foreground_strong='#374151',
            foreground_subtle='#DCE8F0',
            colors=['#ED4D5D'],
            title_font_size=18,
            label_font_size=12,
            major_label_font_size=10,
            legend_font_size=12,
            font_family='Arial',
            opacity=1,
            opacity_hover=0.85
        ),
        height=400,
        show_legend=False,
        show_y_guides=True,
        show_x_guides=False,
        rounded_bars=3,
        x_label_rotation=0
    )

    grafico.x_labels = categorias
    grafico.add('Gastos', valores)

    caminho = os.path.join('static', 'graficos')
    os.makedirs(caminho, exist_ok=True)

    caminho_svg = os.path.join(caminho, 'grafico_categoria.svg')
    grafico.render_to_file(caminho_svg)
    return url_for('static', filename='graficos/grafico_categoria.svg')

#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
#AQUI ACABOU GRÁFICOS
#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

@app.route('/buscar-meses/<int:ano>', methods=['GET', 'POST'])
def buscar_Meses(ano):
    meses = buscarMeses(ano)
    meses = [mes[0] for mes in meses]

    return jsonify({'meses': meses})

@app.route('/relatorios', methods=['GET', 'POST'])
def relatorios():
    if 'id_usuario' not in session:
        flash('Precisa estar loggado', 'error')
        return redirect(url_for('login'))
    else:
        nome = session['nome']
        receitas = calcular_receitas()
        despesas = calcular_despesas()
        saldo = calcular_saldo()
        extras = calcular_servico_extra()
        data = date.today()
        ano = request.form.get('ano', data.year)
        grafico_movimentacoes = graficos_receitas_despesas(ano)
        anos = buscarAnos()
        meses = buscarMeses(ano)
        grafico_categoria = grafico_categorias()

    #tabela trabalho
    cursor = con.cursor()
    cursor.execute("""SELECT FIRST 6
                    sd.DATA_SERVICO_DIARIO 
                     ,sd.PACOTES_COLETADOS 
                     ,sd.QTD_TRABALHADORES 
                     ,sd.VALOR_DIA_TOTAL 
                     ,sd.ID_SERVICO_DIARIO
                     ,sd.STATUS
                    FROM SERVICO_DIARIO sd
                    WHERE SD.ID_USUARIO = ?
                    ORDER BY SD.DATA_SERVICO_DIARIO DESC""", (session['id_usuario'],))

    trabalhos = cursor.fetchall()
    cursor.close()

    # tabela movimentações
    cursor2 = con.cursor()
    cursor2.execute("""SELECT FIRST 6
                            M.DATA_MOVIMENTACAO
                           , CASE M.TIPO
                                WHEN 1 THEN 'Despesa'
                                WHEN 0 THEN 'Receita'
                                ELSE ''
                             END AS tipo
                           , c.nome nome_categoria
                           , M.DESCRICAO
                           , M.VALOR_TOTAL
                           , M.STATUS
                           , M.ID_MOVIMENTACAO
                    FROM MOVIMENTACAO m
                    LEFT JOIN CATEGORIA c ON c.id_categoria = m.ID_CATEGORIA
                    WHERE m.ID_USUARIO = ?
                    ORDER BY M.DATA_MOVIMENTACAO DESC""", (session['id_usuario'], ))
    movimentacoes = cursor2.fetchall()
    cursor2.close()
    usuario = buscarUsuario(id)
    caminho = "img/capas/" + str(usuario[0]) + ".jpg"
    if not os.path.exists(f'static/{caminho}'):
        caminho = 'img/capas/SEMIMAGEM.jpg'

    return render_template('relatorios.html',
                           nome=nome,
                           receitas=receitas,
                           despesas=despesas,
                           saldo=saldo,
                           extras=extras,
                           grafico_movimentacoes=grafico_movimentacoes,
                           grafico_categoria= grafico_categoria,
                           anos=anos,
                           meses=meses,
                           trabalhos=trabalhos,
                           movimentacoes=movimentacoes,
                           img=caminho)

@app.route('/previsoes', methods=['GET', 'POST'])
def previsoes():
    if 'id_usuario' not in session:
        flash('Precisa estar logado')
        return redirect(url_for('login'))

    hoje = date.today()

    if request.method == 'POST':
        data_inicial = date.fromisoformat(request.form['data_inicial'])
        data_final = date.fromisoformat(request.form['data_final'])
    else:
        data_inicial = hoje.replace(day=1)
        data_final = hoje

    if data_inicial > data_final:
        flash('A data inicial não pode ser posterior à data final.')
        return redirect(url_for('previsoes'))

    # Calcula o período do mês anterior
    ano = data_inicial.year
    mes = data_inicial.month - 1

    if mes == 0:
        mes = 12
        ano -= 1

    ultimo_dia = calendar.monthrange(ano, mes)[1]

    inicio_anterior = date(ano, mes, min(data_inicial.day, ultimo_dia))

    ano = data_final.year
    mes = data_final.month - 1

    if mes == 0:
        mes = 12
        ano -= 1

    ultimo_dia = calendar.monthrange(ano, mes)[1]

    fim_anterior = date(ano, mes, min(data_final.day, ultimo_dia))

    receitas, despesas, saldo = buscar_movimentacoes_periodo(
        session['id_usuario'], data_inicial, data_final
    )

    receitas_ant, despesas_ant, saldo_ant = buscar_movimentacoes_periodo(
        session['id_usuario'], inicio_anterior, fim_anterior
    )

    # Calcula as variações percentuais
    var_receitas = ((receitas - receitas_ant) / receitas_ant * 100
                    if receitas_ant != 0 else None)

    var_despesas = ((despesas - despesas_ant) / despesas_ant * 100
                    if despesas_ant != 0 else None)

    var_saldo = ((saldo - saldo_ant) / abs(saldo_ant) * 100
                 if saldo_ant != 0 else None)

    usuario = buscarUsuario(id)
    caminho = "img/capas/" + str(usuario[0]) + ".jpg"

    if not os.path.exists(os.path.join(app.static_folder, caminho)):
        caminho = "img/capas/semimagem.jpg"

    return render_template(
        'previsoes.html',
        nome=session['nome'],
        data_inicial=data_inicial,
        data_final=data_final,
        inicio_anterior=inicio_anterior,
        fim_anterior=fim_anterior,
        receitas=receitas,
        despesas=despesas,
        saldo=saldo,
        receitas_ant=receitas_ant,
        despesas_ant=despesas_ant,
        saldo_ant=saldo_ant,
        var_receitas=var_receitas,
        var_despesas=var_despesas,
        var_saldo=var_saldo,
        img=caminho
    )

def buscarAnos():
    id = session['id_usuario']

    cursor = con.cursor()
    cursor.execute("""SELECT DISTINCT 
                            extract(YEAR FROM DATA_MOVIMENTACAo) ano
                             FROM MOVIMENTACAO
                             WHERE id_usuario = ?""", (id,))
    anos = cursor.fetchall()
    cursor.close()
    if not anos:
        anos = ''

    return anos

def buscarMeses(ano):
    id = session['id_usuario']

    cursor = con.cursor()
    cursor.execute("""SELECT DISTINCT
                             extract(MONTH FROM DATA_MOVIMENTACAo) mes
                             FROM MOVIMENTACAO
                             WHERE id_usuario = ?
                             AND extract(YEAR FROM DATA_MOVIMENTACAo) = ? """, (id, ano))
    meses = cursor.fetchall()
    cursor.close()
    if not meses:
        meses = ''

    return meses

def buscar_movimentacoes_periodo(id_usuario, data_inicial, data_final):
    cursor = con.cursor()

    cursor.execute("""
        SELECT
            CAST(
                COALESCE(SUM(CASE
                    WHEN TIPO = 0 THEN VALOR_TOTAL
                    ELSE 0
                END), 0) AS DECIMAL(18,2)
            ),

            CAST(
                COALESCE(SUM(CASE
                    WHEN TIPO = 1 THEN VALOR_TOTAL
                    ELSE 0
                END), 0) AS DECIMAL(18,2)
            )

        FROM MOVIMENTACAO
        WHERE ID_USUARIO = ?
        AND DATA_MOVIMENTACAO BETWEEN ? AND ?
    """, (id_usuario, data_inicial, data_final))

    resultado = cursor.fetchone()
    cursor.close()

    receitas = resultado[0]
    despesas = resultado[1]
    saldo = receitas - despesas

    return receitas, despesas, saldo

### BAIXAR PDFS####
@app.route('/pdf_trabalho')
def pdf_trabalho():
   if 'id_usuario' not in session:
       return redirect(url_for('login'))


   cursor = con.cursor()


   cursor.execute("""
       SELECT DATA_SERVICO_DIARIO, PACOTES_COLETADOS,
              QTD_TRABALHADORES, VALOR_DIA_TOTAL
       FROM SERVICO_DIARIO
       WHERE ID_USUARIO = ?
   """, (session['id_usuario'],))


   trabalhos = cursor.fetchall()
   cursor.close()


   pdf = FPDF()
   pdf.add_page()


   # Titulo
   pdf.set_text_color(13, 124, 78)
   pdf.set_font("Arial", "B", 18)
   pdf.cell(190, 15, "Historico de Trabalho", align="C", ln=True)


   # Cabeçalho da tabela
   pdf.set_text_color(255, 255, 255)
   pdf.set_fill_color(13, 124, 78)
   pdf.set_font("Arial", "B", 10)


   pdf.cell(35, 10, "Data", 1, 0, "C", True)
   pdf.cell(35, 10, "Pacotes", 1, 0, "C", True)
   pdf.cell(45, 10, "Trabalhadores", 1, 0, "C",True )
   pdf.cell(65, 10, "Valor", 1, 1, "C",True )


   # Dados
   pdf.set_text_color(0, 0, 0)
   pdf.set_font("Arial", size=10)


   for trabalho in trabalhos:
       data = trabalho[0].strftime("%d/%m/%Y")
       valor = f"R$ {float(trabalho[3]):.2f}".replace(".", ",")


       pdf.cell(35, 10, data, 1)
       pdf.cell(35, 10, str(trabalho[1]), 1)
       pdf.cell(45, 10, str(trabalho[2]), 1)
       pdf.cell(65, 10, valor, 1)
       pdf.ln()




   pdf.output("relatorio_trabalho.pdf")


   return send_file(
       "relatorio_trabalho.pdf",
       as_attachment=True
   )

@app.route('/pdf_extra')
def pdf_extra():
   if 'id_usuario' not in session:
       return redirect(url_for('login'))


   cursor = con.cursor()


   cursor.execute("""
       SELECT SERVICO, DATA_SERVICO_EXTRA, VALOR_RECEBIDO
       FROM SERVICO_EXTRA
       WHERE ID_USUARIO = ?
       ORDER BY DATA_SERVICO_EXTRA
   """, (session['id_usuario'],))


   servicos = cursor.fetchall()
   cursor.close()


   pdf = FPDF()
   pdf.add_page()


   # Titulo
   pdf.set_text_color(13, 124, 78)
   pdf.set_font("Arial", "B", 18)
   pdf.cell(190, 15, "Historico de Servico Extra", align="C", ln=True)


   # Cabecalho
   pdf.set_text_color(255, 255, 255)
   pdf.set_fill_color(13, 124, 78)
   pdf.set_font("Arial", "B", 10)


   pdf.cell(60, 10, "Servico", 1, 0, "C", True)
   pdf.cell(50, 10, "Data", 1, 0, "C", True)
   pdf.cell(70, 10, "Valor Recebido", 1, 1, "C", True)


   # Dados
   pdf.set_text_color(0, 0, 0)
   pdf.set_font("Arial", size=10)


   for servico in servicos:
       nome = str(servico[0])
       data = servico[1].strftime("%d/%m/%Y")
       valor = f"R$ {float(servico[2]):.2f}".replace(".", ",")


       pdf.cell(60, 10, nome, 1)
       pdf.cell(50, 10, data, 1)
       pdf.cell(70, 10, valor, 1)
       pdf.ln()


   pdf.output("relatorio_extra.pdf")


   return send_file(
       "relatorio_extra.pdf",
       as_attachment=True
   )




if __name__ == '__main__':
    app.run(debug=True)