<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;

class Staff extends Model
{
    protected $table = 'staffs';

    protected $fillable = [
        'user_id', 'expertise_id' ,'schedule'
    ];
    protected $casts = [
        'schedule' => 'array', // JSON cast
    ];

    public function user(): BelongsTo
    {
        return $this->belongsTo(User::class);
    }

    public function expertise(): BelongsTo
    {
        return $this->belongsTo(Expertise::class);
    }

    public function appointments(): HasMany
    {
        return $this->hasMany(Appointment::class, 'staff_id');
    }
}

