var selectAno = document.querySelector("#ano")
const mesesExibe = [
    '',
    'Janeiro',
    'Fevereiro',
    'Março',
    'Abril',
    'Maio',
    'Junho',
    'Julho',
    'Agosto',
    'Setembro',
    'Outubro',
    'Novembro',
    'Dezembro'
];

selectAno.addEventListener("change", async function(){
    var ano_selecionado = this.value
    var url = "http://127.0.0.1:5000/buscar-meses/" + ano_selecionado

    var resultado = await fetch(url, {
        method: "GET"
    })

    resultado = await resultado.json()
    var meses = resultado.meses

    if (meses.length > 0) {

        var html = "<option value='0'>Todos os meses</option>"

        for (let mes of meses) {
            html += "<option value='" + mes + "'>" +  mesesExibe[mes] +"</option>"
        }

        document.querySelector("#mes").innerHTML = html
        document.querySelector("#div-mes").style.display = "flex"
    }

})

// perguntas
// async e await 
// fetch -> pega e acessar a url
// url -> api -> seu sistema consegue acessar algo pela url
// rota no python -> somente para acessar os meses
// return jsonify({'meses': meses}) json -> comunicar o python e js (jinja)