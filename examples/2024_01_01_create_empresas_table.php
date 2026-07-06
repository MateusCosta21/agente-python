<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('empresas', function (Blueprint $table) {
            $table->id();
            $table->string('razao_social');
            // 5. coluna numerica para CNPJ: quebra com letras, precisa virar string
            $table->unsignedBigInteger('cnpj')->unique();
            $table->timestamps();
        });
    }
};
