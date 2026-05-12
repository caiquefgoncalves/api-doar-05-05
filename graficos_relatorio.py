from flask import jsonify, request, send_file
from main import app
from db import conexao
from funcao import decodificar_token
from fpdf import FPDF

@app.route('/minhas_doacoes', methods=['GET'])
def minhas_doacoes():
    """Retorna as doações e voluntariados do doador logado"""
    token_data = decodificar_token()
    if token_data == False:
        return jsonify({'error': 'Token necessário'}), 401
    if token_data['tipo'] != 1:
        return jsonify({'error': 'Apenas doadores podem acessar'}), 403

    id_doador = token_data['id_usuarios']

    con = conexao()
    cur = con.cursor()

    try:
        # Buscar doações monetárias
        cur.execute("""
            SELECT d.VALOR, d.DATA_DOACAO, p.TITULO, u.NOME as ONG_NOME, u.ID_USUARIOS as ONG_ID, 'Monetário' as TIPO
            FROM DOACOES d
            INNER JOIN PROJETOS p ON d.ID_PROJETOS = p.ID_PROJETOS
            INNER JOIN USUARIOS u ON p.ID_USUARIOS = u.ID_USUARIOS
            WHERE d.ID_USUARIOS = ?
            ORDER BY d.DATA_DOACAO DESC
        """, (id_doador,))
        doacoes = cur.fetchall()

        # Buscar voluntariados
        cur.execute("""
            SELECT v.ID_VOLUNTARIADO, p.TITULO, u.NOME as ONG_NOME, u.ID_USUARIOS as ONG_ID, 'Voluntariado' as TIPO
            FROM VOLUNTARIADO v
            INNER JOIN PROJETOS p ON v.ID_PROJETOS = p.ID_PROJETOS
            INNER JOIN USUARIOS u ON p.ID_USUARIOS = u.ID_USUARIOS
            WHERE v.ID_USUARIOS = ?
            ORDER BY v.ID_VOLUNTARIADO DESC
        """, (id_doador,))
        voluntariados = cur.fetchall()

        atividades = []

        for d in doacoes:
            data_str = ''
            if d[1]:
                try:
                    data_str = d[1].strftime('%d/%m/%Y')
                except:
                    data_str = str(d[1])
            atividades.append({
                'tipo': 'Monetário',
                'valor': f'R$ {d[0]:.2f}'.replace('.', ','),
                'projeto': d[2],
                'ong': d[3],
                'ong_foto': f'{d[4]}.jpeg',
                'data': data_str
            })

        for v in voluntariados:
            atividades.append({
                'tipo': 'Voluntariado',
                'valor': 'Mensagem enviada',
                'projeto': v[1],
                'ong': v[2],
                'ong_foto': f'{v[3]}.jpeg',
                'data': ''
            })

        return jsonify({'atividades': atividades, 'total': len(atividades)}), 200

    except Exception as e:
        print(f"ERRO minhas_doacoes: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        con.close()


@app.route('/frequencia_doacoes', methods=['GET'])
def frequencia_doacoes():
    """Retorna dados para o gráfico com todos os 12 meses"""
    token_data = decodificar_token()
    if token_data == False:
        return jsonify({'error': 'Token necessário'}), 401
    if token_data['tipo'] != 1:
        return jsonify({'error': 'Apenas doadores podem acessar'}), 403

    id_doador = token_data['id_usuarios']

    con = conexao()
    cur = con.cursor()

    try:
        # Buscar contagem de doações por mês
        cur.execute("""
            SELECT 
                EXTRACT(MONTH FROM d.DATA_DOACAO) as MES,
                COUNT(*) as QTD
            FROM DOACOES d
            WHERE d.ID_USUARIOS = ?
            GROUP BY EXTRACT(MONTH FROM d.DATA_DOACAO)
            ORDER BY MES
        """, (id_doador,))
        doacoes_mes = cur.fetchall()

        meses = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']

        # Criar dicionário com todos os meses zerados
        dados_meses = {mes: 0 for mes in meses}

        # Preencher com dados reais
        for d in doacoes_mes:
            if d[0] and 1 <= int(d[0]) <= 12:
                dados_meses[meses[int(d[0]) - 1]] = int(d[1])

        # Converter para lista
        dados = [{'mes': mes, 'qtd': qtd} for mes, qtd in dados_meses.items()]

        return jsonify({'dados': dados}), 200

    except Exception as e:
        print(f"ERRO frequencia_doacoes: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        con.close()


@app.route('/admin/relatorio_doadores', methods=['GET'])
def relatorio_doadores():
    # erro = validar_adm()
    # if erro:
    #     return erro

    con = conexao()
    cur = con.cursor()
    try:
        cur.execute("SELECT ID_USUARIOS, NOME, CPF_CNPJ, EMAIL FROM USUARIOS WHERE TIPO = 1")
        usuarios = cur.fetchall()

        if not usuarios:
            return jsonify({'error': 'Nenhum doador encontrado'}), 404

        pdf = FPDF()
        pdf.add_page()

        # 🎨 CORES
        azul = (12, 89, 139)
        azul_claro = (22, 124, 191)
        rosa = (246, 86, 130)
        laranja = (247, 181, 103)

            # 🖼️ LOGO (ajuste o caminho)
        # pdf.image('static/logo.png', x=80, y=10, w=50)
        pdf.ln(40)

            # 🧾 TÍTULO
        pdf.set_font("Arial", "B", 16)
        pdf.set_text_color(*azul)
        pdf.cell(0, 10, "Relatório de Doadores", ln=True, align="C")

        pdf.ln(5)

        # 🔸 LINHA DECORATIVA
        pdf.set_draw_color(*azul)
        pdf.set_line_width(1)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(10)

            # 📋 LISTA
        for u in usuarios:
            id_usuario = u[0]
            nome = u[1]
            cpf = u[2]
            email = u[3]

                # 🔹 Nome
            pdf.set_font("Arial", "B", 12)
            pdf.set_text_color(*azul)
            pdf.cell(0, 8, nome, ln=True)

                # 🔹 Infos
            pdf.set_font("Arial", "", 11)
            pdf.set_text_color(0, 0, 0)
            pdf.cell(0, 6, f"ID: {id_usuario}", ln=True)
            pdf.cell(0, 6, f"Email: {email}", ln=True)

                # 🔹 CPF (rosa)
            pdf.set_text_color(*rosa)
            pdf.cell(0, 6, f"CPF: {cpf}", ln=True)

                # 🔸 Separador (laranja)
            pdf.set_draw_color(*laranja)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())

            pdf.ln(5)

            # =========================
            # 📌 FOOTER ESTILO HTML
            # =========================

        pdf.set_y(-30)
        largura_total = 190
        bloco = largura_total / 4

        cores = [azul, azul_claro, laranja, rosa]
        x = 10

            # 🎨 barra colorida
        for cor in cores:
            pdf.set_fill_color(*cor)
            pdf.rect(x, pdf.get_y(), bloco, 4, 'F')
            x += bloco

        pdf.ln(6)

            # 🧱 fundo cinza
        pdf.set_fill_color(75, 77, 76)
        y_fundo = pdf.get_y()
        pdf.rect(10, y_fundo, 190, 20, 'F')

            # 📝 texto
        pdf.set_y(y_fundo + 6)
        pdf.set_text_color(200, 200, 200)
        pdf.set_font("Arial", "", 9)
        pdf.cell(0, 5, "© 2026 Doar + — Todos os direitos reservados.", 0, 1, "C")

        pdf_path = "relatorio_usuarios.pdf"
        pdf.output(pdf_path)
        return send_file(pdf_path, as_attachment=True, mimetype='application/pdf')


    except Exception as e:
        con.rollback()
        return jsonify({'error': f'Erro: {str(e)}'}), 500

    finally:
        cur.close()
        con.close()
