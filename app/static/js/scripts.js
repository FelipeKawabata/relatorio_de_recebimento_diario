// =====================================================================
// WIZARD DE RECEBIMENTO - transicoes entre os modais
// =====================================================================

// Etapa 2 -> 3: o servidor dispara este evento (HX-Trigger-After-Swap)
// depois de injetar o formulario no corpo do modal do checklist.
// O show() do segundo modal fica encadeado no 'hidden.bs.modal' do
// primeiro para as animacoes nao se atropelarem (backdrop preso).
document.body.addEventListener('abrirModalConferencia', function () {

    const elemento_modal_pedido = document.getElementById('janela_modal_recebimento');
    const modal_pedido = bootstrap.Modal.getOrCreateInstance(elemento_modal_pedido);
    const modal_checklist = bootstrap.Modal.getOrCreateInstance(
        document.getElementById('modal_recebimento'));

    elemento_modal_pedido.addEventListener('hidden.bs.modal',
                                           () => modal_checklist.show(),
                                           { once: true });

    modal_pedido.hide();
});


// Gravou com sucesso: fecha o checklist e recarrega a tabela da homepage.
document.body.addEventListener('recebimentoGravado', function () {
    bootstrap.Modal.getOrCreateInstance(
        document.getElementById('modal_recebimento')).hide();
    location.reload();
});


// =====================================================================
// FORMULARIO DE CONFERENCIA - pecas aprovadas / reprovadas
// =====================================================================

// Sem nao conformidade: reprovadas = 0 e aprovadas = quantidade total.
// Isto e apenas conveniencia - a rota /recebimento refaz a mesma conta
// no servidor antes de validar, que e onde a regra vale de verdade.
function sincronizarPecas() {

    const check = document.getElementById('houve_nao_conformidade');
    const total = document.getElementById('qt_total');
    const aprovadas = document.getElementById('pecas_aprovadas');
    const reprovadas = document.getElementById('pecas_reprovadas');

    if (!check || !total || !aprovadas || !reprovadas) return;

    if (!check.checked) {
        reprovadas.value = 0;
        aprovadas.value = total.value;
    }
}

// O formulario chega pelo HTMX depois desta pagina carregar, entao nao da
// para ligar o listener no campo direto - ele ainda nao existe. Escutamos
// no body (que sempre existe) e filtramos pelo id de quem disparou.
document.body.addEventListener('change', function (evento) {
    if (evento.target.id === 'houve_nao_conformidade') {
        sincronizarPecas();
    }
});

document.body.addEventListener('input', function (evento) {
    if (evento.target.id === 'qt_total') {
        sincronizarPecas();
    }
});

// Estado inicial: roda assim que o HTMX injeta qualquer fragmento.
document.body.addEventListener('htmx:afterSwap', sincronizarPecas);
