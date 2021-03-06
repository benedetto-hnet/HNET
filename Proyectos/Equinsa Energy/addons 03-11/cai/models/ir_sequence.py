# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import Warning


class ir_sequence(models.Model):
    _inherit = "ir.sequence"

    fiscal_regime = fields.One2many('dei.fiscal_regime', 'sequence')

    start_date = fields.Date('Start Date')
    expiration_date = fields.Date('Expiration Date', compute="get_expiration_date")
    min_value = fields.Integer('min value', compute="get_min_value")
    max_value = fields.Integer('max value', compute="get_max_value")
    dis_min_value = fields.Char('min number', readonly=True, compute='display_min_value')
    dis_max_value = fields.Char('max number', readonly=True, compute='display_max_value')

    percentage_alert = fields.Float('percentage alert', default=80)
    percentage = fields.Float('percentage', compute='compute_percentage')

    l_prefix = fields.Char('prefix', related='prefix')
    l_padding = fields.Integer('Number padding', related='padding')
    l_number_next_actual = fields.Integer('Next Number', related='number_next_actual')

    @api.model
    def create(self, values):
        new_id = super(ir_sequence, self).create(values)
        self.validar()
        return new_id

    def write(self, values):
        write_id = super(ir_sequence, self).write(values)
        self.validar()
        return write_id

    @api.depends('fiscal_regime')
    def get_expiration_date(self):
        self.ensure_one()
        if self.fiscal_regime:
            for regime in self.fiscal_regime:
                if regime.selected and regime.cai.expiration_date:
                    self.expiration_date = regime.cai.expiration_date
                else:
                    self.expiration_date = None
        else:
            self.expiration_date = None

    @api.depends('fiscal_regime')
    def get_min_value(self):
        self.ensure_one()
        if self.fiscal_regime:
            for regime in self.fiscal_regime:
                if regime.selected and regime.desde:
                    self.min_value = regime.desde
                else:
                    self.min_value = 0
        else:
            self.min_value = 0

    @api.depends('fiscal_regime')
    def get_max_value(self):
        self.ensure_one()
        if self.fiscal_regime:
            for regime in self.fiscal_regime:
                if regime.selected and regime.hasta:
                    self.max_value = regime.hasta
                else:
                    self.max_value = 0
        else:
            self.max_value = 0

    @api.depends('min_value')
    def display_min_value(self):
        if self.prefix:
            # rellenar con ceros hasta el numero inicial con el padding especificado
            start_number_filled = str(self.min_value)
            for relleno in range(len(str(self.min_value)), self.padding):
                start_number_filled = '0' + start_number_filled
            self.dis_min_value = self.prefix + str(start_number_filled)

    @api.depends('max_value')
    def display_max_value(self):
        if self.prefix:
            # rellenar con ceros hasta el numero final con el padding especificado
            final_number = self.max_value
            final_number_filled = str(self.max_value)
            for relleno in range(len(str(final_number)), self.padding):
                final_number_filled = '0' + final_number_filled
            self.dis_max_value = self.prefix + str(final_number_filled)

    @api.depends('number_next')
    def compute_percentage(self):
        self.ensure_one()
        numerador = self.number_next_actual - self.min_value
        denominador = self.max_value - self.min_value
        if denominador > 0:
            division = (self.number_next_actual - self.min_value) / (self.max_value - self.min_value)
            self.percentage = (division * 100) - 1
        else:
            self.percentage = 0

    def validar(self):
        """ Verify unique cai in sequence """
        already_in_list = []
        for fiscal_line in self.fiscal_regime:
            if fiscal_line.cai.name in already_in_list:
                raise Warning(_(' %s this cai is already in use ')
                              % (fiscal_line.cai.name))
            already_in_list.append(fiscal_line.cai.name)
        """ No overlap """
        for fiscal_line in self.fiscal_regime:
            for fiscal_line_compare in self.fiscal_regime:
                if fiscal_line.desde > fiscal_line_compare.desde and fiscal_line.desde < fiscal_line_compare.hasta:
                    raise Warning(_('%s to %s fiscal line overlaps ') % (fiscal_line.desde, fiscal_line.hasta))
                if fiscal_line.hasta > fiscal_line_compare.desde and fiscal_line.hasta < fiscal_line_compare.hasta:
                    raise Warning(_('%s to %s fiscal line overlaps ') % (fiscal_line.desde, fiscal_line.hasta))
        """ desde < hasta """
        for fiscal_line in self.fiscal_regime:
            if fiscal_line.desde > fiscal_line.hasta:
                raise Warning(_('min_value %s to max_value %s') % (fiscal_line.desde, fiscal_line.hasta))

    def _next(self, **kw):
        self.check_limits()
        return super(ir_sequence, self)._next()

    def check_limits(self):
        """ Verificar si la secuencia tiene regimenes fiscales """
        # No generar numeros si no hay secuencias activadas
        if self.fiscal_regime:
            flag_any_active = False
            for regimen in self.fiscal_regime:
                if regimen.selected:
                    flag_any_active = True
                    break

            if not flag_any_active:
                raise Warning(_('La secuencia no tiene ningun regimen seleccionado '))

        else:
            # si no hay regimen fiscal agregado a esta secuencia no es necesario validar hacer mas validaciones
            return True

        """ Alerta de que restan pocos numeros en la secuencia """
        if self.percentage and self.percentage_alert:
            if self.percentage > self.percentage_alert:
                restantes = (self.max_value - self.number_next) + 1
        """Error Se terminaron los numeros de la secuencia seleccionada"""
        if self.max_value:
            this_number = self.number_next_actual - 1
            if this_number > self.max_value:
                raise Warning(_('you have no more numbers for this sequence '
                                'this number is %s '
                                'your limit is %s numbers ')
                              % (this_number, self.max_value))

        """Error La fecha de la factura debe ser menor """
        return True
