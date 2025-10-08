// /** @odoo-module **/
// import publicWidget from "@web/legacy/js/public/public_widget";
// import { rpc } from "@web/core/network/rpc";

// publicWidget.registry.add_attachment = publicWidget.Widget.extend({
//     selector: '.div-attached-files',
//     events: {
//         'click #checkbox_use_advance': 'RemoveAttchedFile',
//     },

//      RemoveAttchedFile: function (ev) {
//      var attachment_id = ev.target.closest('div')
//         rpc("/shop/attachments" , {
//             "attachment_id":attachment_id.id
//              }).then(function (data) {
//                 window.location.reload()
//         });
//         attachment_id.remove();
//      },
// });
/** @odoo-module **/

console.log('CHECKBOX');

import { WebsiteSale } from '@website_sale/js/website_sale';
import { rpc } from "@web/core/network/rpc";
//import VariantMixin from "@website_sale/js/sale_variant_mixin";

WebsiteSale.include({
    events: Object.assign(WebsiteSale.prototype.events, {
        'click input[name="checkbox_use_advance"]': "click_checkbox_use_advance",
    }),

    click_checkbox_use_advance: function(ev){
        var checkbox = document.querySelector('input[name="checkbox_use_advance"]').checked;
        if (checkbox){
            console.log('Verdadero');
            // rpc("/shop/add_auto_invoice_appointment" , {
            //     "checkbox":checkbox
            //      }).then(function (data) {
            //         console.log('Actualizado')
            // });
         }
        else{
            console.log('Falso');
        }        
    },


});


