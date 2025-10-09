/** @odoo-module **/

import paymentForm from '@payment/js/payment_form';

paymentForm.include({
    /**
     * Set whether we are paying an installment before submitting.
     *
     * @override method from payment.payment_form
     * @private
     * @param {Event} ev
     * @returns {void}
     */
    async _submitForm(ev) {
        const checkbox = document.querySelector('input[name="checkbox_use_advance"]').checked;
        if (checkbox){
            this.paymentContext['auto_invoice']=checkbox
        }
        await this._super(...arguments);
    },

    /**
     * Add params used by the donation snippet for the RPC to the transaction route.
     *
     * @override method from @payment/js/payment_form
     * @private
     * @return {object} The extended transaction route params.
     */
    prepareTransactionRouteParams() {
        console.log('CAMBIO DE ATRIBUTOSSSSSSSSSSSSSSSSS')
        const transactionRouteParams = this._super(...arguments);
        transactionRouteParams['Valor'] = 'Extra';
        return transactionRouteParams;
    },



});
