// Componente Angular com mascara que so' aceita digitos.
import { Component } from '@angular/core';

@Component({
  selector: 'app-cnpj-input',
  template: `<input [mask]="cnpjMask" formControlName="cnpj" />`,
})
export class CnpjInputComponent {
  // 6. mascara so' de digitos: bloqueia as letras do novo CNPJ
  cnpjMask = '00.000.000/0000-00';

  // 7. validacao no front com regex numerica
  isCnpjValid(value: string): boolean {
    return /^[0-9]{2}\.[0-9]{3}\.[0-9]{3}\/[0-9]{4}-[0-9]{2}$/.test(value);
  }
}
