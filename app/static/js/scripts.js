
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


document.body.addEventListener('htmx:afterSwap', sincronizarPecas);

document.body.addEventListener('recebimentoEditado', function () {
    bootstrap.Modal.getOrCreateInstance(
        document.getElementById('modal_editar_recebimento')).hide();
    location.reload();
});


document.body.addEventListener('categoriaEditada', function () {
    bootstrap.Modal.getOrCreateInstance(
        document.getElementById('modal_editar')).hide();
    location.reload();
});