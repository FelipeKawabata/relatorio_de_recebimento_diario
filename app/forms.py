from flask_wtf import FlaskForm
from wtforms import StringField, Form, SubmitField, BooleanField, IntegerField, FormField, SelectField, FieldList
from wtforms.validators import DataRequired, ValidationError, NumberRange, InputRequired
from flask import session


class ListaInstrumentosForm(FlaskForm):
    nome = StringField('Nome', validators=[DataRequired()])
    descricao = StringField('Descrição')
    enviar = SubmitField('Adicionar instrumento')


class PlanoControleForm(FlaskForm):
    nome = StringField('Nome', validators=[DataRequired()])
    descricao = StringField('Descrição')


class InstrumentoMedicaoForm(Form):
    instrumento_id = SelectField('Instrumento', coerce=int)


class ConferenciaForm(FlaskForm):
    pedido = StringField('Pedido', validators=[DataRequired()])
    item = StringField('Item', validators=[DataRequired()])
    nota_fiscal = StringField('Nota Fiscal', validators=[DataRequired()])
    qt_total = IntegerField('Quantidade total', validators=[
                            NumberRange(min=1), InputRequired()])
    corrida = StringField('Corrida', validators=[DataRequired()])
    plano_controle = SelectField(
        'Plano de controle', coerce=int)
    analise_certificado = BooleanField('Análise de certificado')
    analise_visual = BooleanField('Análise visual')
    analise_ident_rastreab = BooleanField(
        'Análise de identificação e rastreabilidade')
    analise_dimensional = BooleanField('Análise dimensional')
    analise_dureza = BooleanField('Análise de dureza (SH A)')
    analise_ligas = BooleanField('ID Ligas')
    analise_dureza_tt = BooleanField('Análise dureza tratamento térmico')
    analise_ranhuras = BooleanField('Análise de ranhura (MSS-SP 6)')
    analise_18_fios = BooleanField('Análise 18 fios por cm')
    analise_rugosidade_acabamento = BooleanField(
        'Análise de rugosidade e acabamento')
    pecas_aprovadas = IntegerField('Peças aprovadas', validators=[NumberRange(min=0),
                                                                  InputRequired()])
    pecas_reprovadas = IntegerField('Peças reprovadas', default=0, validators=[NumberRange(min=0),
                                                                               InputRequired()])
    instrumentos = FieldList(FormField(InstrumentoMedicaoForm), min_entries=0)
    inspetor = StringField('Inspetor', default=lambda: session.get('usuario'))
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
