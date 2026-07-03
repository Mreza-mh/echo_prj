<?php

namespace App\Models;

use MongoDB\Laravel\Eloquent\Model;

class VitalReading extends Model
{
    protected $connection = 'mongodb';
    protected $collection = 'vital_readings';

    protected $fillable = [
        'patient_id',
        'session_id',
        'heart_rate',
        'valid_hr',
        'device_id',
    ];

    protected $casts = [
        'patient_id' => 'integer',
        'heart_rate' => 'integer',
        'valid_hr' => 'boolean',
    ];
}
