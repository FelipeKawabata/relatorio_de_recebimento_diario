from flask_wtf import FlaskForm
from wtforms import StringField, Form, SubmitField, BooleanField, IntegerField, FormField, SelectField, FieldList
from wtforms.validators import DataRequired, ValidationError, NumberRange, InputRequired
from flask import session


class GrupoMaterialForm(FlaskForm):
    nome = StringField('Nome do grupo de materiais',
                       validators=[DataRequired()])
    enviar_grupo_material = SubmitField('Adicionar grupo de materiais')


class ProcessoForm(FlaskForm):
    nome = StringField('Nome do processo/estado', validators=[DataRequired()])
    enviar_processo = SubmitField('Adicionar processo/estado')


class MaterialForm(FlaskForm):
    nome = StringField('Nome do material', validators=[DataRequired()])
    especificacao = StringField(
        'Especificação técnica', validators=[DataRequired()])
    grupo_id = SelectField('Grupo do material', coerce=int)
    enviar_material = SubmitField('Adicionar material')


class ListaInstrumentosForm(FlaskForm):
    nome = StringField('Nome', validators=[DataRequired()])
    descricao = StringField('Descrição')
    enviar_instrumento = SubmitField('Adicionar instrumento')


class PlanoControleForm(FlaskForm):
    nome = StringField('Nome', validators=[DataRequired()])
    descricao = StringField('Descrição')
    enviar_plano_controle = SubmitField('Adicionar plano de controle')


class InstrumentoMedicaoForm(Form):
    instrumento_id = SelectField('Instrumento', coerce=int)


class SuporteCorridaForm(Form):
    corrida = StringField('Corrida', validators=[DataRequired()])
    qtd_corrida = IntegerField('Quantidade da corrida', validators=[InputRequired(),
                                                                    NumberRange(min=1)])


class ConferenciaForm(FlaskForm):
    pedido = StringField('Pedido', validators=[DataRequired()])
    item = StringField('Item', validators=[DataRequired()])
    nota_fiscal = StringField('Nota Fiscal', validators=[DataRequired()])
    qt_total = IntegerField('Quantidade total', validators=[
                            NumberRange(min=1), InputRequired()])
    certificado = StringField(
        'Nº do certificado', filters=[lambda x: (x or '').strip() or None])
    corridas = FieldList(FormField(SuporteCorridaForm), min_entries=1)
    processo_id = SelectField('Processo/Estado', coerce=int)
    material_id = SelectField('Material', coerce=int)
    plano_controle_id = SelectField('Plano de controle', coerce=int)
    houve_nao_conformidade = BooleanField('Houve não conformidade')
    analise_certificado = BooleanField('Análise de certificado')
    analise_visual = BooleanField('Análise visual')
    identif_e_rastreabilidade = BooleanField(
        'Análise de identificação e rastreabilidade')
    dimensional = BooleanField('Análise dimensional')
    dureza_sha = BooleanField('Análise de dureza (SH A)')
    id_ligas = BooleanField('ID Ligas')
    dureza_tt = BooleanField('Análise dureza tratamento térmico')
    ranhura = BooleanField('Análise de ranhura (MSS-SP 6)')
    fios18_21 = BooleanField('Análise 18 fios por cm')
    rugosidade_acabamento = BooleanField(
        'Análise de rugosidade e acabamento')
    rpnc = StringField(
        'Nº RPNC', filters=[lambda x: (x or '').strip() or None])
    pecas_aprovadas = IntegerField('Peças aprovadas', validators=[NumberRange(min=0),
                                                                  InputRequired()])
    pecas_reprovadas = IntegerField('Peças reprovadas', default=0, validators=[NumberRange(min=0),
                                                                               InputRequired()])
    instrumentos = FieldList(FormField(InstrumentoMedicaoForm), min_entries=0)
    responsavel = StringField(
        'Inspetor', default=lambda: session.get('usuario'))
    enviar = SubmitField('Adicionar recebimento')

    def validate_qt_total(self, field):
        if field.data is None:
            raise ValidationError(
                'Quantidade total está recebendo um valor nulo')
        elif self.pecas_aprovadas.data is None:
            raise ValidationError(
                'Peças aprovadas está recebendo um valor nulo')
        elif self.pecas_reprovadas.data is None:
            raise ValidationError(
                'Peças reprovadas está recebendo um valor nulo')

        if self.pecas_reprovadas.data + self.pecas_aprovadas.data != self.qt_total.data:
            raise ValidationError(
                f'A quantidade total ({field.data}) está diferente da soma entre peças aprovadas ({self.pecas_aprovadas.data}) e peças reprovadas ({self.pecas_reprovadas.data})')

    def validate_corridas(self, field):
        if self.qt_total.data is None:
            return
        soma = 0
        for entrada in field:
            if entrada.qtd_corrida.data is None:
                return
            soma += entrada.qtd_corrida.data
        if soma != self.qt_total.data:
            raise ValidationError(
                f'A soma das corridas ({soma}) é diferente da quantidade total ({self.qt_total.data}).')
