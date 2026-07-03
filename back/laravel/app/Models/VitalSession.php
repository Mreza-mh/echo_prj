<?php

namespace App\Models;

use MongoDB\Laravel\Eloquent\Model;

class VitalSession extends Model
{
    protected $connection = 'mongodb';
    protected $collection = 'vital_sessions';

    protected $fillable = [
        'patient_id',
        'device_id',
        'status',
        'started_by',
    ];

    protected $casts = [
        'patient_id' => 'integer',
        'started_by' => 'integer',
    ];
}
