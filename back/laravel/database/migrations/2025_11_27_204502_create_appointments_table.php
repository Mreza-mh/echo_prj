<?php

use App\Enums\ReservationType;
use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    /**
     * Run the migrations.
     */
    public function up(): void
    {
        Schema::create('appointments', function (Blueprint $table) {
            $table->id();
            $table->foreignId('service_id')->constrained('services')->cascadeOnDelete();
            $table->foreignId('user_id')->constrained('users')->cascadeOnDelete();
            $table->foreignId('staff_id')->constrained('staffs')->cascadeOnDelete();

            $table->date('date_of_turn');
            $table->time('start_time');
            $table->time('end_time');

            $table->foreignId('status_id')->constrained('statuses')->cascadeOnDelete();
            $table->enum('reservation_type', ReservationType::values());
            $table->boolean('permissible_interference')->default(false);
            $table->timestamps();

            $table->index(['staff_id', 'date_of_turn']);
            $table->index(['staff_id','service_id']);


        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('appointments');
    }
};
