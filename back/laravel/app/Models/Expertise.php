<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\HasMany;

class Expertise extends Model
{
    protected $fillable = ['title'];

    public function staffs(): HasMany
    {
        return $this->hasMany(Staff::class);
    }
}

