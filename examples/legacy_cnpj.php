<?php
// Arquivo de exemplo com varios pontos que QUEBRAM no CNPJ alfanumerico.

class FornecedorValidator
{
    // 1. regex numerica: rejeita letras
    public function isValid(string $cnpj): bool
    {
        return preg_match('/^\d{14}$/', $cnpj) === 1;
    }

    // 2. checagem "so' digito"
    public function normalize(string $cnpj): string
    {
        $clean = preg_replace('/[^0-9]/', '', $cnpj);
        if (!ctype_digit($clean)) {
            throw new \InvalidArgumentException('CNPJ invalido');
        }
        return $clean;
    }

    // 3. cast para inteiro: corrompe silenciosamente
    public function toKey(string $cnpj): int
    {
        return intval(preg_replace('/\D/', '', $cnpj));
    }

    // 4. CNPJ de terceiro hardcoded — provavelmente NAO deve mudar
    const FORNECEDOR_PADRAO = '12.345.678/0001-90';
}
