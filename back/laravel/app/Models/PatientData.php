<?php

namespace App\Models;

use MongoDB\Laravel\Eloquent\Model;

class PatientData extends Model
{
    protected $connection = 'mongodb';
    protected $collection = 'patient_profiles';

    protected $fillable = [
        'user_id',
        'age',
        'gender',
        'sex',
        'height',
        'weight',
        'ap_hi',
        'ap_lo',
        'cholesterol',
        'gluc',
        'smoke',
        'alco',
        'active',
        'cp',
        'trestbps',
        'chol',
        'fbs',
        'restecg',
        'thalach',
        'exang',
        'oldpeak',
        'slope',
        'ca',
        'thal',
    ];

    protected $casts = [
        'user_id' => 'integer',
        'age' => 'integer',
        'gender' => 'integer',
        'sex' => 'integer',
        'height' => 'float',
        'weight' => 'float',
        'ap_hi' => 'float',
        'ap_lo' => 'float',
        'cholesterol' => 'integer',
        'gluc' => 'integer',
        'smoke' => 'integer',
        'alco' => 'integer',
        'active' => 'integer',
        'cp' => 'integer',
        'trestbps' => 'float',
        'chol' => 'float',
        'fbs' => 'integer',
        'restecg' => 'integer',
        'thalach' => 'float',
        'exang' => 'integer',
        'oldpeak' => 'float',
        'slope' => 'integer',
        'ca' => 'integer',
        'thal' => 'integer',
    ];
}
